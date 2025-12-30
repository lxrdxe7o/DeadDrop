"""
Storage abstraction layer for encrypted file blobs.

Uses Protocol for type-safe interface, enabling easy migration from
local filesystem to S3 or other cloud storage providers.
"""

from typing import Protocol
from pathlib import Path
import aiofiles
import os


class StorageBackend(Protocol):
    """
    Storage interface protocol.
    
    Implementations can use local disk, S3, Azure Blob Storage, etc.
    """
    
    async def save(self, file_id: str, data: bytes) -> None:
        """Save encrypted blob to storage."""
        ...
    
    async def load(self, file_id: str) -> bytes:
        """Load encrypted blob from storage."""
        ...
    
    async def delete(self, file_id: str) -> None:
        """Delete encrypted blob from storage."""
        ...
    
    async def exists(self, file_id: str) -> bool:
        """Check if file exists in storage."""
        ...


class LocalStorage:
    """
    Local filesystem storage implementation.
    
    Stores encrypted blobs as {uuid}.enc files in the configured directory.
    Suitable for single-server deployments or development.
    """
    
    def __init__(self, base_path: str = "./storage"):
        """
        Initialize local storage.
        
        Args:
            base_path: Directory path for storing encrypted files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, file_id: str) -> Path:
        """
        Get filesystem path for a file ID.
        
        Sanitizes file_id to prevent directory traversal attacks.
        
        Args:
            file_id: File identifier (typically UUID)
        
        Returns:
            Path object for the file
        """
        # Security: Extract only the filename component (prevents ../attacks)
        safe_id = Path(file_id).name
        return self.base_path / f"{safe_id}.enc"
    
    async def save(self, file_id: str, data: bytes) -> None:
        """
        Save encrypted blob to disk.
        
        Args:
            file_id: File identifier
            data: Encrypted file data
        
        Raises:
            IOError: If write fails
        """
        path = self._get_path(file_id)
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)
    
    async def load(self, file_id: str) -> bytes:
        """
        Load encrypted blob from disk.
        
        Args:
            file_id: File identifier
        
        Returns:
            Encrypted file data
        
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
        """
        path = self._get_path(file_id)
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()
    
    async def delete(self, file_id: str) -> None:
        """
        Delete encrypted blob from disk.
        
        Args:
            file_id: File identifier
        
        Note:
            Does not raise error if file doesn't exist (idempotent).
        """
        path = self._get_path(file_id)
        if path.exists():
            os.remove(path)
    
    async def exists(self, file_id: str) -> bool:
        """
        Check if file exists on disk.
        
        Args:
            file_id: File identifier
        
        Returns:
            True if file exists, False otherwise
        """
        return self._get_path(file_id).exists()


# Future S3 implementation example (commented out)
"""
import boto3
from botocore.exceptions import ClientError

class S3Storage:
    '''
    AWS S3 storage implementation.
    
    Suitable for production deployments requiring horizontal scaling.
    '''
    
    def __init__(self, bucket: str, region: str = "us-east-1", prefix: str = "files/"):
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket
        self.prefix = prefix
    
    def _get_key(self, file_id: str) -> str:
        return f"{self.prefix}{file_id}.enc"
    
    async def save(self, file_id: str, data: bytes) -> None:
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=self._get_key(file_id),
                Body=data,
                ServerSideEncryption='AES256'
            )
        except ClientError as e:
            raise IOError(f"S3 upload failed: {e}")
    
    async def load(self, file_id: str) -> bytes:
        try:
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=self._get_key(file_id)
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {file_id}")
            raise IOError(f"S3 download failed: {e}")
    
    async def delete(self, file_id: str) -> None:
        try:
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=self._get_key(file_id)
            )
        except ClientError:
            pass  # Idempotent
    
    async def exists(self, file_id: str) -> bool:
        try:
            self.s3.head_object(
                Bucket=self.bucket,
                Key=self._get_key(file_id)
            )
            return True
        except ClientError:
            return False
"""
