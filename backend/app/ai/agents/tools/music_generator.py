"""
Tool for generating music for groups of scenes.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.ai.models.video_metadata import MusicDefinition
from app.ai.models.task import ProgressCallback
from app.services.replicate import ReplicateService
from app.services.storage.base import StorageService

# Set up logging
logger = logging.getLogger(__name__)


class MusicGeneratorTool:
    """Tool for generating music for groups of scenes."""
    
    def __init__(
        self,
        replicate_service: Optional[ReplicateService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        """
        Initialize the music generator tool.
        
        Args:
            replicate_service: Replicate service instance (creates a new one if None)
            storage_service: Storage service instance (creates a new one if None)
        """
        self.replicate_service = replicate_service or ReplicateService()
        
        # Use StorageAdapter instead of StorageService
        from app.ai.utils.storage_adapter import StorageAdapter
        self.storage_adapter = StorageAdapter()
    
    async def generate_music_for_scene_groups(
        self,
        music_definitions: List[MusicDefinition],
        scene_assets: Dict[int, Dict[str, Any]],
        style: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[int, str]:
        """
        Generate music for groups of scenes.
        
        Args:
            music_definitions: List of music definitions
            scene_assets: Dictionary mapping scene indexes to their assets
            style: Style of the video
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping scene indexes to music URLs
        """
        if not music_definitions:
            logger.warning("No music definitions provided")
            return {}
        
        if progress_callback:
            await progress_callback(10, f"Generating music for {len(music_definitions)} groups")
        
        # Process each music definition
        music_urls = {}
        total_definitions = len(music_definitions)
        
        for i, music_def in enumerate(music_definitions):
            if progress_callback:
                progress = 10 + int((i / total_definitions) * 80)
                await progress_callback(progress, f"Generating music for group {i+1}/{total_definitions}")
            
            # Calculate the total duration for this group
            total_duration = self._calculate_group_duration(music_def.scene_indexes, scene_assets)
            logger.info(f"Total duration for music group {i+1}: {total_duration} seconds")
            
            # Generate the music
            music_url = await self._generate_music(music_def.prompt, total_duration, style)
            
            # Update the music definition with the URL
            music_def.music_url = music_url
            
            # Assign the music URL to all scenes in this group
            for scene_index in music_def.scene_indexes:
                music_urls[scene_index] = music_url
        
        if progress_callback:
            await progress_callback(100, "Music generation complete")
        
        return music_urls
    
    def _calculate_group_duration(
        self,
        scene_indexes: List[int],
        scene_assets: Dict[int, Dict[str, Any]],
    ) -> int:
        """
        Calculate the total duration for a group of scenes.
        
        Args:
            scene_indexes: List of scene indexes
            scene_assets: Dictionary mapping scene indexes to their assets
            
        Returns:
            Total duration in seconds
        """
        total_duration = 0
        for scene_index in scene_indexes:
            if scene_index in scene_assets:
                # Use the audio duration if available, otherwise use a default
                duration = scene_assets[scene_index].get("duration", 5.0)
                total_duration += duration
        
        # Ensure minimum duration of 8 seconds (Replicate's minimum)
        return max(8, int(total_duration))
    
    async def _generate_music(
        self,
        prompt: str,
        duration: int,
        style: str,
    ) -> str:
        """
        Generate music for a group of scenes.
        
        Args:
            prompt: The prompt for music generation
            duration: Duration of the music in seconds
            style: Style of the video
            
        Returns:
            URL of the generated music
        """
        try:
            # Enhance the prompt with style information
            enhanced_prompt = f"{prompt} {style} style."
            
            # Generate the music
            music_url = await self.replicate_service.generate_music(
                prompt=enhanced_prompt,
                duration=duration,
                model_version="stereo-large",
                output_format="mp3",
                temperature=1.0,
                top_k=250,
                top_p=0.0,
                classifier_free_guidance=3.0,
                normalization_strategy="peak",
            )
            
            # Download and store the music
            filename = f"music_group_{duration}s.mp3"
            local_path = await self.storage_adapter.download_and_store_audio(music_url, filename, "music")
            
            # Return the public URL
            return self.storage_adapter.get_public_url_sync(local_path)
        
        except Exception as e:
            logger.error(f"Error generating music: {e}")
            # Return a placeholder music URL
            return self.storage_adapter.get_placeholder_audio_url()
    
    async def regenerate_music(
        self,
        prompt: str,
        duration: int,
        style: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Regenerate music with a different prompt or style.
        
        Args:
            prompt: The prompt for music generation
            duration: Duration of the music in seconds
            style: Style of the video
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the regenerated music
        """
        if progress_callback:
            await progress_callback(10, f"Regenerating music for duration {duration}s")
        
        # Generate new music
        music_url = await self._generate_music(prompt, duration, style)
        
        if progress_callback:
            await progress_callback(100, "Music regeneration complete")
        
        return music_url
