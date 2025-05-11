"""
Audio duration adjustment utilities.

This module provides utilities for adjusting the duration of audio files.
"""
import os
import tempfile
import logging
import asyncio
from typing import Optional

from app.ai.utils.duration.common import get_duration, copy_file, execute_ffmpeg_command, calculate_fade_durations


# Set up logging
logger = logging.getLogger(__name__)


class AudioDurationAdjuster:
    """
    Utility for adjusting the duration of audio files.
    
    This class provides methods for:
    - Speeding up or slowing down audio
    - Trimming audio to a specific duration
    - Extending audio by looping
    - Adding fade-in and fade-out effects
    """
    
    @staticmethod
    async def adjust_duration(
        audio_path: str,
        target_duration: float,
        output_path: Optional[str] = None,
        fade_out: bool = True,
        fade_in: bool = False,
        preserve_pitch: bool = True
    ) -> str:
        """
        Adjust the duration of an audio file.
        
        Args:
            audio_path: Path to the audio file
            target_duration: Target duration in seconds
            output_path: Optional path for the output file (if not provided, a temporary file will be created)
            fade_out: Whether to add a fade-out effect
            fade_in: Whether to add a fade-in effect
            preserve_pitch: Whether to preserve the pitch when changing speed
            
        Returns:
            Path to the adjusted audio file
        """
        # Create output path if not provided
        if not output_path:
            # Create a temporary file with the same extension
            _, ext = os.path.splitext(audio_path)
            temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            output_path = temp_file.name
            temp_file.close()
        
        try:
            # Get the current duration
            current_duration = await get_duration(audio_path)
            
            if current_duration is None:
                raise ValueError(f"Could not determine duration of {audio_path}")
            
            # Determine the adjustment method
            if abs(current_duration - target_duration) < 0.1:
                # Duration is already close enough
                if fade_in or fade_out:
                    # Apply fades without changing duration
                    await AudioDurationAdjuster.apply_fades(
                        audio_path, 
                        output_path, 
                        fade_in=fade_in, 
                        fade_out=fade_out
                    )
                else:
                    # Just copy the file
                    await copy_file(audio_path, output_path)
            
            elif current_duration > target_duration:
                # Need to shorten
                await AudioDurationAdjuster.trim_audio(
                    audio_path, 
                    output_path, 
                    target_duration, 
                    fade_out=fade_out, 
                    fade_in=fade_in
                )
            
            else:
                # Need to extend
                if current_duration >= target_duration / 2:
                    # If the audio is at least half the target duration, adjust speed
                    await AudioDurationAdjuster.adjust_speed(
                        audio_path, 
                        output_path, 
                        current_duration / target_duration, 
                        preserve_pitch=preserve_pitch,
                        fade_out=fade_out, 
                        fade_in=fade_in
                    )
                else:
                    # Otherwise, loop the audio
                    await AudioDurationAdjuster.loop_audio(
                        audio_path, 
                        output_path, 
                        target_duration, 
                        fade_out=fade_out, 
                        fade_in=fade_in
                    )
            
            return output_path
            
        except Exception as e:
            # Clean up the temporary file if there was an error
            if not output_path and os.path.exists(output_path):
                os.unlink(output_path)
            
            logger.error(f"Error adjusting audio duration: {e}")
            raise
    
    @staticmethod
    async def trim_audio(
        input_path: str,
        output_path: str,
        target_duration: float,
        fade_out: bool = True,
        fade_in: bool = False
    ) -> None:
        """
        Trim an audio file to a specific duration.
        
        Args:
            input_path: Path to the input file
            output_path: Path to the output file
            target_duration: Target duration in seconds
            fade_out: Whether to add a fade-out effect
            fade_in: Whether to add a fade-in effect
        """
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_path,
            "-t", str(target_duration)
        ]
        
        # Add fade effects if requested
        filter_complex = []
        
        if fade_in or fade_out:
            fade_in_duration, fade_out_duration = calculate_fade_durations(
                target_duration, 
                fade_in=fade_in, 
                fade_out=fade_out
            )
            
            if fade_in:
                filter_complex.append(f"afade=t=in:st=0:d={fade_in_duration}")
            
            if fade_out:
                filter_complex.append(f"afade=t=out:st={target_duration - fade_out_duration}:d={fade_out_duration}")
        
        # Add filter complex if needed
        if filter_complex:
            command.extend(["-af", ",".join(filter_complex)])
        
        # Add output path
        command.append(output_path)
        
        # Execute the command
        await execute_ffmpeg_command(command)
    
    @staticmethod
    async def adjust_speed(
        input_path: str,
        output_path: str,
        speed_factor: float,
        preserve_pitch: bool = True,
        fade_out: bool = True,
        fade_in: bool = False
    ) -> None:
        """
        Adjust the speed of an audio file.
        
        Args:
            input_path: Path to the input file
            output_path: Path to the output file
            speed_factor: Speed factor (1.0 = normal speed, < 1.0 = slower, > 1.0 = faster)
            preserve_pitch: Whether to preserve the pitch when changing speed
            fade_out: Whether to add a fade-out effect
            fade_in: Whether to add a fade-in effect
        """
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_path
        ]
        
        # Build the filter complex
        filter_complex = []
        
        # Add speed adjustment
        if preserve_pitch:
            # Use ATEMPO filter for speed adjustment with pitch preservation
            # ATEMPO only supports speed factors between 0.5 and 2.0
            # For more extreme adjustments, chain multiple ATEMPO filters
            if speed_factor < 0.5:
                # For speed factors less than 0.5, chain multiple ATEMPO filters
                # e.g., 0.25 = 0.5 * 0.5
                atempo_chain = []
                remaining_factor = speed_factor
                while remaining_factor < 0.5:
                    atempo_chain.append("atempo=0.5")
                    remaining_factor /= 0.5
                atempo_chain.append(f"atempo={remaining_factor}")
                filter_complex.append(",".join(atempo_chain))
            elif speed_factor > 2.0:
                # For speed factors greater than 2.0, chain multiple ATEMPO filters
                # e.g., 4.0 = 2.0 * 2.0
                atempo_chain = []
                remaining_factor = speed_factor
                while remaining_factor > 2.0:
                    atempo_chain.append("atempo=2.0")
                    remaining_factor /= 2.0
                atempo_chain.append(f"atempo={remaining_factor}")
                filter_complex.append(",".join(atempo_chain))
            else:
                # For speed factors between 0.5 and 2.0, use a single ATEMPO filter
                filter_complex.append(f"atempo={speed_factor}")
        else:
            # Use SETPTS filter for speed adjustment without pitch preservation
            filter_complex.append(f"asetpts={1/speed_factor}*PTS")
        
        # Get the duration for fade effects
        current_duration = await get_duration(input_path)
        if current_duration is None:
            raise ValueError(f"Could not determine duration of {input_path}")
        
        target_duration = current_duration / speed_factor
        
        # Add fade effects if requested
        if fade_in or fade_out:
            fade_in_duration, fade_out_duration = calculate_fade_durations(
                target_duration, 
                fade_in=fade_in, 
                fade_out=fade_out
            )
            
            if fade_in:
                filter_complex.append(f"afade=t=in:st=0:d={fade_in_duration}")
            
            if fade_out:
                filter_complex.append(f"afade=t=out:st={target_duration - fade_out_duration}:d={fade_out_duration}")
        
        # Add filter complex
        command.extend(["-af", ",".join(filter_complex)])
        
        # Add output path
        command.append(output_path)
        
        # Execute the command
        await execute_ffmpeg_command(command)
    
    @staticmethod
    async def loop_audio(
        input_path: str,
        output_path: str,
        target_duration: float,
        fade_out: bool = True,
        fade_in: bool = False,
        crossfade_duration: float = 1.0
    ) -> None:
        """
        Loop an audio file to reach a specific duration.
        
        Args:
            input_path: Path to the input file
            output_path: Path to the output file
            target_duration: Target duration in seconds
            fade_out: Whether to add a fade-out effect
            fade_in: Whether to add a fade-in effect
            crossfade_duration: Duration of the crossfade between loops
        """
        # Get the current duration
        current_duration = await get_duration(input_path)
        if current_duration is None:
            raise ValueError(f"Could not determine duration of {input_path}")
        
        # Calculate the number of loops needed
        num_loops = int(target_duration / current_duration) + 1
        
        # Create a temporary file for the looped audio
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Build the ffmpeg command for looping
            loop_command = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-stream_loop", str(num_loops - 1),  # Number of times to loop (0 = no loop)
                "-i", input_path,
                "-t", str(target_duration),  # Limit the output duration
                temp_path
            ]
            
            # Execute the command
            await execute_ffmpeg_command(loop_command)
            
            # Apply fades if requested
            filter_complex = []
            
            if fade_in or fade_out:
                fade_in_duration, fade_out_duration = calculate_fade_durations(
                    target_duration, 
                    fade_in=fade_in, 
                    fade_out=fade_out
                )
                
                if fade_in:
                    filter_complex.append(f"afade=t=in:st=0:d={fade_in_duration}")
                
                if fade_out:
                    filter_complex.append(f"afade=t=out:st={target_duration - fade_out_duration}:d={fade_out_duration}")
            
            # Build the ffmpeg command for fades
            fade_command = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", temp_path
            ]
            
            # Add filter complex if needed
            if filter_complex:
                fade_command.extend(["-af", ",".join(filter_complex)])
            
            # Add output path
            fade_command.append(output_path)
            
            # Execute the command
            await execute_ffmpeg_command(fade_command)
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @staticmethod
    async def apply_fades(
        input_path: str,
        output_path: str,
        fade_in: bool = False,
        fade_out: bool = True,
        fade_in_duration: float = 1.0,
        fade_out_duration: float = 1.0
    ) -> None:
        """
        Apply fade-in and fade-out effects to an audio file.
        
        Args:
            input_path: Path to the input file
            output_path: Path to the output file
            fade_in: Whether to add a fade-in effect
            fade_out: Whether to add a fade-out effect
            fade_in_duration: Duration of the fade-in effect in seconds
            fade_out_duration: Duration of the fade-out effect in seconds
        """
        # Get the current duration
        current_duration = await get_duration(input_path)
        if current_duration is None:
            raise ValueError(f"Could not determine duration of {input_path}")
        
        # Use calculated fade durations if not provided
        if fade_in or fade_out:
            calculated_fade_in_duration, calculated_fade_out_duration = calculate_fade_durations(
                current_duration, 
                fade_in=fade_in, 
                fade_out=fade_out
            )
            
            if fade_in_duration is None or fade_in_duration <= 0:
                fade_in_duration = calculated_fade_in_duration
            
            if fade_out_duration is None or fade_out_duration <= 0:
                fade_out_duration = calculated_fade_out_duration
        
        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_path
        ]
        
        # Build the filter complex
        filter_complex = []
        
        if fade_in:
            # Add fade-in effect
            filter_complex.append(f"afade=t=in:st=0:d={fade_in_duration}")
        
        if fade_out:
            # Add fade-out effect
            filter_complex.append(f"afade=t=out:st={current_duration - fade_out_duration}:d={fade_out_duration}")
        
        # Add filter complex if needed
        if filter_complex:
            command.extend(["-af", ",".join(filter_complex)])
        
        # Add output path
        command.append(output_path)
        
        # Execute the command
        await execute_ffmpeg_command(command)
