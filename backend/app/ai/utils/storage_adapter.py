"""
Storage adapter for the video agent.

This module provides a storage adapter that uses Supabase storage for the video agent.
"""
import os
import uuid
import logging
from typing import Optional, BinaryIO, Union, Dict, Any
from pathlib import Path

from fastapi import Depends

from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class StorageAdapter:
    """
    Storage adapter for the video agent that uses Supabase storage.
    """
    
    def __init__(self, storage_manager: StorageManager = Depends()):
        """
        Initialize the storage adapter.
        
        Args:
            storage_manager: The storage manager
        """
        self.storage_manager = storage_manager
        
    async def create_task_directory_structure(self, task_id: str) -> Dict[str, str]:
        """
        Create a hierarchical directory structure for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            Dictionary with paths for different asset types
        """
        import time
        import os
        
        # Create a timestamp-based directory name
        timestamp = int(time.time())
        base_dir = f"{timestamp}-{task_id}"
        
        # Create a temporary directory for the task
        temp_dir = await self.create_temp_directory()
        task_dir = os.path.join(temp_dir, base_dir)
        
        # Create the directory structure
        os.makedirs(task_dir, exist_ok=True)
        
        # Create subdirectories for different asset types
        paths = {
            "base": task_dir,
            "scenes": {},
            "music": os.path.join(task_dir, "music"),
            "final": os.path.join(task_dir, "final")
        }
        
        # Create the music and final directories
        os.makedirs(paths["music"], exist_ok=True)
        os.makedirs(paths["final"], exist_ok=True)
        
        # Return the paths
        return paths
    
    async def create_scene_directory(self, task_dir: Dict[str, Any], scene_index: int) -> Dict[str, str]:
        """
        Create a directory structure for a scene.
        
        Args:
            task_dir: The task directory structure
            scene_index: The scene index
            
        Returns:
            Dictionary with paths for different scene asset types
        """
        import os
        
        # Create the scene directory
        scene_dir = os.path.join(task_dir["base"], f"scene_{scene_index}")
        
        # Create subdirectories for different asset types
        paths = {
            "base": scene_dir,
            "script": os.path.join(scene_dir, "script"),
            "image": os.path.join(scene_dir, "image"),
            "audio": os.path.join(scene_dir, "audio"),
            "video": os.path.join(scene_dir, "video")
        }
        
        # Create all directories
        for path in paths.values():
            os.makedirs(path, exist_ok=True)
        
        # Store the scene paths in the task directory structure
        task_dir["scenes"][scene_index] = paths
        
        # Return the scene paths
        return paths
    
    async def save_video(self, file_data: Union[bytes, BinaryIO], filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Save a video file to storage.
        
        Args:
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the saved file
        """
        if not filename:
            filename = f"{uuid.uuid4()}.mp4"
        
        return await self.storage_manager.upload_video(
            file_data=file_data,
            filename=filename,
            user_id=user_id
        )
    
    async def save_image(self, file_data: Union[bytes, BinaryIO], filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Save an image file to storage.
        
        Args:
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the saved file
        """
        if not filename:
            filename = f"{uuid.uuid4()}.jpg"
        
        return await self.storage_manager.upload_image(
            file_data=file_data,
            filename=filename,
            user_id=user_id
        )
    
    async def save_audio(self, file_data: Union[bytes, BinaryIO], filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Save an audio file to storage.
        
        Args:
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the saved file
        """
        if not filename:
            filename = f"{uuid.uuid4()}.mp3"
        
        return await self.storage_manager.upload_audio(
            file_data=file_data,
            filename=filename,
            user_id=user_id
        )
    
    async def download_and_store_file_from_url(self, url: str, bucket: str, filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Download a file from a URL and store it.
        
        Args:
            url: The URL to download from
            bucket: The storage bucket
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the stored file
        """
        return await self.storage_manager.upload_file_from_url(
            url=url,
            bucket=bucket,
            path=None,  # Let the storage manager generate a path
            user_id=user_id
        )
    
    async def download_and_store_video(self, url: str, filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Download a video from a URL and store it.
        
        Args:
            url: The URL to download from
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the stored video
        """
        videos_bucket = self.storage_manager.videos_bucket
        return await self.download_and_store_file_from_url(url, videos_bucket, filename, user_id)
    
    async def download_and_store_image(self, url: str, filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Download an image from a URL and store it.
        
        Args:
            url: The URL to download from
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the stored image
        """
        images_bucket = self.storage_manager.images_bucket
        return await self.download_and_store_file_from_url(url, images_bucket, filename, user_id)
    
    async def download_and_store_audio(self, url: str, filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Download an audio file from a URL and store it.
        
        Args:
            url: The URL to download from
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            
        Returns:
            The URL of the stored audio
        """
        audio_bucket = self.storage_manager.audio_bucket
        return await self.download_and_store_file_from_url(url, audio_bucket, filename, user_id)
    
    async def get_public_url(self, path_or_url: str, bucket: Optional[str] = None) -> str:
        """
        Get the public URL for a file (async version).
        
        Args:
            path_or_url: The path or URL of the file
            bucket: Optional bucket name (required if path_or_url is a path, not a URL)
            
        Returns:
            The public URL
        """
        # If it's already a URL, return it
        if path_or_url.startswith("http"):
            return path_or_url
            
        # If it's a path and bucket is provided, get the URL
        if bucket:
            return await self.storage_manager.get_file_url(bucket, path_or_url)
            
        # If no bucket is provided, assume it's a full path with bucket info
        # This is a fallback for backward compatibility
        logger.warning("get_public_url called without bucket parameter, using images bucket as default")
        return await self.storage_manager.get_file_url(self.storage_manager.images_bucket, path_or_url)
    
    def get_public_url_sync(self, path_or_url: str, bucket: Optional[str] = None) -> str:
        """
        Get the public URL for a file (synchronous version).
        This is a simplified version that doesn't actually fetch the URL from storage,
        but just returns the path or URL as is. Use this only for JSON serialization
        or other cases where you can't use async/await.
        
        Args:
            path_or_url: The path or URL of the file
            bucket: Optional bucket name (not used in this sync version)
            
        Returns:
            The path or URL as is
        """
        # If it's already a URL, return it
        if path_or_url.startswith("http"):
            return path_or_url
            
        # For local paths, just return the path
        # This is a simplified version that doesn't actually fetch the URL
        return path_or_url
    
    async def create_temp_directory(self) -> str:
        """
        Create a temporary directory.
        
        Returns:
            The path to the temporary directory
        """
        # Create a unique directory name
        dir_name = str(uuid.uuid4())
        
        # Create the directory in the system's temp directory
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        logger.info(f"Created temporary directory {temp_dir}")
        return temp_dir
    
    async def cleanup_temp_directory(self, dir_path: str) -> None:
        """
        Clean up a temporary directory.
        
        Args:
            dir_path: The path to the temporary directory
        """
        import shutil
        
        # Check if the directory exists
        if os.path.exists(dir_path):
            # Remove the directory and its contents
            shutil.rmtree(dir_path)
            logger.info(f"Cleaned up temporary directory {dir_path}")
    
    def get_local_path(self, url: str) -> Optional[str]:
        """
        Get the local file path from a URL.
        
        Args:
            url: The URL of the file
            
        Returns:
            The local file path or None if it's a remote URL
        """
        # Handle None case
        if url is None:
            return None
            
        # If it's a remote URL, return None
        # This indicates that the URL is not available locally
        if url.startswith("http"):
            return None
            
        # If it's a local path, return it
        return url
    
    def get_placeholder_image_url(self) -> str:
        """
        Get a placeholder image URL.
        
        Returns:
            The URL of a placeholder image
        """
        # Return a URL to a placeholder image
        return "https://placehold.co/1024x1024/gray/white?text=Placeholder+Image"
    
    def get_placeholder_audio_url(self) -> str:
        """
        Get a placeholder audio URL.
        
        Returns:
            The URL of a placeholder audio file
        """
        # Return a URL to a placeholder audio file (silent)
        return "https://replicate.delivery/pbxt/MNaHFqDkZ0Y22hvppxotJazhRYe6TwhK78xAUTCoz3NB9bRV/voice_sample.wav"
    
    def get_placeholder_video_url(self) -> str:
        """
        Get a placeholder video URL.
        
        Returns:
            The URL of a placeholder video
        """
        # Return a URL to a placeholder MP4 video instead of an SVG
        # This is a valid MP4 file that can be processed by MoviePy
        return "https://storage.googleapis.com/pixora-public/placeholders/placeholder_video.mp4"
    
    async def save_scene_asset(
        self, 
        task_dir: Dict[str, Any], 
        scene_index: int, 
        asset_type: str, 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a scene asset to the appropriate location in the hierarchical structure.
        
        Args:
            task_dir: The task directory structure
            scene_index: The scene index
            asset_type: The asset type (image, audio, video, script)
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            metadata: Optional metadata to save with the asset
            
        Returns:
            Dictionary with information about the saved asset
        """
        import os
        import json
        
        # Ensure the scene directory exists
        if scene_index not in task_dir["scenes"]:
            await self.create_scene_directory(task_dir, scene_index)
        
        scene_paths = task_dir["scenes"][scene_index]
        
        # Generate a unique filename if not provided
        if not filename:
            if asset_type == "image":
                filename = f"scene_{scene_index}_image_{uuid.uuid4()}.jpg"
            elif asset_type == "audio":
                filename = f"scene_{scene_index}_audio_{uuid.uuid4()}.mp3"
            elif asset_type == "video":
                filename = f"scene_{scene_index}_video_{uuid.uuid4()}.mp4"
            elif asset_type == "script":
                filename = f"scene_{scene_index}_script_{uuid.uuid4()}.json"
            else:
                filename = f"scene_{scene_index}_{asset_type}_{uuid.uuid4()}"
        
        # Get the appropriate directory for this asset type
        asset_dir = scene_paths.get(asset_type, scene_paths["base"])
        
        # Create the full path
        file_path = os.path.join(asset_dir, filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            if hasattr(file_data, "read"):
                # It's a file-like object
                f.write(file_data.read())
            else:
                # It's bytes
                f.write(file_data)
        
        # Save metadata if provided
        metadata_path = None
        if metadata:
            metadata_filename = f"{os.path.splitext(filename)[0]}_metadata.json"
            metadata_path = os.path.join(asset_dir, metadata_filename)
            
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        # Return information about the saved asset
        result = {
            "path": file_path,
            "filename": filename,
            "asset_type": asset_type,
            "scene_index": scene_index,
            "metadata_path": metadata_path
        }
        
        return result
    
    async def save_music_asset(
        self, 
        task_dir: Dict[str, Any], 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a music asset to the appropriate location in the hierarchical structure.
        
        Args:
            task_dir: The task directory structure
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            metadata: Optional metadata to save with the asset
            
        Returns:
            Dictionary with information about the saved asset
        """
        import os
        import json
        
        # Generate a unique filename if not provided
        if not filename:
            filename = f"music_{uuid.uuid4()}.mp3"
        
        # Get the music directory
        music_dir = task_dir["music"]
        
        # Create the full path
        file_path = os.path.join(music_dir, filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            if hasattr(file_data, "read"):
                # It's a file-like object
                f.write(file_data.read())
            else:
                # It's bytes
                f.write(file_data)
        
        # Save metadata if provided
        metadata_path = None
        if metadata:
            metadata_filename = f"{os.path.splitext(filename)[0]}_metadata.json"
            metadata_path = os.path.join(music_dir, metadata_filename)
            
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        # Return information about the saved asset
        result = {
            "path": file_path,
            "filename": filename,
            "asset_type": "music",
            "metadata_path": metadata_path
        }
        
        return result
    
    async def save_final_video(
        self, 
        task_dir: Dict[str, Any], 
        file_data: Union[bytes, BinaryIO], 
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save the final video to the appropriate location in the hierarchical structure.
        
        Args:
            task_dir: The task directory structure
            file_data: The file data as bytes or a file-like object
            filename: Optional filename (will be generated if not provided)
            user_id: Optional user ID to include in the path
            metadata: Optional metadata to save with the asset
            
        Returns:
            Dictionary with information about the saved asset
        """
        import os
        import json
        
        # Generate a unique filename if not provided
        if not filename:
            filename = f"final_video_{uuid.uuid4()}.mp4"
        
        # Get the final directory
        final_dir = task_dir["final"]
        
        # Create the full path
        file_path = os.path.join(final_dir, filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            if hasattr(file_data, "read"):
                # It's a file-like object
                f.write(file_data.read())
            else:
                # It's bytes
                f.write(file_data)
        
        # Save metadata if provided
        metadata_path = None
        if metadata:
            metadata_filename = f"{os.path.splitext(filename)[0]}_metadata.json"
            metadata_path = os.path.join(final_dir, metadata_filename)
            
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        # Return information about the saved asset
        result = {
            "path": file_path,
            "filename": filename,
            "asset_type": "final_video",
            "metadata_path": metadata_path
        }
        
        return result
    
    async def save_task_metadata(
        self, 
        task_dir: Dict[str, Any], 
        metadata: Dict[str, Any]
    ) -> str:
        """
        Save metadata for the entire task.
        
        Args:
            task_dir: The task directory structure
            metadata: The metadata to save
            
        Returns:
            Path to the saved metadata file
        """
        import os
        import json
        
        # Create the metadata filename
        filename = "task_metadata.json"
        
        # Create the full path
        file_path = os.path.join(task_dir["base"], filename)
        
        # Save the metadata
        with open(file_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return file_path
