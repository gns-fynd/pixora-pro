"""
Request and response models for the video agent API.
"""
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from pydantic import BaseModel, Field


class VideoStyle(str, Enum):
    """Available video styles."""
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ANIME = "anime"
    CINEMATIC = "cinematic"
    ARTISTIC = "artistic"
    VINTAGE = "vintage"
    FUTURISTIC = "futuristic"


class VideoRequest(BaseModel):
    """Request model for video creation."""
    prompt: str = Field(..., description="The prompt describing the video to create")
    duration: int = Field(30, description="Duration of the video in seconds", ge=5, le=120)
    style: VideoStyle = Field(VideoStyle.REALISTIC, description="Style of the video")
    voice_sample_url: Optional[str] = Field(None, description="URL to a voice sample for TTS")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Create a video on how AI will help in healthcare",
                "duration": 30,
                "style": "realistic",
                "voice_sample_url": "https://storage.googleapis.com/falserverless/model_tests/zonos/demo_voice_zonos.wav"
            }
        }


class TaskResponse(BaseModel):
    """Response model for task creation."""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing"
            }
        }


class TaskStatus(BaseModel):
    """Response model for task status."""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task")
    progress: int = Field(0, description="Progress percentage (0-100)")
    video_url: Optional[str] = Field(None, description="URL of the generated video if completed")
    error: Optional[str] = Field(None, description="Error message if task failed")
    stage: Optional[str] = Field(None, description="Current stage of the task")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "progress": 100,
                "video_url": "/storage/videos/123e4567-e89b-12d3-a456-426614174000.mp4",
                "error": None,
                "stage": "finalizing",
                "updated_at": "2025-04-05T12:00:00"
            }
        }


class SceneData(BaseModel):
    """Model for scene data."""
    description: str = Field(..., description="Description of the scene")
    narration: str = Field(..., description="Narration script for the scene")
    duration: float = Field(..., description="Duration of the scene in seconds")
    style_params: Dict[str, Any] = Field(default_factory=dict, description="Style parameters for the scene")
    characters: List[str] = Field(default_factory=list, description="Characters in the scene")
    transition: Optional[str] = Field(None, description="Transition to the next scene")


class StandardVideoMetadata(BaseModel):
    """Model for standard video metadata."""
    scenes: List[SceneData] = Field(..., description="List of scenes in the video")
    needs_character_consistency: bool = Field(False, description="Whether character consistency is needed")
    characters: List[Dict[str, Any]] = Field(default_factory=list, description="Character profiles")
    style: Dict[str, Any] = Field(default_factory=dict, description="Global style parameters")
    transitions: List[Dict[str, Any]] = Field(default_factory=list, description="Transition specifications")
    duration: int = Field(..., description="Total duration in seconds")
    mood: str = Field("neutral", description="Overall mood of the video")


class VideoGenerationPreferences(BaseModel):
    """Model for video generation preferences."""
    style: VideoStyle = Field(VideoStyle.REALISTIC, description="Style of the video")
    duration: int = Field(30, description="Duration of the video in seconds", ge=5, le=120)
    voice_sample_url: Optional[str] = Field(None, description="URL to a voice sample for TTS")
    character_consistency: bool = Field(False, description="Whether character consistency is needed")
    quality: str = Field("standard", description="Quality of the generated video")
    aspect_ratio: str = Field("16:9", description="Aspect ratio of the video")
    
    class Config:
        json_schema_extra = {
            "example": {
                "style": "cinematic",
                "duration": 45,
                "voice_sample_url": "https://storage.googleapis.com/falserverless/model_tests/zonos/demo_voice_zonos.wav",
                "character_consistency": True,
                "quality": "high",
                "aspect_ratio": "16:9"
            }
        }


class UnifiedVideoRequest(BaseModel):
    """Unified request model for video generation."""
    prompt: str = Field(..., description="The prompt describing the video to create")
    preferences: VideoGenerationPreferences = Field(default_factory=VideoGenerationPreferences, description="Preferences for video generation")
    reference_files: Optional[List[str]] = Field(None, description="URLs of reference files")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Create a video on how AI will help in healthcare",
                "preferences": {
                    "style": "cinematic",
                    "duration": 45,
                    "voice_sample_url": "https://storage.googleapis.com/falserverless/model_tests/zonos/demo_voice_zonos.wav",
                    "character_consistency": True,
                    "quality": "high",
                    "aspect_ratio": "16:9"
                },
                "reference_files": [
                    "https://example.com/reference1.jpg",
                    "https://example.com/reference2.jpg"
                ]
            }
        }
