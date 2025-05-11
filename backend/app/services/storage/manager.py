"""
Storage manager for handling file operations.

This module provides a unified interface for storage operations,
abstracting away the underlying storage implementation.
"""
import os
import uuid
import time
from typing import List, Optional, BinaryIO, Union, Dict, Any
from datetime import datetime
import logging

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.storage.base import StorageService
from app.services.storage.local import LocalStorageService
from app.services.storage.supabase import SupabaseStorageService
from app.services.dependencies import get_storage_service_dependency


# Set up logging
logger = logging.getLogger(__name__)


class StorageManager:
    """
    Storage manager for handling file operations.
    
    This class provides a unified interface for storage operations,
    abstracting away the underlying storage implementation.
    """
    
    def __init__(
        self, 
        storage_service: Union[LocalStorageService, SupabaseStorageService] = Depends(get_storage_service_dependency),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the storage manager.
        
        Args:
            storage_service: The storage service implementation to use
            settings: Application settings
        """
        self.storage_service = storage_service
        self.settings = settings
        
        # Default buckets
        self.videos_bucket = settings.STORAGE_VIDEOS_BUCKET
        self.images_bucket = settings.STORAGE_IMAGES_BUCKET
        self.audio_bucket = settings.STORAGE_AUDIO_BUCKET
    
    async def upload_video(
        self, 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Upload a video file to storage.
        
        Args:
            file_data: The video file data
            filename: Optional filename (will be generated if not provided)
            content_type: Optional MIME type
            user_id: Optional user ID to include in the path
            
        Returns:
            The public URL of the uploaded video
        """
        # Generate a unique filename if not provided
        if not filename:
            ext = self._get_extension_from_content_type(content_type) or ".mp4"
            filename = f"{uuid.uuid4()}{ext}"
        
        # Construct the path
        path = self._construct_path(filename, user_id)
        
        # Upload the file
        return await self.storage_service.upload_file(
            file_data=file_data,
            bucket=self.videos_bucket,
            path=path,
            content_type=content_type
        )
    
    async def upload_image(
        self, 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Upload an image file to storage.
        
        Args:
            file_data: The image file data
            filename: Optional filename (will be generated if not provided)
            content_type: Optional MIME type
            user_id: Optional user ID to include in the path
            
        Returns:
            The public URL of the uploaded image
        """
        # Generate a unique filename if not provided
        if not filename:
            ext = self._get_extension_from_content_type(content_type) or ".jpg"
            filename = f"{uuid.uuid4()}{ext}"
        
        # Construct the path
        path = self._construct_path(filename, user_id)
        
        # Upload the file
        return await self.storage_service.upload_file(
            file_data=file_data,
            bucket=self.images_bucket,
            path=path,
            content_type=content_type
        )
    
    async def upload_audio(
        self, 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Upload an audio file to storage.
        
        Args:
            file_data: The audio file data
            filename: Optional filename (will be generated if not provided)
            content_type: Optional MIME type
            user_id: Optional user ID to include in the path
            
        Returns:
            The public URL of the uploaded audio
        """
        # Generate a unique filename if not provided
        if not filename:
            ext = self._get_extension_from_content_type(content_type) or ".mp3"
            filename = f"{uuid.uuid4()}{ext}"
        
        # Construct the path
        path = self._construct_path(filename, user_id)
        
        # Upload the file
        return await self.storage_service.upload_file(
            file_data=file_data,
            bucket=self.audio_bucket,
            path=path,
            content_type=content_type
        )
    
    async def upload_file_from_url(
        self, 
        url: str, 
        bucket: str,
        path: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Download a file from a URL and upload it to storage.
        
        Args:
            url: The URL to download from
            bucket: The storage bucket
            path: Optional path within the bucket (will be generated if not provided)
            content_type: Optional MIME type
            user_id: Optional user ID to include in the path
            
        Returns:
            The public URL of the uploaded file
        """
        import httpx
        
        try:
            # Download the file
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Get content type from response if not provided
                if not content_type:
                    content_type = response.headers.get("content-type")
                
                # Generate path if not provided
                if not path:
                    ext = self._get_extension_from_content_type(content_type) or os.path.splitext(url)[1] or ""
                    filename = f"{uuid.uuid4()}{ext}"
                    path = self._construct_path(filename, user_id)
                
                # Upload the file
                return await self.storage_service.upload_file(
                    file_data=response.content,
                    bucket=bucket,
                    path=path,
                    content_type=content_type
                )
                
        except Exception as e:
            logger.error(f"Error uploading file from URL {url}: {str(e)}")
            raise
    
    async def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            bucket: The storage bucket
            path: The path within the bucket
            
        Returns:
            True if the file was deleted, False otherwise
        """
        return await self.storage_service.delete_file(bucket, path)
    
    async def get_file_url(self, bucket: str, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get the URL for a file.
        
        Args:
            bucket: The storage bucket
            path: The path within the bucket
            expires_in: Optional expiration time in seconds for signed URLs
            
        Returns:
            The URL of the file
        """
        return await self.storage_service.get_file_url(bucket, path, expires_in)
    
    async def list_files(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List files in a bucket with an optional prefix.
        
        Args:
            bucket: The storage bucket
            prefix: Optional prefix to filter files
            
        Returns:
            A list of file paths
        """
        return await self.storage_service.list_files(bucket, prefix)
    
    def _construct_path(self, filename: str, user_id: Optional[str] = None) -> str:
        """
        Construct a path for a file.
        
        Args:
            filename: The filename
            user_id: Optional user ID to include in the path
            
        Returns:
            The constructed path
        """
        # Get current date for organizing files
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        
        # Add a timestamp to the filename to ensure uniqueness
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{int(time.time() * 1000)}{ext}"
        
        # Construct the path
        if user_id:
            return f"{user_id}/{date_path}/{unique_filename}"
        else:
            return f"{date_path}/{unique_filename}"
    
    def _get_extension_from_content_type(self, content_type: Optional[str]) -> Optional[str]:
        """
        Get a file extension from a MIME type.
        
        Args:
            content_type: The MIME type
            
        Returns:
            The file extension or None if not found
        """
        if not content_type:
            return None
            
        # Common MIME types to extensions mapping
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "audio/ogg": ".ogg",
            "application/json": ".json",
            "text/plain": ".txt",
            "text/html": ".html",
            "application/pdf": ".pdf",
        }
        
        return mime_to_ext.get(content_type.lower())
