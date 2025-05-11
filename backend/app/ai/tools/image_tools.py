"""
Image generation tools for Pixora AI Agent.

This module provides tools for image generation using OpenAI's GPT-Image-1 model.
"""

import json
import logging
import tempfile
import os
import base64
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import aiohttp
from openai import AsyncOpenAI

from app.ai.tools.base import Tool


# Set up logging
logger = logging.getLogger(__name__)


class OpenAIImageGenerationTool(Tool):
    """Tool for generating images using OpenAI's GPT-Image-1 model."""
    
    def __init__(self):
        super().__init__(
            name="generate_image",
            description="Generates an image based on a text description using OpenAI's GPT-Image-1 model",
            parameters_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate"
                    },
                    "size": {
                        "type": "string",
                        "description": "Size of the image to generate",
                        "enum": ["1024x1024", "1024x1792", "1792x1024"]
                    },
                    "quality": {
                        "type": "string",
                        "description": "Quality of the image",
                        "enum": ["standard", "hd"]
                    },
                    "style": {
                        "type": "string",
                        "description": "Style of the image",
                        "enum": ["vivid", "natural"]
                    }
                },
                "required": ["prompt"]
            }
        )
    
    async def execute(self, prompt: str, size: str = "1024x1024", 
                     quality: str = "standard", style: str = "vivid") -> str:
        """
        Generate an image from a text prompt using OpenAI's GPT-Image-1.
        
        Args:
            prompt: Detailed description of the image to generate
            size: Size of the image (1024x1024, 1024x1792, or 1792x1024)
            quality: Quality of the image (standard or hd)
            style: Style of the image (vivid or natural)
            
        Returns:
            JSON string containing the generated image information
        """
        try:
            # Import the service
            from app.services.openai import OpenAIImageGenerationService, ImageGenerationRequest, ImageSize, ImageQuality, ImageStyle
            from app.core.config import get_settings
            from app.services.storage import StorageManager
            
            # Create the service
            settings = get_settings()
            storage_manager = StorageManager(settings)
            image_service = OpenAIImageGenerationService(storage_manager, settings)
            
            # Map the size parameter to the appropriate enum value
            size_map = {
                "1024x1024": ImageSize.SQUARE_1024,
                "1024x1792": ImageSize.PORTRAIT_1024_1792,
                "1792x1024": ImageSize.LANDSCAPE_1792_1024
            }
            image_size = size_map.get(size, ImageSize.SQUARE_1024)
            
            # Create the request
            request = ImageGenerationRequest(
                prompt=prompt,
                size=image_size,
                quality=ImageQuality(quality),
                style=ImageStyle(style),
                num_images=1
            )
            
            # Generate the image
            response = await image_service.generate_image(request)
            
            # Return the result
            return json.dumps({
                "image_url": response.images[0],
                "prompt": response.prompt,
                "revised_prompt": response.revised_prompt
            })
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return json.dumps({
                "error": f"Image generation failed: {str(e)}"
            })


class OpenAIImageEditTool(Tool):
    """Tool for editing images using OpenAI's GPT-Image-1 model."""
    
    def __init__(self):
        super().__init__(
            name="edit_image",
            description="Edits an existing image or combines multiple images based on a text prompt using OpenAI's GPT-Image-1 model",
            parameters_schema={
                "type": "object",
                "properties": {
                    "image_urls": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "URLs of the images to edit or combine (up to 4 images)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the desired edits or composition"
                    },
                    "size": {
                        "type": "string",
                        "description": "Size of the output image",
                        "enum": ["1024x1024", "1024x1792", "1792x1024"]
                    }
                },
                "required": ["image_urls", "prompt"]
            }
        )
    
    async def execute(self, image_urls: List[str], prompt: str, size: str = "1024x1024") -> str:
        """
        Edit or combine images based on a text prompt using OpenAI's GPT-Image-1.
        
        Args:
            image_urls: List of URLs of the images to edit or combine (up to 4 images)
            prompt: Detailed description of the desired edits or composition
            size: Size of the output image
            
        Returns:
            JSON string containing the edited image information
        """
        try:
            # Validate input
            if not image_urls:
                raise ValueError("At least one image URL must be provided")
            
            if len(image_urls) > 4:
                raise ValueError("Maximum of 4 images can be processed at once")
            
            # Download the images
            temp_files = []
            for url in image_urls:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download image: {response.status}")
                        image_data = await response.read()
                
                # Create a temporary file for the image
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_file.write(image_data)
                    temp_files.append(temp_file.name)
            
            try:
                # Create OpenAI client
                client = AsyncOpenAI()
                
                # Open the image files
                image_file_handles = [open(file_path, "rb") for file_path in temp_files]
                
                try:
                    # Call the OpenAI API for image editing using the dedicated edit endpoint
                    response = await client.images.edit(
                        model="gpt-image-1",
                        image=image_file_handles,
                        prompt=prompt,
                        response_format="b64_json"
                    )
                    
                    # Extract the base64 image data
                    b64_data = response.data[0].b64_json
                    
                    # Save the image to a temporary file
                    image_bytes = base64.b64decode(b64_data)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file:
                        output_file.write(image_bytes)
                        output_file_path = output_file.name
                    
                    # In a real implementation, we would upload this to a storage service
                    # For now, we'll simulate it with a mock URL
                    edited_image_url = f"https://example.com/images/{os.path.basename(output_file_path)}"
                    
                    # Return the result
                    return json.dumps({
                        "image_url": edited_image_url,
                        "b64_data": b64_data,
                        "original_image_urls": image_urls,
                        "prompt": prompt,
                        "usage": response.usage._asdict() if hasattr(response, 'usage') else None
                    })
                finally:
                    # Close all file handles
                    for handle in image_file_handles:
                        handle.close()
            finally:
                # Clean up the temporary files
                for file_path in temp_files:
                    os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error editing image: {str(e)}")
            return json.dumps({
                "error": f"Image editing failed: {str(e)}"
            })


class OpenAIImageVariationTool(Tool):
    """Tool for creating variations of images using OpenAI's GPT-Image-1 model."""
    
    def __init__(self):
        super().__init__(
            name="create_image_variation",
            description="Creates variations of an existing image using OpenAI's GPT-Image-1 model",
            parameters_schema={
                "type": "object",
                "properties": {
                    "image_url": {
                        "type": "string",
                        "description": "URL of the image to create variations from"
                    },
                    "size": {
                        "type": "string",
                        "description": "Size of the output image",
                        "enum": ["1024x1024", "1024x1792", "1792x1024"]
                    },
                    "num_variations": {
                        "type": "integer",
                        "description": "Number of variations to generate",
                        "minimum": 1,
                        "maximum": 4
                    }
                },
                "required": ["image_url"]
            }
        )
    
    async def execute(self, image_url: str, size: str = "1024x1024", num_variations: int = 1) -> str:
        """
        Create variations of an image using OpenAI's GPT-Image-1.
        
        Args:
            image_url: URL of the image to create variations from
            size: Size of the output image
            num_variations: Number of variations to generate
            
        Returns:
            JSON string containing the variation image information
        """
        try:
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download image: {response.status}")
                    image_data = await response.read()
            
            # Create a temporary file for the image
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            try:
                # Create OpenAI client
                client = AsyncOpenAI()
                
                # Open the image file
                with open(temp_file_path, "rb") as image_file:
                    # Call the OpenAI API for image variations using the dedicated create_variation endpoint
                    response = await client.images.create_variation(
                        model="gpt-image-1",
                        image=image_file,
                        n=num_variations,
                        size=size,
                        response_format="b64_json"
                    )
                
                # Process the variations
                variations = []
                for i, variation in enumerate(response.data):
                    # Extract the base64 image data
                    b64_data = variation.b64_json
                    
                    # Save the image to a temporary file
                    image_bytes = base64.b64decode(b64_data)
                    with tempfile.NamedTemporaryFile(suffix=f"_var{i+1}.png", delete=False) as output_file:
                        output_file.write(image_bytes)
                        output_file_path = output_file.name
                    
                    # In a real implementation, we would upload this to a storage service
                    # For now, we'll simulate it with a mock URL
                    variation_url = f"https://example.com/images/{os.path.basename(output_file_path)}"
                    
                    variations.append({
                        "image_url": variation_url,
                        "b64_data": b64_data
                    })
                
                # Return the result
                return json.dumps({
                    "variations": variations,
                    "original_image_url": image_url,
                    "usage": response.usage._asdict() if hasattr(response, 'usage') else None
                })
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)
        except Exception as e:
            logger.error(f"Error creating image variations: {str(e)}")
            return json.dumps({
                "error": f"Image variation failed: {str(e)}"
            })
