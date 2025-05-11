"""
Common utilities for duration adjustment.

This module provides shared utilities used by multiple duration adjusters.
"""
import os
import logging
import asyncio
import subprocess
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)


async def get_duration(file_path: str) -> Optional[float]:
    """
    Get the duration of a media file.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Duration in seconds, or None if it could not be determined
    """
    try:
        # Use ffprobe to get the duration
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
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
        
        # Parse the duration
        duration_str = stdout.decode().strip()
        return float(duration_str)
        
    except Exception as e:
        logger.error(f"Error getting duration: {e}")
        return None


async def copy_file(input_path: str, output_path: str) -> None:
    """
    Copy a file.
    
    Args:
        input_path: Path to the input file
        output_path: Path to the output file
    """
    # Use ffmpeg to copy the file (this ensures compatibility)
    command = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-i", input_path,
        "-c", "copy",
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        logger.error(f"ffmpeg error: {stderr.decode()}")
        raise RuntimeError(f"Error copying file: {stderr.decode()}")


async def execute_ffmpeg_command(command: list) -> tuple:
    """
    Execute an ffmpeg command and return stdout and stderr.
    
    Args:
        command: The ffmpeg command as a list of strings
        
    Returns:
        Tuple of (stdout, stderr) as bytes
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        logger.error(f"ffmpeg error: {stderr.decode()}")
        raise RuntimeError(f"Error executing ffmpeg command: {stderr.decode()}")
    
    return stdout, stderr


def calculate_fade_durations(
    total_duration: float,
    fade_in: bool = False,
    fade_out: bool = True
) -> tuple:
    """
    Calculate appropriate fade durations based on total media duration.
    
    Args:
        total_duration: Total duration of the media in seconds
        fade_in: Whether to add a fade-in effect
        fade_out: Whether to add a fade-out effect
        
    Returns:
        Tuple of (fade_in_duration, fade_out_duration) in seconds
    """
    # Calculate fade durations (max 1 second, or 1/4 of total duration)
    max_fade_duration = min(1.0, total_duration / 4)
    
    fade_in_duration = max_fade_duration if fade_in else 0.0
    fade_out_duration = max_fade_duration if fade_out else 0.0
    
    return fade_in_duration, fade_out_duration
