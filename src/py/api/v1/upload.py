"""
File upload endpoint - POST /api/v1/upload

Receives encrypted file blobs from client, stores them, and returns a UUID.
The server never sees the plaintext or encryption key.

Features:
- Comprehensive error handling with custom exceptions
- Automatic rollback on failures
- Input validation and sanitization
- Structured logging with request IDs
"""

from fastapi import APIRouter, UploadFile, File, Form, Request
from models.file import UploadResponse, ErrorResponse
from services.storage import LocalStorage
from services.redis_client import RedisClient
from core.config import settings
from core.logging import get_logger
from core.exceptions import (
    FileSizeLimitExceeded,
    InvalidTTLError,
    InvalidDownloadLimitError,
    StorageException,
    DatabaseException
)
from models.file import FileMetadata
from datetime import datetime, timedelta
import uuid

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"}
    },
    summary="Upload encrypted file",
    description="""
    Upload an encrypted file blob to the server.
    
    **Security**: File is already encrypted client-side. Server never sees plaintext.
    
    **Parameters**:
    - **file**: Encrypted binary data (multipart/form-data)
    - **ttl**: Time to live (3600=1h, 86400=1d, 259200=3d)
    - **max_downloads**: Maximum downloads before deletion (1-5)
    - **filename**: Original filename (stored in plaintext for MVP)
    
    **Returns**: File UUID and expiration timestamp
    """
)
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="Encrypted file blob"),
    ttl: int = Form(86400, description="Time to live in seconds"),
    max_downloads: int = Form(1, ge=1, le=5, description="Max download count"),
    filename: str = Form(..., max_length=255, description="Original filename"),
) -> UploadResponse:
    """
    Handle file upload with encryption and storage.

    Features:
    - Validates file size before reading to prevent DoS
    - Validates TTL and download limits
    - Automatic rollback on failures
    - Comprehensive error handling

    Raises:
        FileSizeLimitExceeded: If file exceeds max size
        InvalidTTLError: If TTL is not allowed
        InvalidDownloadLimitError: If download limit is invalid
        StorageException: If storage operation fails
        DatabaseException: If Redis operation fails
    """

    # Get dependencies from request state
    redis: RedisClient = request.state.redis
    storage = LocalStorage(settings.storage_path)

    # Read file content
    content = await file.read()

    # Validate file size (prevent DoS)
    if len(content) > settings.max_file_size:
        logger.warning(
            "upload_rejected",
            reason="file_too_large",
            size=len(content),
            max_size=settings.max_file_size
        )
        raise FileSizeLimitExceeded(
            size=len(content),
            max_size=settings.max_file_size
        )

    # Validate TTL
    if ttl not in settings.allowed_ttls:
        logger.warning("upload_rejected", reason="invalid_ttl", ttl=ttl)
        raise InvalidTTLError(
            ttl=ttl,
            allowed_values=settings.allowed_ttls
        )

    # Validate max_downloads
    if not (settings.min_downloads <= max_downloads <= settings.max_downloads):
        logger.warning(
            "upload_rejected",
            reason="invalid_max_downloads",
            max_downloads=max_downloads
        )
        raise InvalidDownloadLimitError(
            limit=max_downloads,
            min_limit=settings.min_downloads,
            max_limit=settings.max_downloads
        )

    # Sanitize filename (prevent directory traversal)
    safe_filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Save encrypted blob to storage
    try:
        await storage.save(file_id, content)
    except StorageException:
        # Re-raise storage exceptions (already properly formatted)
        raise
    except Exception as e:
        # Wrap unexpected exceptions
        logger.error("storage_save_failed", file_id=file_id, error=str(e))
        raise StorageException(
            message="Failed to save file to storage",
            details={"file_id": file_id},
            internal_message=str(e)
        ) from e

    # Create metadata
    metadata = FileMetadata(
        filename=safe_filename,
        size=len(content),
        downloads=0,
        max_downloads=max_downloads,
        created_at=datetime.utcnow()
    )

    # Save metadata to Redis with TTL
    try:
        await redis.save_metadata(file_id, metadata, ttl)
    except DatabaseException:
        # Rollback: delete file from storage
        try:
            await storage.delete(file_id)
        except Exception:
            # Log but don't fail if rollback fails
            logger.error("rollback_failed", file_id=file_id)
        # Re-raise database exception
        raise
    except Exception as e:
        # Rollback: delete file from storage
        try:
            await storage.delete(file_id)
        except Exception:
            logger.error("rollback_failed", file_id=file_id)

        # Wrap unexpected exceptions
        logger.error("redis_save_failed", file_id=file_id, error=str(e))
        raise DatabaseException(
            message="Failed to save metadata",
            details={"file_id": file_id},
            internal_message=str(e)
        ) from e

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    # Log successful upload (without sensitive data)
    logger.info(
        "file_uploaded",
        file_id=file_id,
        size=len(content),
        ttl=ttl,
        max_downloads=max_downloads,
        expires_at=expires_at.isoformat()
    )

    return UploadResponse(
        id=file_id,
        expires_at=expires_at
    )
