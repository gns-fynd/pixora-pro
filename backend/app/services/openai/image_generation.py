"""
OpenAI image generation service.

This module provides a service for generating images using OpenAI's GPT-Image-1 model.
"""
import logging
import os
import asyncio
import base64
import tempfile
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

import openai

from app.core.config import Settings, get_settings
from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class ImageSize(str, Enum):
    """
    Supported image sizes for GPT-Image-1.
    """
    SQUARE_1024 = "1024x1024"
    LANDSCAPE_1792_1024 = "1792x1024"
    PORTRAIT_1024_1792 = "1024x1792"


class ImageQuality(str, Enum):
    """
    Supported image qualities for GPT-Image-1.
    """
    STANDARD = "standard"
    HD = "hd"


class ImageStyle(str, Enum):
    """
    Supported image styles for GPT-Image-1.
    """
    VIVID = "vivid"
    NATURAL = "natural"


class ImageGenerationRequest(BaseModel):
    """
    Request model for image generation.
    """
    prompt: str = Field(..., description="The text prompt to generate an image from")
    negative_prompt: Optional[str] = Field(None, description="Text to avoid in the generated image")
    size: ImageSize = Field(ImageSize.SQUARE_1024, description="The size of the generated image")
    quality: ImageQuality = Field(ImageQuality.STANDARD, description="The quality of the generated image")
    style: ImageStyle = Field(ImageStyle.VIVID, description="The style of the generated image")
    num_images: int = Field(1, description="Number of images to generate", ge=1, le=4)


class ImageGenerationResponse(BaseModel):
    """
    Response model for image generation.
    """
    images: List[str] = Field(..., description="URLs of the generated images")
    prompt: str = Field(..., description="The prompt used to generate the images")
    revised_prompt: Optional[str] = Field(None, description="The revised prompt used by GPT-Image-1")


# Type for the progress callback function
ProgressCallback = Callable[[float, Optional[str]], None]


class OpenAIImageGenerationService:
    """
    Service for generating images using OpenAI's GPT-Image-1 model.
    """
    
    def __init__(
        self, 
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the OpenAI image generation service.
        
        Args:
            storage_manager: The storage manager
            settings: Application settings
        """
        self.storage_manager = storage_manager
        self.settings = settings
        
        # Initialize OpenAI client
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai
        self.model = settings.OPENAI_IMAGE_MODEL
        self.default_quality = settings.OPENAI_IMAGE_QUALITY
        self.default_style = settings.OPENAI_IMAGE_STYLE
    
    async def generate_image(
        self, 
        request: ImageGenerationRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ImageGenerationResponse:
        """
        Generate images from a text prompt using OpenAI's GPT-Image-1 model.
        
        Args:
            request: The image generation request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The image generation response with image URLs
        """
        try:
            # Update progress if callback provided
            if progress_callback:
                progress_callback(10, "Preparing image generation request")
            
            # Prepare the request to OpenAI
            openai_request = {
                "model": self.model,
                "prompt": request.prompt,
                "n": request.num_images,
                "size": request.size,
                "quality": request.quality,
                "style": request.style,
                "response_format": "b64_json"  # Request base64 data
            }
            
            # Add negative prompt if provided
            if request.negative_prompt:
                # Append the negative prompt to the main prompt
                openai_request["prompt"] += f" Do not include: {request.negative_prompt}"
            
            logger.info(f"Generating image with prompt: {request.prompt}")
            
            # Update progress if callback provided
            if progress_callback:
                progress_callback(20, "Sending request to OpenAI")
            
            # Call the OpenAI API
            response = self.client.Image.create(**openai_request)
            
            # Update progress if callback provided
            if progress_callback:
                progress_callback(60, "Processing image generation results")
            
            # Extract the image data and revised prompt
            image_urls = []
            revised_prompt = None
            
            for i, image_data in enumerate(response["data"]):
                # Get the base64 image data
                b64_data = image_data["b64_json"]
                
                # Get the revised prompt if available
                if "revised_prompt" in image_data:
                    revised_prompt = image_data["revised_prompt"]
                
                # Generate a filename based on the prompt
                safe_prompt = request.prompt[:30].replace(" ", "_").lower()
                filename = f"{safe_prompt}_{i+1}.png"
                
                # Save the image to a temporary file
                image_bytes = base64.b64decode(b64_data)
                
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_file.write(image_bytes)
                    temp_file_path = temp_file.name
                
                try:
                    # Upload the image to our storage
                    storage_url = await self.storage_manager.upload_image(
                        file_data=image_bytes,
                        filename=filename,
                        content_type="image/png",
                        user_id=user_id
                    )
                    
                    image_urls.append(storage_url)
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            
            # Update progress if callback provided
            if progress_callback:
                progress_callback(100, "Image generation complete")
            
            # Create the response
            result = ImageGenerationResponse(
                images=image_urls,
                prompt=request.prompt,
                revised_prompt=revised_prompt
            )
            
            logger.info(f"Generated {len(image_urls)} images successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {str(e)}"
            )
