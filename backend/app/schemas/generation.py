"""
Schemas for generation-related data.

This module defines Pydantic models for generation-related data structures.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Status of a generation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationStep(str, Enum):
    """Steps in the generation process."""
    ANALYZING_PROMPT = "analyzing_prompt"
    GENERATING_IMAGES = "generating_images"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_MUSIC = "generating_music"
    GENERATING_VIDEO = "generating_video"
    ASSEMBLING_VIDEO = "assembling_video"


class GenerationRequest(BaseModel):
    """Request to start a video generation."""
    prompt: str = Field(..., description="The prompt to generate the video from")
    video_id: str = Field(..., description="The ID of the video to generate")
    style: Optional[str] = Field(None, description="The style of the video")
    duration: Optional[float] = Field(None, description="The duration of the video in seconds")
    voice_id: Optional[str] = Field(None, description="The ID of the voice to use")
    music_style: Optional[str] = Field(None, description="The style of the background music")


class GenerationStatusResponse(BaseModel):
    """Response with the status of a generation task."""
    task_id: str = Field(..., description="The ID of the generation task")
    video_id: str = Field(..., description="The ID of the video being generated")
    status: GenerationStatus = Field(..., description="The status of the generation task")
    progress: float = Field(..., description="The overall progress of the generation (0-100)")
    current_step: Optional[GenerationStep] = Field(None, description="The current step in the generation process")
    step_progress: Optional[float] = Field(None, description="The progress of the current step (0-100)")
    message: Optional[str] = Field(None, description="A message describing the current status")
    error: Optional[str] = Field(None, description="Error message if the generation failed")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the generation")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="The steps in the generation process")


class GenerationTaskInfo(BaseModel):
    """Information about a generation task."""
    task_id: str
    video_id: str
    user_id: str
    prompt: str
    status: GenerationStatus = GenerationStatus.PENDING
    progress: float = 0
    current_step: Optional[GenerationStep] = None
    step_progress: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: float  # Unix timestamp
    updated_at: float  # Unix timestamp
