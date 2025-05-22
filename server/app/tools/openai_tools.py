"""
OpenAI tools for Pixora AI Video Creation Platform with improved error handling and JSON mode support
"""
import os
import logging
import time
import json
import base64
from typing import Dict, Any, Optional, List, Union, Tuple
import requests
from pathlib import Path

# Import utilities
from ..utils.file_utils import (
    get_task_storage_path_from_id,
    save_character_image,
    save_scene_image,
    save_script
)

# Import retry utilities
from ..utils.retry import (
    with_retry,
    handle_rate_limit_response,
    extract_rate_limit_info,
    RateLimitExceeded,
    ServiceUnavailable
)

# Import telemetry
from ..utils.telemetry import traced, log_event

# Import services
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Import OpenAI with fallback
try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("openai not installed. OpenAI tools will not work.")
    OPENAI_AVAILABLE = False
    openai = None
    OpenAI = None
    AsyncOpenAI = None

# Initialize OpenAI client
openai_client = None
async_openai_client = None
if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
    try:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")

@traced("generate_script")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def generate_script(
    prompt: str,
    character_consistency: bool = False,
    duration: Optional[float] = None,
    aspect_ratio: Optional[str] = None,
    style: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a script breakdown from a user prompt using OpenAI's GPT-4o API.
    
    Args:
        prompt: The user's prompt describing the desired video
        character_consistency: Whether to maintain consistent characters across scenes
        duration: Optional desired duration of the video in seconds
        aspect_ratio: Optional aspect ratio of the video
        style: Optional style of the video
        
    Returns:
        Dict[str, Any]: A structured script breakdown
    """
    if not OPENAI_AVAILABLE or not async_openai_client:
        raise ImportError("openai not installed or client not initialized. Cannot generate script.")
    
    start_time = time.time()
    
    try:
        # Create the system message
        system_message = """You are a professional video script generator that creates detailed breakdowns for video production.
        
        Your task is to create a detailed video script breakdown with:
        1. A rewritten, enhanced version of the user's prompt
        2. A series of scenes with titles, scripts, and visual descriptions
        3. Appropriate transitions between scenes
        4. Music suggestions that match the mood of each scene
        5. Character profiles if character consistency is requested
        
        CRITICAL: The video_prompt for each scene MUST include motion descriptions for video generation. All scenes will be created as motion videos, not static images. For each scene, you must include:
        
        1. Visual elements to include in the scene
        2. Camera movements (pan, tilt, zoom, tracking)
        3. Dynamic elements that should have motion (e.g., leaves blowing, water flowing)
        
        CRITICAL: The video generation API can only generate videos of 5 or 10 seconds. This is a hard constraint that must be respected. Each scene must be either 5 or 10 seconds long.
        
        Examples of good motion prompts:
        - "A forest scene with leaves gently blowing in the wind, camera slowly panning from left to right"
        - "A cityscape at sunset with cars moving on streets below, camera gradually zooming out to reveal the skyline"
        - "A close-up of a character's face with subtle expressions changing, camera slowly pushing in"
        
        Your output must be a valid JSON object matching the following structure:
        {
          "user_prompt": "Original user prompt",
          "rewritten_prompt": "Enhanced, detailed prompt",
          "voice_character": null,
          "character_consistency": true/false,
          "music": [
            {
              "prompt": "Description of music for specific scenes",
              "scene_indexes": [list of scene indexes]
            }
          ],
          "character_profiles": [
            {
              "name": "Character name",
              "image_prompt": "Detailed description for generating character images"
            }
          ],
          "clips": [
            {
              "scene": {
                "index": 1,
                "title": "Scene title",
                "script": "Scene script/narration",
                "video_prompt": "Visual description with camera movement and dynamic elements",
                "transition": "fade/slide_left/zoom_out/etc.",
                "duration": 5 or 10
              }
            }
          ],
          "expected_duration": estimated duration in seconds
        }
        """
        
        # Create the user message
        user_message = f"Create a video script about: {prompt}."
        
        # Add optional parameters to the user message
        if character_consistency:
            user_message += f" Character consistency: {character_consistency}."
        if duration:
            user_message += f" Duration: {duration} seconds."
        if aspect_ratio:
            user_message += f" Aspect ratio: {aspect_ratio}."
        if style:
            user_message += f" Style: {style}."
        
        logger.info(f"Generating script with prompt: {prompt[:100]}...")
        
        # Call OpenAI to generate the script
        response = await async_openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Check for rate limits
        if hasattr(response, 'headers'):
            rate_limit_info = extract_rate_limit_info(response)
            logger.debug(f"OpenAI rate limit info: {rate_limit_info}")
        
        # Parse the response
        script_data = json.loads(response.choices[0].message.content)
        
        # Add task_id
        import uuid
        task_id = str(uuid.uuid4())
        script_data["task_id"] = task_id
        
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        # Save the script to Supabase storage
        save_script(task_storage_path, script_data)
        
        # Create a task in the database if Supabase is configured
        try:
            if hasattr(supabase_service, 'client') and supabase_service.client:
                supabase_service.create_task(user_id="user_1", task_id=task_id, prompt=prompt)
                logger.info(f"Created task in database: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to create task in database: {str(e)}")
            # Continue execution even if database operations fail
        
        # Add processing time
        script_data["processing_time"] = time.time() - start_time
        
        return script_data
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {str(e)}")
        raise RateLimitExceeded(f"OpenAI rate limit exceeded: {str(e)}")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise ServiceUnavailable(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        raise

@traced("generate_character_images")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def generate_character_images(
    task_id: str,
    character_id: str,
    image_prompt: str
) -> Dict[str, Any]:
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
    if not OPENAI_AVAILABLE or not openai_client:
        raise ImportError("openai not installed or client not initialized. Cannot generate character images.")
    
    start_time = time.time()
    
    try:
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
        
        logger.info(f"Generating character images for character: {character_id}")
        logger.info(f"Prompt: {image_prompt[:100]}...")
        
        try:
            # Call the OpenAI API to generate the grid image with transparent background
            response = openai_client.images.generate(
                model="gpt-image-1",
                prompt=grid_prompt,
                quality="high",
                n=1,
                size="1024x1024",
                background="opaque"
            )
            
            # Check for rate limits
            if hasattr(response, 'headers'):
                rate_limit_info = extract_rate_limit_info(response)
                logger.debug(f"OpenAI rate limit info: {rate_limit_info}")
            
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
        result["processing_time"] = time.time() - start_time
        
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
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {str(e)}")
        raise RateLimitExceeded(f"OpenAI rate limit exceeded: {str(e)}")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise ServiceUnavailable(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating character images: {str(e)}")
        raise

@traced("generate_scene_images")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def generate_scene_images(
    task_id: str,
    scene_index: int,
    video_prompt: str,
    character_references: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a scene image based on the video prompt and character references using OpenAI's GPT-Image-1 API.
    
    Args:
        task_id: ID of the task
        scene_index: Index of the scene
        video_prompt: Detailed description for generating the scene image
        character_references: Optional list of URLs to character images to include in the scene
        
    Returns:
        Dict: A dictionary containing the generated image URL and metadata
    """
    if not OPENAI_AVAILABLE or not openai_client:
        raise ImportError("openai not installed or client not initialized. Cannot generate scene images.")
    
    start_time = time.time()
    
    try:
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
        
        logger.info(f"Generating scene image for scene: {scene_index}")
        logger.info(f"Prompt: {enhanced_prompt[:100]}...")
        
        try:
            # Call the OpenAI API to generate the image
            response = openai_client.images.generate(
                model="gpt-image-1",
                prompt=enhanced_prompt,
                n=1,
                quality="high",
                size="1024x1024"
            )
            
            # Check for rate limits
            if hasattr(response, 'headers'):
                rate_limit_info = extract_rate_limit_info(response)
                logger.debug(f"OpenAI rate limit info: {rate_limit_info}")
            
            # Get the base64 encoded image from the response
            image_base64 = response.data[0].b64_json
            
            # Decode the base64 string to get the image bytes
            image_content = base64.b64decode(image_base64)
            
            logger.info(f"Generated scene image for scene: {scene_index}")
        except Exception as e:
            logger.error(f"Error generating scene image: {str(e)}")
            raise
        
        # Save the image to Supabase storage
        result = save_scene_image(task_storage_path, scene_index, image_content)
        
        # Add additional metadata
        result["prompt"] = video_prompt
        result["character_references"] = character_references
        result["processing_time"] = time.time() - start_time
        
        # Try to upload to FAL.ai for a hosted URL
        fal_url = None
        try:
            if 'fal_client' in globals():
                from ..tools.fal_tools import upload_file_to_fal
                
                # Save to a temporary file
                temp_file_path = f"/tmp/scene_{task_id}_{scene_index}.png"
                with open(temp_file_path, "wb") as f:
                    f.write(image_content)
                
                # Upload to FAL
                fal_url = await upload_file_to_fal(temp_file_path)
                logger.info(f"Uploaded scene image to FAL: {fal_url}")
                
                # Add the FAL URL to the result
                result["fal_url"] = fal_url
                
                # Remove the temporary file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Error uploading to FAL: {str(e)}")
        
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
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {str(e)}")
        raise RateLimitExceeded(f"OpenAI rate limit exceeded: {str(e)}")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise ServiceUnavailable(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating scene image: {str(e)}")
        raise

@traced("call_openai_with_json_mode")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def call_openai_with_json_mode(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    schema: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Call OpenAI API with JSON mode for structured output.
    
    Args:
        system_prompt: System prompt for the model
        user_prompt: User prompt for the model
        model: Model to use (default: gpt-4o)
        schema: Optional JSON schema for structured output
        temperature: Temperature for sampling (default: 0.7)
        max_tokens: Maximum number of tokens to generate (default: None)
        
    Returns:
        Dict[str, Any]: Parsed JSON response
    """
    if not OPENAI_AVAILABLE or not async_openai_client:
        raise ImportError("openai not installed or client not initialized. Cannot call OpenAI API.")
    
    start_time = time.time()
    
    try:
        logger.info(f"Calling OpenAI API with JSON mode")
        logger.info(f"Model: {model}")
        logger.info(f"User prompt: {user_prompt[:100]}...")
        
        # Prepare the response format
        if schema:
            response_format = {
                "type": "json_schema",
                "schema": schema
            }
        else:
            response_format = {"type": "json_object"}
        
        # Prepare the request parameters
        params = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "response_format": response_format,
            "temperature": temperature
        }
        
        # Add max_tokens if provided
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # Call the OpenAI API
        response = await async_openai_client.chat.completions.create(**params)
        
        # Check for rate limits
        if hasattr(response, 'headers'):
            rate_limit_info = extract_rate_limit_info(response)
            logger.debug(f"OpenAI rate limit info: {rate_limit_info}")
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        # Add metadata
        processing_time = time.time() - start_time
        logger.info(f"OpenAI API call completed in {processing_time:.2f}s")
        
        return {
            "result": result,
            "processing_time": processing_time,
            "finish_reason": response.choices[0].finish_reason,
            "model": model
        }
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {str(e)}")
        raise RateLimitExceeded(f"OpenAI rate limit exceeded: {str(e)}")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise ServiceUnavailable(f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise
