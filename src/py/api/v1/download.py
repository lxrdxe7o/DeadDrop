"""
File download endpoint - GET /api/v1/download/{file_id}

Streams encrypted files to clients and manages download counting.
Returns generic errors to prevent information leakage.

Features:
- Atomic download counting
- Background cleanup tasks
- Comprehensive error handling
- Race condition prevention
"""

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from services.storage import LocalStorage
from services.redis_client import RedisClient
from core.config import settings
from core.logging import get_logger
from core.exceptions import (
    FileNotFoundError as DeadDropFileNotFoundError,
    FileDownloadLimitReached,
    StorageException,
    DatabaseException
)
from models.file import ErrorResponse

router = APIRouter()
logger = get_logger(__name__)


async def cleanup_file(file_id: str, redis: RedisClient, storage: LocalStorage) -> None:
    """
    Background task to delete file and metadata after download limit reached.

    Args:
        file_id: File identifier
        redis: Redis client instance
        storage: Storage backend instance

    Note:
        Errors in background tasks are logged but don't affect the response.
        FastAPI's BackgroundTasks ensures this runs after the response is sent.
    """
    try:
        await storage.delete(file_id)
        await redis.delete_metadata(file_id)
        logger.info("file_deleted", file_id=file_id, reason="download_limit_reached")
    except Exception as e:
        # Log errors but don't fail (already sent response to client)
        logger.error(
            "cleanup_failed",
            file_id=file_id,
            error=str(e),
            error_type=e.__class__.__name__
        )


@router.get(
    "/download/{file_id}",
    responses={
        200: {"description": "Encrypted file blob", "content": {"application/octet-stream": {}}},
        404: {"model": ErrorResponse, "description": "File unavailable"}
    },
    summary="Download encrypted file",
    description="""
    Download an encrypted file blob.
    
    **Security Features**:
    - Generic error messages (prevents enumeration attacks)
    - Atomic download counting (prevents race conditions)
    - Automatic cleanup after download limit reached
    
    **Note**: The encryption key is NEVER sent to the server (it's in the URL fragment).
    """
)
async def download_file(
    file_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """
    Handle file download with download counting and cleanup.

    Security features:
    - Generic error messages prevent file ID enumeration
    - Atomic download counting prevents race conditions
    - Background cleanup ensures data is sent before deletion

    Raises:
        FileNotFoundError: If file doesn't exist or has expired
        DatabaseException: If Redis operation fails
        StorageException: If storage operation fails
    """

    # Get dependencies from request state
    redis: RedisClient = request.state.redis
    storage = LocalStorage(settings.storage_path)

    # Check if file metadata exists in Redis
    try:
        metadata = await redis.get_metadata(file_id)
    except DatabaseException as e:
        # Database errors are logged by the exception handler
        # Return generic error to client
        logger.error(
            "download_failed",
            file_id=file_id,
            reason="redis_error",
            error=str(e)
        )
        # Convert to FileNotFoundError for generic client response
        raise DeadDropFileNotFoundError(file_id=file_id) from e

    if not metadata:
        logger.warning("download_failed", file_id=file_id, reason="not_found_or_expired")
        raise DeadDropFileNotFoundError(file_id=file_id)

    # Check if file exists in storage
    # (Handles edge case where Redis entry exists but file was deleted)
    try:
        file_exists = await storage.exists(file_id)
    except Exception as e:
        logger.error(
            "download_failed",
            file_id=file_id,
            reason="exists_check_failed",
            error=str(e)
        )
        raise DeadDropFileNotFoundError(file_id=file_id) from e

    if not file_exists:
        logger.error(
            "download_failed",
            file_id=file_id,
            reason="metadata_exists_but_file_missing"
        )
        # Clean up orphaned metadata (best effort)
        try:
            await redis.delete_metadata(file_id)
        except Exception:
            pass  # Ignore cleanup errors
        raise DeadDropFileNotFoundError(file_id=file_id)

    # Atomically increment download counter
    try:
        new_count = await redis.increment_downloads(file_id)
    except DatabaseException as e:
        logger.error(
            "download_failed",
            file_id=file_id,
            reason="increment_failed",
            error=str(e)
        )
        raise DeadDropFileNotFoundError(file_id=file_id) from e

    if new_count < 0:
        # File expired between metadata check and increment (race condition)
        logger.warning("download_failed", file_id=file_id, reason="expired_during_request")
        raise DeadDropFileNotFoundError(file_id=file_id)

    logger.info(
        "file_downloaded",
        file_id=file_id,
        download_count=new_count,
        max_downloads=metadata.max_downloads
    )

    # Schedule deletion if download limit reached
    if new_count >= metadata.max_downloads:
        background_tasks.add_task(cleanup_file, file_id, redis, storage)
        logger.info("cleanup_scheduled", file_id=file_id, downloads=new_count)

    # Load encrypted file from storage
    try:
        data = await storage.load(file_id)
    except DeadDropFileNotFoundError:
        logger.error("download_failed", file_id=file_id, reason="file_not_found")
        raise
    except StorageException as e:
        logger.error("download_failed", file_id=file_id, error=str(e))
        # Convert to generic FileNotFoundError for client
        raise DeadDropFileNotFoundError(file_id=file_id) from e
    except Exception as e:
        logger.error("download_failed", file_id=file_id, error=str(e))
        raise StorageException(
            message="Failed to load file",
            details={"file_id": file_id},
            internal_message=str(e)
        ) from e

    # Stream file to client
    return StreamingResponse(
        iter([data]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{metadata.filename}.enc"',
            "Content-Length": str(len(data))
        }
    )
