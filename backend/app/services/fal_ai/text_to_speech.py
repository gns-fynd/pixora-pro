"""
Text-to-speech service using Fal.ai minimax-tts model.

This module provides a service for generating speech from text
using the Fal.ai minimax-tts voice clone model.
"""
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum

from fastapi import Depends, HTTPException, status, UploadFile
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.fal_ai.base import FalAiService, ProgressCallback
from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class VoiceCloneRequest(BaseModel):
    """
    Request model for voice cloning.
    """
    audio_url: str = Field(..., description="URL of the audio file to clone voice from (at least 10 seconds)")
    noise_reduction: bool = Field(True, description="Whether to apply noise reduction to the audio")
    volume_normalization: bool = Field(True, description="Whether to normalize the volume of the audio")


class VoiceCloneResponse(BaseModel):
    """
    Response model for voice cloning.
    """
    voice_id: str = Field(..., description="ID of the cloned voice")
    audio_url: str = Field(..., description="URL of the source audio")


class TextToSpeechRequest(BaseModel):
    """
    Request model for text-to-speech generation.
    """
    text: str = Field(..., description="The text to convert to speech")
    voice_id: str = Field(..., description="ID of the voice to use")
    speed: float = Field(1.0, description="Speech speed multiplier", ge=0.5, le=2.0)


class TextToSpeechResponse(BaseModel):
    """
    Response model for text-to-speech generation.
    """
    audio_url: str = Field(..., description="URL of the generated audio")
    text: str = Field(..., description="The text used to generate the audio")
    voice_id: str = Field(..., description="ID of the voice used")


class TextToSpeechService:
    """
    Service for generating speech from text using Fal.ai minimax-tts model.
    """
    
    def __init__(
        self, 
        fal_service: FalAiService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the text-to-speech service.
        
        Args:
            fal_service: The Fal.ai service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.fal_service = fal_service
        self.storage_manager = storage_manager
        self.model_endpoint = settings.FAL_TEXT_TO_SPEECH_MODEL
    
    async def clone_voice(
        self, 
        request: VoiceCloneRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> VoiceCloneResponse:
        """
        Clone a voice from an audio file.
        
        Args:
            request: The voice clone request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The voice clone response with voice ID
        """
        try:
            # Prepare the arguments for the Fal.ai model
            arguments = {
                "audio_url": request.audio_url,
                "noise_reduction": request.noise_reduction,
                "volume_normalization": request.volume_normalization,
            }
            
            # Call the model
            logger.info(f"Cloning voice from audio: {request.audio_url}")
            result = await self.fal_service.call_model(
                model_endpoint=self.model_endpoint,
                arguments=arguments,
                progress_callback=progress_callback,
                with_logs=True
            )
            
            # Extract the voice ID from the result
            if "voice_id" in result:
                voice_id = result["voice_id"]
            else:
                logger.error(f"Unexpected result structure: {result}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected response format from voice cloning service"
                )
            
            # Create the response
            response = VoiceCloneResponse(
                voice_id=voice_id,
                audio_url=request.audio_url
            )
            
            logger.info(f"Cloned voice successfully: {voice_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error cloning voice: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Voice cloning failed: {str(e)}"
            )
    
    async def clone_voice_from_file(
        self, 
        audio_file: UploadFile,
        noise_reduction: bool = True,
        volume_normalization: bool = True,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> VoiceCloneResponse:
        """
        Clone a voice from an uploaded audio file.
        
        Args:
            audio_file: The uploaded audio file
            noise_reduction: Whether to apply noise reduction to the audio
            volume_normalization: Whether to normalize the volume of the audio
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The voice clone response with voice ID
        """
        try:
            # Read the audio file
            audio_data = await audio_file.read()
            
            # Upload the audio to our storage
            audio_url = await self.storage_manager.upload_audio(
                file_data=audio_data,
                filename=audio_file.filename,
                content_type=audio_file.content_type,
                user_id=user_id
            )
            
            # Create the request
            request = VoiceCloneRequest(
                audio_url=audio_url,
                noise_reduction=noise_reduction,
                volume_normalization=volume_normalization
            )
            
            # Clone the voice
            return await self.clone_voice(
                request=request,
                user_id=user_id,
                progress_callback=progress_callback
            )
            
        except Exception as e:
            logger.error(f"Error cloning voice from file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Voice cloning from file failed: {str(e)}"
            )
    
    async def generate_speech(
        self, 
        request: TextToSpeechRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TextToSpeechResponse:
        """
        Generate speech from text.
        
        Args:
            request: The text-to-speech request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The text-to-speech response with audio URL
        """
        try:
            # Prepare the arguments for the Fal.ai model
            arguments = {
                "text": request.text,
                "voice_id": request.voice_id,
                "speed": request.speed,
            }
            
            # Call the model
            logger.info(f"Generating speech from text: {request.text[:50]}...")
            result = await self.fal_service.call_model(
                model_endpoint=f"{self.model_endpoint}/tts",  # Use the TTS endpoint
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
                    detail="Unexpected response format from text-to-speech service"
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
            response = TextToSpeechResponse(
                audio_url=storage_url,
                text=request.text,
                voice_id=request.voice_id
            )
            
            logger.info(f"Generated speech successfully: {storage_url}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech generation failed: {str(e)}"
            )
