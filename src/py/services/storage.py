"""
Storage abstraction layer for encrypted file blobs.

Uses Protocol for type-safe interface, enabling easy migration from
local filesystem to S3 or other cloud storage providers.
Includes comprehensive error handling and timeout support.
"""

import asyncio
from typing import Protocol
from pathlib import Path
import aiofiles
import aiofiles.os
import os
from core.exceptions import (
    StorageWriteError,
    StorageReadError,
    StorageDeleteError,
    FileNotFoundError as DeadDropFileNotFoundError
)


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

    Features:
    - Non-blocking async I/O operations
    - Timeout handling for all operations
    - Comprehensive error handling
    - Directory traversal prevention
    - Idempotent delete operations

    Stores encrypted blobs as {uuid}.enc files in the configured directory.
    Suitable for single-server deployments or development.
    """

    def __init__(
        self,
        base_path: str = "./storage",
        operation_timeout: float = 30.0
    ):
        """
        Initialize local storage.

        Args:
            base_path: Directory path for storing encrypted files
            operation_timeout: Timeout for file operations (seconds)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.operation_timeout = operation_timeout
    
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
            StorageWriteError: If write fails or times out
        """
        path = self._get_path(file_id)
        try:
            async with asyncio.timeout(self.operation_timeout):
                # Write to temp file first, then atomic rename
                temp_path = path.with_suffix('.tmp')
                try:
                    async with aiofiles.open(temp_path, 'wb') as f:
                        await f.write(data)
                    # Atomic rename to prevent partial writes
                    await aiofiles.os.rename(temp_path, path)
                except Exception as e:
                    # Clean up temp file if it exists
                    if temp_path.exists():
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                    raise e

        except asyncio.TimeoutError as e:
            raise StorageWriteError(
                message="Storage write operation timed out",
                details={"file_id": file_id, "size": len(data)}
            ) from e
        except OSError as e:
            raise StorageWriteError(
                message="Failed to write file to storage",
                details={"file_id": file_id, "error": str(e)},
                internal_message=str(e)
            ) from e
        except Exception as e:
            raise StorageWriteError(
                message="Unexpected error writing to storage",
                details={"file_id": file_id, "error": str(e)},
                internal_message=str(e)
            ) from e
    
    async def load(self, file_id: str) -> bytes:
        """
        Load encrypted blob from disk.

        Args:
            file_id: File identifier

        Returns:
            Encrypted file data

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageReadError: If read fails or times out
        """
        path = self._get_path(file_id)
        try:
            async with asyncio.timeout(self.operation_timeout):
                if not path.exists():
                    raise DeadDropFileNotFoundError(
                        file_id=file_id,
                        details={"path": str(path)}
                    )
                async with aiofiles.open(path, 'rb') as f:
                    return await f.read()

        except asyncio.TimeoutError as e:
            raise StorageReadError(
                message="Storage read operation timed out",
                details={"file_id": file_id}
            ) from e
        except DeadDropFileNotFoundError:
            raise  # Re-raise our custom exception
        except OSError as e:
            raise StorageReadError(
                message="Failed to read file from storage",
                details={"file_id": file_id, "error": str(e)},
                internal_message=str(e)
            ) from e
        except Exception as e:
            raise StorageReadError(
                message="Unexpected error reading from storage",
                details={"file_id": file_id, "error": str(e)},
                internal_message=str(e)
            ) from e
    
    async def delete(self, file_id: str) -> None:
        """
        Delete encrypted blob from disk.

        Args:
            file_id: File identifier

        Raises:
            StorageDeleteError: If delete fails (but not if file doesn't exist)

        Note:
            Idempotent - does not raise error if file doesn't exist.
        """
        path = self._get_path(file_id)
        try:
            async with asyncio.timeout(self.operation_timeout):
                if path.exists():
                    await aiofiles.os.remove(path)

        except asyncio.TimeoutError as e:
            raise StorageDeleteError(
                message="Storage delete operation timed out",
                details={"file_id": file_id}
            ) from e
        except OSError as e:
            # Only raise if file exists but can't be deleted
            if path.exists():
                raise StorageDeleteError(
                    message="Failed to delete file from storage",
                    details={"file_id": file_id, "error": str(e)},
                    internal_message=str(e)
                ) from e
        except Exception as e:
            raise StorageDeleteError(
                message="Unexpected error deleting from storage",
                details={"file_id": file_id, "error": str(e)},
                internal_message=str(e)
            ) from e
    
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
