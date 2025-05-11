"""
Base Fal.ai service for interacting with Fal.ai models.

This module provides a base class for interacting with Fal.ai models.
"""
import os
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
import json

import fal_client
from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings


# Set up logging
logger = logging.getLogger(__name__)

# Type for the callback function
T = TypeVar('T')
ProgressCallback = Callable[[float, Optional[str]], None]


class FalAiService:
    """
    Base service for interacting with Fal.ai models.
    """
    
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the Fal.ai service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.fal_api_key = None
        
        # Initialize storage adapter directly instead of using Depends
        from app.ai.utils.storage_adapter import StorageAdapter
        self.storage_adapter = StorageAdapter()
        
        # Default retry settings
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.retry_backoff = 2  # exponential backoff factor
        
        # Rate limiting settings
        self.rate_limit_delay = 1  # seconds
        self.last_request_time = 0
    
    def setup(self):
        """
        Set up the Fal.ai client and settings.
        This method should be called after FastAPI has injected the dependencies.
        """
        if self.fal_api_key is None:
            self.fal_api_key = self.settings.FAL_API_KEY
            
            # Set the API key for the fal_client
            os.environ["FAL_KEY"] = self.fal_api_key
    
    async def _enforce_rate_limit(self):
        # Ensure client is set up
        self.setup()
        """
        Enforce rate limiting to avoid hitting API limits.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            delay = self.rate_limit_delay - time_since_last_request
            logger.debug(f"Rate limiting: waiting {delay:.2f} seconds")
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
    
    async def call_model(
        self, 
        model_endpoint: str, 
        arguments: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
        with_logs: bool = False
    ) -> Dict[str, Any]:
        # Ensure client is set up
        self.setup()
        """
        Call a Fal.ai model with retry logic.
        
        Args:
            model_endpoint: The Fal.ai model endpoint to call
            arguments: The arguments to pass to the model
            progress_callback: Optional callback function for progress updates
            with_logs: Whether to include logs in the response
            
        Returns:
            The model response
        """
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                # Enforce rate limiting
                await self._enforce_rate_limit()
                
                # Define the queue update callback if progress tracking is requested
                queue_callback = None
                if progress_callback:
                    def on_queue_update(update):
                        if isinstance(update, dict) and "status" in update:
                            if update["status"] == "PROCESSING":
                                progress = update.get("progress", 0)
                                message = update.get("message", None)
                                progress_callback(progress, message)
                    
                    queue_callback = on_queue_update
                
                # Call the model
                logger.info(f"Calling Fal.ai model: {model_endpoint}")
                logger.debug(f"Arguments: {json.dumps(arguments, default=str)}")
                
                # Use asyncio to run the blocking fal_client.subscribe in a thread pool
                try:
                    # First try to run the model directly
                    result = await asyncio.to_thread(
                        fal_client.run,
                        model_endpoint,
                        arguments=arguments
                    )
                except Exception as e:
                    # If direct run fails, try subscribing
                    if "InProgress" in str(e):
                        logger.info(f"Model {model_endpoint} is processing, waiting for result...")
                        
                        # Use subscribe to wait for the result
                        result = await asyncio.to_thread(
                            fal_client.subscribe,
                            model_endpoint,
                            arguments=arguments,
                            with_logs=with_logs,
                            on_queue_update=queue_callback
                        )
                        
                        # Check if the result is an InProgress status
                        if isinstance(result, dict) and result.get("status") == "InProgress":
                            # Wait a bit and try to get the final result
                            await asyncio.sleep(2)
                            result = await asyncio.to_thread(
                                fal_client.run,
                                model_endpoint,
                                arguments=arguments
                            )
                    else:
                        # Re-raise if it's not an InProgress error
                        raise
                
                logger.info(f"Fal.ai model call successful: {model_endpoint}")
                return result
                
            except Exception as e:
                last_exception = e
                retries += 1
                
                if retries <= self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (self.retry_backoff ** (retries - 1))
                    logger.warning(f"Fal.ai API call failed, retrying in {delay} seconds. Error: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Fal.ai API call failed after {self.max_retries} retries. Error: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Fal.ai service unavailable: {str(e)}"
                    )
        
        # This should not be reached, but just in case
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fal.ai service unavailable: {str(last_exception)}"
        )
    
    async def upload_file(self, file_path: str) -> str:
        # Ensure client is set up
        self.setup()
        """
        Upload a file to storage using StorageAdapter instead of directly to Fal.ai.
        
        Args:
            file_path: The path to the file to upload
            
        Returns:
            The URL of the uploaded file
        """
        try:
            # Create a storage adapter
            from app.ai.utils.storage_adapter import StorageAdapter
            storage_adapter = StorageAdapter()
            
            # Determine file type based on extension
            import os
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Read the file
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Generate a filename
            filename = f"fal_upload_{os.path.basename(file_path)}"
            
            # Upload to appropriate storage based on file type
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                logger.info(f"Uploading image to storage: {file_path}")
                url = await storage_adapter.save_image(file_data=file_data, filename=filename)
            elif file_ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                logger.info(f"Uploading audio to storage: {file_path}")
                url = await storage_adapter.save_audio(file_data=file_data, filename=filename)
            elif file_ext in ['.mp4', '.webm', '.mov', '.avi']:
                logger.info(f"Uploading video to storage: {file_path}")
                url = await storage_adapter.save_video(file_data=file_data, filename=filename)
            else:
                # Default to image storage for unknown types
                logger.info(f"Uploading file to storage (default image type): {file_path}")
                url = await storage_adapter.save_image(file_data=file_data, filename=filename)
            
            logger.info(f"File uploaded successfully to storage: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"File upload failed: {str(e)}"
            )
    
    async def upload_bytes(self, file_data: bytes, file_name: str) -> str:
        # Ensure client is set up
        self.setup()
        """
        Upload bytes data to storage using StorageAdapter instead of directly to Fal.ai.
        
        Args:
            file_data: The file data as bytes
            file_name: The name of the file
            
        Returns:
            The URL of the uploaded file
        """
        try:
            # Create a storage adapter
            from app.ai.utils.storage_adapter import StorageAdapter
            storage_adapter = StorageAdapter()
            
            # Determine file type based on extension
            import os
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Generate a filename
            filename = f"fal_upload_{file_name}"
            
            # Upload to appropriate storage based on file type
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                logger.info(f"Uploading image bytes to storage: {file_name}")
                url = await storage_adapter.save_image(file_data=file_data, filename=filename)
            elif file_ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                logger.info(f"Uploading audio bytes to storage: {file_name}")
                url = await storage_adapter.save_audio(file_data=file_data, filename=filename)
            elif file_ext in ['.mp4', '.webm', '.mov', '.avi']:
                logger.info(f"Uploading video bytes to storage: {file_name}")
                url = await storage_adapter.save_video(file_data=file_data, filename=filename)
            else:
                # Default to image storage for unknown types
                logger.info(f"Uploading file bytes to storage (default image type): {file_name}")
                url = await storage_adapter.save_image(file_data=file_data, filename=filename)
            
            logger.info(f"Bytes uploaded successfully to storage: {url}")
            return url
                
        except Exception as e:
            logger.error(f"Error uploading bytes to storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Bytes upload failed: {str(e)}"
            )
    
    async def image_to_video(
        self,
        image_path: str,
        prompt: str,
        duration: str = "5",  # "5" or "10" seconds
        aspect_ratio: str = "16:9",  # "16:9", "9:16", or "1:1"
        negative_prompt: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Generate a video from an image using the Fal.ai Kling model.
        
        Args:
            image_path: The path to the image to animate
            prompt: The text prompt to guide the video generation
            duration: Duration of the generated video in seconds
            aspect_ratio: Aspect ratio of the generated video
            negative_prompt: Optional text to avoid in the generated video
            progress_callback: Optional callback for progress updates
            
        Returns:
            The URL of the generated video
        """
        # Ensure client is set up
        self.setup()
        
        if progress_callback:
            await progress_callback(10, "Starting image-to-video generation")
        
        try:
            # Upload the image to Fal.ai if it's a local file
            if os.path.exists(image_path):
                if progress_callback:
                    await progress_callback(20, "Uploading image to Fal.ai")
                
                image_url = await self.upload_file(image_path)
            else:
                # If it's already a URL, use it directly
                image_url = image_path
            
            # Prepare the arguments for the model
            arguments = {
                "prompt": prompt,
                "image_url": image_url,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }
            
            # Add optional arguments if provided
            if negative_prompt:
                arguments["negative_prompt"] = negative_prompt
            
            # Call the model
            if progress_callback:
                await progress_callback(30, "Generating video from image")
            
            model_endpoint = self.settings.FAL_IMAGE_TO_VIDEO_MODEL
            result = await self.call_model(
                model_endpoint=model_endpoint,
                arguments=arguments,
                progress_callback=progress_callback,
                with_logs=True
            )
            
            # Extract the video URL from the result
            if "video" in result and "url" in result["video"]:
                fal_video_url = result["video"]["url"]
                
                # Download and store the video using StorageAdapter
                if progress_callback:
                    await progress_callback(80, "Downloading and storing video")
                
                # Create a storage adapter
                from app.ai.utils.storage_adapter import StorageAdapter
                storage_adapter = StorageAdapter()
                
                # Generate a filename based on the prompt
                import uuid
                safe_prompt = prompt[:30].replace(" ", "_").lower()
                filename = f"{safe_prompt}_{uuid.uuid4()}.mp4"
                
                # Download and store the video
                logger.info(f"Downloading and storing video from Fal.ai: {fal_video_url}")
                local_path = await storage_adapter.download_and_store_video(fal_video_url, filename, "videos")
                
                # Get the public URL
                video_url = storage_adapter.get_public_url_sync(local_path)
                logger.info(f"Video stored successfully: {video_url}")
            else:
                logger.error(f"Unexpected result structure: {result}")
                raise ValueError("Unexpected response format from video generation service")
            
            if progress_callback:
                await progress_callback(100, "Video generation complete")
            
            return video_url
            
        except Exception as e:
            logger.error(f"Error generating video from image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video generation failed: {str(e)}"
            )
