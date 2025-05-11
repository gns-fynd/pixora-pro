"""
OpenAI service for interacting with OpenAI APIs.

This module provides a comprehensive service for interacting with OpenAI APIs,
including text generation, structured output generation, and image generation.
"""
import logging
import os
import asyncio
import base64
import tempfile
import json
from typing import Dict, Any, Optional, List, Callable, Union, Type, TypeVar
from enum import Enum

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.storage import StorageManager
from app.ai.models.task import ProgressCallback

# Set up logging
logger = logging.getLogger(__name__)

# Type for Pydantic model
T = TypeVar('T', bound=BaseModel)


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


class OpenAIService:
    """
    Service for interacting with OpenAI APIs.
    """
    
    def __init__(
        self, 
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the OpenAI service.
        
        Args:
            storage_manager: The storage manager
            settings: Application settings
        """
        self.storage_manager = storage_manager
        self.settings = settings
        
        # Initialize OpenAI client and settings in setup method
        self.client = None
        self.text_model = None
        self.image_model = None
        self.default_quality = None
        self.default_style = None
    
    def setup(self):
        """
        Set up the OpenAI client and settings.
        This method should be called after FastAPI has injected the dependencies.
        """
        if self.client is None:
            # Initialize OpenAI client
            from openai import OpenAI
            self.client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            
            # Set default models and parameters
            self.text_model = getattr(self.settings, "OPENAI_MODEL", "gpt-4o")
            self.image_model = getattr(self.settings, "OPENAI_IMAGE_MODEL", "dall-e-3")
            self.default_quality = getattr(self.settings, "OPENAI_IMAGE_QUALITY", "standard")
            self.default_style = getattr(self.settings, "OPENAI_IMAGE_STYLE", "vivid")
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        # Ensure client is set up
        self.setup()
        """
        Generate text using the OpenAI API.
        
        Args:
            prompt: The prompt to generate text from
            model: The model to use (defaults to settings.OPENAI_MODEL)
            temperature: The temperature to use for generation
            max_tokens: The maximum number of tokens to generate
            progress_callback: Optional callback for progress updates
            
        Returns:
            The generated text
        """
        try:
            if progress_callback:
                await progress_callback(10, "Starting text generation")
            
            response = await self._call_openai_chat_api(
                messages=[{"role": "user", "content": prompt}],
                model=model or self.text_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            if progress_callback:
                await progress_callback(100, "Text generation complete")
            
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.exception(f"Error generating text: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text generation failed: {str(e)}"
            )
    
    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.7,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        # Ensure client is set up
        self.setup()
        """
        Generate structured output using the OpenAI API.
        
        Args:
            prompt: The prompt to generate text from
            output_schema: The JSON schema for the output
            model: The model to use (defaults to settings.OPENAI_MODEL)
            temperature: The temperature to use for generation
            progress_callback: Optional callback for progress updates
            
        Returns:
            The generated structured output
        """
        try:
            if progress_callback:
                await progress_callback(10, "Starting structured output generation")
            
            response = await self._call_openai_chat_api(
                messages=[{"role": "user", "content": prompt}],
                model=model or self.text_model,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            
            if progress_callback:
                await progress_callback(100, "Structured output generation complete")
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            return result
        except Exception as e:
            logger.exception(f"Error generating structured output: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Structured output generation failed: {str(e)}"
            )
    
    async def generate_structured_output_from_pydantic(
        self,
        prompt: str,
        output_model: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.7,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> T:
        """
        Generate structured output using the OpenAI API and parse it into a Pydantic model.
        
        Args:
            prompt: The prompt to generate text from
            output_model: The Pydantic model to parse the output into
            model: The model to use (defaults to settings.OPENAI_MODEL)
            temperature: The temperature to use for generation
            progress_callback: Optional callback for progress updates
            
        Returns:
            The generated structured output as a Pydantic model
        """
        try:
            # Get the JSON schema from the Pydantic model
            schema = output_model.model_json_schema()
            
            # Generate the structured output
            output_dict = await self.generate_structured_output(
                prompt=prompt,
                output_schema=schema,
                model=model,
                temperature=temperature,
                progress_callback=progress_callback,
            )
            
            # Parse the output into the Pydantic model
            return output_model.model_validate(output_dict)
        except Exception as e:
            logger.exception(f"Error generating structured output from Pydantic: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Structured output generation failed: {str(e)}"
            )
    
    async def generate_image(
        self, 
        request: Union[ImageGenerationRequest, str],
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Union[ImageGenerationResponse, str]:
        # Ensure client is set up
        self.setup()
        """
        Generate images from a text prompt using OpenAI's GPT-Image-1 model.
        
        Args:
            request: The image generation request or a prompt string
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The image generation response with image URLs or a single URL if a string prompt was provided
        """
        try:
            # Convert string prompt to request if needed
            if isinstance(request, str):
                prompt = request
                request = ImageGenerationRequest(prompt=prompt)
            else:
                prompt = request.prompt
            
            # Update progress if callback provided
            if progress_callback:
                await progress_callback(10, "Preparing image generation request")
            
            # Prepare the request to OpenAI
            openai_request = {
                "model": self.image_model,
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
                await progress_callback(20, "Sending request to OpenAI")
            
            # Call the OpenAI API
            response = await self._call_openai_image_api(openai_request)
            
            # Update progress if callback provided
            if progress_callback:
                await progress_callback(60, "Processing image generation results")
            
            # Extract the image data and revised prompt
            image_urls = []
            revised_prompt = None
            
            for i, image_data in enumerate(response.data):
                # Get the base64 image data
                b64_data = image_data.b64_json
                
                # Get the revised prompt if available
                if hasattr(image_data, 'revised_prompt'):
                    revised_prompt = image_data.revised_prompt
                
                # Generate a filename based on the prompt
                safe_prompt = request.prompt[:30].replace(" ", "_").lower()
                filename = f"{safe_prompt}_{i+1}.png"
                
                # Decode the base64 data
                image_bytes = base64.b64decode(b64_data)
                
                # Upload the image to storage
                storage_url = await self.storage_manager.upload_image(
                    file_data=image_bytes,
                    filename=filename,
                    content_type="image/png",
                    user_id=user_id
                )
                
                image_urls.append(storage_url)
            
            # Update progress if callback provided
            if progress_callback:
                await progress_callback(100, "Image generation complete")
            
            # Create the response
            result = ImageGenerationResponse(
                images=image_urls,
                prompt=request.prompt,
                revised_prompt=revised_prompt
            )
            
            logger.info(f"Generated {len(image_urls)} images successfully")
            
            # Return a single URL if a string prompt was provided
            if isinstance(request, str):
                return image_urls[0] if image_urls else ""
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {str(e)}"
            )
    
    async def generate_image_with_reference(
        self,
        prompt: str,
        reference_image_path: str,
        size: str = "1024x1024",
        quality: str = "high",
        style: str = "vivid",
        progress_callback: Optional[ProgressCallback] = None,
        user_id: Optional[str] = None,
    ) -> str:
        # Ensure client is set up
        self.setup()
        """
        Generate an image using the OpenAI API with a reference image.
        
        Args:
            prompt: The prompt to generate the image from
            reference_image_path: The path to the reference image
            size: The size of the image (1024x1024, 1792x1024, or 1024x1792)
            quality: The quality of the image (standard or hd)
            style: The style of the image (vivid or natural)
            progress_callback: Optional callback for progress updates
            user_id: Optional user ID for storage
            
        Returns:
            The URL of the generated image
        """
        try:
            if progress_callback:
                await progress_callback(10, "Starting image generation with reference")
            
            # Read the reference image
            with open(reference_image_path, "rb") as f:
                reference_image_data = f.read()
            
            # Incorporate style into the prompt if needed
            if style and style != "none":
                enhanced_prompt = f"{prompt} {style} style."
            else:
                enhanced_prompt = prompt
            
            # For gpt-image-1, we can't use reference_image parameter
            # Instead, we'll enhance the prompt with the reference image description
            enhanced_prompt = f"{enhanced_prompt} The image should be consistent with the reference image provided."
            
            # Create the request
            request = ImageGenerationRequest(
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                style=style
            )
            
            # Generate the image
            response = await self.generate_image(
                request=request,
                user_id=user_id,
                progress_callback=progress_callback
            )
            
            # Return the first image URL
            if isinstance(response, ImageGenerationResponse):
                return response.images[0] if response.images else ""
            return response
            
        except Exception as e:
            logger.error(f"Error generating image with reference: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation with reference failed: {str(e)}"
            )
    
    async def generate_image_variation(
        self,
        image_path: str,
        size: str = "1024x1024",
        quality: str = "high",
        n: int = 1,
        progress_callback: Optional[ProgressCallback] = None,
        user_id: Optional[str] = None,
    ) -> List[str]:
        # Ensure client is set up
        self.setup()
        """
        Generate variations of an image using the OpenAI API.
        
        Args:
            image_path: The path to the image to generate variations of
            size: The size of the image (1024x1024, 1792x1024, or 1024x1792)
            quality: The quality of the image (standard or hd)
            n: The number of variations to generate
            progress_callback: Optional callback for progress updates
            user_id: Optional user ID for storage
            
        Returns:
            A list of URLs of the generated image variations
        """
        try:
            if progress_callback:
                await progress_callback(10, "Starting image variation generation")
            
            # Read the image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Create the request
            response = await self._call_openai_image_variation_api(
                image=image_data,
                size=size,
                quality=quality,
                n=n,
            )
            
            # Process the response
            image_urls = []
            for i, image in enumerate(response.data):
                if hasattr(image, 'b64_json') and image.b64_json:
                    # Decode the base64 data
                    image_bytes = base64.b64decode(image.b64_json)
                    
                    # Generate a filename
                    filename = f"variation_{i+1}.png"
                    
                    # Upload the image to storage
                    storage_url = await self.storage_manager.upload_image(
                        file_data=image_bytes,
                        filename=filename,
                        content_type="image/png",
                        user_id=user_id
                    )
                    
                    image_urls.append(storage_url)
                elif hasattr(image, 'url') and image.url:
                    # Download the image from the URL
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image.url) as resp:
                            if resp.status == 200:
                                image_bytes = await resp.read()
                                
                                # Generate a filename
                                filename = f"variation_{i+1}.png"
                                
                                # Upload the image to storage
                                storage_url = await self.storage_manager.upload_image(
                                    file_data=image_bytes,
                                    filename=filename,
                                    content_type="image/png",
                                    user_id=user_id
                                )
                                
                                image_urls.append(storage_url)
            
            if progress_callback:
                await progress_callback(100, "Image variation generation complete")
            
            return image_urls
            
        except Exception as e:
            logger.error(f"Error generating image variation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image variation generation failed: {str(e)}"
            )
    
    async def _call_openai_chat_api(self, messages, model, temperature, max_tokens=None, response_format=None):
        # Ensure client is set up
        self.setup()
        """Helper method to call OpenAI chat API with proper error handling."""
        try:
            # Prepare the API call parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Add max_tokens if provided
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Add response_format if provided
            if response_format:
                params["response_format"] = response_format
            
            # Call the API
            return await asyncio.to_thread(
                self.client.chat.completions.create,
                **params
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI chat API: {str(e)}")
            raise
    
    async def _call_openai_image_api(self, params):
        # Ensure client is set up
        self.setup()
        """Helper method to call OpenAI image API with proper error handling."""
        try:
            return await asyncio.to_thread(
                self.client.images.generate,
                **params
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI image API: {str(e)}")
            raise
    
    async def _call_openai_image_variation_api(self, image, size, quality, n):
        # Ensure client is set up
        self.setup()
        """Helper method to call OpenAI image variation API with proper error handling."""
        try:
            return await asyncio.to_thread(
                self.client.images.create_variation,
                image=image,
                size=size,
                quality=quality,
                n=n,
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI image variation API: {str(e)}")
            raise
