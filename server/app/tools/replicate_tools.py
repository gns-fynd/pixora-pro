"""
Replicate tools for Pixora AI Video Creation Platform with improved error handling and retry logic
"""
import os
import logging
import time
import json
import asyncio
from typing import Dict, Any, Optional, List, Union, Tuple, cast
import requests

# Import utilities
from ..utils.file_utils import (
    get_task_storage_path_from_id,
    save_music
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

# Import replicate with fallback
try:
    import replicate
    from replicate.client import Client as ReplicateClient
    from replicate.prediction import Prediction
    REPLICATE_AVAILABLE = True
except ImportError:
    logger.warning("replicate not installed. Replicate tools will not work.")
    REPLICATE_AVAILABLE = False
    replicate = None
    ReplicateClient = None
    Prediction = None

# Initialize Replicate client
def initialize_replicate_client() -> bool:
    """
    Initialize the Replicate client with API token from environment variables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global replicate_client
    
    if not REPLICATE_AVAILABLE or ReplicateClient is None:
        logger.warning("Replicate client not available")
        return False
    
    # Check for API token in environment variables
    api_token = os.getenv("REPLICATE_API_TOKEN")
    
    if not api_token:
        logger.warning("REPLICATE_API_TOKEN not set. Replicate tools will not work.")
        return False
    
    try:
        # Initialize the client
        replicate_client = ReplicateClient(api_token=api_token)
        
        # Test the client with a simple operation
        if hasattr(replicate_client, 'models') and hasattr(replicate_client.models, 'list'):
            _ = replicate_client.models.list()
        else:
            logger.warning("Replicate client does not have expected methods")
            return False
        
        logger.info("Replicate client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Replicate client: {str(e)}")
        replicate_client = None
        return False

# Initialize the Replicate client
replicate_client = None
REPLICATE_INITIALIZED = initialize_replicate_client() if REPLICATE_AVAILABLE else False

# Validate Replicate client before each operation
def validate_replicate_client() -> None:
    """
    Validate that the Replicate client is available and initialized.
    
    Raises:
        ImportError: If replicate is not installed
        RuntimeError: If Replicate client is not initialized
    """
    if not REPLICATE_AVAILABLE:
        raise ImportError("replicate not installed. Cannot use Replicate tools.")
    
    if not REPLICATE_INITIALIZED or replicate_client is None:
        raise RuntimeError("Replicate client not initialized. Please set REPLICATE_API_TOKEN environment variable.")

# Helper function to wait for prediction
async def wait_for_prediction(prediction_id: str, timeout: int = 600) -> Any:
    """
    Wait for a prediction to complete.
    
    Args:
        prediction_id: ID of the prediction
        timeout: Maximum time to wait in seconds
        
    Returns:
        Any: Completed prediction
        
    Raises:
        TimeoutError: If the prediction takes too long
        ValueError: If the prediction fails
    """
    if not replicate_client:
        raise RuntimeError("Replicate client not initialized")
    
    start_time = time.time()
    
    # Type checking to avoid None errors
    if not hasattr(replicate_client, 'predictions') or not hasattr(replicate_client.predictions, 'get'):
        raise RuntimeError("Replicate client does not have predictions.get method")
    
    prediction = replicate_client.predictions.get(prediction_id)
    
    while getattr(prediction, 'status', '') not in ["succeeded", "failed", "canceled"]:
        # Check for timeout
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Prediction timed out after {timeout} seconds")
        
        # Wait before checking again
        await asyncio.sleep(2.0)
        
        # Get the updated prediction
        prediction = replicate_client.predictions.get(prediction_id)
        
        # Log progress
        logger.debug(f"Prediction status: {getattr(prediction, 'status', 'unknown')}")
    
    # Check if the prediction failed
    if getattr(prediction, 'status', '') == "failed":
        raise ValueError(f"Prediction failed: {getattr(prediction, 'error', 'unknown error')}")
    
    # Check if the prediction was canceled
    if getattr(prediction, 'status', '') == "canceled":
        raise ValueError("Prediction was canceled")
    
    return prediction

@traced("generate_music")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def generate_music(
    task_id: str, 
    prompt: str, 
    duration: float, 
    scene_indexes: List[int]
) -> Dict[str, Any]:
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
    # Validate Replicate client
    validate_replicate_client()
    
    start_time = time.time()
    
    try:
        # Get the task storage path
        task_storage_path = get_task_storage_path_from_id(task_id)
        
        if not task_storage_path:
            logger.error(f"Task storage path not found for task: {task_id}")
            return {"error": f"Task storage path not found for task: {task_id}"}
        
        # Ensure duration is within model limits (1-30 seconds)
        clamped_duration = min(30, max(1, duration))
        
        # Generate a unique ID for the music
        import uuid
        music_id = str(uuid.uuid4())
        
        logger.info(f"Calling Replicate API for music generation")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Duration: {clamped_duration} seconds")
        
        # Use the specific model version hash
        model_version = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
        
        # Get the audio URL from Replicate
        try:
            # Create the prediction
            if replicate_client is None or not hasattr(replicate_client, 'predictions'):
                raise RuntimeError("Replicate client not properly initialized")
                
            prediction = replicate_client.predictions.create(
                version=model_version,
                input={
                    "prompt": prompt,
                    "duration": int(clamped_duration),
                    "model_version": "stereo-large",
                    "output_format": "mp3"
                }
            )
            
            # Wait for the prediction to complete
            prediction = await wait_for_prediction(prediction.id)
            
            # Get the output URL
            audio_url = prediction.output
            
            # Handle case where output is a list (some models return lists)
            if isinstance(audio_url, list) and len(audio_url) > 0:
                audio_url = audio_url[0]
        except Exception as e:
            logger.error(f"Error using Replicate client: {str(e)}")
            
            # Fall back to the run function if available
            if replicate and hasattr(replicate, 'run'):
                logger.info("Falling back to replicate.run")
                audio_url = replicate.run(
                    model_version,
                    input={
                        "prompt": prompt,
                        "duration": int(clamped_duration),
                        "model_version": "stereo-large",
                        "output_format": "mp3"
                    }
                )
            else:
                raise
        
        # Validate the URL
        if not audio_url or not isinstance(audio_url, str) or not audio_url.startswith("https://"):
            raise ValueError(f"Invalid audio URL returned from Replicate: {audio_url}")
        
        # Download the audio from the URL
        logger.info(f"Downloading music from: {audio_url}")
        audio_response = requests.get(audio_url)
        
        # Check for rate limits or server errors
        handle_rate_limit_response(audio_response, "Replicate")
        
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
        result["processing_time"] = time.time() - start_time
        
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
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error generating music: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            handle_rate_limit_response(e.response, "Replicate")
        raise ServiceUnavailable(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating music: {str(e)}")
        raise

@traced("run_replicate_model")
@with_retry(max_attempts=3, min_wait=2.0, max_wait=15.0)
async def run_replicate_model(
    model_version: str,
    inputs: Dict[str, Any],
    webhook_url: Optional[str] = None
) -> Any:
    """
    Run a Replicate model with the given inputs.
    
    Args:
        model_version: Model version to run
        inputs: Inputs for the model
        webhook_url: Optional webhook URL for asynchronous processing
        
    Returns:
        Any: Output from the model
    """
    # Validate Replicate client
    validate_replicate_client()
    
    start_time = time.time()
    
    try:
        logger.info(f"Running Replicate model: {model_version}")
        logger.info(f"Inputs: {json.dumps({k: v for k, v in inputs.items() if k != 'password' and k != 'token' and k != 'api_key'})}")
        
        try:
            # Use the client for better error handling
            if replicate_client is None or not hasattr(replicate_client, 'predictions'):
                raise RuntimeError("Replicate client not properly initialized")
                
            # Create prediction with or without webhook
            if webhook_url:
                prediction = replicate_client.predictions.create(
                    version=model_version,
                    input=inputs,
                    webhook=webhook_url
                )
            else:
                prediction = replicate_client.predictions.create(
                    version=model_version,
                    input=inputs
                )
            
            # If webhook is provided, return the prediction ID
            if webhook_url:
                return {
                    "prediction_id": prediction.id,
                    "status": prediction.status
                }
            
            # Wait for the prediction to complete
            prediction = await wait_for_prediction(prediction.id)
            
            # Get the output
            output = prediction.output
        except Exception as e:
            logger.error(f"Error using Replicate client: {str(e)}")
            
            # Fall back to the run function if available
            if replicate and hasattr(replicate, 'run'):
                logger.info("Falling back to replicate.run")
                output = replicate.run(
                    model_version,
                    input=inputs
                )
            else:
                raise
        
        # Log the processing time
        processing_time = time.time() - start_time
        logger.info(f"Replicate model {model_version} completed in {processing_time:.2f}s")
        
        return output
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error running Replicate model: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            handle_rate_limit_response(e.response, "Replicate")
        raise ServiceUnavailable(f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Error running Replicate model: {str(e)}")
        raise

@traced("get_prediction_status")
@with_retry(max_attempts=3, min_wait=1.0, max_wait=5.0)
async def get_prediction_status(prediction_id: str) -> Dict[str, Any]:
    """
    Get the status of a Replicate prediction.
    
    Args:
        prediction_id: ID of the prediction
        
    Returns:
        Dict: Status information for the prediction
    """
    # Validate Replicate client
    validate_replicate_client()
    
    try:
        try:
            # Get the prediction
            if replicate_client is None or not hasattr(replicate_client, 'predictions'):
                raise RuntimeError("Replicate client not properly initialized")
                
            prediction = replicate_client.predictions.get(prediction_id)
            
            # Return the status information
            return {
                "id": prediction.id,
                "status": prediction.status,
                "created_at": prediction.created_at,
                "completed_at": prediction.completed_at,
                "error": prediction.error,
                "output": prediction.output,
                "metrics": prediction.metrics
            }
        except Exception as e:
            logger.error(f"Error getting prediction status: {str(e)}")
            raise ServiceUnavailable(f"Error getting prediction status: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting prediction status: {str(e)}")
        raise
