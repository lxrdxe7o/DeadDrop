"""
Pydantic models for file metadata and API request/response schemas.

All models use Pydantic v2 with strict type validation.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal


class FileMetadata(BaseModel):
    """
    File metadata stored in Redis.
    
    Security Note: Filename is stored in plaintext for MVP.
    Future enhancement: Encrypt metadata client-side.
    """
    filename: str = Field(..., description="Original filename (plaintext)")
    size: int = Field(..., ge=1, description="File size in bytes")
    downloads: int = Field(default=0, ge=0, description="Current download count")
    max_downloads: int = Field(..., ge=1, le=5, description="Maximum allowed downloads")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "size": 1048576,
                "downloads": 0,
                "max_downloads": 1,
                "created_at": "2025-12-31T10:00:00Z"
            }
        }


class UploadRequest(BaseModel):
    """
    Validation schema for file upload requests.
    
    Note: This is used with Form data, not JSON body.
    """
    ttl: Literal[3600, 86400, 259200] = Field(
        default=86400,
        description="Time to live in seconds (3600=1h, 86400=1d, 259200=3d)"
    )
    max_downloads: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum number of downloads before auto-deletion"
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename"
    )
    
    @field_validator('filename')
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        """Remove potentially dangerous characters from filename."""
        # Remove path separators and null bytes
        return v.replace('/', '_').replace('\\', '_').replace('\x00', '')


class UploadResponse(BaseModel):
    """Success response for file upload."""
    id: str = Field(..., description="Unique file identifier (UUID)")
    expires_at: datetime = Field(..., description="Expiration timestamp (UTC)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "expires_at": "2025-12-31T22:00:00Z"
            }
        }


class FileInfo(BaseModel):
    """
    File information response (optional endpoint for UX enhancement).
    
    Allows frontend to display "X downloads remaining" without downloading.
    """
    downloads_remaining: int = Field(..., ge=0, description="Remaining downloads")
    expires_in: int = Field(..., ge=0, description="Seconds until expiration")
    size: int = Field(..., description="File size in bytes")


class ErrorResponse(BaseModel):
    """Generic error response (prevents information leakage)."""
    error: str = Field(..., description="Error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "File unavailable"
            }
        }
