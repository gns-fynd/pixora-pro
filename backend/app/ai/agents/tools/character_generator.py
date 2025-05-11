"""
Tool for generating consistent character profiles with 4-angle views.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple

from app.ai.models.task import ProgressCallback
from app.services.openai import OpenAIService
from app.ai.utils.storage_adapter import StorageAdapter
from app.ai.utils.json_utils import save_json_response
from app.ai.models.video_metadata import CharacterProfile

# Set up logging
logger = logging.getLogger(__name__)


class CharacterGeneratorTool:
    """Tool for generating consistent character profiles with 4-angle views."""
    
    def __init__(
        self,
        openai_service: Optional[OpenAIService] = None,
        storage_service: Optional[StorageAdapter] = None,
    ):
        """
        Initialize the character generator tool.
        
        Args:
            openai_service: OpenAI service instance (creates a new one if None)
            storage_service: Storage service instance (creates a new one if None)
        """
        self.openai_service = openai_service or OpenAIService()
        self.storage_service = storage_service or StorageAdapter()
    
    async def generate_character_profiles(
        self,
        character_profiles: List[CharacterProfile],
        style: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate consistent character profiles with 4-angle reference images.
        
        Args:
            character_profiles: List of character profiles with image prompts
            style: Style of the video
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping character names to their profiles with image URLs
        """
        if not character_profiles:
            logger.warning("No character profiles provided for generation")
            return {}
        
        if progress_callback:
            await progress_callback(10, f"Generating profiles for {len(character_profiles)} characters")
        
        # Process each character in parallel
        character_results = {}
        total_characters = len(character_profiles)
        
        for i, profile in enumerate(character_profiles):
            if progress_callback:
                progress = 10 + int((i / total_characters) * 80)
                await progress_callback(progress, f"Generating profile for character {i+1}/{total_characters}: {profile.name}")
            
            # Generate character images
            character_data = await self._generate_character_data(profile, style, progress_callback)
            character_results[profile.name] = character_data
        
        if progress_callback:
            await progress_callback(100, "Character profiles complete")
        
        return character_results
    
    async def _generate_character_data(
        self,
        profile: CharacterProfile,
        style: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        Generate data for a single character.
        
        Args:
            profile: Character profile with image prompt
            style: Style of the video
            progress_callback: Optional callback for progress updates
            
        Returns:
            Character data with images
        """
        # Create the character data
        character_data = {
            "name": profile.name,
            "image_prompt": profile.image_prompt,
            "images": {},
        }
        
        # Generate the character image
        try:
            # Generate a high-quality character image
            # Create a request object with an enhanced prompt
            from app.services.openai.service import ImageGenerationRequest, ImageGenerationResponse
            
            # Directly enhance the prompt for better character generation
            original_prompt = profile.image_prompt
            enhanced_prompt = original_prompt
            
            # If the prompt already contains "4 angles", remove that part
            if "4 angles:" in enhanced_prompt:
                # Extract the character description part
                description = enhanced_prompt.split("4 angles:")[1].strip()
                enhanced_prompt = description
            
            # Add style-specific enhancements
            if style.lower() in ["realistic", "cinematic", "photorealistic"]:
                enhanced_prompt = f"Photorealistic portrait of {enhanced_prompt}, detailed facial features, professional photography, studio lighting, 8k, ultra detailed"
            elif style.lower() in ["anime", "cartoon"]:
                enhanced_prompt = f"High-quality anime style portrait of {enhanced_prompt}, detailed character design, vibrant colors, studio ghibli inspired"
            elif style.lower() in ["3d", "cgi"]:
                enhanced_prompt = f"Highly detailed 3D rendered portrait of {enhanced_prompt}, subsurface scattering, ray tracing, physically based rendering"
            else:
                # Default enhancement
                enhanced_prompt = f"Highly detailed portrait of {enhanced_prompt}, professional quality, perfect lighting"
            
            # Add quality boosters
            enhanced_prompt += ", high resolution, masterpiece, best quality, intricate details, sharp focus"
            
            # Log the enhanced prompt
            logger.info(f"Enhanced character prompt for {profile.name}: {enhanced_prompt[:100]}...")
            
            request = ImageGenerationRequest(
                prompt=enhanced_prompt,
                size="1024x1024",
                style="vivid" if style.lower() in ["realistic", "cinematic"] else "natural",
                quality="hd",  # Use high quality setting
            )
            response = await self.openai_service.generate_image(
                request=request,
            )
            
            # Extract the image URL from the response
            if isinstance(response, ImageGenerationResponse):
                image_url = response.images[0] if response.images else self.storage_service.get_placeholder_image_url()
            else:
                # If it's already a string URL, use it directly
                image_url = response
            
            # Download and store the image using the storage adapter
            filename = f"{profile.name.replace(' ', '_')}_4angles.png"
            local_path = await self.storage_service.download_and_store_image(image_url, filename, "characters")
            
            # Store the local URL using the synchronous version to avoid coroutine objects
            public_url = self.storage_service.get_public_url_sync(local_path)
            character_data["images"]["combined"] = public_url
            
            # For compatibility with existing code, also store as "front" view
            character_data["images"]["front"] = public_url
            
            # Update the profile's image_urls
            profile.image_urls = {
                "combined": public_url,
                "front": public_url
            }
            
            # Log the character data
            logger.info(f"Generated character data for {profile.name}")
            
            # Save the character data to a JSON file
            save_json_response(
                data=character_data,
                category="character_profiles",
                name=f"character_{profile.name.replace(' ', '_')}"
            )
            
            return character_data
            
        except Exception as e:
            logger.error(f"Error generating character data for {profile.name}: {e}")
            # Return minimal data on error
            character_data["images"] = {
                "combined": None,
                "front": None,
            }
            return character_data
    
    async def regenerate_character_image(
        self,
        profile: CharacterProfile,
        style: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate a character image with a different prompt or style.
        
        Args:
            profile: Character profile with image prompt
            style: Style of the video
            progress_callback: Optional callback for progress updates
            
        Returns:
            Updated character data with new images
        """
        if progress_callback:
            await progress_callback(10, f"Regenerating image for character: {profile.name}")
        
        # Generate new character data
        character_data = await self._generate_character_data(profile, style, progress_callback)
        
        if progress_callback:
            await progress_callback(100, f"Character image regenerated for {profile.name}")
        
        return character_data
