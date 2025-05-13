"""
Asset generation tools for Pixora AI Video Creation Platform
"""
import os
import json
import uuid
from typing import Dict, Any, Optional, List
import logging
import openai
import replicate
import base64
import requests

# Import utilities
from ..utils.file_utils import (
    get_task_storage_path_from_id,
    save_character_image,
    save_scene_image,
    save_scene_audio,
    save_music
)

# Import services
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Set FAL_KEY from environment variable if needed
if os.getenv("FAL_CLIENT_API_KEY"):
    os.environ["FAL_KEY"] = os.getenv("FAL_CLIENT_API_KEY")
    # Import fal_client after setting the environment variable
    try:
        import fal_client
    except ImportError:
        logger.warning("fal_client not installed. File uploads will not work.")

async def generate_character_images(task_id: str, character_id: str, image_prompt: str) -> Dict[str, Any]:
    """
    Generate character images from a prompt using OpenAI's GPT-Image-1 API.
    Creates a single 2x2 grid image with transparent background showing different views.
    
    Args:
        task_id: ID of the task
        character_id: ID of the character
        image_prompt: Detailed description for generating character images
        
    Returns:
        Dict: A dictionary containing the generated images
    """
    try:
        # Initialize the OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Create a single prompt for a 2x2 grid with different views
        grid_prompt = f"""
        Create a 2x2 grid image with transparent background showing 4 different views of {image_prompt}:
        - Top-left: Front view, full body, facing directly forward
        - Top-right: Side profile view, full body, facing directly to the right
        - Bottom-left: Back view, full body, facing directly away from the camera
        - Bottom-right: Three-quarter view, full body, facing 45 degrees to the right
        
        Each view should be clearly separated in the grid. The character should be consistent across all views.
        Use transparent background for all views.
        """
        
        try:
            # Call the OpenAI API to generate the grid image with transparent background
            response = client.images.generate(
                model="gpt-image-1",
                prompt=grid_prompt,
                quality="high",
                n=1,
                size="1024x1024",
                background="opaque"
            )
            
            # Get the base64 encoded image from the response
            image_base64 = response.data[0].b64_json
            
            # Decode the base64 string to get the image bytes
            image_content = base64.b64decode(image_base64)
            
            logger.info(f"Generated 2x2 grid image for character: {character_id}")
        except Exception as e:
            logger.error(f"Error generating character grid image: {str(e)}")
            raise
        
        # Save the image to Supabase storage
        result = save_character_image(task_storage_path, character_id, image_content)
        
        # Add additional metadata
        result["prompt"] = image_prompt
        result["character_id"] = character_id
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="character",
                url=result["url"],
                storage_path=result["path"],
                metadata={"prompt": image_prompt, "character_id": character_id}
            )
        
        return result
    except Exception as e:
        logger.error(f"Error generating character images: {str(e)}")
        raise

async def generate_scene_images(task_id: str, scene_index: int, video_prompt: str, character_references: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate a scene image based on the video prompt and character references using OpenAI's GPT-Image-1 API.
    Then upload the image to FAL client to get a hosted URL.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        video_prompt: Detailed description for generating the scene image
        character_references: Optional list of URLs to character images to include in the scene
        
    Returns:
        Dict: A dictionary containing the generated image URL and metadata
    """
    try:
        # Initialize the OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Enhance prompt with character references if available
        enhanced_prompt = video_prompt
        if character_references:
            enhanced_prompt += " Include the following characters: " + ", ".join([
                f"a character that looks like the one in the reference image" 
                for _ in character_references
            ])
        
        try:
            # Call the OpenAI API to generate the image with transparent background
            response = client.images.generate(
                model="gpt-image-1",
                prompt=enhanced_prompt,
                n=1,
                quality="high",
                size="1024x1024"
            )
            
            # Get the base64 encoded image from the response
            image_base64 = response.data[0].b64_json
            
            # Decode the base64 string to get the image bytes
            image_content = base64.b64decode(image_base64)
            
            logger.info(f"Generated scene image for scene: {scene_index}")
            
            # Save the image to a temporary file
            temp_file_path = f"/tmp/scene_{task_id}_{scene_index}.png"
            with open(temp_file_path, "wb") as f:
                f.write(image_content)
            
            # Upload the image to FAL client to get a hosted URL
            fal_url = None
            try:
                if 'fal_client' in globals():
                    fal_url = fal_client.upload_file(temp_file_path)
                    logger.info(f"Uploaded scene image to FAL: {fal_url}")
                else:
                    logger.warning("fal_client not available, skipping upload")
            except Exception as e:
                logger.error(f"Error uploading to FAL: {str(e)}")
            
            # Remove the temporary file
            try:
                os.remove(temp_file_path)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error generating scene image: {str(e)}")
            raise
        
        # Save the image to Supabase storage
        result = save_scene_image(task_storage_path, scene_index, image_content)
        
        # Add additional metadata
        result["prompt"] = video_prompt
        result["character_references"] = character_references
        
        # Add the FAL URL to the result
        if fal_url:
            result["fal_url"] = fal_url
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="scene_image",
                url=result["url"],
                storage_path=result["path"],
                scene_index=scene_index,
                metadata={"prompt": video_prompt, "character_references": character_references, "fal_url": fal_url}
            )
        
        return result
    except Exception as e:
        logger.error(f"Error generating scene image: {str(e)}")
        raise

async def generate_voice_over(task_id: str, scene_index: int, text: str, voice_sample: Optional[str] = None) -> Dict[str, Any]:
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
        
        # Import fal_client here to avoid circular imports
        import fal_client
        
        logger.info(f"Calling Fal.ai ElevenLabs TTS API for scene: {scene_index}")
        
        # Call the Fal.ai ElevenLabs TTS API
        result = fal_client.run(
            "fal-ai/elevenlabs/tts/multilingual-v2",
            params
        )
        
        # Get the audio URL from the result
        audio_url = result["audio_url"]
        
        # Download the audio from the URL
        logger.info(f"Downloading audio from: {audio_url}")
        audio_response = requests.get(audio_url)
        
        if audio_response.status_code != 200:
            raise ValueError(f"Failed to download audio: HTTP {audio_response.status_code}")
        
        audio_content = audio_response.content
        
        logger.info(f"Generated voice-over audio for scene: {scene_index}")
        
        # Save the audio to Supabase storage
        result = save_scene_audio(task_storage_path, scene_index, audio_content)
        
        # Add additional metadata
        result["text"] = text[:100] + "..." if len(text) > 100 else text  # Truncate long text
        
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
    except Exception as e:
        logger.error(f"Error generating voice over: {str(e)}")
        raise

async def generate_music(task_id: str, prompt: str, duration: float, scene_indexes: List[int]) -> Dict[str, Any]:
    """
    Generate background music based on prompt and duration using Replicate's Meta MusicGen API.
    
    Args:
        task_id: ID of the task
        prompt: Description of the desired music
        duration: Desired duration in seconds (1-30)
        scene_indexes: List of scene indexes that use this music
        
    Returns:
        Dict: A dictionary containing the music URL and metadata
    """
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Ensure duration is within model limits (1-30 seconds)
        clamped_duration = min(30, max(1, duration))
        
        music_id = str(uuid.uuid4())
        
        logger.info(f"Calling Replicate API for music generation")
        
        # Use the specific model version hash
        model_version = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
        
        # Get the audio URL from Replicate
        audio_url = replicate.run(
            model_version,
            input={
                "prompt": prompt,
                "duration": int(clamped_duration),
                "model_version": "stereo-large",
                "output_format": "mp3"
            }
        )
        
        # Download the audio from the URL
        logger.info(f"Downloading music from: {audio_url}")
        audio_response = requests.get(audio_url)
        
        if audio_response.status_code != 200:
            raise ValueError(f"Failed to download music: HTTP {audio_response.status_code}")
        
        audio_content = audio_response.content
        
        logger.info(f"Generated music for scenes: {scene_indexes}")
        
        # Save the audio to Supabase storage
        result = save_music(task_storage_path, music_id, scene_indexes, audio_content)
        
        # Add additional metadata
        result["prompt"] = prompt
        result["duration"] = clamped_duration
        result["scene_indexes"] = scene_indexes
        
        # Save the asset to the database
        if supabase_service.client:
            supabase_service.save_asset(
                task_id=task_id,
                asset_type="music",
                url=result["url"],
                storage_path=result["path"],
                metadata={"prompt": prompt, "duration": clamped_duration, "scene_indexes": scene_indexes}
            )
        
        return result
    except Exception as e:
        logger.error(f"Error generating music: {str(e)}")
        raise
