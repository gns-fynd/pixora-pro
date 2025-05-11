"""
Duration adjustment utilities for media files.

This module provides utilities for adjusting the duration of audio, video, and music files.
It is maintained for backward compatibility and imports from the modular structure.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple, Union

# Import from the modular structure
from app.ai.utils.duration import (
    AudioDurationAdjuster,
    VideoDurationAdjuster,
    SceneDurationManager,
    get_duration,
    copy_file
)
from app.ai.utils.duration.media_utils import (
    get_media_info,
    get_media_type,
    extract_audio,
    extract_frame,
    combine_audio_video,
    convert_image_to_video
)

# Set up logging
logger = logging.getLogger(__name__)

# Re-export classes and functions for backward compatibility
__all__ = [
    'AudioDurationAdjuster',
    'VideoDurationAdjuster',
    'SceneDurationManager',
    'get_duration',
    'copy_file',
    'get_media_info',
    'get_media_type',
    'extract_audio',
    'extract_frame',
    'combine_audio_video',
    'convert_image_to_video'
]
