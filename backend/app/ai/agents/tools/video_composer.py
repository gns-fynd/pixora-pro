"""
Tool for composing the final video from scene assets.
"""
import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple

import moviepy.editor as mp
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, concatenate_audioclips

from app.ai.models.request import SceneData
from app.ai.models.task import ProgressCallback
from app.services.storage.base import StorageService

# Set up logging
logger = logging.getLogger(__name__)


class VideoComposerTool:
    """Tool for composing the final video from scene assets."""
    
    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
    ):
        """
        Initialize the video composer tool.
        
        Args:
            storage_service: Storage service instance (creates a new one if None)
        """
        # Use StorageAdapter instead of StorageService
        from app.ai.utils.storage_adapter import StorageAdapter
        self.storage_adapter = StorageAdapter()
    
    async def compose_video(
        self,
        scene_assets: List[Dict[str, Any]],
        music_urls: List[str],
        transitions: List[Dict[str, Any]],
        task_id: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Compose the final video from scene assets.
        
        Args:
            scene_assets: List of scene asset dictionaries (each with 'video_url' and 'audio_url')
            music_urls: List of background music URLs
            transitions: List of transition specifications
            task_id: ID of the task
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the final video
        """
        if progress_callback:
            await progress_callback(10, "Starting video composition")
        
        # Create a temporary directory for processing
        temp_dir = await self.storage_adapter.create_temp_directory()
        
        try:
            # Process scene videos
            if progress_callback:
                await progress_callback(20, "Processing scene videos")
            
            video_clips = []
            
            for i, assets in enumerate(scene_assets):
                # Get the video and audio paths
                video_path = self.storage_adapter.get_local_path(assets["video_url"])
                audio_path = self.storage_adapter.get_local_path(assets["audio_url"])
                
                # Check if paths are None (remote URLs)
                if video_path is None:
                    logger.warning(f"Video path is None for scene {i}, downloading from URL: {assets['video_url']}")
                    # Download the video to a temporary file
                    import tempfile
                    import aiohttp
                    
                    # Create a temporary file
                    temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    temp_video_path = temp_video.name
                    temp_video.close()
                    
                    # Download the video
                    async with aiohttp.ClientSession() as session:
                        async with session.get(assets["video_url"]) as response:
                            if response.status == 200:
                                with open(temp_video_path, "wb") as f:
                                    f.write(await response.read())
                                video_path = temp_video_path
                            else:
                                logger.error(f"Failed to download video: {response.status}")
                                continue  # Skip this scene
                
                if audio_path is None:
                    logger.warning(f"Audio path is None for scene {i}, downloading from URL: {assets['audio_url']}")
                    # Download the audio to a temporary file
                    import tempfile
                    import aiohttp
                    
                    # Create a temporary file
                    temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    temp_audio_path = temp_audio.name
                    temp_audio.close()
                    
                    # Download the audio
                    async with aiohttp.ClientSession() as session:
                        async with session.get(assets["audio_url"]) as response:
                            if response.status == 200:
                                with open(temp_audio_path, "wb") as f:
                                    f.write(await response.read())
                                audio_path = temp_audio_path
                            else:
                                logger.error(f"Failed to download audio: {response.status}")
                                continue  # Skip this scene
                
                # Load the video and audio clips
                try:
                    video_clip = VideoFileClip(video_path)
                    audio_clip = AudioFileClip(audio_path)
                except Exception as e:
                    logger.error(f"Error loading video or audio clip: {e}")
                    continue  # Skip this scene
                
                # Set the audio for the video clip
                video_clip = video_clip.set_audio(audio_clip)
                
                # Apply transition if specified and not the first clip
                if i > 0 and i - 1 < len(transitions):
                    transition = transitions[i - 1]
                    # Handle both string and dictionary transitions
                    if isinstance(transition, str):
                        transition_type = transition
                        transition_duration = 1.0
                    else:
                        transition_type = transition.get("type", "fade")
                        transition_duration = transition.get("duration", 1.0)
                    
                    # Apply the transition
                    if transition_type == "fade":
                        video_clip = video_clip.fadein(transition_duration)
                    elif transition_type == "dissolve":
                        # For dissolve, we'll handle it during concatenation
                        pass
                    # Add more transition types as needed
                
                video_clips.append(video_clip)
                
                if progress_callback:
                    progress = 20 + int((i / len(scene_assets)) * 30)
                    await progress_callback(progress, f"Processed scene {i+1}/{len(scene_assets)}")
            
            # Concatenate video clips
            if progress_callback:
                await progress_callback(50, "Concatenating video clips")
            
            # Check if we have any valid video clips
            if not video_clips:
                logger.error("No valid video clips to concatenate")
                # Return a placeholder video URL
                return self.storage_adapter.get_placeholder_video_url()
            
            final_video = concatenate_videoclips(video_clips, method="compose")
            
            # Process background music
            if progress_callback:
                await progress_callback(60, "Processing background music")
            
            music_clips = []
            
            for i, music_url in enumerate(music_urls):
                music_path = self.storage_adapter.get_local_path(music_url)
                
                # Check if path is None (remote URL)
                if music_path is None:
                    logger.warning(f"Music path is None for music {i}, downloading from URL: {music_url}")
                    # Download the music to a temporary file
                    import tempfile
                    import aiohttp
                    
                    # Create a temporary file
                    temp_music = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    temp_music_path = temp_music.name
                    temp_music.close()
                    
                    # Download the music
                    async with aiohttp.ClientSession() as session:
                        async with session.get(music_url) as response:
                            if response.status == 200:
                                with open(temp_music_path, "wb") as f:
                                    f.write(await response.read())
                                music_path = temp_music_path
                            else:
                                logger.error(f"Failed to download music: {response.status}")
                                continue  # Skip this music
                
                try:
                    music_clip = AudioFileClip(music_path)
                except Exception as e:
                    logger.error(f"Error loading music clip: {e}")
                    continue  # Skip this music
                
                # Adjust volume to be background music
                music_clip = music_clip.volumex(0.3)
                
                music_clips.append(music_clip)
                
                if progress_callback:
                    progress = 60 + int((i / len(music_urls)) * 10)
                    await progress_callback(progress, f"Processed music {i+1}/{len(music_urls)}")
            
            # Combine music clips if there are multiple
            if len(music_clips) > 1:
                # Calculate durations for each music clip
                total_video_duration = final_video.duration
                music_durations = []
                
                if len(music_clips) == 2:
                    # Split the video in half
                    music_durations = [total_video_duration / 2, total_video_duration / 2]
                elif len(music_clips) == 3:
                    # Split the video in thirds
                    third = total_video_duration / 3
                    music_durations = [third, third, third]
                else:
                    # Default to equal distribution
                    segment_duration = total_video_duration / len(music_clips)
                    music_durations = [segment_duration] * len(music_clips)
                
                # Adjust music clips to the calculated durations
                for i, (clip, duration) in enumerate(zip(music_clips, music_durations)):
                    if clip.duration > duration:
                        music_clips[i] = clip.subclip(0, duration)
                    elif clip.duration < duration:
                        # Loop the clip to reach the desired duration
                        repeats = int(duration / clip.duration) + 1
                        extended_clip = clip
                        for _ in range(repeats - 1):
                            extended_clip = concatenate_audioclips([extended_clip, clip])
                        music_clips[i] = extended_clip.subclip(0, duration)
                
                # Set start times for each music clip
                start_times = [sum(music_durations[:i]) for i in range(len(music_clips))]
                
                # Create composite audio with music clips at their start times
                music_composite = CompositeAudioClip([
                    clip.set_start(start_time)
                    for clip, start_time in zip(music_clips, start_times)
                ])
                
                # Mix with the video's audio
                final_audio = CompositeAudioClip([final_video.audio, music_composite])
                final_video = final_video.set_audio(final_audio)
            elif len(music_clips) == 1:
                # If there's only one music clip, loop it to match the video duration
                music_clip = music_clips[0]
                
                if music_clip.duration < final_video.duration:
                    # Loop the music to match the video duration
                    repeats = int(final_video.duration / music_clip.duration) + 1
                    extended_music = music_clip
                    for _ in range(repeats - 1):
                        extended_music = concatenate_audioclips([extended_music, music_clip])
                    music_clip = extended_music.subclip(0, final_video.duration)
                else:
                    # Trim the music to match the video duration
                    music_clip = music_clip.subclip(0, final_video.duration)
                
                # Mix with the video's audio
                final_audio = CompositeAudioClip([final_video.audio, music_clip])
                final_video = final_video.set_audio(final_audio)
            
            # Write the final video to a file
            if progress_callback:
                await progress_callback(80, "Writing final video")
            
            output_filename = f"{task_id}.mp4"
            output_path = os.path.join(temp_dir, output_filename)
            
            final_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=os.path.join(temp_dir, "temp_audio.m4a"),
                remove_temp=True,
                fps=24,
            )
            
            # Save the final video to storage
            if progress_callback:
                await progress_callback(90, "Saving final video")
            
            # Store the final video
            with open(output_path, "rb") as f:
                final_video_path = await self.storage_adapter.save_video(
                    file_data=f,
                    filename=output_filename
                )
            
            if progress_callback:
                await progress_callback(100, "Video composition complete")
            
            # Return the URL of the final video
            return self.storage_adapter.get_public_url_sync(final_video_path)
        
        except Exception as e:
            logger.error(f"Error composing video: {e}")
            # Return a placeholder video URL
            return self.storage_adapter.get_placeholder_video_url()
        
        finally:
            # Clean up
            await self.storage_adapter.cleanup_temp_directory(temp_dir)
    
    async def edit_scene(
        self,
        scene_index: int,
        scene_assets: List[Dict[str, Any]],
        new_scene_assets: Dict[str, Any],
        music_urls: List[str],
        transitions: List[Dict[str, Any]],
        task_id: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Edit a scene in an existing video.
        
        Args:
            scene_index: Index of the scene to edit (0-based)
            scene_assets: List of all scene asset dictionaries
            new_scene_assets: New assets for the scene to edit
            music_urls: List of background music URLs
            transitions: List of transition specifications
            task_id: ID of the task
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the updated video
        """
        if progress_callback:
            await progress_callback(10, f"Editing scene {scene_index + 1}")
        
        # Update the scene assets
        updated_scene_assets = scene_assets.copy()
        updated_scene_assets[scene_index] = new_scene_assets
        
        # Compose the video with the updated scene
        return await self.compose_video(
            scene_assets=updated_scene_assets,
            music_urls=music_urls,
            transitions=transitions,
            task_id=f"{task_id}_edited",
            progress_callback=progress_callback,
        )
    
    async def extract_scene(
        self,
        scene_index: int,
        scene_assets: List[Dict[str, Any]],
        task_id: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Extract a single scene as a standalone video.
        
        Args:
            scene_index: Index of the scene to extract (0-based)
            scene_assets: List of all scene asset dictionaries
            task_id: ID of the task
            progress_callback: Optional callback for progress updates
            
        Returns:
            URL of the extracted scene video
        """
        if progress_callback:
            await progress_callback(10, f"Extracting scene {scene_index + 1}")
        
        # Get the scene assets
        if scene_index < 0 or scene_index >= len(scene_assets):
            logger.error(f"Scene index {scene_index} out of range")
            return self.storage_adapter.get_placeholder_video_url()
        
        scene_asset = scene_assets[scene_index]
        
        # Return the scene video URL directly
        if "video_url" in scene_asset:
            return scene_asset["video_url"]
        
        # If no video URL, return a placeholder
        return self.storage_adapter.get_placeholder_video_url()
