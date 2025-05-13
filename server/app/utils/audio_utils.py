"""
Audio utilities for Pixora AI Video Creation Platform
"""
import os
import uuid
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import tempfile
import logging
import requests

# Configure logging
logger = logging.getLogger(__name__)

def get_audio_duration(audio_path: str) -> Optional[float]:
    """
    Get the duration of an audio file.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Optional[float]: The duration in seconds, or None if it could not be determined
    """
    try:
        # Get the duration of the audio file using ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.stdout.strip():
            duration = float(result.stdout.strip())
            logger.debug(f"Audio duration: {duration} seconds")
            return duration
        else:
            logger.warning(f"Could not determine audio duration for {audio_path}")
            return None
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return None

def get_audio_duration_from_content(audio_content: bytes) -> Optional[float]:
    """
    Get the duration of an audio file from its content.
    
    Args:
        audio_content: Content of the audio file
        
    Returns:
        Optional[float]: The duration in seconds, or None if it could not be determined
    """
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_path = audio_file.name
            audio_file.write(audio_content)
        
        # Get the duration of the audio file
        duration = get_audio_duration(audio_path)
        
        # Clean up the temporary file
        os.remove(audio_path)
        
        return duration
    except Exception as e:
        logger.error(f"Error getting audio duration from content: {str(e)}")
        return None

def normalize_audio_duration(audio_content: bytes, target_duration: float) -> Tuple[bytes, float]:
    """
    Normalize audio duration to match the target duration.
    
    Args:
        audio_content: The audio content as bytes
        target_duration: The target duration in seconds
        
    Returns:
        Tuple[bytes, float]: The normalized audio content and its actual duration
    """
    try:
        # Create a unique ID for the audio file
        audio_id = str(uuid.uuid4())
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_content)
        
        output_path = input_path + ".normalized.mp3"
        
        # Get the current duration of the audio file
        current_duration = get_audio_duration(input_path)
        
        if current_duration is None:
            logger.warning("Could not determine audio duration, returning original audio")
            return audio_content, target_duration
        
        logger.info(f"Normalizing audio duration from {current_duration} to {target_duration} seconds")
        
        # Calculate the speed factor
        speed_factor = current_duration / target_duration
        
        # Use FFmpeg to adjust the audio speed
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path, 
            "-filter:a", f"atempo={speed_factor}", 
            "-vn", output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the normalized audio content
        with open(output_path, "rb") as f:
            normalized_audio = f.read()
        
        # Get the actual duration of the normalized audio
        actual_duration = get_audio_duration(output_path)
        
        # Clean up temporary files
        os.remove(input_path)
        os.remove(output_path)
        
        return normalized_audio, actual_duration or target_duration
    except Exception as e:
        logger.error(f"Error normalizing audio duration: {str(e)}")
        return audio_content, target_duration

def mix_audio(voice_over: bytes, background_music: bytes, voice_level: float = 1.0, music_level: float = 0.3) -> bytes:
    """
    Mix voice-over and background music.
    
    Args:
        voice_over: The voice-over audio content as bytes
        background_music: The background music audio content as bytes
        voice_level: The volume level for the voice-over (0.0-1.0)
        music_level: The volume level for the background music (0.0-1.0)
        
    Returns:
        bytes: The mixed audio content
    """
    try:
        # Create unique IDs for the audio files
        voice_id = str(uuid.uuid4())
        music_id = str(uuid.uuid4())
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as voice_file:
            voice_path = voice_file.name
            voice_file.write(voice_over)
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as music_file:
            music_path = music_file.name
            music_file.write(background_music)
        
        output_path = voice_path + ".mixed.mp3"
        
        # Get the duration of the voice-over
        voice_duration = get_audio_duration(voice_path)
        
        if voice_duration is None:
            logger.warning("Could not determine voice-over duration, returning original voice-over")
            return voice_over
        
        logger.info(f"Mixing voice-over ({voice_duration} seconds) with background music")
        
        # Use FFmpeg to mix the audio files
        subprocess.run([
            "ffmpeg", "-y", 
            "-i", voice_path, 
            "-i", music_path, 
            "-filter_complex", f"[0:a]volume={voice_level}[a];[1:a]volume={music_level}[b];[a][b]amix=inputs=2:duration=first[out]", 
            "-map", "[out]", 
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the mixed audio content
        with open(output_path, "rb") as f:
            mixed_audio = f.read()
        
        # Clean up temporary files
        os.remove(voice_path)
        os.remove(music_path)
        os.remove(output_path)
        
        return mixed_audio
    except Exception as e:
        logger.error(f"Error mixing audio: {str(e)}")
        return voice_over

def download_audio(audio_url: str) -> Optional[bytes]:
    """
    Download audio from a URL.
    
    Args:
        audio_url: URL of the audio file
        
    Returns:
        Optional[bytes]: The audio content, or None if it could not be downloaded
    """
    try:
        # Download the audio from the URL
        response = requests.get(audio_url)
        
        if response.status_code != 200:
            logger.error(f"Failed to download audio: HTTP {response.status_code}")
            return None
        
        return response.content
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return None

def generate_silence(duration: float) -> bytes:
    """
    Generate a silent audio file of the specified duration.
    
    Args:
        duration: Duration of the silence in seconds
        
    Returns:
        bytes: The silent audio content
    """
    try:
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as output_file:
            output_path = output_file.name
        
        # Use FFmpeg to generate silence
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the silent audio content
        with open(output_path, "rb") as f:
            silent_audio = f.read()
        
        # Clean up the temporary file
        os.remove(output_path)
        
        return silent_audio
    except Exception as e:
        logger.error(f"Error generating silence: {str(e)}")
        # Return a simple MP3 header as a fallback
        return b"\xff\xfb\x90\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

def trim_audio(audio_content: bytes, start_time: float, end_time: float) -> bytes:
    """
    Trim an audio file to the specified start and end times.
    
    Args:
        audio_content: The audio content as bytes
        start_time: Start time in seconds
        end_time: End time in seconds
        
    Returns:
        bytes: The trimmed audio content
    """
    try:
        # Create a temporary file for the input
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_content)
        
        # Create a temporary file for the output
        output_path = input_path + ".trimmed.mp3"
        
        # Calculate the duration
        duration = end_time - start_time
        
        # Use FFmpeg to trim the audio
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:a", "copy",
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the trimmed audio content
        with open(output_path, "rb") as f:
            trimmed_audio = f.read()
        
        # Clean up temporary files
        os.remove(input_path)
        os.remove(output_path)
        
        return trimmed_audio
    except Exception as e:
        logger.error(f"Error trimming audio: {str(e)}")
        return audio_content

def concatenate_audio(audio_files: List[bytes]) -> bytes:
    """
    Concatenate multiple audio files.
    
    Args:
        audio_files: List of audio content as bytes
        
    Returns:
        bytes: The concatenated audio content
    """
    try:
        # Create a temporary directory for the input files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a list file for FFmpeg
            list_file_path = os.path.join(temp_dir, "list.txt")
            
            # Write each audio file to the temporary directory
            file_paths = []
            for i, audio_content in enumerate(audio_files):
                file_path = os.path.join(temp_dir, f"audio_{i}.mp3")
                with open(file_path, "wb") as f:
                    f.write(audio_content)
                file_paths.append(file_path)
                
                # Add the file to the list file
                with open(list_file_path, "a") as f:
                    f.write(f"file '{file_path}'\n")
            
            # Create a temporary file for the output
            output_path = os.path.join(temp_dir, "output.mp3")
            
            # Use FFmpeg to concatenate the audio files
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Read the concatenated audio content
            with open(output_path, "rb") as f:
                concatenated_audio = f.read()
            
            return concatenated_audio
        finally:
            # Clean up the temporary directory
            import shutil
            shutil.rmtree(temp_dir)
    except Exception as e:
        logger.error(f"Error concatenating audio: {str(e)}")
        # Return the first audio file as a fallback
        return audio_files[0] if audio_files else b""
