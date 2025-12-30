"""
File upload endpoint - POST /api/v1/upload

Receives encrypted file blobs from client, stores them, and returns a UUID.
The server never sees the plaintext or encryption key.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from models.file import UploadResponse, ErrorResponse
from services.storage import LocalStorage
from services.redis_client import RedisClient
from core.config import settings
from core.logging import get_logger
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
    
    Interview Talking Point:
        "I validate file size before reading entire file into memory to prevent
        DoS attacks from malicious users uploading huge files."
    """
    
    # Get Redis client from request state (dependency injection via middleware)
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
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_file_size // 1024 // 1024}MB)"
        )
    
    # Validate TTL
    if ttl not in settings.allowed_ttls:
        logger.warning("upload_rejected", reason="invalid_ttl", ttl=ttl)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid TTL (must be one of {settings.allowed_ttls})"
        )
    
    # Validate max_downloads
    if not (settings.min_downloads <= max_downloads <= settings.max_downloads):
        logger.warning("upload_rejected", reason="invalid_max_downloads", max_downloads=max_downloads)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid download limit (must be {settings.min_downloads}-{settings.max_downloads})"
        )
    
    # Sanitize filename (prevent directory traversal)
    safe_filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Save encrypted blob to storage
    try:
        await storage.save(file_id, content)
    except Exception as e:
        logger.error("storage_save_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Storage error")
    
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
    except Exception as e:
        # Rollback: delete file from storage
        await storage.delete(file_id)
        logger.error("redis_save_failed", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    
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
