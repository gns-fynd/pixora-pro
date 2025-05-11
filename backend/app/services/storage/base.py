"""
Base storage service interface.

This module defines the abstract base class for storage services.
All storage implementations should inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, BinaryIO, Union


class StorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def upload_file(
        self, 
        file_data: Union[bytes, BinaryIO], 
        bucket: str, 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_data: The file data as bytes or file-like object
            bucket: The storage bucket name
            path: The path within the bucket
            content_type: Optional MIME type of the file

        Returns:
            The public URL of the uploaded file
        """
        pass

    @abstractmethod
    async def download_file(self, bucket: str, path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            The file content as bytes
        """
        pass

    @abstractmethod
    async def get_file_url(self, bucket: str, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get the URL for a file.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket
            expires_in: Optional expiration time in seconds for signed URLs

        Returns:
            The URL of the file
        """
        pass

    @abstractmethod
    async def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            True if the file was deleted, False otherwise
        """
        pass

    @abstractmethod
    async def list_files(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List files in a bucket with an optional prefix.

        Args:
            bucket: The storage bucket name
            prefix: Optional prefix to filter files

        Returns:
            A list of file paths
        """
        pass

    @abstractmethod
    async def create_bucket(self, bucket: str, is_public: bool = False) -> bool:
        """
        Create a new bucket.

        Args:
            bucket: The storage bucket name
            is_public: Whether the bucket should be publicly accessible

        Returns:
            True if the bucket was created, False otherwise
        """
        pass

    @abstractmethod
    async def delete_bucket(self, bucket: str) -> bool:
        """
        Delete a bucket.

        Args:
            bucket: The storage bucket name

        Returns:
            True if the bucket was deleted, False otherwise
        """
        pass
