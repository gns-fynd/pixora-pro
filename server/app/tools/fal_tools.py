"""
FAL.ai tools for Pixora AI Video Creation Platform with improved error handling and retry logic
"""
import os
import logging
import time
import json
from typing import Dict, Any, Optional, List, Union, Tuple
import requests
import base64

# Import utilities
from ..utils.file_utils import (
    get_task_storage_path_from_id,
    save_character_image,
    save_scene_image,
    save_scene_audio
)

# Import retry utilities
from ..utils.retry import (
    with_retry,
    handle_rate_limit_response,
    RateLimitExceeded,
    ServiceUnavailable
)

# Import telemetry
from ..utils.telemetry import traced, log_event

# Import services
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Import fal_client with fallback
try:
    import fal_client
    from pathlib import Path
    FAL_AVAILABLE = True
except ImportError:
    logger.warning("fal_client not installed. FAL.ai tools will not work.")
    FAL_AVAILABLE = False
    fal_client = None

# Initialize FAL client
def initialize_fal_client() -> bool:
    """
    Initialize the FAL client with API key from environment variables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    if not FAL_AVAILABLE:
        return False
    
    # Check for API key in environment variables
    fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_CLIENT_API_KEY")
    
    if not fal_key:
        logger.warning("FAL_KEY or FAL_CLIENT_API_KEY not set. FAL.ai tools will not work.")
        return False
    
    try:
        # Set FAL_KEY environment variable if not already set
        if not os.getenv("FAL_KEY"):
            os.environ["FAL_KEY"] = fal_key
        
        # Test the client by checking if it's configured
        if hasattr(fal_client, 'is_configured') and callable(fal_client.is_configured):
            if not fal_client.is_configured():
                fal_client.configure(api_key=fal_key)
        
        logger.info("FAL client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing FAL client: {str(e)}")
        return False

# Initialize the FAL client
FAL_INITIALIZED = initialize_fal_client() if FAL_AVAILABLE else False

# Define callback for FAL.ai queue updates
def on_queue_update(update: Any) -> None:
    """Callback for FAL.ai queue updates."""
    if hasattr(update, 'logs'):
        for log in update.logs:
            logger.info(f"FAL progress: {log.get('message', '')}")
    elif isinstance(update, dict) and 'logs' in update:
        for log in update['logs']:
            logger.info(f"FAL progress: {log.get('message', '')}")

# Validate FAL client before each operation
def validate_fal_client() -> None:
    """
    Validate that the FAL client is available and initialized.
    
    Raises:
        ImportError: If fal_client is not installed
        RuntimeError: If FAL client is not initialized
    """
    if not FAL_AVAILABLE:
        raise ImportError("fal_client not installed. Cannot use FAL.ai tools.")
    
    if not FAL_INITIALIZED:
        raise RuntimeError("FAL client not initialized. Please set FAL_KEY environment variable.")

@traced("generate_voice_over")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def generate_voice_over(
    task_id: str, 
    scene_index: int, 
    text: str, 
    voice_sample: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate text-to-speech audio from script text using Fal.ai ElevenLabs TTS API.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        text: The script text to convert to speech
        voice_sample: Optional URL to a voice sample to clone
        
    Returns:
        Dict: A dictionary containing the audio URL and duration
    """
    # Validate FAL client
    validate_fal_client()
    
    start_time = time.time()
    
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Default voice sample if none provided
        if voice_sample is None:
            voice_sample = "https://replicate.delivery/pbxt/MNaHFqDkZ0Y22hvppxotJazhRYe6TwhK78xAUTCoz3NB9bRV/voice_sample.wav"
        
        # Prepare parameters
        params = {
            "text": text,
            "model_name": "eleven_multilingual_v2"
        }
        
        # Add voice sample if provided
        if voice_sample:
            params["voice_sample"] = voice_sample
        
        logger.info(f"Calling Fal.ai ElevenLabs TTS API for scene: {scene_index}")
        
        # Call the Fal.ai ElevenLabs TTS API
        try:
            result = fal_client.subscribe(
                "fal-ai/elevenlabs/tts/multilingual-v2",
                arguments=params,
                with_logs=True,
                on_queue_update=on_queue_update
            )
        except Exception as e:
            logger.error(f"Error calling Fal.ai ElevenLabs TTS API: {str(e)}")
            raise ServiceUnavailable(f"Error calling Fal.ai ElevenLabs TTS API: {str(e)}")
        
        # Get the audio URL from the result
        audio_url = result.get("audio", {}).get("url")
        
        if not audio_url:
            raise ValueError("No audio URL returned from Fal.ai API")
        
        # Validate the URL
        if not audio_url.startswith("https://"):
            raise ValueError(f"Invalid audio URL: {audio_url}")
        
        # Download the audio from the URL
        logger.info(f"Downloading audio from: {audio_url}")
        audio_response = requests.get(audio_url)
        
        # Check for rate limits or server errors
        handle_rate_limit_response(audio_response, "Fal.ai")
        
        if audio_response.status_code != 200:
            raise ValueError(f"Failed to download audio: HTTP {audio_response.status_code}")
        
        audio_content = audio_response.content
        
        logger.info(f"Generated voice-over audio for scene: {scene_index}")
        
        # Save the audio to Supabase storage
        result = save_scene_audio(task_storage_path, scene_index, audio_content)
        
        # Add additional metadata
        result["text"] = text[:100] + "..." if len(text) > 100 else text  # Truncate long text
        result["duration"] = time.time() - start_time
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="audio",
                url=result["url"],
                storage_path=result["path"],
                scene_index=scene_index,
                metadata={"text": text}
            )
        
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error generating voice over: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            handle_rate_limit_response(e.response, "Fal.ai")
        raise ServiceUnavailable(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating voice over: {str(e)}")
        raise

@traced("create_scene_video_with_motion")
@with_retry(max_attempts=2, min_wait=5.0, max_wait=30.0)
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
    # Validate FAL client
    validate_fal_client()
    
    start_time = time.time()
    scene_image_content = None
    
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Download the scene image if it's a URL
        if scene_image.startswith(('http://', 'https://')):
            logger.info(f"Downloading scene image from: {scene_image}")
            image_response = requests.get(scene_image)
            
            # Check for rate limits or server errors
            handle_rate_limit_response(image_response, "Image Service")
            
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
                scene_image = await upload_file_to_fal(temp_image_path)
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
            
            # Check for rate limits or server errors
            handle_rate_limit_response(audio_response, "Audio Service")
            
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: HTTP {audio_response.status_code}")
                return {"error": f"Failed to download audio: HTTP {audio_response.status_code}"}
            
            audio_content = audio_response.content
            
            # Save to a temporary file
            temp_audio_path = f"/tmp/audio_{task_id}_{scene_index}.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_content)
            
            # Get the actual duration of the audio file
            from ..utils.audio_utils import get_audio_duration
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
        
        logger.info(f"Generating video from image with Kling 1.6")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Duration: {video_duration} seconds")
        
        # Call the Kling 1.6 model
        try:
            # Ensure duration is within 1-30 seconds and an integer
            clamped_duration = str(int(min(30, max(1, video_duration))))
            
            result = fal_client.subscribe(
                "fal-ai/kling-video/v1.6/pro/image-to-video",
                arguments={
                    "prompt": prompt,
                    "image_url": scene_image,
                    "duration": clamped_duration,
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
            
            # Check for rate limits or server errors
            handle_rate_limit_response(video_response, "Kling Video Service")
            
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
            # Import here to avoid circular imports
            from ..utils.video_utils import combine_video_with_audio
            output_video_content = await combine_video_with_audio(temp_video_path, audio_url)
            
            # Remove the temporary file
            try:
                os.remove(temp_video_path)
            except:
                pass
            
            # Save the video to Supabase storage
            from ..utils.file_utils import save_scene_video
            result = save_scene_video(task_storage_path, scene_index, output_video_content)
            
            # Add additional metadata
            result["scene_image"] = scene_image
            result["audio_url"] = audio_url
            result["prompt"] = prompt
            result["duration"] = video_duration
            result["has_motion"] = True
            result["processing_time"] = time.time() - start_time
            
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
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error creating scene video: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            handle_rate_limit_response(e.response, "Fal.ai")
        # Fall back to static image video if we have the image content
        if scene_image_content:
            return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
        raise ServiceUnavailable(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating scene video with motion: {str(e)}")
        # Fall back to static image video if we have the image content
        if scene_image_content:
            return await _create_static_image_video(task_id, scene_index, scene_image_content, audio_url, duration)
        raise

@traced("create_static_image_video")
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
    start_time = time.time()
    
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
            
            # Check for rate limits or server errors
            handle_rate_limit_response(audio_response, "Audio Service")
            
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: HTTP {audio_response.status_code}")
                return {"error": f"Failed to download audio: HTTP {audio_response.status_code}"}
            
            audio_content = audio_response.content
        else:
            # Read the audio file
            with open(audio_url, "rb") as f:
                audio_content = f.read()
        
        # Create the static image video
        from ..utils.video_utils import create_static_image_video
        video_content = create_static_image_video(image_content, audio_content, duration)
        
        # Save the video to Supabase storage
        from ..utils.file_utils import save_scene_video
        result = save_scene_video(task_storage_path, scene_index, video_content)
        
        # Add additional metadata
        result["audio_url"] = audio_url
        result["duration"] = duration
        result["has_motion"] = False
        result["processing_time"] = time.time() - start_time
        
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

@traced("upload_file_to_fal")
@with_retry(max_attempts=3, min_wait=1.0, max_wait=5.0)
async def upload_file_to_fal(file_path: Union[str, Path]) -> str:
    """
    Upload a file to FAL.ai and get a hosted URL.
    
    Args:
        file_path: Path to the file to upload
        
    Returns:
        str: Hosted URL of the uploaded file
    """
    # Validate FAL client
    validate_fal_client()
    
    try:
        logger.info(f"Uploading file to FAL: {file_path}")
        
        # Convert to Path object if it's a string
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # Upload the file
        url = fal_client.upload_file(file_path)
        
        if not url or not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Invalid URL returned from FAL: {url}")
        
        logger.info(f"File uploaded to FAL: {url}")
        return url
    except Exception as e:
        logger.error(f"Error uploading file to FAL: {str(e)}")
        raise
