"""
AI module for the Pixora AI application.

This package contains AI-related modules for the Pixora AI application.
"""

from .orchestrator import VideoOrchestrator
from .agents import ScriptAgent, VideoAgent, process_video_request, get_video_agent
from .tools import (
    # Asset tools
    generate_character_images, generate_scene_image, generate_voice_over,
    generate_music, generate_assets_for_scene, generate_music_for_scenes,
    
    # Video tools
    create_scene_video_with_motion, normalize_duration, apply_transition,
    stitch_video, create_video_for_scene,
    
    # Script tools
    generate_script, refine_script
)

__all__ = [
    # Orchestrator
    "VideoOrchestrator",
    
    # Agents
    "ScriptAgent",
    "VideoAgent",
    "process_video_request",
    "get_video_agent",
    
    # Asset tools
    "generate_character_images",
    "generate_scene_image",
    "generate_voice_over",
    "generate_music",
    "generate_assets_for_scene",
    "generate_music_for_scenes",
    
    # Video tools
    "create_scene_video_with_motion",
    "normalize_duration",
    "apply_transition",
    "stitch_video",
    "create_video_for_scene",
    
    # Script tools
    "generate_script",
    "refine_script"
]
