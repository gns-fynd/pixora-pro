"""
Video generation tools for the Pixora AI application.

This module provides tools for creating videos from images and audio,
applying transitions, and stitching videos together.
"""
import os
import logging
import asyncio
import tempfile
import subprocess
from typing import List, Dict, Any, Optional, Tuple, Union

from app.models import Scene, TransitionType
from app.services.fal_ai import FalAiService
from app.services.storage import StorageService
from app.ai.utils import (
    save_file, ensure_directory_exists, generate_unique_filename,
    get_audio_duration, normalize_audio, add_background_music
)

# Set up logging
logger = logging.getLogger(__name__)


async def create_scene_video_with_motion(
    scene_image_path: str,
    audio_path: str,
    output_path: str,
    motion_type: str = "pan",
    fal_ai_service: FalAiService = None,
) -> str:
    """
    Create a video with motion from a still image and audio.

    Args:
        scene_image_path: Path to the scene image
        audio_path: Path to the audio file
        output_path: Path to save the output video
        motion_type: Type of motion to apply (pan, zoom, etc.)
        fal_ai_service: The FAL AI service

    Returns:
        Path to the generated video
    """
    if not fal_ai_service:
        raise ValueError("FAL AI service is required for video generation with motion")
    
    try:
        # Get the duration of the audio
        audio_duration = get_audio_duration(audio_path)
        if audio_duration is None:
            logger.warning("Could not determine audio duration, using default of 10 seconds")
            audio_duration = 10.0
        
        # Generate the video with motion using Kling 1.6 model via Fal.ai
        logger.info(f"Generating video with {motion_type} motion for image: {scene_image_path}")
        
        # Create a temporary file for the video without audio
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_video_path = temp_file.name
        
        try:
            # Generate the video with motion
            video_data = await fal_ai_service.generate_video_with_motion(
                image_path=scene_image_path,
                duration=audio_duration,
                motion_type=motion_type
            )
            
            if not video_data:
                logger.error(f"Failed to generate video with motion for image: {scene_image_path}")
                raise ValueError(f"Failed to generate video with motion")
            
            # Save the video to the temporary file
            with open(temp_video_path, "wb") as f:
                f.write(video_data)
            
            # Add the audio to the video
            cmd = [
                "ffmpeg",
                "-y",
                "-i", temp_video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            logger.info(f"Generated video with motion for image: {scene_image_path}")
            
            return output_path
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in ffmpeg command: {e.stderr}")
        raise ValueError(f"Error adding audio to video: {e.stderr}")
    except Exception as e:
        logger.error(f"Error creating video with motion: {str(e)}")
        raise


async def normalize_duration(
    video_path: str,
    target_duration: float,
    output_path: str,
) -> str:
    """
    Adjust the duration of a video to match a target duration.

    Args:
        video_path: Path to the input video
        target_duration: Target duration in seconds
        output_path: Path to save the output video

    Returns:
        Path to the normalized video
    """
    try:
        # Get the current duration of the video
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        current_duration = float(result.stdout.strip())
        
        # Calculate the speed factor
        speed_factor = current_duration / target_duration
        
        # Adjust the video speed
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-filter_complex", f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]",
            "-map", "[v]",
            "-map", "[a]",
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        logger.info(f"Normalized video duration from {current_duration:.2f}s to {target_duration:.2f}s")
        
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in ffmpeg command: {e.stderr}")
        raise ValueError(f"Error normalizing video duration: {e.stderr}")
    except Exception as e:
        logger.error(f"Error normalizing video duration: {str(e)}")
        raise


async def apply_transition(
    video1_path: str,
    video2_path: str,
    transition_type: TransitionType,
    output_path: str,
    transition_duration: float = 1.0,
) -> str:
    """
    Apply a transition between two videos.

    Args:
        video1_path: Path to the first video
        video2_path: Path to the second video
        transition_type: Type of transition to apply
        output_path: Path to save the output video
        transition_duration: Duration of the transition in seconds

    Returns:
        Path to the video with transition
    """
    try:
        # Get the duration of the first video
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video1_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video1_duration = float(result.stdout.strip())
        
        # Create a filter complex based on the transition type
        filter_complex = ""
        
        if transition_type == TransitionType.FADE:
            # Crossfade transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=fade:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.SLIDE_LEFT:
            # Slide left transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=slideleft:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.SLIDE_RIGHT:
            # Slide right transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=slideright:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.ZOOM_IN:
            # Zoom in transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=zoomin:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.ZOOM_OUT:
            # Zoom out transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=zoomout:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.FADE_TO_BLACK:
            # Fade to black transition
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS,fade=t=out:st=0:d={transition_duration}[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS,fade=t=in:st=0:d={transition_duration}[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1start][v1end][v2start][v2end]concat=n=4:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS,afade=t=out:st=0:d={transition_duration}[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={transition_duration}[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1start][a1end][a2start][a2end]concat=n=4:v=0:a=1[outa]"
            )
        elif transition_type == TransitionType.CROSSFADE:
            # Crossfade transition (similar to fade but with different parameters)
            filter_complex = (
                f"[0:v]trim=0:{video1_duration-transition_duration},setpts=PTS-STARTPTS[v1start];"
                f"[0:v]trim={video1_duration-transition_duration}:{video1_duration},setpts=PTS-STARTPTS[v1end];"
                f"[1:v]trim=0:{transition_duration},setpts=PTS-STARTPTS[v2start];"
                f"[1:v]trim={transition_duration},setpts=PTS-STARTPTS[v2end];"
                f"[v1end][v2start]xfade=transition=dissolve:duration={transition_duration}:offset=0[xfade];"
                f"[v1start][xfade][v2end]concat=n=3:v=1:a=0[outv];"
                f"[0:a]atrim=0:{video1_duration-transition_duration},asetpts=PTS-STARTPTS[a1start];"
                f"[0:a]atrim={video1_duration-transition_duration}:{video1_duration},asetpts=PTS-STARTPTS[a1end];"
                f"[1:a]atrim=0:{transition_duration},asetpts=PTS-STARTPTS[a2start];"
                f"[1:a]atrim={transition_duration},asetpts=PTS-STARTPTS[a2end];"
                f"[a1end][a2start]acrossfade=d={transition_duration}[xfadea];"
                f"[a1start][xfadea][a2end]concat=n=3:v=0:a=1[outa]"
            )
        else:
            # Default to a simple concatenation
            filter_complex = (
                f"[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]"
            )
        
        # Apply the transition
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:v", "5M",
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        logger.info(f"Applied {transition_type} transition between videos")
        
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in ffmpeg command: {e.stderr}")
        raise ValueError(f"Error applying transition: {e.stderr}")
    except Exception as e:
        logger.error(f"Error applying transition: {str(e)}")
        raise


async def stitch_video(
    video_paths: List[str],
    transition_types: List[TransitionType],
    output_path: str,
    background_music_path: Optional[str] = None,
    music_level: float = 0.3,
) -> str:
    """
    Stitch multiple videos together with transitions.

    Args:
        video_paths: List of paths to videos
        transition_types: List of transition types to apply between videos
        output_path: Path to save the output video
        background_music_path: Optional path to background music
        music_level: Volume level for the background music

    Returns:
        Path to the stitched video
    """
    try:
        if not video_paths:
            raise ValueError("No video paths provided")
        
        if len(video_paths) == 1:
            # If there's only one video, just copy it
            if background_music_path:
                # Add background music
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
                    temp_audio_path = temp_audio_file.name
                
                try:
                    # Extract audio from the video
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-i", video_paths[0],
                        "-vn",
                        "-acodec", "copy",
                        temp_audio_path
                    ]
                    
                    subprocess.run(cmd, capture_output=True, check=True)
                    
                    # Add background music to the audio
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mixed_audio_file:
                        temp_mixed_audio_path = temp_mixed_audio_file.name
                    
                    try:
                        add_background_music(
                            voice_path=temp_audio_path,
                            music_path=background_music_path,
                            output_path=temp_mixed_audio_path,
                            music_level=music_level
                        )
                        
                        # Replace the audio in the video
                        cmd = [
                            "ffmpeg",
                            "-y",
                            "-i", video_paths[0],
                            "-i", temp_mixed_audio_path,
                            "-c:v", "copy",
                            "-c:a", "aac",
                            "-map", "0:v",
                            "-map", "1:a",
                            output_path
                        ]
                        
                        subprocess.run(cmd, capture_output=True, check=True)
                    finally:
                        # Clean up the temporary file
                        if os.path.exists(temp_mixed_audio_path):
                            os.remove(temp_mixed_audio_path)
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
            else:
                # Just copy the video
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", video_paths[0],
                    "-c", "copy",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
            
            return output_path
        
        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Apply transitions between videos
            current_video_path = video_paths[0]
            
            for i in range(1, len(video_paths)):
                # Get the transition type
                transition_type = transition_types[i - 1] if i - 1 < len(transition_types) else TransitionType.FADE
                
                # Create a temporary file for the output
                temp_output_path = os.path.join(temp_dir, f"temp_output_{i}.mp4")
                
                # Apply the transition
                await apply_transition(
                    video1_path=current_video_path,
                    video2_path=video_paths[i],
                    transition_type=transition_type,
                    output_path=temp_output_path
                )
                
                # Update the current video path
                current_video_path = temp_output_path
            
            # Add background music if provided
            if background_music_path:
                # Extract audio from the video
                temp_audio_path = os.path.join(temp_dir, "temp_audio.mp3")
                
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", current_video_path,
                    "-vn",
                    "-acodec", "copy",
                    temp_audio_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
                
                # Add background music to the audio
                temp_mixed_audio_path = os.path.join(temp_dir, "temp_mixed_audio.mp3")
                
                add_background_music(
                    voice_path=temp_audio_path,
                    music_path=background_music_path,
                    output_path=temp_mixed_audio_path,
                    music_level=music_level
                )
                
                # Replace the audio in the video
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", current_video_path,
                    "-i", temp_mixed_audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-map", "0:v",
                    "-map", "1:a",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
            else:
                # Just copy the final video
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", current_video_path,
                    "-c", "copy",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
        
        logger.info(f"Stitched {len(video_paths)} videos together")
        
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in ffmpeg command: {e.stderr}")
        raise ValueError(f"Error stitching videos: {e.stderr}")
    except Exception as e:
        logger.error(f"Error stitching videos: {str(e)}")
        raise


async def create_video_for_scene(
    scene: Scene,
    scene_image_url: str,
    voice_over_url: str,
    output_path: str,
    motion_type: str = "pan",
    fal_ai_service: FalAiService = None,
    storage_service: StorageService = None,
) -> str:
    """
    Create a video for a scene.

    Args:
        scene: The scene
        scene_image_url: URL to the scene image
        voice_over_url: URL to the voice over audio
        output_path: Path to save the output video
        motion_type: Type of motion to apply
        fal_ai_service: The FAL AI service
        storage_service: The storage service

    Returns:
        Path to the generated video
    """
    try:
        # Download the scene image and voice over
        scene_image_data = await storage_service.get_file(scene_image_url)
        voice_over_data = await storage_service.get_file(voice_over_url)
        
        if not scene_image_data or not voice_over_data:
            raise ValueError("Failed to download scene image or voice over")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image_file:
            temp_image_path = temp_image_file.name
            temp_image_file.write(scene_image_data)
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
            temp_audio_file.write(voice_over_data)
        
        try:
            # Create the video with motion
            await create_scene_video_with_motion(
                scene_image_path=temp_image_path,
                audio_path=temp_audio_path,
                output_path=output_path,
                motion_type=motion_type,
                fal_ai_service=fal_ai_service
            )
            
            return output_path
        finally:
            # Clean up temporary files
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
    except Exception as e:
        logger.error(f"Error creating video for scene: {str(e)}")
        raise
