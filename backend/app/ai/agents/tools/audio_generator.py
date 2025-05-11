"""
Audio generator tool for the video agent.

This module provides tools for generating narration audio and background music.
"""
import logging
from typing import Dict, Any, Optional, List, Union

from fastapi import Depends

from app.services.replicate.tts import VoiceCloneTTSService, TTSRequest
from app.services.replicate.base import ReplicateService
from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
from app.ai.utils.storage_adapter import StorageAdapter


# Set up logging
logger = logging.getLogger(__name__)


class AudioGeneratorTool:
    """
    Tool for generating audio for scenes.
    """
    
    def __init__(
        self,
        tts_service: VoiceCloneTTSService = Depends(),
        replicate_service: ReplicateService = Depends(),
        storage_adapter: HierarchicalStorageAdapter = Depends()
    ):
        """
        Initialize the audio generator tool.
        
        Args:
            tts_service: The TTS service for narration
            replicate_service: The Replicate service for music generation
            storage_adapter: The storage adapter for saving audio
        """
        self.tts_service = tts_service
        self.replicate_service = replicate_service
        self.storage_adapter = storage_adapter
    
    async def generate_narration(
        self,
        task_id: str,
        scene_index: int,
        script: str,
        voice_sample_url: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate narration audio for a scene.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            script: The narration script
            voice_sample_url: Optional URL to a voice sample for cloning
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with audio information
        """
        try:
            # Log the request
            logger.info(f"Generating narration for scene {scene_index} with script: {script[:100]}...")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Generating narration for scene {scene_index}")
            
            # Create the TTS request
            tts_request = TTSRequest(
                text=script,
                voice_sample_url=voice_sample_url,
                chunk_length=200  # Default chunk length
            )
            
            # Generate the audio
            tts_response = await self.tts_service.generate_speech(
                request=tts_request,
                user_id=user_id
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Narration generated, saving to storage")
            
            # Get the audio URL
            audio_url = tts_response.audio_url
            
            # Download and save the audio to storage
            stored_url = await self.storage_adapter.save_scene_audio(
                task_id=task_id,
                scene_index=scene_index,
                file_data=await self._download_audio(audio_url),
                filename=f"scene_{scene_index}_narration.mp3",
                audio_type="narration"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Narration saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "audio_url": stored_url,
                "script": script,
                "duration": tts_response.duration,
                "voice_sample_url": voice_sample_url
            }
            
        except Exception as e:
            logger.error(f"Error generating narration for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def regenerate_narration(
        self,
        task_id: str,
        scene_index: int,
        new_script: str,
        voice_sample_url: Optional[str] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Regenerate narration audio for a scene.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            new_script: The new narration script
            voice_sample_url: Optional URL to a voice sample for cloning
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with audio information
        """
        try:
            # Log the request
            logger.info(f"Regenerating narration for scene {scene_index} with script: {new_script[:100]}...")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Regenerating narration for scene {scene_index}")
            
            # Create the TTS request
            tts_request = TTSRequest(
                text=new_script,
                voice_sample_url=voice_sample_url,
                chunk_length=200  # Default chunk length
            )
            
            # Generate the audio
            tts_response = await self.tts_service.generate_speech(
                request=tts_request,
                user_id=user_id
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Narration regenerated, saving to storage")
            
            # Get the audio URL
            audio_url = tts_response.audio_url
            
            # Download and save the audio to storage
            import time
            stored_url = await self.storage_adapter.save_scene_audio(
                task_id=task_id,
                scene_index=scene_index,
                file_data=await self._download_audio(audio_url),
                filename=f"scene_{scene_index}_narration_v{int(time.time())}.mp3",
                audio_type="narration"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Narration saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "audio_url": stored_url,
                "script": new_script,
                "duration": tts_response.duration,
                "voice_sample_url": voice_sample_url
            }
            
        except Exception as e:
            logger.error(f"Error regenerating narration for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def generate_music(
        self,
        task_id: str,
        mood: str,
        duration: int,
        genre: str = "ambient",
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate background music.
        
        Args:
            task_id: The task ID
            mood: The mood of the music
            duration: The duration in seconds
            genre: The music genre
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with music information
        """
        try:
            # Log the request
            logger.info(f"Generating background music with mood: {mood}, genre: {genre}, duration: {duration}s")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Generating background music")
            
            # Create the prompt for music generation
            prompt = f"{mood} {genre} music, instrumental, no vocals"
            
            # Generate the music
            music_url = await self.replicate_service.generate_music(
                prompt=prompt,
                duration=min(duration, 30),  # MusicGen has a 30-second limit
                model_version="stereo-large",
                output_format="mp3",
                temperature=1.0,
                progress_callback=lambda progress, message: progress_callback(10 + progress * 0.4, message) if progress_callback else None
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Music generated, saving to storage")
            
            # Download and save the music to storage
            stored_url = await self.storage_adapter.save_background_music(
                task_id=task_id,
                file_data=await self._download_audio(music_url),
                filename=f"background_music_{mood}_{genre}.mp3"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Music saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "audio_url": stored_url,
                "mood": mood,
                "genre": genre,
                "duration": duration,
                "prompt": prompt
            }
            
        except Exception as e:
            logger.error(f"Error generating background music: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _download_audio(self, url: str) -> bytes:
        """
        Download audio from a URL.
        
        Args:
            url: The audio URL
            
        Returns:
            The audio data as bytes
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content


# Function tool for OpenAI Assistants API
async def generate_narration_tool(
    ctx,
    scene_index: int,
    script: str,
    voice_type: str = "neutral"
) -> Dict[str, Any]:
    """
    Generate narration audio for a scene.
    
    Args:
        scene_index: The index of the scene to generate narration for
        script: The narration script
        voice_type: The type of voice to use (neutral, male, female, etc.)
        
    Returns:
        Dictionary with audio information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Get voice sample URL based on voice type
    voice_sample_url = None
    voice_samples = ctx.context.get("voice_samples", {})
    
    if voice_type in voice_samples:
        voice_sample_url = voice_samples[voice_type]
    
    # Create the audio generator tool
    from app.services.replicate.tts import VoiceCloneTTSService
    from app.services.replicate.base import ReplicateService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    tts_service = VoiceCloneTTSService()
    replicate_service = ReplicateService()
    storage_adapter = HierarchicalStorageAdapter()
    
    audio_generator = AudioGeneratorTool(
        tts_service=tts_service,
        replicate_service=replicate_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="narration_generation",
            progress=progress,
            message=message
        )
    
    # Generate the narration
    result = await audio_generator.generate_narration(
        task_id=task_id,
        scene_index=scene_index,
        script=script,
        voice_sample_url=voice_sample_url,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    scene_key = f"scene_{scene_index}"
    scenes = ctx.context.get("scenes", {})
    
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    if "audio" not in scenes[scene_key]:
        scenes[scene_key]["audio"] = {}
    
    scenes[scene_key]["audio"]["narration"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result


# Function tool for OpenAI Assistants API
async def regenerate_scene_audio_tool(
    ctx,
    scene_index: int,
    new_script: str,
    voice_character_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Regenerate narration audio for a scene.
    
    Args:
        scene_index: The index of the scene to regenerate narration for
        new_script: The new narration script
        voice_character_url: Optional URL to a voice sample for cloning
        
    Returns:
        Dictionary with audio information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the audio generator tool
    from app.services.replicate.tts import VoiceCloneTTSService
    from app.services.replicate.base import ReplicateService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    tts_service = VoiceCloneTTSService()
    replicate_service = ReplicateService()
    storage_adapter = HierarchicalStorageAdapter()
    
    audio_generator = AudioGeneratorTool(
        tts_service=tts_service,
        replicate_service=replicate_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="narration_regeneration",
            progress=progress,
            message=message
        )
    
    # Regenerate the narration
    result = await audio_generator.regenerate_narration(
        task_id=task_id,
        scene_index=scene_index,
        new_script=new_script,
        voice_sample_url=voice_character_url,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    scene_key = f"scene_{scene_index}"
    scenes = ctx.context.get("scenes", {})
    
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    if "audio" not in scenes[scene_key]:
        scenes[scene_key]["audio"] = {}
    
    scenes[scene_key]["audio"]["narration"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result


# Function tool for OpenAI Assistants API
async def generate_music_tool(
    ctx,
    mood: str,
    duration: int,
    genre: str = "ambient"
) -> Dict[str, Any]:
    """
    Generate background music matching the mood.
    
    Args:
        mood: The mood of the music (e.g., "happy", "sad", "tense", "relaxed")
        duration: Duration in seconds (max 30)
        genre: The music genre (e.g., "ambient", "electronic", "orchestral")
        
    Returns:
        Dictionary with music information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the audio generator tool
    from app.services.replicate.tts import VoiceCloneTTSService
    from app.services.replicate.base import ReplicateService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    tts_service = VoiceCloneTTSService()
    replicate_service = ReplicateService()
    storage_adapter = HierarchicalStorageAdapter()
    
    audio_generator = AudioGeneratorTool(
        tts_service=tts_service,
        replicate_service=replicate_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="music_generation",
            progress=progress,
            message=message
        )
    
    # Generate the music
    result = await audio_generator.generate_music(
        task_id=task_id,
        mood=mood,
        duration=min(duration, 30),  # MusicGen has a 30-second limit
        genre=genre,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    ctx.context.set("background_music", result)
    
    # Return the result
    return result
