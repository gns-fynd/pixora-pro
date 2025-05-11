"""
Music generation service using Replicate's Meta MusicGen model.

This module provides a service for generating music from text prompts
using the Meta MusicGen model via Replicate.
"""
import logging
import os
import tempfile
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union, BinaryIO

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.replicate.base import ReplicateService, ProgressCallback
from app.services.storage import StorageManager


# Set up logging
logger = logging.getLogger(__name__)


class ModelVersion(str, Enum):
    """
    Available model versions for Meta MusicGen.
    """
    STEREO_SMALL = "stereo-small"
    STEREO_MEDIUM = "stereo-medium"
    STEREO_LARGE = "stereo-large"
    MELODY = "melody"


class OutputFormat(str, Enum):
    """
    Available output formats for Meta MusicGen.
    """
    MP3 = "mp3"
    WAV = "wav"


class NormalizationStrategy(str, Enum):
    """
    Available normalization strategies for Meta MusicGen.
    """
    PEAK = "peak"
    LOUDNESS = "loudness"
    CLIP = "clip"
    RMS = "rms"


class MusicGenerationRequest(BaseModel):
    """
    Request model for music generation.
    """
    prompt: str = Field(..., description="The text prompt to generate music from")
    duration: int = Field(8, description="Duration of the generated audio in seconds", ge=1, le=30)
    model_version: ModelVersion = Field(ModelVersion.STEREO_LARGE, description="The model version to use")
    output_format: OutputFormat = Field(OutputFormat.MP3, description="The output format")
    temperature: float = Field(1.0, description="Temperature for sampling", ge=0.0, le=1.0)
    top_k: int = Field(250, description="Top-k sampling", ge=0, le=500)
    top_p: float = Field(0.0, description="Top-p sampling", ge=0.0, le=1.0)
    classifier_free_guidance: float = Field(3.0, description="Classifier-free guidance scale", ge=1.0, le=10.0)
    continuation: bool = Field(False, description="Whether to continue from a previous generation")
    continuation_start: float = Field(0.0, description="Start time for continuation in seconds", ge=0.0)
    multi_band_diffusion: bool = Field(False, description="Whether to use multi-band diffusion")
    normalization_strategy: NormalizationStrategy = Field(NormalizationStrategy.PEAK, description="Normalization strategy")


class MusicGenerationResponse(BaseModel):
    """
    Response model for music generation.
    """
    audio_url: str = Field(..., description="URL of the generated audio")
    prompt: str = Field(..., description="The prompt used to generate the audio")
    duration: int = Field(..., description="Duration of the generated audio in seconds")
    model_version: str = Field(..., description="The model version used")


class MusicGenerationService:
    """
    Service for generating music from text prompts using Meta MusicGen via Replicate.
    """
    
    def __init__(
        self, 
        replicate_service: ReplicateService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the music generation service.
        
        Args:
            replicate_service: The Replicate service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.replicate_service = replicate_service
        self.storage_manager = storage_manager
        self.settings = settings
        
        # Meta MusicGen model ID
        self.model_id = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
    
    async def generate_music(
        self, 
        request: MusicGenerationRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> MusicGenerationResponse:
        """
        Generate music from a text prompt.
        
        Args:
            request: The music generation request
            user_id: Optional user ID for storage path
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The music generation response with audio URL
        """
        try:
            # Prepare the input data for the model
            input_data = {
                "prompt": request.prompt,
                "duration": request.duration,
                "model_version": request.model_version,
                "output_format": request.output_format,
                "temperature": request.temperature,
                "top_k": request.top_k,
                "top_p": request.top_p,
                "classifier_free_guidance": request.classifier_free_guidance,
                "continuation": request.continuation,
                "continuation_start": request.continuation_start,
                "multi_band_diffusion": request.multi_band_diffusion,
                "normalization_strategy": request.normalization_strategy
            }
            
            # Update progress
            if progress_callback:
                progress_callback(10.0, "Starting music generation")
            
            # Run the model
            logger.info(f"Generating music with prompt: {request.prompt}")
            output = await self.replicate_service.run_model(
                model_id=self.model_id,
                input_data=input_data,
                progress_callback=lambda progress, message: progress_callback(
                    10.0 + progress * 0.7,  # Scale progress to 10-80%
                    message
                ) if progress_callback else None
            )
            
            # Update progress
            if progress_callback:
                progress_callback(80.0, "Music generation complete, uploading to storage")
            
            # Generate a filename based on the prompt
            safe_prompt = request.prompt[:30].replace(" ", "_").lower()
            extension = "mp3" if request.output_format == OutputFormat.MP3 else "wav"
            filename = f"{safe_prompt}.{extension}"
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Download the audio to the temporary file
                await self.replicate_service.download_output(
                    output=output,
                    output_path=temp_path,
                    progress_callback=lambda progress, message: progress_callback(
                        80.0 + progress * 0.1,  # Scale progress to 80-90%
                        message
                    ) if progress_callback else None
                )
                
                # Read the temporary file
                with open(temp_path, "rb") as file:
                    file_data = file.read()
                
                # Upload the audio to storage
                content_type = "audio/mpeg" if extension == "mp3" else "audio/wav"
                storage_url = await self.storage_manager.upload_audio(
                    file_data=file_data,
                    filename=filename,
                    content_type=content_type,
                    user_id=user_id
                )
                
                # Update progress
                if progress_callback:
                    progress_callback(100.0, "Music generation and upload complete")
                
                # Create the response
                response = MusicGenerationResponse(
                    audio_url=storage_url,
                    prompt=request.prompt,
                    duration=request.duration,
                    model_version=request.model_version
                )
                
                logger.info(f"Generated music successfully: {storage_url}")
                return response
                
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error generating music: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Music generation failed: {str(e)}"
            )
