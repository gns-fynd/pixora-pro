"""
File utilities for Pixora AI Video Creation Platform
"""
import os
import uuid
import tempfile
import json
from typing import Dict, Any, Optional, List, Union
import logging
import requests

# Import services
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Get storage bucket names from environment variables
VIDEOS_BUCKET = os.getenv("STORAGE_VIDEOS_BUCKET", "videos")
IMAGES_BUCKET = os.getenv("STORAGE_IMAGES_BUCKET", "images")
AUDIO_BUCKET = os.getenv("STORAGE_AUDIO_BUCKET", "audio")
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "supabase")

def ensure_storage_buckets():
    """Ensure all storage buckets exist in Supabase."""
    if not hasattr(supabase_service, 'storage') or not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Cannot ensure buckets exist.")
        return
    
    buckets = [VIDEOS_BUCKET, IMAGES_BUCKET, AUDIO_BUCKET]
    
    for bucket_name in buckets:
        try:
            # Check if the bucket exists
            try:
                all_buckets = supabase_service.storage.list_buckets()
                bucket_exists = any(bucket["name"] == bucket_name for bucket in all_buckets)
            except Exception as e:
                logger.warning(f"Error listing buckets: {str(e)}")
                # Assume bucket doesn't exist if we can't list buckets
                bucket_exists = False
            
            # Create the bucket if it doesn't exist
            if not bucket_exists:
                try:
                    supabase_service.storage.create_bucket(bucket_name, {"public": True})
                    logger.info(f"Created Supabase storage bucket: {bucket_name}")
                except Exception as e:
                    logger.warning(f"Error creating bucket {bucket_name}: {str(e)}")
                    # Continue with next bucket even if this one fails
        except Exception as e:
            logger.error(f"Error ensuring bucket {bucket_name} exists: {str(e)}")

# Call this function to ensure buckets exist
ensure_storage_buckets()

def get_file_url(storage_path: str, bucket_name: str = VIDEOS_BUCKET) -> str:
    """
    Get the public URL for a file in Supabase storage.
    
    Args:
        storage_path: Path to the file in Supabase storage
        bucket_name: Name of the bucket
        
    Returns:
        str: Public URL to access the file
    """
    if not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Cannot get file URL.")
        return f"/api/fallback/{storage_path}"
    
    try:
        # Get the public URL from Supabase
        url = supabase_service.storage.from_(bucket_name).get_public_url(storage_path)
        return url
    except Exception as e:
        logger.error(f"Error getting file URL: {str(e)}")
        return f"/api/fallback/{storage_path}"

def get_task_storage_path(task_id: str, prompt: str) -> str:
    """
    Get the storage path for a task.
    
    Args:
        task_id: ID of the task
        prompt: User prompt for the task
        
    Returns:
        str: Storage path for the task
    """
    # Create a directory name from the prompt and task ID
    # Use the first 10 characters of the prompt (or fewer if the prompt is shorter)
    prompt_prefix = prompt[:10].replace(" ", "_").lower()
    dir_name = f"{prompt_prefix}_{task_id}"
    
    # Return the storage path
    return f"tasks/{dir_name}"

def get_scene_storage_path(task_storage_path: str, scene_index: int) -> str:
    """
    Get the storage path for a scene within a task.
    
    Args:
        task_storage_path: Storage path for the task
        scene_index: Index of the scene
        
    Returns:
        str: Storage path for the scene
    """
    # Return the storage path
    return f"{task_storage_path}/scene{scene_index}"

def get_music_storage_path(task_storage_path: str) -> str:
    """
    Get the storage path for music within a task.
    
    Args:
        task_storage_path: Storage path for the task
        
    Returns:
        str: Storage path for the music
    """
    # Return the storage path
    return f"{task_storage_path}/music"

def save_file(file_content: bytes, storage_path: str, bucket_name: str = VIDEOS_BUCKET) -> Dict[str, Any]:
    """
    Save a file to Supabase storage.
    
    Args:
        file_content: Content of the file
        storage_path: Path to save the file to in Supabase storage
        bucket_name: Name of the bucket
        
    Returns:
        Dict: Information about the saved file
    """
    # Create a temporary file as fallback
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        logger.debug(f"Created temporary file: {temp_path}")
    except Exception as e:
        logger.warning(f"Failed to create temporary file: {str(e)}")
    
    # Check if Supabase storage is available
    if not hasattr(supabase_service, 'storage') or not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Using local storage fallback.")
        
        if temp_path:
            logger.info(f"Saved file to temporary location: {temp_path}")
            
            # Return information about the saved file
            return {
                "path": storage_path,
                "url": f"/api/fallback/{storage_path}",
                "size": len(file_content),
                "temp_path": temp_path
            }
        else:
            # If we couldn't create a temporary file, return minimal information
            return {
                "path": storage_path,
                "url": f"/api/fallback/{storage_path}",
                "size": len(file_content)
            }
    
    # Try to save to Supabase
    try:
        # Ensure the bucket exists
        try:
            ensure_storage_buckets()
        except Exception as e:
            logger.warning(f"Error ensuring buckets exist: {str(e)}")
        
        # Create parent directories if needed
        parent_dir = os.path.dirname(storage_path)
        if parent_dir:
            try:
                # This is a no-op in Supabase, but we keep it for clarity
                logger.debug(f"Ensuring parent directory exists: {parent_dir}")
            except Exception as e:
                logger.warning(f"Error ensuring parent directory exists: {str(e)}")
        
        # Upload the file to Supabase
        try:
            supabase_service.storage.from_(bucket_name).upload(storage_path, file_content)
            logger.info(f"Saved file to Supabase storage: {storage_path}")
        except Exception as e:
            logger.error(f"Error uploading file to Supabase: {str(e)}")
            raise
        
        # Get the public URL
        try:
            url = supabase_service.storage.from_(bucket_name).get_public_url(storage_path)
        except Exception as e:
            logger.warning(f"Error getting public URL: {str(e)}")
            url = f"/api/fallback/{storage_path}"
        
        # Return information about the saved file
        result = {
            "path": storage_path,
            "url": url,
            "size": len(file_content)
        }
        
        # Add temporary path if available
        if temp_path:
            result["temp_path"] = temp_path
        
        return result
    except Exception as e:
        logger.error(f"Error saving file to Supabase storage: {str(e)}")
        
        # Fall back to temporary file
        if temp_path:
            logger.info(f"Falling back to temporary location: {temp_path}")
            
            # Return information about the saved file
            return {
                "path": storage_path,
                "url": f"/api/fallback/{storage_path}",
                "size": len(file_content),
                "temp_path": temp_path
            }
        else:
            # If we couldn't create a temporary file, return minimal information
            return {
                "path": storage_path,
                "url": f"/api/fallback/{storage_path}",
                "size": len(file_content)
            }

def save_character_image(task_storage_path: str, character_id: str, image_content: bytes) -> Dict[str, Any]:
    """
    Save a character image for a task.
    
    Args:
        task_storage_path: Storage path for the task
        character_id: ID of the character
        image_content: Content of the image
        
    Returns:
        Dict: Information about the saved image
    """
    # Create the storage path
    storage_path = f"{task_storage_path}/characters/{character_id}.png"
    
    # Save the file
    result = save_file(image_content, storage_path)
    
    # Add additional metadata
    result["type"] = "character_image"
    result["character_id"] = character_id
    
    return result

def save_scene_image(task_storage_path: str, scene_index: int, image_content: bytes) -> Dict[str, Any]:
    """
    Save a scene image for a task.
    
    Args:
        task_storage_path: Storage path for the task
        scene_index: Index of the scene
        image_content: Content of the image
        
    Returns:
        Dict: Information about the saved image
    """
    # Create the storage path
    scene_storage_path = get_scene_storage_path(task_storage_path, scene_index)
    storage_path = f"{scene_storage_path}/image.png"
    
    # Save the file
    result = save_file(image_content, storage_path)
    
    # Add additional metadata
    result["type"] = "scene_image"
    result["scene_index"] = scene_index
    
    return result

def save_scene_audio(task_storage_path: str, scene_index: int, audio_content: bytes) -> Dict[str, Any]:
    """
    Save scene audio for a task.
    
    Args:
        task_storage_path: Storage path for the task
        scene_index: Index of the scene
        audio_content: Content of the audio
        
    Returns:
        Dict: Information about the saved audio
    """
    # Create the storage path
    scene_storage_path = get_scene_storage_path(task_storage_path, scene_index)
    storage_path = f"{scene_storage_path}/audio.mp3"
    
    # Save the file
    result = save_file(audio_content, storage_path)
    
    # Add additional metadata
    result["type"] = "scene_audio"
    result["scene_index"] = scene_index
    
    return result

def save_scene_video(task_storage_path: str, scene_index: int, video_content: bytes) -> Dict[str, Any]:
    """
    Save a scene video for a task.
    
    Args:
        task_storage_path: Storage path for the task
        scene_index: Index of the scene
        video_content: Content of the video
        
    Returns:
        Dict: Information about the saved video
    """
    # Create the storage path
    scene_storage_path = get_scene_storage_path(task_storage_path, scene_index)
    storage_path = f"{scene_storage_path}/video.mp4"
    
    # Save the file
    result = save_file(video_content, storage_path)
    
    # Add additional metadata
    result["type"] = "scene_video"
    result["scene_index"] = scene_index
    
    return result

def save_music(task_storage_path: str, music_id: str, scene_indexes: List[int], music_content: bytes) -> Dict[str, Any]:
    """
    Save background music for a task.
    
    Args:
        task_storage_path: Storage path for the task
        music_id: ID of the music
        scene_indexes: List of scene indexes that use this music
        music_content: Content of the music
        
    Returns:
        Dict: Information about the saved music
    """
    # Create the storage path
    music_storage_path = get_music_storage_path(task_storage_path)
    
    # Create a filename based on the scene indexes
    scene_str = "_".join([str(i) for i in scene_indexes])
    storage_path = f"{music_storage_path}/clip_{scene_str}.mp3"
    
    # Save the file
    result = save_file(music_content, storage_path)
    
    # Add additional metadata
    result["type"] = "music"
    result["music_id"] = music_id
    result["scene_indexes"] = scene_indexes
    
    return result

def save_final_video(task_storage_path: str, video_content: bytes) -> Dict[str, Any]:
    """
    Save the final video for a task.
    
    Args:
        task_storage_path: Storage path for the task
        video_content: Content of the video
        
    Returns:
        Dict: Information about the saved video
    """
    # Create the storage path
    storage_path = f"{task_storage_path}/fullvideo.mp4"
    
    # Save the file
    result = save_file(video_content, storage_path)
    
    # Add additional metadata
    result["type"] = "final_video"
    
    return result

def save_script(task_storage_path: str, script_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save the script for a task.
    
    Args:
        task_storage_path: Storage path for the task
        script_content: Content of the script
        
    Returns:
        Dict: Information about the saved script
    """
    # Create the storage path
    storage_path = f"{task_storage_path}/script.json"
    
    # Convert the script to JSON
    script_json = json.dumps(script_content, indent=2)
    
    # Save the file
    result = save_file(script_json.encode("utf-8"), storage_path)
    
    # Add additional metadata
    result["type"] = "script"
    
    return result

def save_uploaded_file(file_content: bytes, file_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Save an uploaded file to the uploads bucket.
    
    Args:
        file_content: Content of the file
        file_name: Optional name for the file
        
    Returns:
        Dict: Information about the saved file
    """
    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())
    
    # Determine file extension
    extension = ""
    if file_name:
        extension = os.path.splitext(file_name)[1]
    
    # Create the storage path
    storage_path = f"{file_id}{extension}"
    
    # Save the file
    result = save_file(file_content, storage_path, IMAGES_BUCKET)
    
    # Add additional metadata
    result["type"] = "uploaded_file"
    result["id"] = file_id
    result["name"] = file_name
    
    return result

def download_file(file_url: str) -> Optional[bytes]:
    """
    Download a file from a URL.
    
    Args:
        file_url: URL of the file
        
    Returns:
        Optional[bytes]: Content of the file, or None if the file couldn't be downloaded
    """
    # Check if the URL is a Supabase URL
    if supabase_service.storage and (
        "supabase" in file_url or 
        file_url.startswith(supabase_service.url)
    ):
        # Extract the bucket and path from the URL
        # This is a simplified approach and might need to be adjusted based on the actual URL format
        try:
            # Try to download using the Supabase client
            # This is a placeholder and might need to be adjusted based on the actual Supabase API
            path_parts = file_url.split("/storage/v1/object/public/")
            if len(path_parts) > 1:
                bucket_path = path_parts[1].split("/", 1)
                bucket = bucket_path[0]
                path = bucket_path[1] if len(bucket_path) > 1 else ""
                
                content = supabase_service.download_file(path, bucket)
                if content:
                    return content
        except Exception as e:
            logger.error(f"Error downloading file from Supabase: {str(e)}")
    
    # If not a Supabase URL or download failed, try to download using requests
    try:
        response = requests.get(file_url)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.error(f"Error downloading file from URL: {str(e)}")
    
    # If all methods failed, return None
    return None

def delete_file(storage_path: str, bucket_name: str = VIDEOS_BUCKET) -> bool:
    """
    Delete a file from Supabase storage.
    
    Args:
        storage_path: Path to the file in Supabase storage
        bucket_name: Name of the bucket
        
    Returns:
        bool: True if the file was deleted, False otherwise
    """
    if not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Cannot delete file.")
        return False
    
    try:
        # Delete the file from Supabase
        supabase_service.storage.from_(bucket_name).remove([storage_path])
        logger.info(f"Deleted file from Supabase storage: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file from Supabase storage: {str(e)}")
        return False

def delete_directory(storage_path: str, bucket_name: str = VIDEOS_BUCKET) -> bool:
    """
    Delete a directory and all its contents from Supabase storage.
    
    Args:
        storage_path: Path to the directory in Supabase storage
        bucket_name: Name of the bucket
        
    Returns:
        bool: True if the directory was deleted, False otherwise
    """
    if not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Cannot delete directory.")
        return False
    
    try:
        # List all files in the directory
        response = supabase_service.storage.from_(bucket_name).list(storage_path)
        
        # Delete each file
        for item in response:
            item_path = f"{storage_path}/{item['name']}"
            
            # If the item is a folder, recursively delete it
            if item.get("id") is None:  # This is a folder
                delete_directory(item_path, bucket_name)
            else:  # This is a file
                supabase_service.storage.from_(bucket_name).remove([item_path])
        
        logger.info(f"Deleted directory from Supabase storage: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting directory from Supabase storage: {str(e)}")
        return False

def get_task_storage_path_from_id(task_id: str) -> str:
    """
    Get the storage path for a task from its ID.
    
    Args:
        task_id: ID of the task
        
    Returns:
        str: Storage path for the task
    """
    if not hasattr(supabase_service, 'storage') or not supabase_service.storage:
        logger.warning("Supabase storage not initialized. Using default task storage path.")
        return f"tasks/task_{task_id}"
    
    try:
        # List all directories in the tasks directory
        try:
            response = supabase_service.storage.from_(VIDEOS_BUCKET).list("tasks")
            
            # Find the directory that ends with the task ID
            for item in response:
                if item.get("id") is not None and item["name"].endswith(task_id):
                    return f"tasks/{item['name']}"
        except Exception as e:
            logger.warning(f"Error listing tasks directory: {str(e)}")
        
        # If we couldn't find the task or there was an error, create a new path
        return f"tasks/task_{task_id}"
    except Exception as e:
        logger.error(f"Error getting task storage path: {str(e)}")
        return f"tasks/task_{task_id}"
