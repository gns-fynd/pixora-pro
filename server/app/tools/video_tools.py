"""
Video generation tools for Pixora AI Video Creation Platform
"""
import os
import json
import uuid
import subprocess
import tempfile
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import shutil
import logging
import requests

# Import utilities
from ..utils.file_utils import (
    get_task_storage_path_from_id,
    save_scene_video,
    save_final_video
)
from ..utils.audio_utils import (
    get_audio_duration,
    normalize_audio_duration
)
from ..utils.video_utils import (
    get_video_duration,
    create_static_image_video,
    normalize_video_duration,
    apply_transition,
    stitch_videos
)

# Import services
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

async def create_scene_video_with_motion(
    task_id: str,
    scene_index: int,
    scene_image: str,
    audio_url: str,
    prompt: str,
    duration: float
) -> Dict[str, Any]:
    """
    Create a video for a scene by first generating a motion video from the image,
    then combining it with audio.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        scene_image: URL to the scene image (must be a hosted URL)
        audio_url: URL to the audio file
        prompt: Text description to guide the video generation
        duration: Duration of the video in seconds
        
    Returns:
        Dict: A dictionary containing the video URL and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Import fal_client here to avoid circular imports
        import fal_client
        
        # Download the scene image if it's a URL
        if scene_image.startswith(('http://', 'https://')):
            logger.info(f"Downloading scene image from: {scene_image}")
            image_response = requests.get(scene_image)
            
            if image_response.status_code != 200:
                logger.error(f"Failed to download scene image: HTTP {image_response.status_code}")
                return {"error": f"Failed to download scene image: HTTP {image_response.status_code}"}
            
            scene_image_content = image_response.content
            
            # Save to a temporary file
            temp_image_path = f"/tmp/scene_{task_id}_{scene_index}.png"
            with open(temp_image_path, "wb") as f:
                f.write(scene_image_content)
            
            # Upload the image to FAL to get a hosted URL
            try:
                scene_image = fal_client.upload_file(temp_image_path)
                logger.info(f"Uploaded scene image to FAL: {scene_image}")
            except Exception as e:
                logger.error(f"Error uploading image to FAL: {str(e)}")
                # Fall back to static image video
                return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
            
            # Remove the temporary file
            try:
                os.remove(temp_image_path)
            except:
                pass
        
        # Download the audio if it's a URL
        if audio_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading audio from: {audio_url}")
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: HTTP {audio_response.status_code}")
                return {"error": f"Failed to download audio: HTTP {audio_response.status_code}"}
            
            audio_content = audio_response.content
            
            # Save to a temporary file
            temp_audio_path = f"/tmp/audio_{task_id}_{scene_index}.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_content)
            
            # Get the actual duration of the audio file
            actual_duration = get_audio_duration(temp_audio_path)
            
            # Use the actual duration if available, otherwise use the provided duration
            video_duration = actual_duration if actual_duration is not None else duration
            
            # Remove the temporary file
            try:
                os.remove(temp_audio_path)
            except:
                pass
        else:
            video_duration = duration
        
        # Define the callback function for progress updates
        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    logger.info(f"Kling progress: {log['message']}")
        
        logger.info(f"Generating video from image with Kling 1.6")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Duration: {video_duration} seconds")
        
        # Call the Kling 1.6 model
        try:
            result = fal_client.subscribe(
                "fal-ai/kling-video/v1.6/pro/image-to-video",
                arguments={
                    "prompt": prompt,
                    "image_url": scene_image,
                    "duration": str(int(min(30, max(1, video_duration)))),  # Ensure duration is within 1-30 seconds and an integer
                    "aspect_ratio": "16:9",
                    "negative_prompt": "blur, distort, and low quality",
                    "cfg_scale": 0.5
                },
                with_logs=True,
                on_queue_update=on_queue_update,
            )
            
            # Extract the video URL from the result
            video_url = result.get("video", {}).get("url")
            
            if not video_url:
                logger.warning("No video URL returned from Kling API")
                # Fall back to static image video
                return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
            
            # Download the video
            logger.info(f"Downloading video from: {video_url}")
            video_response = requests.get(video_url)
            
            if video_response.status_code != 200:
                logger.error(f"Error downloading video: HTTP {video_response.status_code}")
                # Fall back to static image video
                return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
            
            # Get the video content
            motion_video_content = video_response.content
            
            # Save to a temporary file
            temp_video_path = f"/tmp/video_{task_id}_{scene_index}.mp4"
            with open(temp_video_path, "wb") as f:
                f.write(motion_video_content)
            
            # Combine with audio
            output_video_content = await _combine_video_with_audio(temp_video_path, audio_url)
            
            # Remove the temporary file
            try:
                os.remove(temp_video_path)
            except:
                pass
            
            # Save the video to Supabase storage
            result = save_scene_video(task_storage_path, scene_index, output_video_content)
            
            # Add additional metadata
            result["scene_image"] = scene_image
            result["audio_url"] = audio_url
            result["prompt"] = prompt
            result["duration"] = video_duration
            result["has_motion"] = True
            
            # Save the asset to the database
            if supabase_service.client:
                supabase_service.save_asset(
                    task_id=task_id,
                    asset_type="video",
                    url=result["url"],
                    storage_path=result["path"],
                    scene_index=scene_index,
                    metadata={
                        "scene_image": scene_image,
                        "audio_url": audio_url,
                        "prompt": prompt,
                        "duration": video_duration,
                        "has_motion": True
                    }
                )
            
            return result
        except Exception as e:
            logger.error(f"Error calling Kling API: {str(e)}")
            # Fall back to static image video
            return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
        
    except Exception as e:
        logger.error(f"Error creating scene video with motion: {str(e)}")
        # Fall back to static image video if we have the image content
        if 'scene_image_content' in locals():
            return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
        else:
            raise

async def _create_static_image_video(
    task_id: str,
    scene_index: int,
    image_content: bytes,
    audio_url: str,
    duration: float
) -> Dict[str, Any]:
    """
    Create a video from a static image and audio.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        image_content: Content of the image
        audio_url: URL to the audio file
        duration: Duration of the video in seconds
        
    Returns:
        Dict: A dictionary containing the video URL and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Download the audio if it's a URL
        if audio_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading audio from: {audio_url}")
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: HTTP {audio_response.status_code}")
                return {"error": f"Failed to download audio: HTTP {audio_response.status_code}"}
            
            audio_content = audio_response.content
        else:
            # Read the audio file
            with open(audio_url, "rb") as f:
                audio_content = f.read()
        
        # Create the static image video
        video_content = create_static_image_video(image_content, audio_content, duration)
        
        # Save the video to Supabase storage
        result = save_scene_video(task_storage_path, scene_index, video_content)
        
        # Add additional metadata
        result["audio_url"] = audio_url
        result["duration"] = duration
        result["has_motion"] = False
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="video",
                url=result["url"],
                storage_path=result["path"],
                scene_index=scene_index,
                metadata={
                    "audio_url": audio_url,
                    "duration": duration,
                    "has_motion": False
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error creating static image video: {str(e)}")
        raise

async def _combine_video_with_audio(video_path: str, audio_url: str) -> bytes:
    """
    Combine a video with audio.
    
    Args:
        video_path: Path to the video file
        audio_url: URL to the audio file
        
    Returns:
        bytes: Content of the combined video
    """
    try:
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as output_file:
            output_path = output_file.name
        
        # Download the audio if it's a URL
        if audio_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading audio from: {audio_url}")
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: HTTP {audio_response.status_code}")
                # Return the original video
                with open(video_path, "rb") as f:
                    return f.read()
            
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
                audio_path = audio_file.name
                audio_file.write(audio_response.content)
        else:
            audio_path = audio_url
        
        # Use FFmpeg to combine the video with audio
        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the output video content
        with open(output_path, "rb") as f:
            output_video_content = f.read()
        
        # Clean up temporary files
        try:
            if audio_url.startswith(('http://', 'https://')):
                os.remove(audio_path)
            os.remove(output_path)
        except:
            pass
        
        return output_video_content
    except Exception as e:
        logger.error(f"Error combining video with audio: {str(e)}")
        # Return the original video
        with open(video_path, "rb") as f:
            return f.read()

async def normalize_duration(task_id: str, scene_index: int, video_url: str, target_duration: float) -> Dict[str, Any]:
    """
    Adjust a video's duration to match the target duration.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        video_url: URL to the video file
        target_duration: Target duration in seconds
        
    Returns:
        Dict: A dictionary containing the normalized video URL and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Download the video if it's a URL
        if video_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading video from: {video_url}")
            video_response = requests.get(video_url)
            
            if video_response.status_code != 200:
                logger.error(f"Failed to download video: HTTP {video_response.status_code}")
                return {"error": f"Failed to download video: HTTP {video_response.status_code}"}
            
            video_content = video_response.content
        else:
            # Read the video file
            with open(video_url, "rb") as f:
                video_content = f.read()
        
        # Normalize the video duration
        normalized_video_content = normalize_video_duration(video_content, target_duration)
        
        # Save the video to Supabase storage
        result = save_scene_video(task_storage_path, scene_index, normalized_video_content)
        
        # Add additional metadata
        result["original_url"] = video_url
        result["target_duration"] = target_duration
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="video",
                url=result["url"],
                storage_path=result["path"],
                scene_index=scene_index,
                metadata={
                    "original_url": video_url,
                    "target_duration": target_duration
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error normalizing video duration: {str(e)}")
        raise

async def apply_transition(task_id: str, video1_url: str, video2_url: str, transition_type: str) -> Dict[str, Any]:
    """
    Apply a transition effect between two videos.
    
    Args:
        task_id: ID of the task
        video1_url: URL to the first video
        video2_url: URL to the second video
        transition_type: Type of transition (fade, slide_left, slide_right, etc.)
        
    Returns:
        Dict: A dictionary containing the video URL with transition and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Download the videos if they're URLs
        if video1_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading first video from: {video1_url}")
            video1_response = requests.get(video1_url)
            
            if video1_response.status_code != 200:
                logger.error(f"Failed to download first video: HTTP {video1_response.status_code}")
                return {"error": f"Failed to download first video: HTTP {video1_response.status_code}"}
            
            video1_content = video1_response.content
        else:
            # Read the video file
            with open(video1_url, "rb") as f:
                video1_content = f.read()
        
        if video2_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading second video from: {video2_url}")
            video2_response = requests.get(video2_url)
            
            if video2_response.status_code != 200:
                logger.error(f"Failed to download second video: HTTP {video2_response.status_code}")
                return {"error": f"Failed to download second video: HTTP {video2_response.status_code}"}
            
            video2_content = video2_response.content
        else:
            # Read the video file
            with open(video2_url, "rb") as f:
                video2_content = f.read()
        
        # Apply the transition
        transition_video_content = apply_transition(video1_content, video2_content, transition_type)
        
        # Generate a unique ID for the video
        video_id = str(uuid.uuid4())
        
        # Save the video to Supabase storage
        result = save_scene_video(task_storage_path, video_id, transition_video_content)
        
        # Add additional metadata
        result["video1_url"] = video1_url
        result["video2_url"] = video2_url
        result["transition_type"] = transition_type
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="transition_video",
                url=result["url"],
                storage_path=result["path"],
                metadata={
                    "video1_url": video1_url,
                    "video2_url": video2_url,
                    "transition_type": transition_type
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error applying transition: {str(e)}")
        raise

async def stitch_video(task_id: str, scene_videos: List[str], transitions: List[str], music_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Stitch multiple scene videos with audio and transitions into a final video.
    
    Args:
        task_id: ID of the task
        scene_videos: List of URLs to scene videos
        transitions: List of transition types
        music_url: Optional URL to background music
        
    Returns:
        Dict: A dictionary containing the final stitched video URL and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Download the videos if they're URLs
        video_contents = []
        for i, video_url in enumerate(scene_videos):
            if video_url.startswith(('http://', 'https://')):
                logger.info(f"Downloading video {i+1} from: {video_url}")
                video_response = requests.get(video_url)
                
                if video_response.status_code != 200:
                    logger.error(f"Failed to download video {i+1}: HTTP {video_response.status_code}")
                    return {"error": f"Failed to download video {i+1}: HTTP {video_response.status_code}"}
                
                video_contents.append(video_response.content)
            else:
                # Read the video file
                with open(video_url, "rb") as f:
                    video_contents.append(f.read())
        
        # Download the music if it's a URL
        music_content = None
        if music_url:
            if music_url.startswith(('http://', 'https://')):
                logger.info(f"Downloading music from: {music_url}")
                music_response = requests.get(music_url)
                
                if music_response.status_code != 200:
                    logger.error(f"Failed to download music: HTTP {music_response.status_code}")
                    music_content = None
                else:
                    music_content = music_response.content
            else:
                # Read the music file
                with open(music_url, "rb") as f:
                    music_content = f.read()
        
        # Stitch the videos
        stitched_video_content = stitch_videos(video_contents, transitions, music_content)
        
        # Save the video to Supabase storage
        result = save_final_video(task_storage_path, stitched_video_content)
        
        # Add additional metadata
        result["scene_videos"] = scene_videos
        result["transitions"] = transitions
        result["music_url"] = music_url
        
        # Save the video to the database
        if supabase_service.client:
            # Get the duration of the video
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_file.write(stitched_video_content)
                temp_path = temp_file.name
            
            duration = get_video_duration(temp_path)
            
            try:
                os.remove(temp_path)
            except:
                pass
            
            supabase_service.save_video(
                task_id=task_id,
                url=result["url"],
                storage_path=result["path"],
                duration=duration or 0
            )
        
        return result
    except Exception as e:
        logger.error(f"Error stitching video: {str(e)}")
        raise
