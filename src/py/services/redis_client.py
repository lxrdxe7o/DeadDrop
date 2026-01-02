"""
Redis client for file metadata and TTL management.

Handles atomic operations for download counting and metadata storage.
Includes timeout handling, retry logic, and comprehensive error handling.
"""

import asyncio
from functools import wraps
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from typing import Optional, TypeVar, Callable, Any
from models.file import FileMetadata
from core.exceptions import (
    RedisConnectionError,
    RedisTimeoutError,
    RedisOperationError
)

T = TypeVar('T')


def retry_on_failure(max_retries: int = 3, base_delay: float = 0.1):
    """
    Decorator to retry Redis operations on transient failures.

    Uses exponential backoff: delay * (2 ** attempt)

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (exponentially increased)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    continue
                except RedisError as e:
                    # Non-transient errors should not be retried
                    raise RedisOperationError(
                        message="Redis operation failed",
                        details={"error": str(e), "operation": func.__name__},
                        internal_message=str(e)
                    ) from e

            # All retries exhausted
            if isinstance(last_exception, TimeoutError):
                raise RedisTimeoutError(
                    message="Redis operation timed out after multiple retries",
                    details={"attempts": max_retries + 1, "operation": func.__name__}
                ) from last_exception
            else:
                raise RedisConnectionError(
                    message="Failed to connect to Redis after multiple retries",
                    details={"attempts": max_retries + 1, "operation": func.__name__}
                ) from last_exception

        return wrapper
    return decorator


class RedisClient:
    """
    Redis connection manager with file metadata operations.

    Features:
    - Connection pooling for better performance
    - Timeout handling for all operations
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Atomic download counter increments
    """

    def __init__(
        self,
        redis_url: str,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0
    ):
        """
        Initialize Redis client with connection pooling.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout for operations (seconds)
            socket_connect_timeout: Socket connection timeout (seconds)
        """
        self.redis: Optional[Redis] = None
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self._pool: Optional[ConnectionPool] = None
    
    async def connect(self) -> None:
        """
        Establish Redis connection with pooling.

        Called during application startup.
        """
        try:
            # Create connection pool for better resource management
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=True,
                encoding="utf-8"
            )

            self.redis = Redis(connection_pool=self._pool)

            # Test connection
            await asyncio.wait_for(self.redis.ping(), timeout=self.socket_connect_timeout)

        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Redis connection timeout",
                details={"url": self.redis_url}
            ) from e
        except ConnectionError as e:
            raise RedisConnectionError(
                message="Failed to connect to Redis",
                details={"url": self.redis_url}
            ) from e
        except Exception as e:
            raise RedisConnectionError(
                message="Unexpected error connecting to Redis",
                details={"error": str(e)}
            ) from e
    
    async def disconnect(self) -> None:
        """
        Close Redis connection and pool gracefully.

        Called during application shutdown.
        """
        if self.redis:
            await self.redis.close()
        if self._pool:
            await self._pool.disconnect()
    
    def _key(self, file_id: str) -> str:
        """
        Generate Redis key for file ID.
        
        Args:
            file_id: File identifier
        
        Returns:
            Redis key in format "file:{uuid}"
        """
        return f"file:{file_id}"
    
    @retry_on_failure(max_retries=3, base_delay=0.1)
    async def save_metadata(
        self,
        file_id: str,
        metadata: FileMetadata,
        ttl: int
    ) -> None:
        """
        Save file metadata with TTL.

        Args:
            file_id: File identifier
            metadata: File metadata object
            ttl: Time to live in seconds

        Raises:
            RedisTimeoutError: If operation times out
            RedisConnectionError: If connection fails
            RedisOperationError: If Redis operation fails

        Note:
            Uses Redis EXPIRE for automatic cleanup - no cron jobs needed!
            Includes retry logic for transient failures.
        """
        key = self._key(file_id)
        try:
            await asyncio.wait_for(
                self.redis.set(
                    key,
                    metadata.model_dump_json(),
                    ex=ttl  # Automatic expiration
                ),
                timeout=self.socket_timeout
            )
        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Timeout saving metadata",
                details={"file_id": file_id}
            ) from e
    
    @retry_on_failure(max_retries=3, base_delay=0.1)
    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """
        Retrieve file metadata.

        Args:
            file_id: File identifier

        Returns:
            FileMetadata object if found, None if expired/deleted

        Raises:
            RedisTimeoutError: If operation times out
            RedisConnectionError: If connection fails
            RedisOperationError: If Redis operation fails
        """
        key = self._key(file_id)
        try:
            data = await asyncio.wait_for(
                self.redis.get(key),
                timeout=self.socket_timeout
            )
            if data:
                return FileMetadata.model_validate_json(data)
            return None
        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Timeout retrieving metadata",
                details={"file_id": file_id}
            ) from e
    
    @retry_on_failure(max_retries=3, base_delay=0.1)
    async def increment_downloads(self, file_id: str) -> int:
        """
        Atomically increment download counter.

        Args:
            file_id: File identifier

        Returns:
            New download count, or -1 if file doesn't exist

        Raises:
            RedisTimeoutError: If operation times out
            RedisConnectionError: If connection fails
            RedisOperationError: If Redis operation fails

        Note:
            Updates metadata in-place while preserving TTL.
            Includes retry logic for transient failures.
        """
        key = self._key(file_id)
        metadata = await self.get_metadata(file_id)
        if not metadata:
            return -1

        # Increment counter
        metadata.downloads += 1

        try:
            # Preserve existing TTL
            ttl = await asyncio.wait_for(
                self.redis.ttl(key),
                timeout=self.socket_timeout
            )
            if ttl <= 0:
                # File expired between get and increment (race condition)
                return -1

            # Update metadata with preserved TTL
            await asyncio.wait_for(
                self.redis.set(key, metadata.model_dump_json(), ex=ttl),
                timeout=self.socket_timeout
            )
            return metadata.downloads

        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Timeout incrementing download counter",
                details={"file_id": file_id}
            ) from e
    
    @retry_on_failure(max_retries=3, base_delay=0.1)
    async def delete_metadata(self, file_id: str) -> None:
        """
        Delete file metadata.

        Args:
            file_id: File identifier

        Raises:
            RedisTimeoutError: If operation times out
            RedisConnectionError: If connection fails
            RedisOperationError: If Redis operation fails

        Note:
            Called during cleanup after download limit reached.
            Includes retry logic for transient failures.
        """
        try:
            await asyncio.wait_for(
                self.redis.delete(self._key(file_id)),
                timeout=self.socket_timeout
            )
        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Timeout deleting metadata",
                details={"file_id": file_id}
            ) from e
    
    @retry_on_failure(max_retries=3, base_delay=0.1)
    async def get_ttl(self, file_id: str) -> int:
        """
        Get remaining TTL for a file.

        Args:
            file_id: File identifier

        Returns:
            Seconds until expiration, or -2 if key doesn't exist

        Raises:
            RedisTimeoutError: If operation times out
            RedisConnectionError: If connection fails
            RedisOperationError: If Redis operation fails
        """
        try:
            return await asyncio.wait_for(
                self.redis.ttl(self._key(file_id)),
                timeout=self.socket_timeout
            )
        except asyncio.TimeoutError as e:
            raise RedisTimeoutError(
                message="Timeout getting TTL",
                details={"file_id": file_id}
            ) from e

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is responsive, False otherwise
        """
        try:
            await asyncio.wait_for(self.redis.ping(), timeout=1.0)
            return True
        except Exception:
            return False
