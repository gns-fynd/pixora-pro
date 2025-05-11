"""
Scene breakdown router for the Pixora AI platform.

This module provides API endpoints for scene breakdown and video generation.
"""
import logging
import time
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.ai import PromptAnalyzer, VideoGenerator
from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/scenes",
    tags=["scenes"],
    responses={404: {"description": "Not found"}},
)


class ScriptRequest(BaseModel):
    """
    Request model for script generation.
    """
    prompt: str = Field(..., description="The prompt to generate a script from")
    style: Optional[str] = Field(None, description="Optional style for the video")


class ScriptResponse(BaseModel):
    """
    Response model for script generation.
    """
    title: str = Field(..., description="The title of the video")
    description: str = Field(..., description="The description of the video")
    style: str = Field(..., description="The style of the video")
    narration: str = Field(..., description="The narration text for the video")
    tone: Optional[str] = Field(None, description="The tone of the video")
    target_audience: Optional[str] = Field(None, description="The target audience for the video")
    key_points: Optional[List[str]] = Field(None, description="Key points of the video")


class SceneBreakdownRequest(BaseModel):
    """
    Request model for scene breakdown.
    """
    script: Dict[str, Any] = Field(..., description="The script to break down into scenes")
    duration: int = Field(30, description="The duration of the video in seconds", ge=10, le=300)


class SceneResponse(BaseModel):
    """
    Response model for a scene.
    """
    id: str = Field(..., description="The scene ID")
    title: str = Field(..., description="The scene title")
    description: str = Field(..., description="The scene description")
    duration: int = Field(..., description="The scene duration in seconds")
    narration: str = Field(..., description="The narration text for the scene")


class SceneBreakdownResponse(BaseModel):
    """
    Response model for scene breakdown.
    """
    scenes: List[SceneResponse] = Field(..., description="The scenes")
    total_duration: int = Field(..., description="The total duration of the video in seconds")


class VideoGenerationRequest(BaseModel):
    """
    Request model for video generation.
    """
    prompt: str = Field(..., description="The prompt to generate a video from")
    aspect_ratio: str = Field("16:9", description="The aspect ratio of the video")
    duration: int = Field(30, description="The duration of the video in seconds", ge=10, le=300)
    style: Optional[str] = Field(None, description="Optional style for the video")


class VideoGenerationResponse(BaseModel):
    """
    Response model for video generation.
    """
    task_id: str = Field(..., description="The task ID")
    prompt: str = Field(..., description="The prompt used to generate the video")
    aspect_ratio: str = Field(..., description="The aspect ratio of the video")
    duration: int = Field(..., description="The requested maximum duration of the video in seconds")
    style: Optional[str] = Field(None, description="The style of the video")
    status: str = Field(..., description="The status of the video generation")
    cost: int = Field(..., description="The cost of the video generation in credits")
    actual_duration: Optional[int] = Field(None, description="The actual duration of the video determined by the voiceover (available in the result)")


class VideoStatusResponse(BaseModel):
    """
    Response model for video status.
    """
    task_id: str = Field(..., description="The task ID")
    status: str = Field(..., description="The status of the video generation")
    progress: float = Field(..., description="The progress of the video generation (0-100)")
    message: str = Field(..., description="The progress message")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the video generation")


@router.post("/script", response_model=ScriptResponse)
async def generate_script(
    request: ScriptRequest,
    current_user: User = Depends(get_current_user),
    prompt_analyzer: PromptAnalyzer = Depends(),
):
    """
    Generate a script from a prompt.
    """
    try:
        # Generate the script
        script = await prompt_analyzer.analyze_prompt(
            prompt=request.prompt,
            style=request.style
        )
        
        return script
        
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Script generation failed: {str(e)}"
        )


@router.post("/breakdown", response_model=SceneBreakdownResponse)
async def generate_scene_breakdown(
    request: SceneBreakdownRequest,
    current_user: User = Depends(get_current_user),
    prompt_analyzer: PromptAnalyzer = Depends(),
):
    """
    Generate a scene breakdown from a script.
    """
    try:
        # Generate the scene breakdown
        scenes = await prompt_analyzer.generate_scene_breakdown(
            script=request.script,
            duration=request.duration
        )
        
        # Calculate the total duration
        total_duration = sum(scene["duration"] for scene in scenes)
        
        return {
            "scenes": scenes,
            "total_duration": total_duration,
        }
        
    except Exception as e:
        logger.error(f"Error generating scene breakdown: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scene breakdown generation failed: {str(e)}"
        )


# Store the last request time for each user to implement rate limiting
user_last_request = {}
# Minimum time between requests in seconds
MIN_REQUEST_INTERVAL = 5

@router.post("/video", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    video_generator: VideoGenerator = Depends(),
):
    """
    Generate a video from a prompt.
    """
    try:
        # Check if the user has made a request recently
        user_id = current_user.id
        current_time = time.time()
        
        if user_id in user_last_request:
            time_since_last_request = current_time - user_last_request[user_id]
            if time_since_last_request < MIN_REQUEST_INTERVAL:
                # If the user has made a request too recently, return a rate limit error
                logger.warning(f"Rate limit exceeded for user {user_id}. Last request was {time_since_last_request:.2f} seconds ago.")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait at least {MIN_REQUEST_INTERVAL} seconds between video generation requests."
                )
        
        # Update the last request time for this user
        user_last_request[user_id] = current_time
        
        # Check if there's already an active task for this user
        active_tasks = [
            task_id for task_id, progress in video_generator.progress.items()
            if progress.get("user_id") == user_id and progress.get("progress", 100) < 100
        ]
        
        if active_tasks:
            logger.warning(f"User {user_id} already has active tasks: {active_tasks}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active video generation task. Please wait for it to complete or check its status."
            )
        
        # Generate the video
        result = await video_generator.generate_video(
            prompt=request.prompt,
            user_id=user_id,
            aspect_ratio=request.aspect_ratio,
            duration=request.duration,
            style=request.style,
            background_tasks=background_tasks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video generation failed: {str(e)}"
        )


@router.get("/debug/progress")
async def get_progress_debug(
    video_generator: VideoGenerator = Depends(),
):
    """
    Debug endpoint to get the progress dictionary.
    """
    return {
        "progress": video_generator.progress,
        "background_tasks": list(video_generator.background_tasks.keys())
    }


@router.get("/video/{task_id}", response_model=VideoStatusResponse)
async def get_video_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    video_generator: VideoGenerator = Depends(),
):
    """
    Get the status of a video generation task.
    """
    try:
        # Log the progress dictionary for debugging
        logger.info(f"Progress dictionary: {video_generator.progress}")
        logger.info(f"Looking for task ID: {task_id}")
        
        # Get the video status
        video_status = await video_generator.get_video_status(task_id)
        
        return video_status
        
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video status: {str(e)}"
        )
