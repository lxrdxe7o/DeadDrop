"""
Redis client for file metadata and TTL management.

Handles atomic operations for download counting and metadata storage.
"""

from redis.asyncio import Redis
from typing import Optional
from models.file import FileMetadata


class RedisClient:
    """
    Redis connection manager with file metadata operations.
    
    Uses Redis for:
    - File metadata storage (JSON)
    - Automatic TTL/expiration
    - Atomic download counter increments
    """
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
        """
        self.redis: Optional[Redis] = None
        self.redis_url = redis_url
    
    async def connect(self) -> None:
        """
        Establish Redis connection.
        
        Called during application startup.
        """
        self.redis = await Redis.from_url(
            self.redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
    
    async def disconnect(self) -> None:
        """
        Close Redis connection.
        
        Called during application shutdown.
        """
        if self.redis:
            await self.redis.close()
    
    def _key(self, file_id: str) -> str:
        """
        Generate Redis key for file ID.
        
        Args:
            file_id: File identifier
        
        Returns:
            Redis key in format "file:{uuid}"
        """
        return f"file:{file_id}"
    
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
        
        Interview Note:
            Uses Redis EXPIRE for automatic cleanup - no cron jobs needed!
        """
        key = self._key(file_id)
        await self.redis.set(
            key,
            metadata.model_dump_json(),
            ex=ttl  # Automatic expiration
        )
    
    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """
        Retrieve file metadata.
        
        Args:
            file_id: File identifier
        
        Returns:
            FileMetadata object if found, None if expired/deleted
        """
        key = self._key(file_id)
        data = await self.redis.get(key)
        if data:
            return FileMetadata.model_validate_json(data)
        return None
    
    async def increment_downloads(self, file_id: str) -> int:
        """
        Atomically increment download counter.
        
        Args:
            file_id: File identifier
        
        Returns:
            New download count, or -1 if file doesn't exist
        
        Note:
            Updates metadata in-place while preserving TTL.
        """
        key = self._key(file_id)
        metadata = await self.get_metadata(file_id)
        if not metadata:
            return -1
        
        # Increment counter
        metadata.downloads += 1
        
        # Preserve existing TTL
        ttl = await self.redis.ttl(key)
        if ttl <= 0:
            # File expired between get and increment (race condition)
            return -1
        
        # Update metadata with preserved TTL
        await self.redis.set(key, metadata.model_dump_json(), ex=ttl)
        return metadata.downloads
    
    async def delete_metadata(self, file_id: str) -> None:
        """
        Delete file metadata.
        
        Args:
            file_id: File identifier
        
        Note:
            Called during cleanup after download limit reached.
        """
        await self.redis.delete(self._key(file_id))
    
    async def get_ttl(self, file_id: str) -> int:
        """
        Get remaining TTL for a file.
        
        Args:
            file_id: File identifier
        
        Returns:
            Seconds until expiration, or -2 if key doesn't exist
        """
        return await self.redis.ttl(self._key(file_id))
