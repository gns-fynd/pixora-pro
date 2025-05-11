"""
Asset generation tools for the Pixora AI application.

This module provides tools for generating various assets like character images,
scene images, voice overs, and music.
"""
import os
import logging
import asyncio
import tempfile
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union

from app.models import CharacterProfile, Scene, MusicPrompt
from app.services.openai import OpenAIService
from app.services.replicate import ReplicateService
from app.services.storage import StorageService
from app.ai.utils import (
    save_file, ensure_directory_exists, generate_unique_filename,
    get_audio_duration, normalize_audio
)

# Set up logging
logger = logging.getLogger(__name__)


async def generate_character_images(
    character_profile: CharacterProfile,
    views: List[str] = ["front"],
    storage_service: StorageService = None,
    openai_service: OpenAIService = None,
) -> Dict[str, str]:
    """
    Generate character images based on a character profile.

    Args:
        character_profile: The character profile
        views: List of views to generate (e.g., "front", "side", "back")
        storage_service: The storage service
        openai_service: The OpenAI service

    Returns:
        Dictionary mapping view names to image URLs
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for character image generation")
    
    if not storage_service:
        raise ValueError("Storage service is required for character image generation")
    
    try:
        image_urls = {}
        
        # Generate images for each view
        for view in views:
            # Create a prompt for the view
            prompt = f"{character_profile.image_prompt}"
            
            if view == "front":
                prompt += ", front view, facing camera"
            elif view == "side":
                prompt += ", side profile view"
            elif view == "back":
                prompt += ", back view"
            elif view == "three_quarter":
                prompt += ", three-quarter view"
            
            # Add quality parameters
            prompt += ", high quality, detailed, 4K, professional lighting"
            
            # Generate the image
            logger.info(f"Generating {view} view image for character: {character_profile.name}")
            image_data = await openai_service.generate_image(prompt)
            
            if not image_data:
                logger.error(f"Failed to generate {view} view image for character: {character_profile.name}")
                continue
            
            # Save the image
            file_name = generate_unique_filename(f"character_{character_profile.name}_{view}", "png")
            file_info = await storage_service.save_file(
                file_content=image_data,
                file_type="character",
                file_id=file_name,
                file_extension=".png"
            )
            
            # Store the URL
            image_urls[view] = file_info["file_url"]
            
            logger.info(f"Generated {view} view image for character: {character_profile.name}")
        
        # Update the character profile with the image URLs
        character_profile.image_urls = image_urls
        
        return image_urls
    except Exception as e:
        logger.error(f"Error generating character images: {str(e)}")
        raise


async def generate_scene_image(
    scene: Scene,
    style: str = "cinematic",
    storage_service: StorageService = None,
    openai_service: OpenAIService = None,
) -> str:
    """
    Generate a scene image based on a scene description.

    Args:
        scene: The scene
        style: The style of the image
        storage_service: The storage service
        openai_service: The OpenAI service

    Returns:
        URL to the generated image
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for scene image generation")
    
    if not storage_service:
        raise ValueError("Storage service is required for scene image generation")
    
    try:
        # Create a prompt for the scene
        prompt = scene.video_prompt
        
        # Add style parameters
        if style == "cinematic":
            prompt += ", cinematic, movie scene, professional cinematography, film quality"
        elif style == "cartoon":
            prompt += ", cartoon style, animated, vibrant colors"
        elif style == "realistic":
            prompt += ", photorealistic, detailed, high resolution"
        elif style == "artistic":
            prompt += ", artistic, creative, stylized"
        
        # Add quality parameters
        prompt += ", high quality, detailed, 4K, professional lighting"
        
        # Generate the image
        logger.info(f"Generating image for scene: {scene.title}")
        image_data = await openai_service.generate_image(prompt)
        
        if not image_data:
            logger.error(f"Failed to generate image for scene: {scene.title}")
            raise ValueError(f"Failed to generate image for scene: {scene.title}")
        
        # Save the image
        file_name = generate_unique_filename(f"scene_{scene.index}", "png")
        file_info = await storage_service.save_file(
            file_content=image_data,
            file_type="scene",
            file_id=file_name,
            file_extension=".png"
        )
        
        logger.info(f"Generated image for scene: {scene.title}")
        
        return file_info["file_url"]
    except Exception as e:
        logger.error(f"Error generating scene image: {str(e)}")
        raise


async def generate_voice_over(
    script: str,
    voice_character: Optional[str] = None,
    storage_service: StorageService = None,
    replicate_service: ReplicateService = None,
) -> Tuple[str, float]:
    """
    Generate a voice over from a script.

    Args:
        script: The script text
        voice_character: Optional URL to a voice sample
        storage_service: The storage service
        replicate_service: The Replicate service

    Returns:
        Tuple of (URL to the generated audio, duration in seconds)
    """
    if not replicate_service:
        raise ValueError("Replicate service is required for voice over generation")
    
    if not storage_service:
        raise ValueError("Storage service is required for voice over generation")
    
    try:
        # Generate the voice over
        logger.info(f"Generating voice over for script: {script[:50]}...")
        
        # Use Replicate's LLaSA-3B-Long for voice synthesis
        audio_data = await replicate_service.generate_voice_over(
            text=script,
            voice_sample_url=voice_character
        )
        
        if not audio_data:
            logger.error(f"Failed to generate voice over for script: {script[:50]}...")
            raise ValueError(f"Failed to generate voice over")
        
        # Save the audio to a temporary file to get its duration
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        try:
            # Get the duration of the audio
            duration = get_audio_duration(temp_file_path)
            
            if duration is None:
                logger.warning("Could not determine voice over duration, using estimate")
                # Estimate duration based on word count (average speaking rate is about 150 words per minute)
                word_count = len(script.split())
                duration = word_count / 2.5  # 150 words per minute = 2.5 words per second
            
            # Normalize the audio
            normalized_temp_path = temp_file_path + ".normalized.mp3"
            normalize_audio(temp_file_path, normalized_temp_path)
            
            # Save the normalized audio
            file_name = generate_unique_filename("voice_over", "mp3")
            with open(normalized_temp_path, "rb") as f:
                normalized_audio_data = f.read()
            
            file_info = await storage_service.save_file(
                file_content=normalized_audio_data,
                file_type="audio",
                file_id=file_name,
                file_extension=".mp3"
            )
            
            logger.info(f"Generated voice over with duration: {duration:.2f} seconds")
            
            return file_info["file_url"], duration
        finally:
            # Clean up temporary files
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(normalized_temp_path):
                os.remove(normalized_temp_path)
    except Exception as e:
        logger.error(f"Error generating voice over: {str(e)}")
        raise


async def generate_music(
    prompt: str,
    duration: float,
    storage_service: StorageService = None,
    replicate_service: ReplicateService = None,
) -> str:
    """
    Generate background music.

    Args:
        prompt: The music description
        duration: The desired duration in seconds
        storage_service: The storage service
        replicate_service: The Replicate service

    Returns:
        URL to the generated music
    """
    if not replicate_service:
        raise ValueError("Replicate service is required for music generation")
    
    if not storage_service:
        raise ValueError("Storage service is required for music generation")
    
    try:
        # Generate the music
        logger.info(f"Generating music for prompt: {prompt}")
        
        # Use Meta's MusicGen through Replicate
        audio_data = await replicate_service.generate_music(
            prompt=prompt,
            duration=duration
        )
        
        if not audio_data:
            logger.error(f"Failed to generate music for prompt: {prompt}")
            raise ValueError(f"Failed to generate music")
        
        # Save the music
        file_name = generate_unique_filename("music", "mp3")
        file_info = await storage_service.save_file(
            file_content=audio_data,
            file_type="music",
            file_id=file_name,
            file_extension=".mp3"
        )
        
        logger.info(f"Generated music for prompt: {prompt}")
        
        return file_info["file_url"]
    except Exception as e:
        logger.error(f"Error generating music: {str(e)}")
        raise


async def generate_assets_for_scene(
    scene: Scene,
    style: str = "cinematic",
    voice_character: Optional[str] = None,
    storage_service: StorageService = None,
    openai_service: OpenAIService = None,
    replicate_service: ReplicateService = None,
) -> Dict[str, Any]:
    """
    Generate all assets for a scene.

    Args:
        scene: The scene
        style: The style of the scene
        voice_character: Optional URL to a voice sample
        storage_service: The storage service
        openai_service: The OpenAI service
        replicate_service: The Replicate service

    Returns:
        Dictionary with asset URLs and metadata
    """
    try:
        # Generate assets in parallel
        scene_image_task = asyncio.create_task(
            generate_scene_image(
                scene=scene,
                style=style,
                storage_service=storage_service,
                openai_service=openai_service
            )
        )
        
        voice_over_task = asyncio.create_task(
            generate_voice_over(
                script=scene.script,
                voice_character=voice_character,
                storage_service=storage_service,
                replicate_service=replicate_service
            )
        )
        
        # Wait for all tasks to complete
        scene_image_url = await scene_image_task
        voice_over_url, voice_over_duration = await voice_over_task
        
        # Return the assets
        return {
            "scene_image_url": scene_image_url,
            "voice_over_url": voice_over_url,
            "voice_over_duration": voice_over_duration
        }
    except Exception as e:
        logger.error(f"Error generating assets for scene: {str(e)}")
        raise


async def generate_music_for_scenes(
    music_prompts: List[MusicPrompt],
    scene_count: int,
    storage_service: StorageService = None,
    replicate_service: ReplicateService = None,
) -> Dict[int, str]:
    """
    Generate music for scenes based on music prompts.

    Args:
        music_prompts: List of music prompts
        scene_count: Total number of scenes
        storage_service: The storage service
        replicate_service: The Replicate service

    Returns:
        Dictionary mapping scene indexes to music URLs
    """
    try:
        # Create a mapping of scene indexes to music prompts
        scene_to_music_prompt = {}
        for music_prompt in music_prompts:
            for scene_index in music_prompt.scene_indexes:
                scene_to_music_prompt[scene_index] = music_prompt.prompt
        
        # Generate music for each unique prompt
        unique_prompts = set(music_prompt.prompt for music_prompt in music_prompts)
        prompt_to_url = {}
        
        for prompt in unique_prompts:
            # Estimate duration based on the number of scenes using this music
            scenes_with_prompt = sum(
                1 for music_prompt in music_prompts
                if music_prompt.prompt == prompt
                for _ in music_prompt.scene_indexes
            )
            
            # Assume each scene is about 15 seconds
            estimated_duration = scenes_with_prompt * 15
            
            # Generate the music
            music_url = await generate_music(
                prompt=prompt,
                duration=estimated_duration,
                storage_service=storage_service,
                replicate_service=replicate_service
            )
            
            prompt_to_url[prompt] = music_url
        
        # Map scene indexes to music URLs
        scene_to_music_url = {}
        for scene_index in range(1, scene_count + 1):
            if scene_index in scene_to_music_prompt:
                prompt = scene_to_music_prompt[scene_index]
                scene_to_music_url[scene_index] = prompt_to_url[prompt]
        
        return scene_to_music_url
    except Exception as e:
        logger.error(f"Error generating music for scenes: {str(e)}")
        raise
