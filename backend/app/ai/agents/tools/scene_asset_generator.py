"""
Tool for generating assets for a scene with TTS-based duration.
"""
import json
import logging
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from app.ai.models.video_metadata import SceneClip
from app.ai.models.task import ProgressCallback
from app.services.openai import OpenAIService
from app.services.fal_ai import FalAiService
from app.services.replicate import ReplicateService
from app.ai.utils.storage_adapter import StorageAdapter
from app.ai.utils.json_utils import save_json_response

# Set up logging
logger = logging.getLogger(__name__)


class SceneAssetGeneratorTool:
    """Tool for generating assets for a scene with TTS-based duration."""
    
    def __init__(
        self,
        openai_service: Optional[OpenAIService] = None,
        fal_ai_service: Optional[FalAiService] = None,
        replicate_service: Optional[ReplicateService] = None,
        storage_service: Optional[StorageAdapter] = None,
    ):
        """
        Initialize the scene asset generator tool.
        
        Args:
            openai_service: OpenAI service instance (creates a new one if None)
            fal_ai_service: Fal.ai service instance (creates a new one if None)
            replicate_service: Replicate service instance (creates a new one if None)
            storage_service: Storage service instance (creates a new one if None)
        """
        self.openai_service = openai_service or OpenAIService()
        self.fal_ai_service = fal_ai_service or FalAiService()
        self.replicate_service = replicate_service or ReplicateService()
        self.storage_service = storage_service or StorageAdapter()
    
    async def generate_scene_assets(
        self,
        scene: SceneClip,
        style: str,
        character_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        voice_character_url: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        Generate all assets for a scene in the correct order.
        
        Args:
            scene: Scene clip data
            style: Style of the video
            character_profiles: Character profiles for consistency (optional)
            voice_character_url: URL to a voice sample for TTS
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping asset types to their URLs
        """
        if progress_callback:
            await progress_callback(10, f"Generating assets for scene {scene.index}: {scene.title}")
        
        # Step 1: Generate the narration audio first
        if progress_callback:
            await progress_callback(20, "Generating narration audio")
        
        audio_url = await self._generate_narration_audio(scene.script, voice_character_url)
        
        # Step 2: Get the audio duration
        audio_duration = await self._get_audio_duration(audio_url)
        logger.info(f"Audio duration for scene {scene.index}: {audio_duration} seconds")
        
        # Step 3: Generate the scene image
        if progress_callback:
            await progress_callback(40, "Generating scene image")
        
        image_url = await self._generate_scene_image(scene, style, character_profiles)
        
        # Check if the image URL is a placeholder (indicating failure)
        is_placeholder = image_url == self.storage_service.get_placeholder_image_url()
        
        # Step 4: Generate the scene video with the audio duration (only if image generation succeeded)
        video_url = None
        if not is_placeholder:
            if progress_callback:
                await progress_callback(60, "Generating scene video")
            
            video_url = await self._generate_scene_video(image_url, scene, style, audio_duration)
        else:
            logger.warning(f"Skipping video generation for scene {scene.index} due to failed image generation")
            if progress_callback:
                await progress_callback(60, "Skipping video generation due to failed image generation")
            
            # Use placeholder video URL
            video_url = self.storage_service.get_placeholder_video_url()
        
        if progress_callback:
            await progress_callback(100, "Scene assets complete")
        
        # Return the asset URLs and metadata
        return {
            "voice_character_url": voice_character_url,
            "scene": {
                "index": scene.index,
                "title": scene.title,
                "script": scene.script,
                "video_prompt": scene.video_prompt,
                "duration": audio_duration,
                "transition": scene.transition
            },
            "image_url": image_url,
            "audio_url": audio_url,
            "video_url": video_url
        }
    
    async def _generate_scene_image(
        self,
        scene: SceneClip,
        style: str,
        character_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate an image for a scene.
        
        Args:
            scene: Scene clip data
            style: Style of the video
            character_profiles: Character profiles for consistency (optional)
            
        Returns:
            URL of the generated image
        """
        # Create the image prompt
        image_prompt = self._create_image_prompt(scene, style, character_profiles)
        
        # Check if we need to use a reference image for character consistency
        reference_image_path = None
        
        # Only use character consistency when a specific character is the main focus
        # Check if any character name is explicitly mentioned in the prompt
        if character_profiles and scene.video_prompt:
            character_mentioned = False
            main_character = None
            
            # Find if any character is explicitly mentioned in the prompt
            for character_name, character_data in character_profiles.items():
                if character_name.lower() in scene.video_prompt.lower():
                    character_mentioned = True
                    main_character = character_name
                    
                    # Get the file path from the URL if this character has an image
                    if "images" in character_data and "combined" in character_data["images"]:
                        reference_image_path = self.storage_service.get_local_path(character_data["images"]["combined"])
                        if reference_image_path:
                            logger.info(f"Using reference image for character consistency: {character_name}")
                            break
                        else:
                            # Try to convert remote URL to base64 for reference
                            try:
                                import aiohttp
                                import base64
                                import tempfile
                                
                                image_url = character_data["images"]["combined"]
                                logger.info(f"Attempting to download remote image for {character_name}")
                                
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(image_url) as response:
                                        if response.status == 200:
                                            # Create a temporary file
                                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                                                temp_file.write(await response.read())
                                                reference_image_path = temp_file.name
                                                logger.info(f"Successfully downloaded reference image to {reference_image_path}")
                                                break
                            except Exception as e:
                                logger.warning(f"Failed to download reference image for {character_name}: {e}")
                                logger.warning(f"Reference image for {character_name} is a remote URL and cannot be used directly")
        
        # Generate the image
        try:
            # Create a request object instead of passing prompt directly
            from app.services.openai.service import ImageGenerationRequest, ImageGenerationResponse
            
            # Log the image generation prompt
            logger.info(f"Generating scene image with prompt: {image_prompt[:100]}...")
            
            if reference_image_path:
                # Generate with reference in 16:9 aspect ratio
                logger.info(f"Using reference image: {reference_image_path}")
                image_url = await self.openai_service.generate_image_with_reference(
                    prompt=image_prompt,
                    reference_image_path=reference_image_path,
                    size="1792x1024",  # 16:9 aspect ratio
                    style="vivid" if style.lower() in ["realistic", "cinematic"] else "natural",
                    quality="hd",  # Use high quality setting
                )
            else:
                # Generate without reference in 16:9 aspect ratio
                logger.info("Generating image without reference")
                request = ImageGenerationRequest(
                    prompt=image_prompt,
                    size="1792x1024",  # 16:9 aspect ratio
                    style="vivid" if style.lower() in ["realistic", "cinematic"] else "natural",
                    quality="hd",  # Use high quality setting
                )
                response = await self.openai_service.generate_image(
                    request=request,
                )
                
                # Extract the image URL from the response
                if isinstance(response, ImageGenerationResponse):
                    if not response.images:
                        raise ValueError("No images returned from image generation")
                    image_url = response.images[0]
                else:
                    # If it's already a string URL, use it directly
                    image_url = response
            
            # Download and store the image
            scene_id = scene.index
            filename = f"scene_{scene_id}.png"
            local_path = await self.storage_service.download_and_store_image(image_url, filename, "scenes")
            
            # Return the public URL using the synchronous version to avoid coroutine objects
            return self.storage_service.get_public_url_sync(local_path)
        
        except Exception as e:
            logger.error(f"Error generating scene image for scene {scene.index}: {e}")
            # Return a placeholder image URL
            return self.storage_service.get_placeholder_image_url()
    
    async def _generate_narration_audio(
        self,
        script: str,
        voice_character_url: Optional[str] = None,
    ) -> str:
        """
        Generate narration audio for a scene.
        
        Args:
            script: Narration script
            voice_character_url: URL to a voice sample for TTS
            
        Returns:
            URL of the generated audio
        """
        try:
            # Use the provided voice character URL or default
            voice_id = voice_character_url or "male-1"
            
            # Generate the audio using Replicate's llasa-3b-long model
            # For the default voice sample, use its known transcript
            prompt_text = None
            if voice_id == "https://replicate.delivery/pbxt/MNaHFqDkZ0Y22hvppxotJazhRYe6TwhK78xAUTCoz3NB9bRV/voice_sample.wav":
                prompt_text = "You open your eyes so that only a slender chink of light seeps in, and peer at the gingko trees in front of the Provincial Office. As though there, between those branches, the wind is about to take on visible form."
            
            # Log the narration generation
            logger.info(f"Generating narration audio with script: {script[:100]}...")
            
            audio_url = await self.replicate_service.text_to_speech(
                text=script,
                voice_sample_url=voice_id,
                chunk_length=200,  # Default chunk length
                prompt_text=prompt_text,  # Use the transcript of the reference audio
            )
            
            # Log the successful generation
            logger.info(f"Successfully generated narration audio: {audio_url}")
            
            # The audio is already saved to our storage by the replicate_service
            # so we can just return the URL
            return audio_url
        
        except Exception as e:
            logger.error(f"Error generating narration audio: {e}")
            # Return a placeholder audio URL
            return self.storage_service.get_placeholder_audio_url()
    
    async def _get_audio_duration(self, audio_url: str) -> float:
        """
        Get the duration of an audio file.
        
        Args:
            audio_url: URL of the audio file
            
        Returns:
            Duration of the audio in seconds
        """
        # Get the file path from the URL
        audio_path = self.storage_service.get_local_path(audio_url)
        
        # If audio_path is None (remote URL), we can't get the duration directly
        if audio_path is None:
            logger.warning(f"Cannot get duration for remote audio URL: {audio_url}")
            # Default to 5 seconds for remote URLs
            return 5.0
        
        # Use ffprobe to get the duration
        try:
            # Run ffprobe to get the duration
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            
            return duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            # Default to 5 seconds if we can't get the duration
            return 5.0
    
    async def _generate_scene_video(
        self,
        image_url: str,
        scene: SceneClip,
        style: str,
        duration: float,
    ) -> str:
        """
        Generate a video for a scene from an image.
        
        Args:
            image_url: URL of the scene image
            scene: Scene clip data
            style: Style of the video
            duration: Duration of the video in seconds
            
        Returns:
            URL of the generated video
        """
        try:
            # Create the video prompt
            video_prompt = scene.video_prompt
            
            # Convert duration to string (Fal.ai expects "5" or "10")
            # Round up to the nearest supported duration
            if duration <= 5:
                duration_str = "5"
            else:
                duration_str = "10"
            
            # Get the local path of the image
            image_path = self.storage_service.get_local_path(image_url)
            
            # If image_path is None (remote URL), we can't generate a video directly
            if image_path is None:
                logger.warning(f"Cannot generate video for remote image URL: {image_url}")
                # Download the image first
                try:
                    import tempfile
                    import os
                    import aiohttp
                    
                    # Create a temporary file with the right extension
                    ext = os.path.splitext(image_url)[1]
                    if not ext:
                        # Default to .jpg if no extension is found
                        ext = ".jpg"
                    
                    # Create a temporary file
                    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                    temp_path = temp_file.name
                    temp_file.close()
                    
                    # Download the image
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as response:
                            if response.status == 200:
                                with open(temp_path, "wb") as f:
                                    f.write(await response.read())
                                image_path = temp_path
                            else:
                                raise ValueError(f"Failed to download image: {response.status}")
                except Exception as e:
                    logger.error(f"Error downloading image for video generation: {e}")
                    raise
            
            # Log the video generation
            logger.info(f"Generating scene video with prompt: {video_prompt[:100]}...")
            logger.info(f"Using image: {image_path}, duration: {duration_str}s, aspect ratio: 16:9")
            
            # Generate the video
            video_url = await self.fal_ai_service.image_to_video(
                image_path=image_path,
                prompt=video_prompt,
                duration=duration_str,
                aspect_ratio="16:9",
            )
            
            # Log the successful generation
            logger.info(f"Successfully generated scene video: {video_url}")
            
            # Download and store the video
            scene_id = scene.index
            filename = f"scene_{scene_id}.mp4"
            local_path = await self.storage_service.download_and_store_video(video_url, filename, "scenes")
            
            # Return the public URL using the synchronous version to avoid coroutine objects
            return self.storage_service.get_public_url_sync(local_path)
        
        except Exception as e:
            logger.error(f"Error generating scene video for scene {scene.index}: {e}")
            # Return a placeholder video URL
            return self.storage_service.get_placeholder_video_url()
    
    def _create_image_prompt(
        self,
        scene: SceneClip,
        style: str,
        character_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        """
        Create a prompt for generating a scene image.
        
        Args:
            scene: Scene clip data
            style: Style of the video
            character_profiles: Character profiles for consistency (optional)
            
        Returns:
            Image generation prompt
        """
        # Start with the scene video prompt
        prompt = scene.video_prompt
        
        # Add style information
        prompt += f" {style} style."
        
        # Add character descriptions if available
        if character_profiles:
            for character_name, character_data in character_profiles.items():
                if character_name.lower() in prompt.lower():
                    # Add a brief character description
                    if "image_prompt" in character_data:
                        # Extract key details from the image prompt
                        image_prompt = character_data["image_prompt"]
                        # Extract a brief description (after "4 angles:" if present)
                        if "4 angles:" in image_prompt:
                            description = image_prompt.split("4 angles:")[1].strip()
                            prompt += f" {character_name}: {description}."
        
        # Add quality boosters
        prompt += " Highly detailed, professional quality, cinematic lighting."
        
        return prompt
    
    async def regenerate_scene_image(
        self,
        scene: SceneClip,
        style: str,
        character_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Regenerate an image for a scene with a different prompt or style.
        
        Args:
            scene: Scene clip data
            style: Style of the video
            character_profiles: Character profiles for consistency (optional)
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the regenerated image
        """
        if progress_callback:
            await progress_callback(10, f"Regenerating image for scene {scene.index}")
        
        # Generate a new image
        image_url = await self._generate_scene_image(scene, style, character_profiles)
        
        if progress_callback:
            await progress_callback(100, f"Scene image regenerated for scene {scene.index}")
        
        return image_url
