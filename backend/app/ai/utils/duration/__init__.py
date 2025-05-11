"""
Duration adjustment utilities for media files.

This module provides utilities for adjusting the duration of audio, video, and music files,
as well as managing scene durations in a video.
"""

# Import all components for easy access
from app.ai.utils.duration.audio_adjuster import AudioDurationAdjuster
from app.ai.utils.duration.video_adjuster import VideoDurationAdjuster
from app.ai.utils.duration.scene_manager import SceneDurationManager
from app.ai.utils.duration.common import get_duration, copy_file, execute_ffmpeg_command, calculate_fade_durations
from app.ai.utils.duration.media_utils import (
    get_media_info,
    get_media_type,
    extract_audio,
    extract_frame,
    combine_audio_video,
    convert_image_to_video
)

# For backward compatibility
__all__ = [
    'AudioDurationAdjuster',
    'VideoDurationAdjuster',
    'SceneDurationManager',
    'get_duration',
    'copy_file',
    'execute_ffmpeg_command',
    'calculate_fade_durations',
    'get_media_info',
    'get_media_type',
    'extract_audio',
    'extract_frame',
    'combine_audio_video',
    'convert_image_to_video',
]
