"""
Video utilities for Pixora AI Video Creation Platform
"""
import os
import uuid
import subprocess
import tempfile
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import shutil
import logging
import requests

# Import audio utilities
from .audio_utils import get_audio_duration, get_audio_duration_from_content

# Configure logging
logger = logging.getLogger(__name__)

def get_video_duration(video_path: str) -> Optional[float]:
    """
    Get the duration of a video file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Optional[float]: The duration in seconds, or None if it could not be determined
    """
    try:
        # Get the duration of the video file using ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.stdout.strip():
            duration = float(result.stdout.strip())
            logger.debug(f"Video duration: {duration} seconds")
            return duration
        else:
            logger.warning(f"Could not determine video duration for {video_path}")
            return None
    except Exception as e:
        logger.error(f"Error getting video duration: {str(e)}")
        return None

def get_video_duration_from_content(video_content: bytes) -> Optional[float]:
    """
    Get the duration of a video file from its content.
    
    Args:
        video_content: Content of the video file
        
    Returns:
        Optional[float]: The duration in seconds, or None if it could not be determined
    """
    try:
        # Create a temporary file for the video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_path = video_file.name
            video_file.write(video_content)
        
        # Get the duration of the video file
        duration = get_video_duration(video_path)
        
        # Clean up the temporary file
        os.remove(video_path)
        
        return duration
    except Exception as e:
        logger.error(f"Error getting video duration from content: {str(e)}")
        return None

def create_static_image_video(image_content: bytes, audio_content: bytes, duration: float) -> bytes:
    """
    Create a video from a static image and audio.
    
    Args:
        image_content: Content of the image
        audio_content: Content of the audio
        duration: Duration of the video in seconds
        
    Returns:
        bytes: Content of the created video
    """
    try:
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file, \
             tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file, \
             tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as output_file:
            
            image_path = image_file.name
            audio_path = audio_file.name
            output_path = output_file.name
            
            # Write the image and audio to the temporary files
            image_file.write(image_content)
            audio_file.write(audio_content)
            
            # Get the actual duration of the audio file
            actual_duration = get_audio_duration(audio_path)
            
            # Use the actual duration if available, otherwise use the provided duration
            video_duration = actual_duration if actual_duration is not None else duration
            
            logger.info(f"Creating static image video with duration: {video_duration} seconds")
            
            # Use FFmpeg to create the video
            subprocess.run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Read the video content
            with open(output_path, "rb") as f:
                video_content = f.read()
            
            # Clean up temporary files
            os.remove(image_path)
            os.remove(audio_path)
            os.remove(output_path)
            
            return video_content
    except Exception as e:
        logger.error(f"Error creating static image video: {str(e)}")
        raise

def normalize_video_duration(video_content: bytes, target_duration: float) -> bytes:
    """
    Adjust a video's duration to match the target duration.
    
    Args:
        video_content: Content of the video
        target_duration: Target duration in seconds
        
    Returns:
        bytes: Content of the normalized video
    """
    try:
        # Create a temporary file for the input video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(video_content)
        
        # Get the original duration of the video
        original_duration = get_video_duration(input_path)
        
        if original_duration is None:
            logger.warning("Could not determine original video duration, returning original video")
            return video_content
        
        # Calculate the speed factor
        speed_factor = original_duration / target_duration
        
        # Create a temporary file for the output
        output_path = input_path + ".normalized.mp4"
        
        logger.info(f"Normalizing video duration from {original_duration} to {target_duration} seconds")
        
        # Use FFmpeg to adjust the video duration
        if 0.95 <= speed_factor <= 1.05:
            # If speed_factor is close to 1, just copy the video
            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_path,
                "-c", "copy",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # Use setpts for video and atempo for audio
            atempo_filter = f"atempo={1/speed_factor}"
            # For extreme speed changes, chain multiple atempo filters
            if speed_factor > 2.0:
                atempo_filter = f"atempo=2.0,atempo={1/speed_factor/2.0}"
            elif speed_factor < 0.5:
                atempo_filter = f"atempo=0.5,atempo={1/speed_factor/0.5}"
            
            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_path,
                "-filter_complex", f"[0:v]setpts={speed_factor}*PTS[v];[0:a]{atempo_filter}[a]",
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the normalized video content
        with open(output_path, "rb") as f:
            normalized_video = f.read()
        
        # Clean up temporary files
        os.remove(input_path)
        os.remove(output_path)
        
        return normalized_video
    except Exception as e:
        logger.error(f"Error normalizing video duration: {str(e)}")
        return video_content

def apply_transition(video1_content: bytes, video2_content: bytes, transition_type: str) -> bytes:
    """
    Apply a transition effect between two videos.
    
    Args:
        video1_content: Content of the first video
        video2_content: Content of the second video
        transition_type: Type of transition (fade, slide_left, slide_right, etc.)
        
    Returns:
        bytes: Content of the video with transition
    """
    try:
        # Create temporary files for the input videos
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video1_file, \
             tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video2_file:
            
            video1_path = video1_file.name
            video2_path = video2_file.name
            
            # Write the videos to the temporary files
            video1_file.write(video1_content)
            video2_file.write(video2_content)
            
            # Get the duration of the first video
            video1_duration = get_video_duration(video1_path)
            
            if video1_duration is None:
                logger.warning("Could not determine first video duration, using default transition")
                video1_duration = 5.0
            
            # Create a temporary file for the output
            output_path = video1_path + ".transition.mp4"
            
            logger.info(f"Applying {transition_type} transition between videos")
            
            # Different transition types use different FFmpeg filters
            transition_filters = {
                "fade": f"[0:v]format=yuva420p,fade=t=out:st={video1_duration-1}:d=1:alpha=1[v0]; [1:v]format=yuva420p,fade=t=in:st=0:d=1:alpha=1[v1]; [v0][v1]overlay",
                "slide_left": f"[0:v][1:v]xfade=transition=slideright:duration=1:offset={video1_duration-1}",
                "slide_right": f"[0:v][1:v]xfade=transition=slideleft:duration=1:offset={video1_duration-1}",
                "zoom_in": f"[0:v][1:v]xfade=transition=zoomin:duration=1:offset={video1_duration-1}",
                "zoom_out": f"[0:v][1:v]xfade=transition=zoomout:duration=1:offset={video1_duration-1}",
                "fade_to_black": f"[0:v]fade=t=out:st={video1_duration-1}:d=1:color=black[v0]; [1:v]fade=t=in:st=0:d=1:color=black[v1]; [v0][v1]concat=n=2:v=1:a=0",
                "crossfade": f"[0:v][1:v]xfade=transition=fade:duration=1:offset={video1_duration-1}",
            }
            
            # Get the appropriate filter for the transition type
            filter_complex = transition_filters.get(transition_type, transition_filters["fade"])
            
            # Apply the transition
            subprocess.run([
                "ffmpeg", "-y",
                "-i", video1_path,
                "-i", video2_path,
                "-filter_complex", filter_complex,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Read the video content
            with open(output_path, "rb") as f:
                output_video = f.read()
            
            # Clean up temporary files
            os.remove(video1_path)
            os.remove(video2_path)
            os.remove(output_path)
            
            return output_video
    except Exception as e:
        logger.error(f"Error applying transition: {str(e)}")
        # Return the first video as a fallback
        return video1_content

def stitch_videos(video_contents: List[bytes], transitions: List[str], music_content: Optional[bytes] = None) -> bytes:
    """
    Stitch multiple videos with transitions and optional background music.
    
    Args:
        video_contents: List of video contents
        transitions: List of transition types
        music_content: Optional background music content
        
    Returns:
        bytes: Content of the stitched video
    """
    try:
        # Create a temporary directory for working files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Write all videos to temporary files
            video_paths = []
            for i, video_content in enumerate(video_contents):
                video_path = os.path.join(temp_dir, f"video_{i}.mp4")
                with open(video_path, "wb") as f:
                    f.write(video_content)
                video_paths.append(video_path)
            
            # Create a concat file for FFmpeg
            concat_file_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file_path, "w") as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Create a temporary file for the output
            output_path = os.path.join(temp_dir, "output.mp4")
            
            logger.info(f"Stitching {len(video_contents)} videos")
            
            # Use FFmpeg to concatenate the videos
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file_path,
                "-c", "copy",
                output_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # If music is provided, add it to the video
            if music_content:
                # Write the music to a temporary file
                music_path = os.path.join(temp_dir, "music.mp3")
                with open(music_path, "wb") as f:
                    f.write(music_content)
                
                # Create a temporary file for the output with music
                output_with_music_path = os.path.join(temp_dir, "output_with_music.mp4")
                
                logger.info("Adding background music to stitched video")
                
                # Use FFmpeg to add background music
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", output_path,
                    "-i", music_path,
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]",
                    "-map", "0:v",
                    "-map", "[a]",
                    "-c:v", "copy",
                    output_with_music_path
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Update the output path
                output_path = output_with_music_path
            
            # Read the final video content
            with open(output_path, "rb") as f:
                stitched_video = f.read()
            
            return stitched_video
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
    except Exception as e:
        logger.error(f"Error stitching videos: {str(e)}")
        # Return the first video as a fallback
        return video_contents[0] if video_contents else b""

def download_video(video_url: str) -> Optional[bytes]:
    """
    Download a video from a URL.
    
    Args:
        video_url: URL of the video
        
    Returns:
        Optional[bytes]: Content of the video, or None if it could not be downloaded
    """
    try:
        # Download the video from the URL
        response = requests.get(video_url)
        
        if response.status_code != 200:
            logger.error(f"Failed to download video: HTTP {response.status_code}")
            return None
        
        return response.content
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return None

def extract_frame(video_content: bytes, time_position: float) -> Optional[bytes]:
    """
    Extract a frame from a video at the specified time position.
    
    Args:
        video_content: Content of the video
        time_position: Time position in seconds
        
    Returns:
        Optional[bytes]: Content of the extracted frame, or None if it could not be extracted
    """
    try:
        # Create a temporary file for the input video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(video_content)
        
        # Create a temporary file for the output frame
        output_path = input_path + ".frame.png"
        
        logger.info(f"Extracting frame at {time_position} seconds")
        
        # Use FFmpeg to extract the frame
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-ss", str(time_position),
            "-vframes", "1",
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the frame content
        with open(output_path, "rb") as f:
            frame_content = f.read()
        
        # Clean up temporary files
        os.remove(input_path)
        os.remove(output_path)
        
        return frame_content
    except Exception as e:
        logger.error(f"Error extracting frame: {str(e)}")
        return None

def create_scene_video_with_motion(scene_image_content: bytes, audio_content: bytes, prompt: str, duration: float) -> bytes:
    """
    Create a video for a scene by first generating a motion video from the image,
    then combining it with audio.
    
    Args:
        scene_image_content: Content of the scene image
        audio_content: Content of the audio
        prompt: Text description to guide the video generation
        duration: Duration of the video in seconds
        
    Returns:
        bytes: Content of the created video
    """
    try:
        # Import fal_client here to avoid circular imports
        import fal_client
        
        # Create temporary files for the image and audio
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file, \
             tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            
            image_path = image_file.name
            audio_path = audio_file.name
            
            # Write the image and audio to the temporary files
            image_file.write(scene_image_content)
            audio_file.write(audio_content)
            
            # Upload the image to FAL to get a hosted URL
            try:
                image_url = fal_client.upload_file(image_path)
                logger.info(f"Uploaded scene image to FAL: {image_url}")
            except Exception as e:
                logger.error(f"Error uploading image to FAL: {str(e)}")
                # Fall back to static image video
                return create_static_image_video(scene_image_content, audio_content, duration)
            
            # Define the callback function for progress updates
            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        logger.info(f"Kling progress: {log['message']}")
            
            logger.info(f"Generating video from image with Kling 1.6")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Duration: {duration} seconds")
            
            # Call the Kling 1.6 model
            try:
                result = fal_client.subscribe(
                    "fal-ai/kling-video/v1.6/pro/image-to-video",
                    arguments={
                        "prompt": prompt,
                        "image_url": image_url,
                        "duration": str(int(min(30, max(1, duration)))),  # Ensure duration is within 1-30 seconds and an integer
                        "aspect_ratio": "16:9",
                        "negative_prompt": "blur, distort, and low quality",
                        "cfg_scale": 0.5
                    },
                    with_logs=True,
                    on_queue_update=on_queue_update,
                )
                
                # Extract the video URL from the result
                video_url = result.get("video", {}).get("url")
                
                if not video_url:
                    logger.warning("No video URL returned from Kling API")
                    # Fall back to static image video
                    return create_static_image_video(scene_image_content, audio_content, duration)
                
                # Download the video
                logger.info(f"Downloading video from: {video_url}")
                video_response = requests.get(video_url)
                
                if video_response.status_code != 200:
                    logger.error(f"Error downloading video: HTTP {video_response.status_code}")
                    # Fall back to static image video
                    return create_static_image_video(scene_image_content, audio_content, duration)
                
                # Get the video content
                motion_video_content = video_response.content
                
                # Create a temporary file for the motion video
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as motion_video_file:
                    motion_video_path = motion_video_file.name
                    motion_video_file.write(motion_video_content)
                
                # Create a temporary file for the output
                output_path = motion_video_path + ".with_audio.mp4"
                
                # Use FFmpeg to combine the video with audio
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", motion_video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    output_path
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Read the output video content
                with open(output_path, "rb") as f:
                    output_video_content = f.read()
                
                # Clean up temporary files
                os.remove(motion_video_path)
                os.remove(output_path)
                
                return output_video_content
            except Exception as e:
                logger.error(f"Error calling Kling API: {str(e)}")
                # Fall back to static image video
                return create_static_image_video(scene_image_content, audio_content, duration)
            
    except Exception as e:
        logger.error(f"Error creating scene video with motion: {str(e)}")
        # Fall back to static image video
        return create_static_image_video(scene_image_content, audio_content, duration)
    finally:
        # Clean up temporary files
        try:
            os.remove(image_path)
            os.remove(audio_path)
        except:
            pass
