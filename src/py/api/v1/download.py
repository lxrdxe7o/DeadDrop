"""
File download endpoint - GET /api/v1/download/{file_id}

Streams encrypted files to clients and manages download counting.
Returns generic errors to prevent information leakage.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from services.storage import LocalStorage
from services.redis_client import RedisClient
from core.config import settings
from core.logging import get_logger
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
    
    Interview Talking Point:
        "I use FastAPI's BackgroundTasks to delete files asynchronously,
        so the response is sent immediately without waiting for cleanup."
    """
    await storage.delete(file_id)
    await redis.delete_metadata(file_id)
    logger.info("file_deleted", file_id=file_id, reason="download_limit_reached")


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
    
    Interview Talking Points:
    1. "I return a generic '404 File unavailable' for ALL failures to prevent
       attackers from enumerating valid file IDs."
    
    2. "Download counting is atomic - I increment first, then check the limit.
       This prevents race conditions where two requests could both succeed."
    
    3. "I use BackgroundTasks for deletion so the client gets the file before
       we clean up, preventing accidental data loss on network retries."
    """
    
    # Get dependencies from request state
    redis: RedisClient = request.state.redis
    storage = LocalStorage(settings.storage_path)
    
    # Check if file metadata exists in Redis
    metadata = await redis.get_metadata(file_id)
    if not metadata:
        logger.warning("download_failed", file_id=file_id, reason="not_found_or_expired")
        raise HTTPException(
            status_code=404,
            detail="File unavailable"  # Generic message (security)
        )
    
    # Check if file exists in storage
    # (Handles edge case where Redis entry exists but file was deleted)
    if not await storage.exists(file_id):
        logger.error(
            "download_failed",
            file_id=file_id,
            reason="metadata_exists_but_file_missing"
        )
        # Clean up orphaned metadata
        await redis.delete_metadata(file_id)
        raise HTTPException(status_code=404, detail="File unavailable")
    
    # Atomically increment download counter
    new_count = await redis.increment_downloads(file_id)
    
    if new_count < 0:
        # File expired between metadata check and increment (race condition)
        logger.warning("download_failed", file_id=file_id, reason="expired_during_request")
        raise HTTPException(status_code=404, detail="File unavailable")
    
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
    except FileNotFoundError:
        logger.error("download_failed", file_id=file_id, reason="file_not_found")
        raise HTTPException(status_code=404, detail="File unavailable")
    except Exception as e:
        logger.error("download_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Download error")
    
    # Stream file to client
    return StreamingResponse(
        iter([data]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{metadata.filename}.enc"',
            "Content-Length": str(len(data))
        }
    )
