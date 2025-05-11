"""
Local file-based storage service for the Pixora AI application.

This module provides utilities for storing and retrieving files using the local filesystem.
"""
import os
import uuid
import shutil
import glob
from typing import Optional, Dict, Any, BinaryIO, List, Union
from fastapi import Depends, UploadFile, File, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.storage.base import StorageService


class LocalStorageService(StorageService):
    """
    Local file-based implementation of the StorageService interface.
    """

    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the storage service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "storage")
        
        # Create storage directories if they don't exist
        self._ensure_storage_dirs()

    def _ensure_storage_dirs(self):
        """
        Ensure that the storage directories exist.
        """
        # Create the main storage directory
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Create subdirectories for different asset types
        asset_types = ["characters", "scenes", "audio", "music", "videos", "uploads"]
        for asset_type in asset_types:
            os.makedirs(os.path.join(self.storage_dir, asset_type), exist_ok=True)

    async def create_bucket(self, bucket: str, is_public: bool = False) -> bool:
        """
        Create a directory for a video project.

        Args:
            bucket: The name of the bucket (video project ID)
            is_public: Whether the bucket should be publicly accessible

        Returns:
            True if the bucket was created successfully, False otherwise
        """
        try:
            bucket_path = os.path.join(self.storage_dir, "videos", bucket)
            os.makedirs(bucket_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating bucket: {str(e)}")
            return False

    async def delete_bucket(self, bucket: str) -> bool:
        """
        Delete a video project directory.

        Args:
            bucket: The name of the bucket (video project ID)

        Returns:
            True if the bucket was deleted successfully, False otherwise
        """
        try:
            bucket_path = os.path.join(self.storage_dir, "videos", bucket)
            if os.path.exists(bucket_path):
                shutil.rmtree(bucket_path)
            return True
        except Exception as e:
            print(f"Error deleting bucket: {str(e)}")
            return False

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
        try:
            # Construct the full path
            full_path = os.path.join(self.storage_dir, "videos", bucket, path)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write the file
            if isinstance(file_data, bytes):
                with open(full_path, "wb") as f:
                    f.write(file_data)
            else:
                # Assume it's a file-like object
                with open(full_path, "wb") as f:
                    shutil.copyfileobj(file_data, f)
            
            # Generate URL
            file_url = f"/storage/videos/{bucket}/{path}"
            
            return file_url
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file: {str(e)}"
            )

    async def download_file(self, bucket: str, path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            The file content as bytes
        """
        try:
            full_path = os.path.join(self.storage_dir, "videos", bucket, path)
            if not os.path.exists(full_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {path}"
                )
            
            with open(full_path, "rb") as f:
                return f.read()
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error downloading file: {str(e)}"
            )

    async def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket

        Returns:
            True if the file was deleted successfully, False otherwise
        """
        try:
            full_path = os.path.join(self.storage_dir, "videos", bucket, path)
            if not os.path.exists(full_path):
                return False
            
            os.remove(full_path)
            return True
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False

    async def list_files(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List files in a bucket.

        Args:
            bucket: The storage bucket name
            prefix: Optional prefix to filter files

        Returns:
            List of file paths
        """
        try:
            bucket_path = os.path.join(self.storage_dir, "videos", bucket)
            if not os.path.exists(bucket_path):
                return []
            
            if prefix:
                search_path = os.path.join(bucket_path, prefix, "**")
                files = glob.glob(search_path, recursive=True)
            else:
                search_path = os.path.join(bucket_path, "**")
                files = glob.glob(search_path, recursive=True)
            
            # Filter out directories
            files = [f for f in files if os.path.isfile(f)]
            
            # Convert to relative paths
            relative_files = [os.path.relpath(f, bucket_path) for f in files]
            
            return relative_files
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []

    async def get_file_url(self, bucket: str, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get the URL for a file.

        Args:
            bucket: The storage bucket name
            path: The path within the bucket
            expires_in: Optional expiration time in seconds for signed URLs

        Returns:
            The URL for the file
        """
        # For local storage, we don't need to worry about expiration
        return f"/storage/videos/{bucket}/{path}"

    # Additional methods for video project management

    async def create_video_project(self, project_id: str) -> Dict[str, Any]:
        """
        Create a new video project with the required folder structure.

        Args:
            project_id: The ID of the video project

        Returns:
            Dict containing the project path and URLs
        """
        try:
            # Create the project directory
            await self.create_bucket(project_id)
            
            # Return project information
            return {
                "project_id": project_id,
                "project_path": os.path.join(self.storage_dir, "videos", project_id),
                "project_url": f"/storage/videos/{project_id}"
            }
        except Exception as e:
            print(f"Error creating video project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating video project: {str(e)}"
            )

    async def create_scene_directory(self, project_id: str, scene_id: str) -> Dict[str, Any]:
        """
        Create a directory for a scene within a video project.

        Args:
            project_id: The ID of the video project
            scene_id: The ID of the scene

        Returns:
            Dict containing the scene path and URL
        """
        try:
            # Create the scene directory
            scene_path = os.path.join(self.storage_dir, "videos", project_id, scene_id)
            os.makedirs(scene_path, exist_ok=True)
            
            # Return scene information
            return {
                "scene_id": scene_id,
                "scene_path": scene_path,
                "scene_url": f"/storage/videos/{project_id}/{scene_id}"
            }
        except Exception as e:
            print(f"Error creating scene directory: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating scene directory: {str(e)}"
            )

    async def save_scene_file(
        self, 
        project_id: str, 
        scene_id: str, 
        file_type: str, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Save a file for a specific scene.

        Args:
            project_id: The ID of the video project
            scene_id: The ID of the scene
            file_type: The type of file (video, audio, music)
            file_content: The content of the file

        Returns:
            Dict containing the file path and URL
        """
        try:
            # Determine the file extension
            if file_type == "video":
                file_extension = ".mp4"
            elif file_type in ["audio", "music"]:
                file_extension = ".mp3"
            else:
                file_extension = ".bin"
            
            # Construct the file path
            file_name = f"{file_type}{file_extension}"
            file_path = os.path.join(scene_id, file_name)
            
            # Upload the file
            file_url = await self.upload_file(file_content, project_id, file_path)
            
            return {
                "file_path": os.path.join(self.storage_dir, "videos", project_id, file_path),
                "file_url": file_url,
                "file_size": len(file_content)
            }
        except Exception as e:
            print(f"Error saving scene file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving scene file: {str(e)}"
            )

    async def save_project_file(
        self, 
        project_id: str, 
        file_type: str, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Save a file at the project level.

        Args:
            project_id: The ID of the video project
            file_type: The type of file (full_video, script, log)
            file_content: The content of the file

        Returns:
            Dict containing the file path and URL
        """
        try:
            # Determine the file name and extension
            if file_type == "full_video":
                file_name = "full_video.mp4"
            elif file_type == "script":
                file_name = "script.json"
            elif file_type == "log":
                file_name = "logfile.log"
            else:
                file_name = f"{file_type}.bin"
            
            # Upload the file
            file_url = await self.upload_file(file_content, project_id, file_name)
            
            return {
                "file_path": os.path.join(self.storage_dir, "videos", project_id, file_name),
                "file_url": file_url,
                "file_size": len(file_content)
            }
        except Exception as e:
            print(f"Error saving project file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving project file: {str(e)}"
            )

    # Legacy methods for backward compatibility

    async def save_file(
        self,
        file_content: bytes,
        file_type: str,
        file_id: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save a file to storage (legacy method).

        Args:
            file_content: The content of the file
            file_type: The type of file (character, scene, audio, music, video)
            file_id: Optional ID for the file (generates a UUID if not provided)
            file_extension: Optional file extension (inferred from file_type if not provided)

        Returns:
            Dict containing the file path and URL
        """
        # Generate a file ID if not provided
        if file_id is None:
            file_id = str(uuid.uuid4())
        
        # Determine the file extension if not provided
        if file_extension is None:
            if file_type in ["character", "scene"]:
                file_extension = ".png"
            elif file_type in ["audio", "music"]:
                file_extension = ".mp3"
            elif file_type == "video":
                file_extension = ".mp4"
            else:
                file_extension = ".bin"
        
        # Determine the storage directory based on file type
        if file_type == "character":
            storage_subdir = "characters"
        elif file_type == "scene":
            storage_subdir = "scenes"
        elif file_type == "audio":
            storage_subdir = "audio"
        elif file_type == "music":
            storage_subdir = "music"
        elif file_type == "video":
            storage_subdir = "videos"
        else:
            storage_subdir = "other"
        
        # Create the full file path
        file_path = os.path.join(self.storage_dir, storage_subdir, f"{file_id}{file_extension}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Generate a URL for the file
        file_url = f"/storage/{storage_subdir}/{file_id}{file_extension}"
        
        # Return the file information
        return {
            "file_id": file_id,
            "file_path": file_path,
            "file_url": file_url,
            "file_type": file_type,
            "file_size": len(file_content)
        }

    async def save_upload_file(
        self,
        upload_file: UploadFile = File(...),
        file_type: str = "other",
        file_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save an uploaded file to storage (legacy method).

        Args:
            upload_file: The uploaded file
            file_type: The type of file (character, scene, audio, music, video)
            file_id: Optional ID for the file (generates a UUID if not provided)

        Returns:
            Dict containing the file path and URL
        """
        # Read the file content
        file_content = await upload_file.read()
        
        # Get the file extension from the filename
        _, file_extension = os.path.splitext(upload_file.filename)
        
        # Save the file
        return await self.save_file(
            file_content=file_content,
            file_type=file_type,
            file_id=file_id,
            file_extension=file_extension
        )

    async def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Get a file from storage (legacy method).

        Args:
            file_path: The path to the file

        Returns:
            The file content, or None if the file doesn't exist
        """
        # Check if the file exists
        if not os.path.exists(file_path):
            return None
        
        # Read the file
        with open(file_path, "rb") as f:
            return f.read()
