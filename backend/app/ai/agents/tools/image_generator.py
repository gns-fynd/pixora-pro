"""
Image generator tool for the video agent.

This module provides tools for generating and regenerating images for scenes.
"""
import logging
import time
from typing import Dict, Any, Optional, List, Union

from fastapi import Depends
from openai.types.chat import ChatCompletionMessageToolCall

from app.services.openai import OpenAIService
from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
from app.ai.utils.storage_adapter import StorageAdapter


# Set up logging
logger = logging.getLogger(__name__)


class ImageGeneratorTool:
    """
    Tool for generating images for scenes.
    """
    
    def __init__(
        self,
        openai_service: OpenAIService = Depends(),
        storage_adapter: HierarchicalStorageAdapter = Depends()
    ):
        """
        Initialize the image generator tool.
        
        Args:
            openai_service: The OpenAI service for image generation
            storage_adapter: The storage adapter for saving images
        """
        self.openai_service = openai_service
        self.storage_adapter = storage_adapter
    
    async def generate_scene_image(
        self,
        task_id: str,
        scene_index: int,
        prompt: str,
        style: str,
        aspect_ratio: str = "16:9",
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate an image for a scene.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            prompt: The image prompt
            style: The image style
            aspect_ratio: The aspect ratio (16:9, 4:3, 1:1)
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with image information
        """
        try:
            # Log the request
            logger.info(f"Generating image for scene {scene_index} with prompt: {prompt[:100]}...")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Generating image for scene {scene_index}")
            
            # Enhance the prompt with the style
            enhanced_prompt = self._enhance_prompt(prompt, style)
            
            # Determine image dimensions based on aspect ratio
            width, height = self._get_dimensions_from_aspect_ratio(aspect_ratio)
            
            # Generate the image
            image_data = await self.openai_service.generate_image(
                prompt=enhanced_prompt,
                size=f"{width}x{height}",
                quality="hd",
                style="vivid"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Image generated, saving to storage")
            
            # Get the image URL
            image_url = image_data.data[0].url
            
            # Download and save the image to storage
            stored_url = await self.storage_adapter.save_scene_image(
                task_id=task_id,
                scene_index=scene_index,
                file_data=await self._download_image(image_url),
                filename=f"scene_{scene_index}_image.png"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Image saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "image_url": stored_url,
                "prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "style": style,
                "aspect_ratio": aspect_ratio,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Error generating image for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def regenerate_scene_image(
        self,
        task_id: str,
        scene_index: int,
        new_prompt: str,
        style_adjustments: Optional[str] = None,
        aspect_ratio: str = "16:9",
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Regenerate an image for a scene with adjustments.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            new_prompt: The new image prompt
            style_adjustments: Optional style adjustments
            aspect_ratio: The aspect ratio (16:9, 4:3, 1:1)
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with image information
        """
        try:
            # Log the request
            logger.info(f"Regenerating image for scene {scene_index} with prompt: {new_prompt[:100]}...")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Regenerating image for scene {scene_index}")
            
            # Enhance the prompt with the style adjustments
            enhanced_prompt = self._enhance_prompt(new_prompt, style_adjustments or "")
            
            # Determine image dimensions based on aspect ratio
            width, height = self._get_dimensions_from_aspect_ratio(aspect_ratio)
            
            # Generate the image
            image_data = await self.openai_service.generate_image(
                prompt=enhanced_prompt,
                size=f"{width}x{height}",
                quality="hd",
                style="vivid"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Image regenerated, saving to storage")
            
            # Get the image URL
            image_url = image_data.data[0].url
            
            # Download and save the image to storage
            stored_url = await self.storage_adapter.save_scene_image(
                task_id=task_id,
                scene_index=scene_index,
                file_data=await self._download_image(image_url),
                filename=f"scene_{scene_index}_image_v{int(time.time())}.png"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Image saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "image_url": stored_url,
                "prompt": new_prompt,
                "enhanced_prompt": enhanced_prompt,
                "style_adjustments": style_adjustments,
                "aspect_ratio": aspect_ratio,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Error regenerating image for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """
        Enhance a prompt with style information.
        
        Args:
            prompt: The base prompt
            style: The style description
            
        Returns:
            Enhanced prompt
        """
        # If style is empty, return the original prompt
        if not style:
            return prompt
        
        # Combine the prompt and style
        return f"{prompt}. Style: {style}"
    
    def _get_dimensions_from_aspect_ratio(self, aspect_ratio: str) -> tuple:
        """
        Get image dimensions from an aspect ratio.
        
        Args:
            aspect_ratio: The aspect ratio (16:9, 4:3, 1:1)
            
        Returns:
            Tuple of (width, height)
        """
        # Default to 1024x1024 for square
        if aspect_ratio == "1:1":
            return (1024, 1024)
        
        # 16:9 widescreen
        if aspect_ratio == "16:9":
            return (1792, 1024)  # Closest to 16:9 that works with DALL-E
        
        # 4:3 standard
        if aspect_ratio == "4:3":
            return (1344, 1024)  # Closest to 4:3 that works with DALL-E
        
        # 9:16 vertical (mobile)
        if aspect_ratio == "9:16":
            return (1024, 1792)  # Closest to 9:16 that works with DALL-E
        
        # Default to 1024x1024 for unknown aspect ratios
        logger.warning(f"Unknown aspect ratio: {aspect_ratio}, defaulting to 1:1")
        return (1024, 1024)
    
    async def _download_image(self, url: str) -> bytes:
        """
        Download an image from a URL.
        
        Args:
            url: The image URL
            
        Returns:
            The image data as bytes
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content


# Function tool for OpenAI Assistants API
async def generate_scene_image_tool(
    ctx,
    scene_index: int,
    prompt: str,
    style: str,
    aspect_ratio: str = "16:9"
) -> Dict[str, Any]:
    """
    Generate an image for a specific scene.
    
    Args:
        scene_index: The index of the scene to generate an image for
        prompt: The image prompt describing what to generate
        style: The style of the image (e.g., "photorealistic", "cartoon", "cinematic")
        aspect_ratio: The aspect ratio of the image (16:9, 4:3, 1:1)
        
    Returns:
        Dictionary with image information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the image generator tool
    from app.services.openai import OpenAIService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    openai_service = OpenAIService()
    storage_adapter = HierarchicalStorageAdapter()
    
    image_generator = ImageGeneratorTool(
        openai_service=openai_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="image_generation",
            progress=progress,
            message=message
        )
    
    # Generate the image
    result = await image_generator.generate_scene_image(
        task_id=task_id,
        scene_index=scene_index,
        prompt=prompt,
        style=style,
        aspect_ratio=aspect_ratio,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    scene_key = f"scene_{scene_index}"
    scenes = ctx.context.get("scenes", {})
    
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    scenes[scene_key]["image"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result


# Function tool for OpenAI Assistants API
async def regenerate_scene_image_tool(
    ctx,
    scene_index: int,
    new_prompt: str,
    style_adjustments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Regenerate the image for a specific scene.
    
    Args:
        scene_index: The index of the scene to regenerate an image for
        new_prompt: The new image prompt
        style_adjustments: Optional style adjustments
        
    Returns:
        Dictionary with image information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Get the current scene data
    scenes = ctx.context.get("scenes", {})
    scene_key = f"scene_{scene_index}"
    
    # Get the current aspect ratio
    aspect_ratio = "16:9"  # Default
    if scene_key in scenes and "image" in scenes[scene_key]:
        aspect_ratio = scenes[scene_key]["image"].get("aspect_ratio", "16:9")
    
    # Create the image generator tool
    from app.services.openai import OpenAIService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    openai_service = OpenAIService()
    storage_adapter = HierarchicalStorageAdapter()
    
    image_generator = ImageGeneratorTool(
        openai_service=openai_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="image_regeneration",
            progress=progress,
            message=message
        )
    
    # Regenerate the image
    result = await image_generator.regenerate_scene_image(
        task_id=task_id,
        scene_index=scene_index,
        new_prompt=new_prompt,
        style_adjustments=style_adjustments,
        aspect_ratio=aspect_ratio,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    scenes[scene_key]["image"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result
