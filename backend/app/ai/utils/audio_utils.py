"""
Audio utilities for the Pixora AI application.

This module provides utilities for audio processing.
"""
import os
import subprocess
import tempfile
import logging
from typing import Optional, List, Tuple, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)


def get_audio_duration(audio_path: str) -> Optional[float]:
    """
    Get the duration of an audio file in seconds.

    Args:
        audio_path: Path to the audio file

    Returns:
        Duration in seconds, or None if the duration couldn't be determined
    """
    try:
        # Use ffprobe to get the duration
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting audio duration for {audio_path}: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error getting audio duration for {audio_path}: {str(e)}")
        return None


def normalize_audio(audio_path: str, output_path: str, target_level: float = -18.0) -> bool:
    """
    Normalize audio volume to a target level.

    Args:
        audio_path: Path to the input audio file
        output_path: Path to save the normalized audio
        target_level: Target loudness level in dB LUFS (default: -18.0)

    Returns:
        True if normalization was successful, False otherwise
    """
    try:
        # Use ffmpeg to normalize the audio
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", audio_path,
            "-af", f"loudnorm=I={target_level}:LRA=7:TP=-1.5",
            "-ar", "44100",  # Set sample rate to 44.1 kHz
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error normalizing audio {audio_path}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error normalizing audio {audio_path}: {str(e)}")
        return False


def combine_audio_tracks(audio_paths: List[str], output_path: str) -> bool:
    """
    Combine multiple audio tracks into a single file.

    Args:
        audio_paths: List of paths to audio files
        output_path: Path to save the combined audio

    Returns:
        True if combination was successful, False otherwise
    """
    try:
        if not audio_paths:
            logger.error("No audio paths provided")
            return False
        
        if len(audio_paths) == 1:
            # If there's only one audio file, just copy it
            cmd = [
                "ffmpeg",
                "-y",
                "-i", audio_paths[0],
                "-c", "copy",
                output_path
            ]
        else:
            # Create a filter complex to concatenate the audio files
            inputs = []
            for i, path in enumerate(audio_paths):
                inputs.extend(["-i", path])
            
            filter_complex = ";".join([f"[{i}:0]" for i in range(len(audio_paths))]) + \
                             f"concat=n={len(audio_paths)}:v=0:a=1[out]"
            
            cmd = [
                "ffmpeg",
                "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                output_path
            ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error combining audio tracks: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error combining audio tracks: {str(e)}")
        return False


def add_background_music(
    voice_path: str,
    music_path: str,
    output_path: str,
    voice_level: float = 1.0,
    music_level: float = 0.3
) -> bool:
    """
    Mix voice and background music.

    Args:
        voice_path: Path to the voice audio file
        music_path: Path to the music audio file
        output_path: Path to save the mixed audio
        voice_level: Volume level for the voice (default: 1.0)
        music_level: Volume level for the music (default: 0.3)

    Returns:
        True if mixing was successful, False otherwise
    """
    try:
        # Get the duration of the voice audio
        voice_duration = get_audio_duration(voice_path)
        if voice_duration is None:
            logger.error(f"Could not determine voice duration for {voice_path}")
            return False
        
        # Create a temporary file for the trimmed music
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_music_path = temp_file.name
        
        try:
            # Trim or loop the music to match the voice duration
            cmd = [
                "ffmpeg",
                "-y",
                "-i", music_path,
                "-t", str(voice_duration),
                "-af", "afade=t=out:st=" + str(max(0, voice_duration - 3)) + ":d=3",  # Fade out at the end
                temp_music_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Mix the voice and music
            cmd = [
                "ffmpeg",
                "-y",
                "-i", voice_path,
                "-i", temp_music_path,
                "-filter_complex", f"[0:a]volume={voice_level}[voice];[1:a]volume={music_level}[music];[voice][music]amix=inputs=2:duration=first",
                "-ar", "44100",  # Set sample rate to 44.1 kHz
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            return True
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_music_path):
                os.remove(temp_music_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error adding background music: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error adding background music: {str(e)}")
        return False


def extract_audio_from_video(video_path: str, output_path: str) -> bool:
    """
    Extract audio from a video file.

    Args:
        video_path: Path to the video file
        output_path: Path to save the extracted audio

    Returns:
        True if extraction was successful, False otherwise
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-q:a", "2",  # High quality
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting audio from video {video_path}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error extracting audio from video {video_path}: {str(e)}")
        return False


def convert_audio_format(input_path: str, output_path: str, format: str = "mp3") -> bool:
    """
    Convert audio to a different format.

    Args:
        input_path: Path to the input audio file
        output_path: Path to save the converted audio
        format: Output format (default: "mp3")

    Returns:
        True if conversion was successful, False otherwise
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting audio format for {input_path}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error converting audio format for {input_path}: {str(e)}")
        return False


def get_audio_properties(audio_path: str) -> Optional[Dict[str, Any]]:
    """
    Get properties of an audio file.

    Args:
        audio_path: Path to the audio file

    Returns:
        Dictionary with audio properties, or None if properties couldn't be determined
    """
    try:
        # Use ffprobe to get audio properties
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_name,channels,sample_rate:format=duration,bit_rate",
            "-of", "json",
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)
        
        # Extract relevant properties
        properties = {}
        
        # Get stream properties
        if "streams" in data and data["streams"]:
            stream = data["streams"][0]
            properties["codec"] = stream.get("codec_name")
            properties["channels"] = int(stream.get("channels", 0))
            properties["sample_rate"] = int(stream.get("sample_rate", 0))
        
        # Get format properties
        if "format" in data:
            format_info = data["format"]
            properties["duration"] = float(format_info.get("duration", 0))
            if "bit_rate" in format_info:
                properties["bit_rate"] = int(format_info.get("bit_rate", 0))
        
        return properties
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting audio properties for {audio_path}: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error getting audio properties for {audio_path}: {str(e)}")
        return None
