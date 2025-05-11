"""
Media file utilities.

This module provides utilities for working with media files.
"""
import os
import logging
import asyncio
import subprocess
import tempfile
from typing import Optional, Dict, Any, List, Tuple, Union

# Set up logging
logger = logging.getLogger(__name__)


async def get_media_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a media file.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Dictionary of media information, or None if it could not be determined
    """
    try:
        # Use ffprobe to get media information
        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffprobe error: {stderr.decode()}")
            return None
        
        # Parse the JSON output
        import json
        return json.loads(stdout.decode())
        
    except Exception as e:
        logger.error(f"Error getting media info: {e}")
        return None


def get_media_type(file_path: str) -> str:
    """
    Determine the type of media file based on extension.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Media type ('audio', 'video', 'image', or 'unknown')
    """
    # Get the file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # Audio extensions
    if ext in ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a']:
        return 'audio'
    
    # Video extensions
    elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']:
        return 'video'
    
    # Image extensions
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
        return 'image'
    
    # Unknown
    else:
        return 'unknown'


async def extract_audio(
    video_path: str,
    output_path: Optional[str] = None,
    start_time: Optional[float] = None,
    duration: Optional[float] = None
) -> str:
    """
    Extract audio from a video file.
    
    Args:
        video_path: Path to the video file
        output_path: Optional path for the output file (if not provided, a temporary file will be created)
        start_time: Optional start time in seconds
        duration: Optional duration in seconds
        
    Returns:
        Path to the extracted audio file
    """
    # Create output path if not provided
    if not output_path:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    try:
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", video_path
        ]
        
        # Add start time if provided
        if start_time is not None:
            command.extend(["-ss", str(start_time)])
        
        # Add duration if provided
        if duration is not None:
            command.extend(["-t", str(duration)])
        
        # Add output options
        command.extend([
            "-vn",  # No video
            "-acodec", "libmp3lame",  # MP3 codec
            "-q:a", "2",  # Quality
            output_path
        ])
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode()}")
            raise RuntimeError(f"Error extracting audio: {stderr.decode()}")
        
        return output_path
        
    except Exception as e:
        # Clean up the temporary file if there was an error
        if not output_path and os.path.exists(output_path):
            os.unlink(output_path)
        
        logger.error(f"Error extracting audio: {e}")
        raise


async def extract_frame(
    video_path: str,
    output_path: Optional[str] = None,
    time_position: float = 0.0
) -> str:
    """
    Extract a frame from a video file.
    
    Args:
        video_path: Path to the video file
        output_path: Optional path for the output file (if not provided, a temporary file will be created)
        time_position: Time position in seconds
        
    Returns:
        Path to the extracted frame
    """
    # Create output path if not provided
    if not output_path:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    try:
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", video_path,
            "-ss", str(time_position),  # Seek to position
            "-frames:v", "1",  # Extract one frame
            "-q:v", "2",  # Quality
            output_path
        ]
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode()}")
            raise RuntimeError(f"Error extracting frame: {stderr.decode()}")
        
        return output_path
        
    except Exception as e:
        # Clean up the temporary file if there was an error
        if not output_path and os.path.exists(output_path):
            os.unlink(output_path)
        
        logger.error(f"Error extracting frame: {e}")
        raise


async def combine_audio_video(
    video_path: str,
    audio_path: str,
    output_path: Optional[str] = None,
    audio_volume: float = 1.0
) -> str:
    """
    Combine a video file with an audio file.
    
    Args:
        video_path: Path to the video file
        audio_path: Path to the audio file
        output_path: Optional path for the output file (if not provided, a temporary file will be created)
        audio_volume: Volume adjustment for the audio (1.0 = normal)
        
    Returns:
        Path to the combined video file
    """
    # Create output path if not provided
    if not output_path:
        # Create a temporary file with the same extension as the video
        _, ext = os.path.splitext(video_path)
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    try:
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", video_path,  # Video input
            "-i", audio_path,  # Audio input
            "-c:v", "copy",  # Copy video codec
            "-filter_complex", f"[1:a]volume={audio_volume}[a]",  # Adjust audio volume
            "-map", "0:v",  # Map video from first input
            "-map", "[a]",  # Map processed audio
            "-shortest",  # End when the shortest input ends
            output_path
        ]
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode()}")
            raise RuntimeError(f"Error combining audio and video: {stderr.decode()}")
        
        return output_path
        
    except Exception as e:
        # Clean up the temporary file if there was an error
        if not output_path and os.path.exists(output_path):
            os.unlink(output_path)
        
        logger.error(f"Error combining audio and video: {e}")
        raise


async def convert_image_to_video(
    image_path: str,
    output_path: Optional[str] = None,
    duration: float = 5.0,
    motion_type: str = "none"
) -> str:
    """
    Convert an image to a video.
    
    Args:
        image_path: Path to the image file
        output_path: Optional path for the output file (if not provided, a temporary file will be created)
        duration: Duration of the video in seconds
        motion_type: Type of motion effect ('none', 'zoom_in', 'zoom_out', 'pan_left', 'pan_right')
        
    Returns:
        Path to the video file
    """
    # Create output path if not provided
    if not output_path:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    try:
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-loop", "1",  # Loop the image
            "-i", image_path,  # Image input
            "-c:v", "libx264",  # Video codec
            "-t", str(duration),  # Duration
            "-pix_fmt", "yuv420p"  # Pixel format
        ]
        
        # Add motion effect if requested
        if motion_type != "none":
            if motion_type == "zoom_in":
                # Zoom in effect
                command.extend([
                    "-vf", f"scale=2*iw:-1,zoompan=z='min(zoom+0.0015,1.5)':d={int(duration*25)}:s=1280x720:fps=25"
                ])
            elif motion_type == "zoom_out":
                # Zoom out effect
                command.extend([
                    "-vf", f"scale=1.5*iw:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={int(duration*25)}:s=1280x720:fps=25"
                ])
            elif motion_type == "pan_left":
                # Pan left effect
                command.extend([
                    "-vf", f"scale=2*iw:-1,zoompan=z=1.2:x='min(iw,max(0,x+1))':d={int(duration*25)}:s=1280x720:fps=25"
                ])
            elif motion_type == "pan_right":
                # Pan right effect
                command.extend([
                    "-vf", f"scale=2*iw:-1,zoompan=z=1.2:x='max(0,min(iw-(iw/zoom),x-1))':d={int(duration*25)}:s=1280x720:fps=25"
                ])
        
        # Add output path
        command.append(output_path)
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode()}")
            raise RuntimeError(f"Error converting image to video: {stderr.decode()}")
        
        return output_path
        
    except Exception as e:
        # Clean up the temporary file if there was an error
        if not output_path and os.path.exists(output_path):
            os.unlink(output_path)
        
        logger.error(f"Error converting image to video: {e}")
        raise
