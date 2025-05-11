"""
Text-to-music service using Fal.ai elevenlabs/sound-effects model.

This module provides a service for generating music and sound effects from text
using the Fal.ai elevenlabs/sound-effects model.
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


class TextToMusicRequest(BaseModel):
    """
    Request model for text-to-music generation.
    """
    text: str = Field(..., description="The text description of the music or sound effect to generate")
    duration: float = Field(5.0, description="Duration of the generated audio in seconds", ge=1.0, le=30.0)
    prompt_influence: float = Field(0.5, description="How closely to follow the prompt", ge=0.0, le=1.0)


class TextToMusicResponse(BaseModel):
    """
    Response model for text-to-music generation.
    """
    audio_url: str = Field(..., description="URL of the generated audio")
    text: str = Field(..., description="The text used to generate the audio")
    duration: float = Field(..., description="Duration of the generated audio in seconds")


class TextToMusicService:
    """
    Service for generating music and sound effects from text using Fal.ai elevenlabs/sound-effects model.
    """
    
    def __init__(
        self, 
        fal_service: FalAiService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the text-to-music service.
        
        Args:
            fal_service: The Fal.ai service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.fal_service = fal_service
        self.storage_manager = storage_manager
        self.model_endpoint = settings.FAL_TEXT_TO_MUSIC_MODEL
    
    async def generate_music(
        self, 
        request: TextToMusicRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TextToMusicResponse:
        """
        Generate music or sound effects from a text description.
        
        Args:
            request: The text-to-music request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The text-to-music response with audio URL
        """
        try:
            # Prepare the arguments for the Fal.ai model
            arguments = {
                "text": request.text,
                "duration": request.duration,
                "prompt_influence": request.prompt_influence,
            }
            
            # Call the model
            logger.info(f"Generating music from text: {request.text[:50]}...")
            result = await self.fal_service.call_model(
                model_endpoint=self.model_endpoint,
                arguments=arguments,
                progress_callback=progress_callback,
                with_logs=True
            )
            
            # Extract the audio URL from the result
            if "audio" in result and "url" in result["audio"]:
                fal_audio_url = result["audio"]["url"]
            else:
                logger.error(f"Unexpected result structure: {result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected response format from text-to-music service"
                )
            
            # Generate a filename based on the text
            safe_text = request.text[:30].replace(" ", "_").lower()
            filename = f"{safe_text}.mp3"
            
            # Upload the audio from the Fal.ai URL to our storage
            storage_url = await self.storage_manager.upload_file_from_url(
                url=fal_audio_url,
                bucket=self.storage_manager.audio_bucket,
                content_type="audio/mpeg",
                user_id=user_id
            )
            
            # Create the response
            response = TextToMusicResponse(
                audio_url=storage_url,
                text=request.text,
                duration=request.duration
            )
            
            logger.info(f"Generated music successfully: {storage_url}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating music: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Music generation failed: {str(e)}"
            )
    
    async def generate_background_music(
        self, 
        mood: str,
        duration: float = 10.0,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TextToMusicResponse:
        """
        Generate background music with a specific mood.
        
        Args:
            mood: The mood of the music (e.g., "happy", "sad", "suspenseful")
            duration: Duration of the generated audio in seconds
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The text-to-music response with audio URL
        """
        # Create a more detailed prompt based on the mood
        prompt_map = {
            "happy": "Upbeat and cheerful background music with a positive vibe",
            "sad": "Melancholic and emotional background music with a somber tone",
            "suspenseful": "Tense and dramatic background music with building suspense",
            "relaxing": "Calm and soothing background music with gentle melodies",
            "epic": "Grand and powerful background music with orchestral elements",
            "mysterious": "Intriguing and enigmatic background music with subtle tension",
            "romantic": "Warm and tender background music with emotional melodies",
            "playful": "Light and fun background music with a whimsical character",
        }
        
        # Use the mapped prompt or the mood directly if not in the map
        text = prompt_map.get(mood.lower(), f"{mood} background music")
        
        # Create the request
        request = TextToMusicRequest(
            text=text,
            duration=duration,
            prompt_influence=0.7  # Higher influence for better adherence to the mood
        )
        
        # Generate the music
        return await self.generate_music(
            request=request,
            user_id=user_id,
            progress_callback=progress_callback
        )
    
    async def generate_sound_effect(
        self, 
        description: str,
        duration: float = 3.0,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TextToMusicResponse:
        """
        Generate a sound effect with a specific description.
        
        Args:
            description: The description of the sound effect
            duration: Duration of the generated audio in seconds
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The text-to-music response with audio URL
        """
        # Create the request with higher prompt influence for sound effects
        request = TextToMusicRequest(
            text=f"Sound effect: {description}",
            duration=duration,
            prompt_influence=0.9  # Higher influence for more accurate sound effects
        )
        
        # Generate the sound effect
        return await self.generate_music(
            request=request,
            user_id=user_id,
            progress_callback=progress_callback
        )
