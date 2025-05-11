"""
Text-to-image service using Fal.ai FLUX model.

This module provides a service for generating images from text prompts
using the Fal.ai FLUX model.
"""
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.fal_ai.base import FalAiService, ProgressCallback
from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class ImageSize(str, Enum):
    """
    Supported image sizes for the FLUX model.
    """
    SQUARE = "square"  # 1024x1024
    LANDSCAPE_16_9 = "landscape_16_9"  # 1024x576
    PORTRAIT_9_16 = "portrait_9_16"  # 576x1024
    LANDSCAPE_4_3 = "landscape_4_3"  # 1024x768
    PORTRAIT_3_4 = "portrait_3_4"  # 768x1024
    LANDSCAPE_3_2 = "landscape_3_2"  # 1024x683
    PORTRAIT_2_3 = "portrait_2_3"  # 683x1024
    WIDESCREEN = "widescreen"  # 1280x512


class TextToImageRequest(BaseModel):
    """
    Request model for text-to-image generation.
    """
    prompt: str = Field(..., description="The text prompt to generate an image from")
    negative_prompt: Optional[str] = Field(None, description="Text to avoid in the generated image")
    image_size: ImageSize = Field(ImageSize.SQUARE, description="The size of the generated image")
    num_inference_steps: int = Field(28, description="Number of denoising steps", ge=1, le=50)
    guidance_scale: float = Field(3.5, description="How closely to follow the prompt", ge=1.0, le=20.0)
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    num_images: int = Field(1, description="Number of images to generate", ge=1, le=4)


class TextToImageResponse(BaseModel):
    """
    Response model for text-to-image generation.
    """
    images: List[str] = Field(..., description="URLs of the generated images")
    prompt: str = Field(..., description="The prompt used to generate the images")
    seed: Optional[int] = Field(None, description="The seed used for generation")


class TextToImageService:
    """
    Service for generating images from text prompts using Fal.ai FLUX model.
    """
    
    def __init__(
        self, 
        fal_service: FalAiService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the text-to-image service.
        
        Args:
            fal_service: The Fal.ai service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.fal_service = fal_service
        self.storage_manager = storage_manager
        self.model_endpoint = settings.FAL_TEXT_TO_IMAGE_MODEL
    
    async def generate_image(
        self, 
        request: TextToImageRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TextToImageResponse:
        """
        Generate images from a text prompt.
        
        Args:
            request: The text-to-image request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The text-to-image response with image URLs
        """
        try:
            # Prepare the arguments for the Fal.ai model
            arguments = {
                "prompt": request.prompt,
                "image_size": request.image_size,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
                "num_images": request.num_images,
            }
            
            # Add optional arguments if provided
            if request.negative_prompt:
                arguments["negative_prompt"] = request.negative_prompt
            
            if request.seed is not None:
                arguments["seed"] = request.seed
            
            # Call the model
            logger.info(f"Generating image with prompt: {request.prompt}")
            result = await self.fal_service.call_model(
                model_endpoint=self.model_endpoint,
                arguments=arguments,
                progress_callback=progress_callback,
                with_logs=True
            )
            
            # Extract the image URLs from the result
            image_urls = []
            
            # The result structure depends on the model version
            if "images" in result:
                # For newer FLUX versions
                fal_image_urls = [img["url"] for img in result["images"]]
            elif "image" in result:
                # For older FLUX versions
                fal_image_urls = [result["image"]["url"]]
            else:
                logger.error(f"Unexpected result structure: {result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected response format from image generation service"
                )
            
            # Upload the images to our storage
            for i, fal_url in enumerate(fal_image_urls):
                # Generate a filename based on the prompt
                safe_prompt = request.prompt[:30].replace(" ", "_").lower()
                filename = f"{safe_prompt}_{i+1}.png"
                
                # Upload the image from the Fal.ai URL to our storage
                storage_url = await self.storage_manager.upload_file_from_url(
                    url=fal_url,
                    bucket=self.storage_manager.images_bucket,
                    content_type="image/png",
                    user_id=user_id
                )
                
                image_urls.append(storage_url)
            
            # Get the seed from the result if available
            seed = result.get("seed", request.seed)
            
            # Create the response
            response = TextToImageResponse(
                images=image_urls,
                prompt=request.prompt,
                seed=seed
            )
            
            logger.info(f"Generated {len(image_urls)} images successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {str(e)}"
            )
