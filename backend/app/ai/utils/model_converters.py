"""
Model converters for the Pixora AI application.

This module provides utilities for converting between different model formats.
"""
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from app.schemas.ai_generation import (
    UnifiedGenerationResponse,
    ResponseType,
    UIAction,
    UIActionType
)


def unified_request_to_video_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a unified request to a video request.

    Args:
        request: The unified request

    Returns:
        The video request
    """
    # Extract the prompt
    prompt = request.get("prompt", "")
    
    # Extract the duration (default to 60 seconds)
    duration = 60.0
    if "preferences" in request and "duration" in request["preferences"]:
        try:
            duration = float(request["preferences"]["duration"])
        except (ValueError, TypeError):
            pass
    
    # Extract the style (default to "cinematic")
    style = "cinematic"
    if "preferences" in request and "style" in request["preferences"]:
        style = request["preferences"]["style"]
    
    # Extract the voice sample URL
    voice_sample_url = None
    if "preferences" in request and "voice_sample_url" in request["preferences"]:
        voice_sample_url = request["preferences"]["voice_sample_url"]
    
    # Extract character consistency
    character_consistency = False
    if "preferences" in request and "character_consistency" in request["preferences"]:
        character_consistency = bool(request["preferences"]["character_consistency"])
    
    # Extract reference files
    reference_files = []
    if "reference_files" in request:
        reference_files = request["reference_files"]
    
    # Create the video request
    video_request = {
        "prompt": prompt,
        "duration": duration,
        "style": style,
        "voice_sample_url": voice_sample_url,
        "character_consistency": character_consistency,
        "reference_files": reference_files
    }
    
    return video_request


def video_result_to_unified_response(
    result: Dict[str, Any],
    task_id: str,
    message: str = "Task completed",
    response_type: Optional[ResponseType] = None
) -> UnifiedGenerationResponse:
    """
    Convert a video result to a unified response.

    Args:
        result: The video result
        task_id: The task ID
        message: Optional message
        response_type: Optional response type

    Returns:
        The unified response
    """
    # Determine the response type if not provided
    if response_type is None:
        if "video_url" in result:
            response_type = ResponseType.VIDEO
        elif "scenes" in result:
            response_type = ResponseType.CLIPS
        elif "script" in result:
            response_type = ResponseType.SCRIPT
        else:
            response_type = ResponseType.ANALYSIS
    
    # Create the UI action
    ui_action = UIAction(
        type=UIActionType.UPDATE,
        target="main_content"
    )
    
    # Customize the UI action based on the response type
    if response_type == ResponseType.VIDEO:
        ui_action = UIAction(
            type=UIActionType.UPDATE,
            target="video_player",
            params={"video_url": result.get("video_url")}
        )
    elif response_type == ResponseType.CLIPS:
        ui_action = UIAction(
            type=UIActionType.UPDATE,
            target="clips_viewer",
            params={"scenes": result.get("scenes", [])}
        )
    elif response_type == ResponseType.SCRIPT:
        ui_action = UIAction(
            type=UIActionType.UPDATE,
            target="script_editor",
            params={"script": result.get("script", {})}
        )
    
    # Create the unified response
    response = UnifiedGenerationResponse(
        response_type=response_type,
        message=message,
        data=result,
        task_id=task_id,
        ui_action=ui_action
    )
    
    return response
