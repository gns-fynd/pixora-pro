"""
Text-to-speech service using Replicate.

This module provides a service for generating speech using Replicate's LLASA model.
"""
import logging
from typing import Dict, Any, Optional, List

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.replicate.base import ReplicateService, ProgressCallback


# Set up logging
logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    """Request model for text-to-speech."""
    
    text: str = Field(..., description="The text to convert to speech")
    voice_sample_url: Optional[str] = Field(None, description="Optional URL to a voice sample for cloning")
    chunk_length: int = Field(200, description="Maximum chunk length for processing long text")


class TTSResponse(BaseModel):
    """Response model for text-to-speech."""
    
    audio_url: str = Field(..., description="URL to the generated audio")
    duration: Optional[float] = Field(None, description="Duration of the audio in seconds")


class VoiceCloneTTSService:
    """Service for generating speech using Replicate's LLASA model."""
    
    def __init__(
        self,
        replicate_service: ReplicateService = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the TTS service.
        
        Args:
            replicate_service: The Replicate service
            settings: Application settings
        """
        self.replicate_service = replicate_service
        self.settings = settings
        
        # LLASA model ID
        self.tts_model = "kjjk10/llasa-3b-long:0494f04972b675631af41c253a45c4341bf637f07eed9a39bad3b1fd66f73a2e"
    
    async def generate_speech(
        self,
        request: TTSRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TTSResponse:
        """
        Generate speech using LLASA.
        
        Args:
            request: The TTS request
            user_id: Optional user ID for tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            The TTS response
        """
        try:
            # Log the request
            logger.info(f"Generating speech with LLASA: {len(request.text)} characters")
            
            if progress_callback:
                await progress_callback(10, "Initializing TTS model")
            
            # Check if text is too long and needs chunking
            MAX_CHARS_PER_CHUNK = 3000  # Maximum characters per chunk
            if len(request.text) > MAX_CHARS_PER_CHUNK:
                return await self._generate_speech_chunked(request, user_id, progress_callback)
            
            # Prepare the input for the LLASA model
            input_data = {
                "text": request.text,
                "chunk_length": request.chunk_length
            }
            
            # Add return_timestamps=True for long texts (>3000 characters)
            # This is required by the model for longer texts
            if len(request.text) > 3000:
                logger.info(f"Text length is {len(request.text)} characters, adding return_timestamps=True")
                input_data["return_timestamps"] = True
            
            # Add voice sample if provided
            if request.voice_sample_url:
                input_data["voice_sample"] = request.voice_sample_url
            
            # Run the model
            result = await self.replicate_service.run_model(
                model_id=self.tts_model,  # Fixed parameter name to match base.py
                input_data=input_data,    # Fixed parameter name to match base.py
                progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback(100, "Audio generation complete")
            
            # Handle the result, which could be a string URL, a dictionary, or a binary file-like object
            audio_url = ""
            
            # First, try to handle it as a binary response
            if hasattr(result, "read"):
                # It's a file-like object, handle it
                filename_prefix = "tts"
                audio_url = await self.replicate_service.handle_binary_response(
                    response=result,
                    file_type="audio",
                    filename_prefix=filename_prefix,
                    storage_category="audio"
                )
            # If it's a string, use it directly
            elif isinstance(result, str):
                audio_url = result
            # If it's a dictionary, try to get the output URL
            elif isinstance(result, dict) and "output" in result:
                audio_url = result["output"]
            
            if not audio_url:
                raise ValueError("No audio output returned from the TTS model")
            
            # Estimate duration based on text length (rough estimate: 3 chars per second)
            estimated_duration = len(request.text) / 3
            
            # Return the response
            return TTSResponse(
                audio_url=audio_url,
                duration=estimated_duration
            )
        
        except Exception as e:
            logger.error(f"Error generating speech with TTS: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech generation failed: {str(e)}"
            )
    
    async def _generate_speech_chunked(
        self,
        request: TTSRequest,
        user_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TTSResponse:
        """
        Generate speech for long text by breaking it into chunks.
        
        Args:
            request: The TTS request
            user_id: Optional user ID for tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            The TTS response with combined audio
        """
        import re
        from app.ai.utils.storage_adapter import StorageAdapter
        
        # Create a storage adapter
        storage_adapter = StorageAdapter()
        
        # Log the chunking process
        logger.info(f"Text too long ({len(request.text)} chars), breaking into chunks")
        
        # Maximum characters per chunk
        MAX_CHARS_PER_CHUNK = 3000
        
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', request.text)
        
        # Group sentences into chunks
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed the limit, start a new chunk
            if len(current_chunk) + len(sentence) > MAX_CHARS_PER_CHUNK:
                if current_chunk:  # Don't add empty chunks
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                # Add to current chunk with a space if not empty
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Log the number of chunks
        logger.info(f"Split text into {len(chunks)} chunks")
        
        # Generate audio for each chunk
        audio_urls = []
        total_duration = 0
        
        for i, chunk in enumerate(chunks):
            # Update progress
            if progress_callback:
                progress_percent = 10 + (i / len(chunks)) * 80
                await progress_callback(progress_percent, f"Processing chunk {i+1}/{len(chunks)}")
            
            # Create a new request for this chunk
            chunk_request = TTSRequest(
                text=chunk,
                voice_sample_url=request.voice_sample_url,
                chunk_length=request.chunk_length
            )
            
            # Generate speech for this chunk
            chunk_response = await self.generate_speech(
                request=chunk_request,
                user_id=user_id,
                progress_callback=None  # Don't pass progress callback to avoid nested updates
            )
            
            # Add the audio URL and duration
            audio_urls.append(chunk_response.audio_url)
            total_duration += chunk_response.duration or 0
        
        # Combine the audio files
        if progress_callback:
            await progress_callback(90, "Combining audio chunks")
        
        combined_audio_url = await self._combine_audio_files(audio_urls)
        
        if progress_callback:
            await progress_callback(100, "Audio generation complete")
        
        # Return the response with the combined audio URL
        return TTSResponse(
            audio_url=combined_audio_url,
            duration=total_duration
        )
        
    async def _combine_audio_files(self, audio_urls: List[str]) -> str:
        """
        Combine multiple audio files into a single file.
        
        Args:
            audio_urls: List of audio URLs to combine
            
        Returns:
            URL of the combined audio file
        """
        import tempfile
        import os
        import asyncio
        import uuid
        from app.ai.utils.storage_adapter import StorageAdapter
        
        if not audio_urls:
            return ""
        
        if len(audio_urls) == 1:
            return audio_urls[0]
        
        # Create a storage adapter
        storage_adapter = StorageAdapter()
        
        # Create a temporary directory for the audio files
        temp_dir = await storage_adapter.create_temp_directory()
        
        try:
            # Download all audio files
            input_files = []
            for i, url in enumerate(audio_urls):
                # Skip empty URLs
                if not url:
                    continue
                
                # Get the local path if it's a local file
                local_path = storage_adapter.get_local_path(url)
                
                if local_path:
                    # It's already a local file
                    input_files.append(local_path)
                else:
                    # It's a remote URL, download it
                    temp_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
                    await storage_adapter.download_and_store_audio(url, os.path.basename(temp_path))
                    input_files.append(temp_path)
            
            # Create a file list for ffmpeg
            file_list_path = os.path.join(temp_dir, "file_list.txt")
            with open(file_list_path, "w") as f:
                for input_file in input_files:
                    f.write(f"file '{input_file}'\n")
            
            # Create an output file
            output_path = os.path.join(temp_dir, f"combined_{uuid.uuid4()}.mp3")
            
            # Use ffmpeg to concatenate the audio files
            command = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-f", "concat",  # Use concat demuxer
                "-safe", "0",  # Don't require safe filenames
                "-i", file_list_path,  # Input file list
                "-c", "copy",  # Copy codec (no re-encoding)
                output_path  # Output file
            ]
            
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error combining audio files: {stderr.decode()}")
                # Fall back to the first file
                return audio_urls[0]
            
            # Upload the combined file
            with open(output_path, "rb") as f:
                combined_url = await storage_adapter.save_audio(
                    file_data=f,
                    filename=f"combined_tts_{uuid.uuid4()}.mp3"
                )
            
            return combined_url
            
        except Exception as e:
            logger.error(f"Error combining audio files: {str(e)}")
            # Fall back to the first file
            return audio_urls[0] if audio_urls else ""
        finally:
            # Clean up the temporary directory
            await storage_adapter.cleanup_temp_directory(temp_dir)
