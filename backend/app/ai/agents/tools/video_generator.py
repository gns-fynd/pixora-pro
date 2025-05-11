"""
Video generator tool for the video agent.

This module provides tools for converting images to videos and combining videos with audio.
"""
import logging
import time
import os
from typing import Dict, Any, Optional, List, Union

from fastapi import Depends

from app.services.fal_ai.base import FalAIService
from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
from app.ai.utils.storage_adapter import StorageAdapter


# Set up logging
logger = logging.getLogger(__name__)


class VideoGeneratorTool:
    """
    Tool for generating videos from images and combining videos with audio.
    """
    
    def __init__(
        self,
        fal_ai_service: FalAIService = Depends(),
        storage_adapter: HierarchicalStorageAdapter = Depends()
    ):
        """
        Initialize the video generator tool.
        
        Args:
            fal_ai_service: The Fal.ai service for image-to-video conversion
            storage_adapter: The storage adapter for saving videos
        """
        self.fal_ai_service = fal_ai_service
        self.storage_adapter = storage_adapter
    
    async def image_to_video(
        self,
        task_id: str,
        scene_index: int,
        image_url: str,
        duration: float,
        motion_type: str = "gentle_pan",
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Convert a static image to a video with motion.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            image_url: The URL of the image to convert
            duration: The duration of the video in seconds
            motion_type: The type of motion to apply
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with video information
        """
        try:
            # Log the request
            logger.info(f"Converting image to video for scene {scene_index} with motion: {motion_type}")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Converting image to video for scene {scene_index}")
            
            # Convert the image to video
            video_url = await self.fal_ai_service.image_to_video(
                image_url=image_url,
                motion_type=motion_type,
                duration=duration
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(50, f"Video generated, saving to storage")
            
            # Download and save the video to storage
            stored_url = await self.storage_adapter.save_scene_video(
                task_id=task_id,
                scene_index=scene_index,
                file_data=await self._download_video(video_url),
                filename=f"scene_{scene_index}_video.mp4"
            )
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Video saved to storage")
            
            # Return the result
            return {
                "status": "success",
                "video_url": stored_url,
                "image_url": image_url,
                "duration": duration,
                "motion_type": motion_type
            }
            
        except Exception as e:
            logger.error(f"Error converting image to video for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def combine_video_audio(
        self,
        task_id: str,
        scene_index: int,
        video_url: str,
        audio_url: str,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Combine video and audio for a scene.
        
        Args:
            task_id: The task ID
            scene_index: The scene index
            video_url: The URL of the video
            audio_url: The URL of the audio
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with combined video information
        """
        try:
            # Log the request
            logger.info(f"Combining video and audio for scene {scene_index}")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Combining video and audio for scene {scene_index}")
            
            # Create a temporary directory for processing
            temp_dir = await self.storage_adapter.create_temp_directory()
            
            try:
                # Download the video and audio
                video_path = os.path.join(temp_dir, f"scene_{scene_index}_video.mp4")
                audio_path = os.path.join(temp_dir, f"scene_{scene_index}_audio.mp3")
                output_path = os.path.join(temp_dir, f"scene_{scene_index}_combined.mp4")
                
                # Download the files
                with open(video_path, "wb") as f:
                    f.write(await self._download_video(video_url))
                
                with open(audio_path, "wb") as f:
                    f.write(await self._download_audio(audio_url))
                
                # Update progress
                if progress_callback:
                    await progress_callback(30, f"Files downloaded, combining video and audio")
                
                # Combine the video and audio using FFmpeg
                import subprocess
                
                # Use FFmpeg to combine the video and audio
                command = [
                    "ffmpeg",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    output_path
                ]
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {stderr.decode()}")
                    raise Exception(f"FFmpeg error: {stderr.decode()}")
                
                # Update progress
                if progress_callback:
                    await progress_callback(70, f"Video and audio combined, saving to storage")
                
                # Save the combined video to storage
                with open(output_path, "rb") as f:
                    stored_url = await self.storage_adapter.save_scene_video(
                        task_id=task_id,
                        scene_index=scene_index,
                        file_data=f,
                        filename=f"scene_{scene_index}_combined.mp4"
                    )
                
                # Update progress
                if progress_callback:
                    await progress_callback(100, f"Combined video saved to storage")
                
                # Return the result
                return {
                    "status": "success",
                    "video_url": stored_url,
                    "original_video_url": video_url,
                    "audio_url": audio_url
                }
                
            finally:
                # Clean up the temporary directory
                await self.storage_adapter.cleanup_temp_directory(temp_dir)
            
        except Exception as e:
            logger.error(f"Error combining video and audio for scene {scene_index}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def compose_final_video(
        self,
        task_id: str,
        scene_videos: List[str],
        background_music_url: Optional[str] = None,
        transitions: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Compose the final video from all components.
        
        Args:
            task_id: The task ID
            scene_videos: List of URLs to scene videos
            background_music_url: Optional URL to background music
            transitions: Optional list of transitions between scenes
            user_id: Optional user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with final video information
        """
        try:
            # Log the request
            logger.info(f"Composing final video with {len(scene_videos)} scenes")
            
            # Update progress
            if progress_callback:
                await progress_callback(10, f"Composing final video")
            
            # Create a temporary directory for processing
            temp_dir = await self.storage_adapter.create_temp_directory()
            
            try:
                # Download all scene videos
                video_paths = []
                for i, video_url in enumerate(scene_videos):
                    video_path = os.path.join(temp_dir, f"scene_{i}.mp4")
                    with open(video_path, "wb") as f:
                        f.write(await self._download_video(video_url))
                    video_paths.append(video_path)
                
                # Download background music if provided
                music_path = None
                if background_music_url:
                    music_path = os.path.join(temp_dir, "background_music.mp3")
                    with open(music_path, "wb") as f:
                        f.write(await self._download_audio(background_music_url))
                
                # Update progress
                if progress_callback:
                    await progress_callback(30, f"Files downloaded, composing final video")
                
                # Create a file list for FFmpeg
                file_list_path = os.path.join(temp_dir, "file_list.txt")
                with open(file_list_path, "w") as f:
                    for video_path in video_paths:
                        f.write(f"file '{video_path}'\n")
                
                # Output path for the final video
                output_path = os.path.join(temp_dir, "final_video.mp4")
                
                # Combine the videos using FFmpeg
                import subprocess
                
                # Use FFmpeg to concatenate the videos
                concat_command = [
                    "ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", file_list_path,
                    "-c", "copy",
                    output_path
                ]
                
                process = subprocess.Popen(
                    concat_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {stderr.decode()}")
                    raise Exception(f"FFmpeg error: {stderr.decode()}")
                
                # If background music is provided, add it to the video
                final_output_path = output_path
                if music_path:
                    # Update progress
                    if progress_callback:
                        await progress_callback(60, f"Adding background music")
                    
                    # Output path for the video with music
                    final_output_path = os.path.join(temp_dir, "final_video_with_music.mp4")
                    
                    # Use FFmpeg to add background music
                    music_command = [
                        "ffmpeg",
                        "-i", output_path,
                        "-i", music_path,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-map", "0:v:0",
                        "-map", "1:a:0",
                        "-shortest",
                        final_output_path
                    ]
                    
                    process = subprocess.Popen(
                        music_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        logger.error(f"FFmpeg error: {stderr.decode()}")
                        raise Exception(f"FFmpeg error: {stderr.decode()}")
                
                # Update progress
                if progress_callback:
                    await progress_callback(80, f"Final video composed, saving to storage")
                
                # Save the final video to storage
                with open(final_output_path, "rb") as f:
                    stored_url = await self.storage_adapter.save_final_video(
                        task_id=task_id,
                        file_data=f,
                        filename="final_video.mp4"
                    )
                
                # Update progress
                if progress_callback:
                    await progress_callback(100, f"Final video saved to storage")
                
                # Return the result
                return {
                    "status": "success",
                    "video_url": stored_url,
                    "scene_count": len(scene_videos),
                    "has_background_music": background_music_url is not None
                }
                
            finally:
                # Clean up the temporary directory
                await self.storage_adapter.cleanup_temp_directory(temp_dir)
            
        except Exception as e:
            logger.error(f"Error composing final video: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _download_video(self, url: str) -> bytes:
        """
        Download a video from a URL.
        
        Args:
            url: The video URL
            
        Returns:
            The video data as bytes
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    
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
async def image_to_video_tool(
    ctx,
    scene_index: int,
    image_url: str,
    duration: float,
    motion_type: str = "gentle_pan"
) -> Dict[str, Any]:
    """
    Convert a static image to video with motion.
    
    Args:
        scene_index: The index of the scene
        image_url: The URL of the image to convert
        duration: Duration of the video in seconds
        motion_type: The type of motion to apply (gentle_pan, zoom_in, zoom_out, etc.)
        
    Returns:
        Dictionary with video information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the video generator tool
    from app.services.fal_ai.base import FalAIService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    fal_ai_service = FalAIService()
    storage_adapter = HierarchicalStorageAdapter()
    
    video_generator = VideoGeneratorTool(
        fal_ai_service=fal_ai_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="image_to_video",
            progress=progress,
            message=message
        )
    
    # Convert the image to video
    result = await video_generator.image_to_video(
        task_id=task_id,
        scene_index=scene_index,
        image_url=image_url,
        duration=duration,
        motion_type=motion_type,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    scene_key = f"scene_{scene_index}"
    scenes = ctx.context.get("scenes", {})
    
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    scenes[scene_key]["video"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result


# Function tool for OpenAI Assistants API
async def combine_video_audio_tool(
    ctx,
    scene_index: int,
    video_url: str,
    audio_url: str
) -> Dict[str, Any]:
    """
    Combine video and audio for a scene.
    
    Args:
        scene_index: The index of the scene
        video_url: The URL of the video
        audio_url: The URL of the audio
        
    Returns:
        Dictionary with combined video information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the video generator tool
    from app.services.fal_ai.base import FalAIService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    fal_ai_service = FalAIService()
    storage_adapter = HierarchicalStorageAdapter()
    
    video_generator = VideoGeneratorTool(
        fal_ai_service=fal_ai_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="combine_video_audio",
            progress=progress,
            message=message
        )
    
    # Combine the video and audio
    result = await video_generator.combine_video_audio(
        task_id=task_id,
        scene_index=scene_index,
        video_url=video_url,
        audio_url=audio_url,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    scene_key = f"scene_{scene_index}"
    scenes = ctx.context.get("scenes", {})
    
    if scene_key not in scenes:
        scenes[scene_key] = {}
    
    scenes[scene_key]["combined_video"] = result
    ctx.context.set("scenes", scenes)
    
    # Return the result
    return result


# Function tool for OpenAI Assistants API
async def compose_final_video_tool(
    ctx,
    scene_videos: List[str],
    background_music_url: Optional[str] = None,
    transitions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Compose the final video from all components.
    
    Args:
        scene_videos: List of URLs to scene videos
        background_music_url: Optional URL to background music
        transitions: Optional list of transitions between scenes
        
    Returns:
        Dictionary with final video information
    """
    # Get the task context
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # Create the video generator tool
    from app.services.fal_ai.base import FalAIService
    from app.ai.utils.hierarchical_storage_adapter import HierarchicalStorageAdapter
    
    fal_ai_service = FalAIService()
    storage_adapter = HierarchicalStorageAdapter()
    
    video_generator = VideoGeneratorTool(
        fal_ai_service=fal_ai_service,
        storage_adapter=storage_adapter
    )
    
    # Define a progress callback
    async def progress_callback(progress: float, message: str):
        # Update progress in the context
        ctx.context.set_progress(
            stage="compose_final_video",
            progress=progress,
            message=message
        )
    
    # Compose the final video
    result = await video_generator.compose_final_video(
        task_id=task_id,
        scene_videos=scene_videos,
        background_music_url=background_music_url,
        transitions=transitions,
        user_id=user_id,
        progress_callback=progress_callback
    )
    
    # Store the result in the context
    ctx.context.set("final_video", result)
    
    # Return the result
    return result
