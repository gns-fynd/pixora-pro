"""
Supabase storage service implementation.

This module provides a concrete implementation of the StorageService
interface using Supabase Storage.
"""
import io
import os
import mimetypes
from typing import List, Optional, BinaryIO, Union, Dict, Any
import logging

import httpx
from fastapi import Depends
from supabase import create_client, Client

from app.core.config import Settings, get_settings
from app.services.storage.base import StorageService


# Set up logging
logger = logging.getLogger(__name__)


class SupabaseStorageService(StorageService):
    """Supabase implementation of the StorageService interface."""

    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the Supabase storage service.

        Args:
            settings: Application settings
        """
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.supabase_service_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        
        # Initialize Supabase client
        self.client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize admin client with service key for operations that need to bypass RLS
        self.admin_client = create_client(self.supabase_url, self.supabase_service_key)
        
        # Storage buckets
        self.videos_bucket = settings.STORAGE_VIDEOS_BUCKET
        self.images_bucket = settings.STORAGE_IMAGES_BUCKET
        self.audio_bucket = settings.STORAGE_AUDIO_BUCKET
        
        # Public URL for assets
        self.storage_public_url = settings.STORAGE_PUBLIC_URL or f"{self.supabase_url}/storage/v1/object/public"

    async def upload_file(
        self, 
        file_data: Union[bytes, BinaryIO], 
        bucket: str, 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to Supabase storage.

        Args:
            file_data: The file data as bytes or file-like object
            bucket: The storage bucket name
            path: The path within the bucket
            content_type: Optional MIME type of the file

        Returns:
            The public URL of the uploaded file
        """
        try:
            # Ensure the bucket exists
            await self.create_bucket(bucket, is_public=True)
            
            # Determine content type if not provided
            if not content_type:
                content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            
            # Convert file-like object to bytes if needed
            if hasattr(file_data, 'read'):
                file_data = file_data.read()
            
            # Upload the file
            response = self.admin_client.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            # Generate public URL
            public_url = f"{self.storage_public_url}/{bucket}/{path}"
            
            logger.info(f"File uploaded successfully: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading file to {bucket}/{path}: {str(e)}")
            raise

    async def download_file(self, bucket: str, path: str) -> bytes:
        """
        Download a file from Supabase storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            The file content as bytes
        """
        try:
            # Download the file
            response = self.admin_client.storage.from_(bucket).download(path)
            
            logger.info(f"File downloaded successfully: {bucket}/{path}")
            return response
            
        except Exception as e:
            logger.error(f"Error downloading file from {bucket}/{path}: {str(e)}")
            raise

    async def get_file_url(self, bucket: str, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get the URL for a file in Supabase storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket
            expires_in: Optional expiration time in seconds for signed URLs

        Returns:
            The URL of the file
        """
        try:
            if expires_in:
                # Generate signed URL with expiration
                signed_url = self.admin_client.storage.from_(bucket).create_signed_url(
                    path=path,
                    expires_in=expires_in
                )
                return signed_url["signedURL"]
            else:
                # Generate public URL
                public_url = self.admin_client.storage.from_(bucket).get_public_url(path)
                return public_url
                
        except Exception as e:
            logger.error(f"Error getting URL for {bucket}/{path}: {str(e)}")
            raise

    async def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete a file from Supabase storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            True if the file was deleted, False otherwise
        """
        try:
            # Delete the file
            self.admin_client.storage.from_(bucket).remove([path])
            
            logger.info(f"File deleted successfully: {bucket}/{path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {bucket}/{path}: {str(e)}")
            return False

    async def list_files(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List files in a Supabase storage bucket with an optional prefix.

        Args:
            bucket: The storage bucket name
            prefix: Optional prefix to filter files

        Returns:
            A list of file paths
        """
        try:
            # List files in the bucket
            response = self.admin_client.storage.from_(bucket).list(path=prefix or "")
            
            # Extract file paths
            file_paths = [item["name"] for item in response]
            
            return file_paths
            
        except Exception as e:
            logger.error(f"Error listing files in {bucket} with prefix {prefix}: {str(e)}")
            return []

    async def create_bucket(self, bucket: str, is_public: bool = False) -> bool:
        """
        Create a new bucket in Supabase storage if it doesn't exist.

        Args:
            bucket: The storage bucket name
            is_public: Whether the bucket should be publicly accessible

        Returns:
            True if the bucket was created or already exists, False otherwise
        """
        try:
            # Check if bucket exists
            try:
                buckets = self.admin_client.storage.list_buckets()
                # Ensure buckets is a list we can iterate over
                if not isinstance(buckets, list):
                    logger.warning(f"Unexpected response from list_buckets: {type(buckets)}")
                    buckets = []
                
                bucket_exists = any(b.get("name") == bucket for b in buckets if isinstance(b, dict))
            except Exception as list_error:
                logger.warning(f"Error listing buckets: {str(list_error)}")
                bucket_exists = False
            
            if not bucket_exists:
                try:
                    # Create the bucket
                    self.admin_client.storage.create_bucket(
                        bucket,
                        options={
                            "public": is_public,
                            "file_size_limit": 52428800  # 50MB limit
                        }
                    )
                    logger.info(f"Bucket created successfully: {bucket}")
                except Exception as create_error:
                    # If the error is because the bucket already exists, that's fine
                    if "already exists" in str(create_error).lower():
                        logger.info(f"Bucket {bucket} already exists")
                        bucket_exists = True
                    else:
                        # Re-raise if it's a different error
                        raise create_error
            
            # If bucket is public, set public policy
            if is_public and (bucket_exists or not bucket_exists):
                try:
                    # Set public access policy using the correct method
                    # The update_bucket method doesn't exist on SyncBucketProxy
                    # Instead, we'll use the bucket's public URL directly
                    logger.info(f"Bucket {bucket} is set to public, skipping policy update (not needed)")
                    # No need to update the bucket policy as it's already set when creating the bucket
                except Exception as policy_error:
                    logger.warning(f"Error setting public policy for bucket {bucket}: {str(policy_error)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating bucket {bucket}: {str(e)}")
            return False

    async def delete_bucket(self, bucket: str) -> bool:
        """
        Delete a bucket from Supabase storage.

        Args:
            bucket: The storage bucket name

        Returns:
            True if the bucket was deleted, False otherwise
        """
        try:
            # Delete the bucket
            self.admin_client.storage.delete_bucket(bucket)
            
            logger.info(f"Bucket deleted successfully: {bucket}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting bucket {bucket}: {str(e)}")
            return False
