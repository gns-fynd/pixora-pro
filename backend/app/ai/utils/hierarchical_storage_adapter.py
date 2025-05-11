"""
Hierarchical storage adapter for the video agent.

This module provides an enhanced storage adapter that uses a hierarchical folder structure
for organizing files related to video generation.
"""
import os
import uuid
import json
import time
import logging
from typing import Optional, BinaryIO, Union, Dict, Any, List
from pathlib import Path
from datetime import datetime

from fastapi import Depends

from app.services.storage import StorageManager
from app.ai.utils.storage_adapter import StorageAdapter


# Set up logging
logger = logging.getLogger(__name__)


class HierarchicalStorageAdapter(StorageAdapter):
    """
    Enhanced storage adapter for the video agent that uses a hierarchical folder structure.
    
    This adapter organizes files in a hierarchical structure:
    {timestamp}-{task_id}/
    ├── scene_1/
    │   ├── script.json
    │   ├── video/
    │   │   └── scene_1.mp4
    │   ├── audio/
    │   │   └── narration.mp3
    │   └── image/
    │       └── scene_image.png
    ├── scene_2/
    │   └── ...
    ├── music/
    │   └── background.mp3
    └── final_video.mp4
    """
    
    def __init__(self, storage_manager: StorageManager = Depends()):
        """
        Initialize the hierarchical storage adapter.
        
        Args:
            storage_manager: The storage manager
        """
        super().__init__(storage_manager)
        self.metadata = {}
    
    async def initialize_task_storage(self, task_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Initialize storage for a new task.
        
        Args:
            task_id: The task ID
            user_id: Optional user ID
            
        Returns:
            Dictionary with storage information
        """
        # Create a timestamp for the folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create the base folder name
        base_folder = f"{timestamp}-{task_id}"
        
        # Store metadata
        self.metadata[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "base_folder": base_folder,
            "created_at": time.time(),
            "updated_at": time.time(),
            "scenes": {},
            "music": {},
            "final_video": None
        }
        
        # Save metadata to storage
        await self._save_metadata(task_id)
        
        logger.info(f"Initialized storage for task {task_id} with base folder {base_folder}")
        
        return self.metadata[task_id]
    
    async def _save_metadata(self, task_id: str) -> None:
        """
        Save metadata to storage.
        
        Args:
            task_id: The task ID
        """
        if task_id not in self.metadata:
            logger.warning(f"No metadata found for task {task_id}")
            return
        
        # Create a temporary file for the metadata
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Write the metadata to the temporary file
            with open(temp_path, "w") as f:
                json.dump(self.metadata[task_id], f, indent=2)
            
            # Upload the metadata file
            base_folder = self.metadata[task_id]["base_folder"]
            filename = f"metadata.json"
            
            # Save to storage
            await self.storage_manager.upload_file(
                file_data=open(temp_path, "rb"),
                bucket=self.storage_manager.videos_bucket,
                path=f"{base_folder}/{filename}",
                content_type="application/json"
            )
            
            logger.info(f"Saved metadata for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error saving metadata for task {task_id}: {str(e)}")
            raise
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def save_scene_script(
        self, 
        task_id: str, 
        scene_index: int, 
        script_data: Dict[str, Any]
    ) -> str:
        """
        Save a scene script to storage.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            script_data: The script data
            
        Returns:
            The URL of the saved script
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Create a temporary file for the script
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Write the script data to the temporary file
            with open(temp_path, "w") as f:
                json.dump(script_data, f, indent=2)
            
            # Get the base folder from metadata
            base_folder = self.metadata[task_id]["base_folder"]
            
            # Create the scene folder path
            scene_folder = f"scene_{scene_index}"
            filename = "script.json"
            
            # Full path
            full_path = f"{base_folder}/{scene_folder}/{filename}"
            
            # Save to storage
            url = await self.storage_manager.upload_file(
                file_data=open(temp_path, "rb"),
                bucket=self.storage_manager.videos_bucket,
                path=full_path,
                content_type="application/json"
            )
            
            # Update metadata
            if "scenes" not in self.metadata[task_id]:
                self.metadata[task_id]["scenes"] = {}
            
            if str(scene_index) not in self.metadata[task_id]["scenes"]:
                self.metadata[task_id]["scenes"][str(scene_index)] = {}
            
            self.metadata[task_id]["scenes"][str(scene_index)]["script"] = {
                "url": url,
                "path": full_path,
                "updated_at": time.time()
            }
            
            # Save metadata
            await self._save_metadata(task_id)
            
            logger.info(f"Saved script for scene {scene_index} of task {task_id}")
            
            return url
            
        except Exception as e:
            logger.error(f"Error saving script for scene {scene_index} of task {task_id}: {str(e)}")
            raise
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def save_scene_image(
        self, 
        task_id: str, 
        scene_index: int, 
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None
    ) -> str:
        """
        Save a scene image to storage.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            file_data: The image data
            filename: Optional filename
            
        Returns:
            The URL of the saved image
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Generate a filename if not provided
        if not filename:
            ext = ".jpg"
            filename = f"scene_image_{uuid.uuid4()}{ext}"
        
        # Get the base folder from metadata
        base_folder = self.metadata[task_id]["base_folder"]
        
        # Create the scene folder path
        scene_folder = f"scene_{scene_index}"
        image_folder = "image"
        
        # Full path
        full_path = f"{base_folder}/{scene_folder}/{image_folder}/{filename}"
        
        # Save to storage
        url = await self.storage_manager.upload_file(
            file_data=file_data,
            bucket=self.storage_manager.images_bucket,
            path=full_path,
            content_type="image/jpeg"
        )
        
        # Update metadata
        if "scenes" not in self.metadata[task_id]:
            self.metadata[task_id]["scenes"] = {}
        
        if str(scene_index) not in self.metadata[task_id]["scenes"]:
            self.metadata[task_id]["scenes"][str(scene_index)] = {}
        
        if "images" not in self.metadata[task_id]["scenes"][str(scene_index)]:
            self.metadata[task_id]["scenes"][str(scene_index)]["images"] = []
        
        self.metadata[task_id]["scenes"][str(scene_index)]["images"].append({
            "url": url,
            "path": full_path,
            "filename": filename,
            "created_at": time.time()
        })
        
        # Save metadata
        await self._save_metadata(task_id)
        
        logger.info(f"Saved image for scene {scene_index} of task {task_id}")
        
        return url
    
    async def save_scene_audio(
        self, 
        task_id: str, 
        scene_index: int, 
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None,
        audio_type: str = "narration"
    ) -> str:
        """
        Save scene audio to storage.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            file_data: The audio data
            filename: Optional filename
            audio_type: The type of audio (narration, music, etc.)
            
        Returns:
            The URL of the saved audio
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Generate a filename if not provided
        if not filename:
            ext = ".mp3"
            filename = f"{audio_type}_{uuid.uuid4()}{ext}"
        
        # Get the base folder from metadata
        base_folder = self.metadata[task_id]["base_folder"]
        
        # Create the scene folder path
        scene_folder = f"scene_{scene_index}"
        audio_folder = "audio"
        
        # Full path
        full_path = f"{base_folder}/{scene_folder}/{audio_folder}/{filename}"
        
        # Save to storage
        url = await self.storage_manager.upload_file(
            file_data=file_data,
            bucket=self.storage_manager.audio_bucket,
            path=full_path,
            content_type="audio/mpeg"
        )
        
        # Update metadata
        if "scenes" not in self.metadata[task_id]:
            self.metadata[task_id]["scenes"] = {}
        
        if str(scene_index) not in self.metadata[task_id]["scenes"]:
            self.metadata[task_id]["scenes"][str(scene_index)] = {}
        
        if "audio" not in self.metadata[task_id]["scenes"][str(scene_index)]:
            self.metadata[task_id]["scenes"][str(scene_index)]["audio"] = {}
        
        self.metadata[task_id]["scenes"][str(scene_index)]["audio"][audio_type] = {
            "url": url,
            "path": full_path,
            "filename": filename,
            "created_at": time.time()
        }
        
        # Save metadata
        await self._save_metadata(task_id)
        
        logger.info(f"Saved {audio_type} audio for scene {scene_index} of task {task_id}")
        
        return url
    
    async def save_scene_video(
        self, 
        task_id: str, 
        scene_index: int, 
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None
    ) -> str:
        """
        Save a scene video to storage.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            file_data: The video data
            filename: Optional filename
            
        Returns:
            The URL of the saved video
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Generate a filename if not provided
        if not filename:
            ext = ".mp4"
            filename = f"scene_{scene_index}{ext}"
        
        # Get the base folder from metadata
        base_folder = self.metadata[task_id]["base_folder"]
        
        # Create the scene folder path
        scene_folder = f"scene_{scene_index}"
        video_folder = "video"
        
        # Full path
        full_path = f"{base_folder}/{scene_folder}/{video_folder}/{filename}"
        
        # Save to storage
        url = await self.storage_manager.upload_file(
            file_data=file_data,
            bucket=self.storage_manager.videos_bucket,
            path=full_path,
            content_type="video/mp4"
        )
        
        # Update metadata
        if "scenes" not in self.metadata[task_id]:
            self.metadata[task_id]["scenes"] = {}
        
        if str(scene_index) not in self.metadata[task_id]["scenes"]:
            self.metadata[task_id]["scenes"][str(scene_index)] = {}
        
        self.metadata[task_id]["scenes"][str(scene_index)]["video"] = {
            "url": url,
            "path": full_path,
            "filename": filename,
            "created_at": time.time()
        }
        
        # Save metadata
        await self._save_metadata(task_id)
        
        logger.info(f"Saved video for scene {scene_index} of task {task_id}")
        
        return url
    
    async def save_background_music(
        self, 
        task_id: str, 
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None
    ) -> str:
        """
        Save background music to storage.
        
        Args:
            task_id: The task ID
            file_data: The audio data
            filename: Optional filename
            
        Returns:
            The URL of the saved audio
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Generate a filename if not provided
        if not filename:
            ext = ".mp3"
            filename = f"background_music_{uuid.uuid4()}{ext}"
        
        # Get the base folder from metadata
        base_folder = self.metadata[task_id]["base_folder"]
        
        # Create the music folder path
        music_folder = "music"
        
        # Full path
        full_path = f"{base_folder}/{music_folder}/{filename}"
        
        # Save to storage
        url = await self.storage_manager.upload_file(
            file_data=file_data,
            bucket=self.storage_manager.audio_bucket,
            path=full_path,
            content_type="audio/mpeg"
        )
        
        # Update metadata
        if "music" not in self.metadata[task_id]:
            self.metadata[task_id]["music"] = {}
        
        self.metadata[task_id]["music"]["background"] = {
            "url": url,
            "path": full_path,
            "filename": filename,
            "created_at": time.time()
        }
        
        # Save metadata
        await self._save_metadata(task_id)
        
        logger.info(f"Saved background music for task {task_id}")
        
        return url
    
    async def save_final_video(
        self, 
        task_id: str, 
        file_data: Union[bytes, BinaryIO],
        filename: Optional[str] = None
    ) -> str:
        """
        Save the final video to storage.
        
        Args:
            task_id: The task ID
            file_data: The video data
            filename: Optional filename
            
        Returns:
            The URL of the saved video
        """
        # Check if we have metadata for this task
        if task_id not in self.metadata:
            await self.initialize_task_storage(task_id)
        
        # Generate a filename if not provided
        if not filename:
            ext = ".mp4"
            filename = f"final_video{ext}"
        
        # Get the base folder from metadata
        base_folder = self.metadata[task_id]["base_folder"]
        
        # Full path
        full_path = f"{base_folder}/{filename}"
        
        # Save to storage
        url = await self.storage_manager.upload_file(
            file_data=file_data,
            bucket=self.storage_manager.videos_bucket,
            path=full_path,
            content_type="video/mp4"
        )
        
        # Update metadata
        self.metadata[task_id]["final_video"] = {
            "url": url,
            "path": full_path,
            "filename": filename,
            "created_at": time.time()
        }
        
        # Save metadata
        await self._save_metadata(task_id)
        
        logger.info(f"Saved final video for task {task_id}")
        
        return url
    
    async def get_task_metadata(self, task_id: str) -> Dict[str, Any]:
        """
        Get metadata for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task metadata
        """
        # Check if we have metadata for this task in memory
        if task_id in self.metadata:
            return self.metadata[task_id]
        
        # Try to load metadata from storage
        try:
            # First, we need to find the base folder for this task
            # This is a bit tricky since we don't know the timestamp
            # We'll need to list all files in the videos bucket and look for a pattern
            
            # List all files in the videos bucket
            files = await self.storage_manager.list_files(self.storage_manager.videos_bucket)
            
            # Look for a folder that contains the task ID
            base_folder = None
            for file in files:
                if task_id in file and "metadata.json" in file:
                    # Extract the base folder from the file path
                    base_folder = os.path.dirname(file)
                    break
            
            if not base_folder:
                logger.warning(f"No metadata found for task {task_id}")
                return {}
            
            # Download the metadata file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                # Get the URL of the metadata file
                metadata_url = await self.storage_manager.get_file_url(
                    self.storage_manager.videos_bucket,
                    f"{base_folder}/metadata.json"
                )
                
                # Download the file
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(metadata_url)
                    response.raise_for_status()
                    
                    # Write the file to disk
                    with open(temp_path, "wb") as f:
                        f.write(response.content)
                    
                    # Load the metadata
                    with open(temp_path, "r") as f:
                        metadata = json.load(f)
                    
                    # Store in memory
                    self.metadata[task_id] = metadata
                    
                    return metadata
                    
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error loading metadata for task {task_id}: {str(e)}")
            return {}
    
    async def cleanup_task_storage(self, task_id: str) -> bool:
        """
        Clean up storage for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get metadata for this task
        metadata = await self.get_task_metadata(task_id)
        if not metadata:
            logger.warning(f"No metadata found for task {task_id}")
            return False
        
        # Get the base folder
        base_folder = metadata.get("base_folder")
        if not base_folder:
            logger.warning(f"No base folder found for task {task_id}")
            return False
        
        # List all files in the videos bucket with this base folder
        try:
            # List files in the videos bucket
            video_files = await self.storage_manager.list_files(
                self.storage_manager.videos_bucket,
                prefix=base_folder
            )
            
            # Delete each file
            for file in video_files:
                await self.storage_manager.delete_file(
                    self.storage_manager.videos_bucket,
                    file
                )
            
            # List files in the images bucket
            image_files = await self.storage_manager.list_files(
                self.storage_manager.images_bucket,
                prefix=base_folder
            )
            
            # Delete each file
            for file in image_files:
                await self.storage_manager.delete_file(
                    self.storage_manager.images_bucket,
                    file
                )
            
            # List files in the audio bucket
            audio_files = await self.storage_manager.list_files(
                self.storage_manager.audio_bucket,
                prefix=base_folder
            )
            
            # Delete each file
            for file in audio_files:
                await self.storage_manager.delete_file(
                    self.storage_manager.audio_bucket,
                    file
                )
            
            # Remove from memory
            if task_id in self.metadata:
                del self.metadata[task_id]
            
            logger.info(f"Cleaned up storage for task {task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up storage for task {task_id}: {str(e)}")
            return False
