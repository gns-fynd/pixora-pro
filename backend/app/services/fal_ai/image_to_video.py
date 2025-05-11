"""
Image-to-video service using Fal.ai Kling model.

This module provides a service for generating videos from images
using the Fal.ai Kling model.
"""
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum

from fastapi import Depends, HTTPException, status, UploadFile
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.fal_ai.base import FalAiService, ProgressCallback
from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class AspectRatio(str, Enum):
    """
    Supported aspect ratios for the Kling model.
    """
    LANDSCAPE_16_9 = "16:9"  # Landscape
    PORTRAIT_9_16 = "9:16"  # Portrait
    SQUARE_1_1 = "1:1"  # Square


class Duration(str, Enum):
    """
    Supported durations for the Kling model.
    """
    SECONDS_5 = "5"  # 5 seconds
    SECONDS_10 = "10"  # 10 seconds


class ImageToVideoRequest(BaseModel):
    """
    Request model for image-to-video generation.
    """
    prompt: str = Field(..., description="The text prompt to guide the video generation")
    image_url: str = Field(..., description="URL of the image to animate")
    duration: Duration = Field(Duration.SECONDS_5, description="Duration of the generated video")
    aspect_ratio: AspectRatio = Field(AspectRatio.LANDSCAPE_16_9, description="Aspect ratio of the generated video")
    negative_prompt: Optional[str] = Field(None, description="Text to avoid in the generated video")


class ImageToVideoResponse(BaseModel):
    """
    Response model for image-to-video generation.
    """
    video_url: str = Field(..., description="URL of the generated video")
    prompt: str = Field(..., description="The prompt used to generate the video")
    image_url: str = Field(..., description="URL of the source image")
    duration: str = Field(..., description="Duration of the generated video")
    aspect_ratio: str = Field(..., description="Aspect ratio of the generated video")


class ImageToVideoService:
    """
    Service for generating videos from images using Fal.ai Kling model.
    """
    
    def __init__(
        self, 
        fal_service: FalAiService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the image-to-video service.
        
        Args:
            fal_service: The Fal.ai service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.fal_service = fal_service
        self.storage_manager = storage_manager
        self.model_endpoint = settings.FAL_IMAGE_TO_VIDEO_MODEL
    
    async def generate_video_from_url(
        self, 
        request: ImageToVideoRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ImageToVideoResponse:
        """
        Generate a video from an image URL.
        
        Args:
            request: The image-to-video request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The image-to-video response with video URL
        """
        try:
            # Prepare the arguments for the Fal.ai model
            arguments = {
                "prompt": request.prompt,
                "image_url": request.image_url,
                "duration": request.duration,
                "aspect_ratio": request.aspect_ratio,
            }
            
            # Add optional arguments if provided
            if request.negative_prompt:
                arguments["negative_prompt"] = request.negative_prompt
            
            # Call the model
            logger.info(f"Generating video from image: {request.image_url}")
            result = await self.fal_service.call_model(
                model_endpoint=self.model_endpoint,
                arguments=arguments,
                progress_callback=progress_callback,
                with_logs=True
            )
            
            # Extract the video URL from the result
            if "video" in result and "url" in result["video"]:
                fal_video_url = result["video"]["url"]
            else:
                logger.error(f"Unexpected result structure: {result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected response format from video generation service"
                )
            
            # Generate a filename based on the prompt
            safe_prompt = request.prompt[:30].replace(" ", "_").lower()
            filename = f"{safe_prompt}.mp4"
            
            # Upload the video from the Fal.ai URL to our storage
            storage_url = await self.storage_manager.upload_file_from_url(
                url=fal_video_url,
                bucket=self.storage_manager.videos_bucket,
                content_type="video/mp4",
                user_id=user_id
            )
            
            # Create the response
            response = ImageToVideoResponse(
                video_url=storage_url,
                prompt=request.prompt,
                image_url=request.image_url,
                duration=request.duration,
                aspect_ratio=request.aspect_ratio
            )
            
            logger.info(f"Generated video successfully: {storage_url}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video generation failed: {str(e)}"
            )
    
    async def generate_video_from_file(
        self, 
        prompt: str,
        image_file: UploadFile,
        duration: Duration = Duration.SECONDS_5,
        aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE_16_9,
        negative_prompt: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ImageToVideoResponse:
        """
        Generate a video from an uploaded image file.
        
        Args:
            prompt: The text prompt to guide the video generation
            image_file: The uploaded image file
            duration: Duration of the generated video
            aspect_ratio: Aspect ratio of the generated video
            negative_prompt: Optional text to avoid in the generated video
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The image-to-video response with video URL
        """
        try:
            # Read the image file
            image_data = await image_file.read()
            
            # Upload the image to our storage
            image_url = await self.storage_manager.upload_image(
                file_data=image_data,
                filename=image_file.filename,
                content_type=image_file.content_type,
                user_id=user_id
            )
            
            # Create the request
            request = ImageToVideoRequest(
                prompt=prompt,
                image_url=image_url,
                duration=duration,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt
            )
            
            # Generate the video
            return await self.generate_video_from_url(
                request=request,
                user_id=user_id,
                progress_callback=progress_callback
            )
            
        except Exception as e:
            logger.error(f"Error generating video from file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video generation from file failed: {str(e)}"
            )
