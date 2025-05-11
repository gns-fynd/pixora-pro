"""
Base service for interacting with Replicate models.

This module provides a base service for interacting with Replicate models.
"""
import logging
import os
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union, BinaryIO

import replicate
from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings


# Set up logging
logger = logging.getLogger(__name__)

# Type for progress callback function
ProgressCallback = Callable[[float, Optional[str]], None]


class ReplicateService:
    """
    Base service for interacting with Replicate models.
    """
    
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the Replicate service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.api_token_set = False
        
        # Initialize storage adapter directly instead of using Depends
        from app.ai.utils.storage_adapter import StorageAdapter
        self.storage_adapter = StorageAdapter()
    
    def setup(self):
        """
        Set up the Replicate client and settings.
        This method should be called after FastAPI has injected the dependencies.
        """
        if not self.api_token_set:
            # Set the Replicate API token
            if hasattr(self.settings, 'REPLICATE_API_TOKEN') and self.settings.REPLICATE_API_TOKEN:
                os.environ["REPLICATE_API_TOKEN"] = self.settings.REPLICATE_API_TOKEN
                self.api_token_set = True
            else:
                logger.warning("REPLICATE_API_TOKEN not set in environment variables")
    
    async def run_model(
        self,
        model_id: str,
        input_data: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Any:
        """
        Run a Replicate model.
        
        Args:
            model_id: The Replicate model ID (e.g., "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb")
            input_data: The input data for the model
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The model output
        """
        # Ensure client is set up
        self.setup()
        
        try:
            # Check if the Replicate API token is set
            if not self.settings.REPLICATE_API_TOKEN:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="REPLICATE_API_TOKEN not set in environment variables"
                )
            
            # Log the input data (excluding sensitive information)
            safe_input = input_data.copy()
            if "voice_sample" in safe_input:
                safe_input["voice_sample"] = "[VOICE_SAMPLE_URL]"  # Don't log the full URL
            logger.info(f"Running Replicate model {model_id} with input: {safe_input}")
            
            # Update progress
            if progress_callback:
                progress_callback(0.0, "Starting model run")
            
            # Run the model in a separate thread to avoid blocking the event loop
            output = await asyncio.to_thread(
                replicate.run,
                model_id,
                input=input_data
            )
            
            # Log information about the output
            output_type = type(output).__name__
            if hasattr(output, "read"):
                logger.info(f"Replicate model returned a file-like object of type: {output_type}")
            elif isinstance(output, str):
                logger.info(f"Replicate model returned a string: {output[:100]}...")
            elif isinstance(output, dict):
                logger.info(f"Replicate model returned a dictionary with keys: {list(output.keys())}")
            else:
                logger.info(f"Replicate model returned an object of type: {output_type}")
            
            # Update progress
            if progress_callback:
                progress_callback(100.0, "Model run complete")
            
            return output
            
        except Exception as e:
            logger.error(f"Error running Replicate model: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Replicate model run failed: {str(e)}"
            )
    
    async def download_output(
        self,
        output: BinaryIO,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        # Ensure client is set up
        self.setup()
        """
        Download the output from a Replicate model run.
        
        Args:
            output: The output from the model run
            output_path: The path to save the output to
            progress_callback: Optional callback function for progress updates
            
        Returns:
            The path to the downloaded file
        """
        try:
            # Update progress
            if progress_callback:
                progress_callback(0.0, "Starting download")
            
            # Download the output in a separate thread to avoid blocking the event loop
            await asyncio.to_thread(
                self._download_file,
                output,
                output_path
            )
            
            # Update progress
            if progress_callback:
                progress_callback(100.0, "Download complete")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading output: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Output download failed: {str(e)}"
            )
    
    def _download_file(self, output: BinaryIO, output_path: str) -> None:
        """
        Download a file from a Replicate model output.
        
        Args:
            output: The output from the model run
            output_path: The path to save the output to
        """
        with open(output_path, "wb") as file:
            file.write(output.read())
    
    async def handle_binary_response(
        self, 
        response: Any, 
        file_type: str,
        filename_prefix: str,
        storage_category: str
    ) -> str:
        """
        Handle a binary response from a Replicate model.
        
        Args:
            response: The response from the model
            file_type: The file type (e.g., "audio", "image")
            filename_prefix: Prefix for the filename
            storage_category: Category for storage (e.g., "audio", "images")
            
        Returns:
            URL of the stored file
        """
        import tempfile
        import os
        import uuid
        from app.ai.utils.storage_adapter import StorageAdapter
        
        # Create a storage adapter
        storage_adapter = StorageAdapter()
        
        # Check if the response is a file-like object
        if hasattr(response, "read"):
            logger.info(f"Handling binary {file_type} response")
            
            # Create a temporary file with the right extension
            ext = ".mp3" if file_type == "audio" else ".jpg"
            temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                # Write the binary data to the temporary file
                with open(temp_path, "wb") as f:
                    f.write(response.read())
                
                # Generate a unique filename
                unique_id = str(uuid.uuid4())
                filename = f"{filename_prefix}_{unique_id}{ext}"
                
                # Upload the file to storage - using consistent method names
                if file_type == "audio":
                    # Using save_audio method
                    with open(temp_path, "rb") as audio_file:
                        local_path = await storage_adapter.save_audio(
                            file_data=audio_file,
                            filename=filename
                        )
                elif file_type == "image":
                    # Using save_image method
                    with open(temp_path, "rb") as image_file:
                        local_path = await storage_adapter.save_image(
                            file_data=image_file,
                            filename=filename
                        )
                else:  # video or other file types
                    # Using save_video method
                    with open(temp_path, "rb") as video_file:
                        local_path = await storage_adapter.save_video(
                            file_data=video_file,
                            filename=filename
                        )
                
                # Log the successful upload
                logger.info(f"Successfully uploaded {file_type} to storage: {local_path}")
                
                # Get the public URL
                return storage_adapter.get_public_url_sync(local_path)
                
            except Exception as e:
                logger.error(f"Error handling binary {file_type} response: {e}")
                raise
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        # If it's not a file-like object, return it as is
        return response
    
    async def text_to_speech(
        self,
        text: str,
        voice_sample_url: Optional[str] = None,
        chunk_length: int = 200,
        prompt_text: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Generate speech using LLASA.
        
        Args:
            text: The text to convert to speech
            voice_sample_url: Optional URL to a voice sample for cloning
            chunk_length: Maximum chunk length for processing long text
            prompt_text: Optional transcript of the text (prevents internal Whisper API call)
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the generated audio
        """
        # LLASA model ID
        tts_model_id = "kjjk10/llasa-3b-long:0494f04972b675631af41c253a45c4341bf637f07eed9a39bad3b1fd66f73a2e"
        
        # Prepare the input for the LLASA model
        input_data = {
            "text": text,
            "chunk_length": chunk_length
        }
        
        # Add return_timestamps=True for long texts (>3000 characters)
        # This is required by the model for longer texts
        if len(text) > 3000:
            logger.info(f"Text length is {len(text)} characters, adding return_timestamps=True")
            input_data["return_timestamps"] = True
        
        # Add prompt_text if provided
        if prompt_text:
            input_data["prompt_text"] = prompt_text
            logger.info(f"Using prompt_text for TTS: {prompt_text[:50]}...")
        
        # Add voice sample if provided
        if voice_sample_url:
            input_data["voice_sample"] = voice_sample_url
        
        # Run the model directly
        result = await self.run_model(
            model_id=tts_model_id,
            input_data=input_data,
            progress_callback=progress_callback
        )
        
        # Handle the result, which could be a string URL, a dictionary, or a binary file-like object
        try:
            # First, try to handle it as a binary response
            if hasattr(result, "read"):
                # It's a file-like object, handle it
                filename_prefix = "tts"
                return await self.handle_binary_response(
                    response=result,
                    file_type="audio",
                    filename_prefix=filename_prefix,
                    storage_category="audio"
                )
            
            # If it's a string, return it directly
            if isinstance(result, str):
                return result
                
            # If it's a dictionary, try to get the output URL
            if isinstance(result, dict) and "output" in result:
                return result["output"]
            
            # If we got here, we couldn't extract a valid URL
            logger.error(f"Unexpected TTS result format: {type(result).__name__}")
            raise ValueError("No audio output returned from the TTS model")
            
        except Exception as e:
            logger.error(f"Error processing TTS result: {e}")
            raise
    
    async def generate_music(
        self,
        prompt: str,
        duration: int = 8,
        model_version: str = "stereo-large",
        output_format: str = "mp3",
        temperature: float = 1.0,
        top_k: int = 250,
        top_p: float = 0.0,
        classifier_free_guidance: float = 3.0,
        continuation: bool = False,
        continuation_start: float = 0.0,
        multi_band_diffusion: bool = False,
        normalization_strategy: str = "peak",
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Generate music from a text prompt using Meta MusicGen.
        
        Args:
            prompt: The text prompt to generate music from
            duration: Duration of the generated audio in seconds (1-30)
            model_version: The model version to use (stereo-small, stereo-medium, stereo-large, melody)
            output_format: The output format (mp3 or wav)
            temperature: Temperature for sampling (0.0-1.0)
            top_k: Top-k sampling (0-500)
            top_p: Top-p sampling (0.0-1.0)
            classifier_free_guidance: Classifier-free guidance scale (1.0-10.0)
            continuation: Whether to continue from a previous generation
            continuation_start: Start time for continuation in seconds
            multi_band_diffusion: Whether to use multi-band diffusion
            normalization_strategy: Normalization strategy (peak, loudness, clip, rms)
            progress_callback: Optional callback for progress updates
            
        Returns:
            The URL of the generated audio
        """
        # Meta MusicGen model ID
        music_model_id = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
        
        # Prepare the input data for the model
        input_data = {
            "prompt": prompt,
            "duration": duration,
            "model_version": model_version,
            "output_format": output_format,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "classifier_free_guidance": classifier_free_guidance,
            "continuation": continuation,
            "continuation_start": continuation_start,
            "multi_band_diffusion": multi_band_diffusion,
            "normalization_strategy": normalization_strategy
        }
        
        # Log the prompt
        logger.info(f"Generating music with prompt: {prompt[:100]}...")
        
        # Run the model
        result = await self.run_model(
            model_id=music_model_id,
            input_data=input_data,
            progress_callback=progress_callback
        )
        
        # Handle the result, which could be a string URL, a dictionary, or a binary file-like object
        try:
            # First, try to handle it as a binary response
            if hasattr(result, "read"):
                # It's a file-like object, handle it
                filename_prefix = f"music_{duration}s"
                return await self.handle_binary_response(
                    response=result,
                    file_type="audio",
                    filename_prefix=filename_prefix,
                    storage_category="music"
                )
            
            # If it's a string, return it directly
            if isinstance(result, str):
                return result
                
            # If it's a dictionary, try to get the output URL
            if isinstance(result, dict) and "output" in result:
                return result["output"]
            
            # If we got here, we couldn't extract a valid URL
            logger.error(f"Unexpected music generation result format: {type(result).__name__}")
            raise ValueError("No audio output returned from the music generation model")
            
        except Exception as e:
            logger.error(f"Error processing music generation result: {e}")
            raise
