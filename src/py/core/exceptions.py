"""
Custom exception classes for DeadDrop application.

This module defines a hierarchy of custom exceptions that provide:
- Better error categorization and handling
- Consistent error responses to clients
- Improved logging and debugging
- Scalability for future error types
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class DeadDropException(Exception):
    """
    Base exception class for all DeadDrop-specific errors.

    All custom exceptions should inherit from this class to allow
    for centralized exception handling and monitoring.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        internal_message: Optional[str] = None
    ):
        """
        Initialize the exception.

        Args:
            message: User-facing error message
            details: Additional context for logging (not sent to client)
            internal_message: Internal error details (for logging only)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.internal_message = internal_message or message


# Storage-related exceptions
class StorageException(DeadDropException):
    """Base exception for storage-related errors."""
    pass


class StorageWriteError(StorageException):
    """Raised when writing to storage fails."""
    pass


class StorageReadError(StorageException):
    """Raised when reading from storage fails."""
    pass


class StorageDeleteError(StorageException):
    """Raised when deleting from storage fails."""
    pass


class StorageQuotaExceeded(StorageException):
    """Raised when storage quota is exceeded."""
    pass


# Database/Redis-related exceptions
class DatabaseException(DeadDropException):
    """Base exception for database-related errors."""
    pass


class RedisConnectionError(DatabaseException):
    """Raised when Redis connection fails."""
    pass


class RedisTimeoutError(DatabaseException):
    """Raised when Redis operation times out."""
    pass


class RedisOperationError(DatabaseException):
    """Raised when a Redis operation fails."""
    pass


# File-related exceptions
class FileException(DeadDropException):
    """Base exception for file-related errors."""
    pass


class FileNotFoundError(FileException):
    """Raised when a requested file is not found or expired."""

    def __init__(self, file_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="File not found or has expired",
            details={**(details or {}), "file_id": file_id}
        )
        self.file_id = file_id


class FileSizeLimitExceeded(FileException):
    """Raised when uploaded file exceeds size limit."""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"File size ({size} bytes) exceeds maximum allowed size ({max_size} bytes)",
            details={"size": size, "max_size": max_size}
        )
        self.size = size
        self.max_size = max_size


class FileDownloadLimitReached(FileException):
    """Raised when file has reached its download limit."""

    def __init__(self, file_id: str, max_downloads: int):
        super().__init__(
            message="File has reached its download limit",
            details={"file_id": file_id, "max_downloads": max_downloads}
        )
        self.file_id = file_id
        self.max_downloads = max_downloads


# Validation exceptions
class ValidationException(DeadDropException):
    """Base exception for validation errors."""
    pass


class InvalidTTLError(ValidationException):
    """Raised when TTL value is invalid."""

    def __init__(self, ttl: int, allowed_values: list):
        super().__init__(
            message=f"Invalid TTL: {ttl}. Allowed values: {allowed_values}",
            details={"ttl": ttl, "allowed_values": allowed_values}
        )
        self.ttl = ttl
        self.allowed_values = allowed_values


class InvalidDownloadLimitError(ValidationException):
    """Raised when download limit is invalid."""

    def __init__(self, limit: int, min_limit: int, max_limit: int):
        super().__init__(
            message=f"Invalid download limit: {limit}. Must be between {min_limit} and {max_limit}",
            details={"limit": limit, "min": min_limit, "max": max_limit}
        )
        self.limit = limit
        self.min_limit = min_limit
        self.max_limit = max_limit


# Rate limiting exceptions
class RateLimitException(DeadDropException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded. Please try again in {retry_after} seconds",
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


# Circuit breaker exceptions
class CircuitBreakerOpenError(DeadDropException):
    """Raised when circuit breaker is open (service unavailable)."""

    def __init__(self, service: str, retry_after: int):
        super().__init__(
            message=f"Service temporarily unavailable. Please try again in {retry_after} seconds",
            details={"service": service, "retry_after": retry_after}
        )
        self.service = service
        self.retry_after = retry_after


def exception_to_http_exception(exc: DeadDropException) -> HTTPException:
    """
    Convert a DeadDrop exception to an HTTPException.

    This function maps custom exceptions to appropriate HTTP status codes
    and user-facing error messages while preserving internal details for logging.

    Args:
        exc: The DeadDrop exception to convert

    Returns:
        HTTPException with appropriate status code and message
    """
    # Map exception types to HTTP status codes
    status_map = {
        FileNotFoundError: status.HTTP_404_NOT_FOUND,
        FileSizeLimitExceeded: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        FileDownloadLimitReached: status.HTTP_410_GONE,
        InvalidTTLError: status.HTTP_400_BAD_REQUEST,
        InvalidDownloadLimitError: status.HTTP_400_BAD_REQUEST,
        ValidationException: status.HTTP_400_BAD_REQUEST,
        RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
        CircuitBreakerOpenError: status.HTTP_503_SERVICE_UNAVAILABLE,
        StorageQuotaExceeded: status.HTTP_507_INSUFFICIENT_STORAGE,
        RedisConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
        RedisTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
        DatabaseException: status.HTTP_503_SERVICE_UNAVAILABLE,
        StorageException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    # Find the most specific status code for this exception type
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exc_type, code in status_map.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    # Add retry-after header for rate limiting and circuit breaker
    headers = {}
    if isinstance(exc, (RateLimitException, CircuitBreakerOpenError)):
        headers["Retry-After"] = str(exc.retry_after)

    return HTTPException(
        status_code=status_code,
        detail={"error": exc.message},
        headers=headers if headers else None
    )
