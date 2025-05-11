"""
Schemas for the unified AI generation API.

This module defines the schemas for the unified AI generation endpoint.
"""
import enum
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ResponseType(str, enum.Enum):
    """Response type for the unified generation endpoint."""
    
    SCRIPT = "script"
    VIDEO = "video"
    CLIPS = "clips"
    AUDIO = "audio"
    IMAGE = "image"
    ANALYSIS = "analysis"


class UIActionType(str, enum.Enum):
    """UI action type for the client."""
    
    UPDATE = "update"  # Update content in place
    REPLACE = "replace"  # Replace content with new content
    MODAL = "modal"  # Show content in a modal
    OVERLAY = "overlay"  # Show content in an overlay
    TOAST = "toast"  # Show a toast notification
    NAVIGATE = "navigate"  # Navigate to a new page


class UIAction(BaseModel):
    """UI action for the client to perform."""
    
    type: UIActionType
    target: str
    params: Optional[Dict[str, Any]] = None
    preserve_state: Optional[bool] = False


class UnifiedGenerationRequest(BaseModel):
    """Request model for the unified generation endpoint."""
    
    prompt: str
    video_id: Optional[UUID] = None
    scene_id: Optional[UUID] = None
    reference_files: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    client_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Response data models for different response types
class ScriptData(BaseModel):
    """Data model for script responses."""
    
    script_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    scenes: List[Dict[str, Any]]
    duration: Optional[float] = None
    style: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoData(BaseModel):
    """Data model for video responses."""
    
    video_id: Optional[UUID] = None
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    title: Optional[str] = None
    description: Optional[str] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ClipsData(BaseModel):
    """Data model for clips/scene responses."""
    
    scene_id: Optional[UUID] = None
    video_id: Optional[UUID] = None
    clips: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class AudioData(BaseModel):
    """Data model for audio responses."""
    
    audio_id: Optional[UUID] = None
    url: str
    duration: Optional[float] = None
    type: Optional[str] = None  # e.g., "voiceover", "music", "sound_effect"
    metadata: Optional[Dict[str, Any]] = None


class ImageData(BaseModel):
    """Data model for image responses."""
    
    image_id: Optional[UUID] = None
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AnalysisData(BaseModel):
    """Data model for analysis responses."""
    
    analysis: Dict[str, Any]
    suggestions: Optional[List[str]] = None
    possible_intents: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class UnifiedGenerationResponse(BaseModel):
    """Response model for the unified generation endpoint."""
    
    response_type: ResponseType
    message: str
    data: Union[ScriptData, VideoData, ClipsData, AudioData, ImageData, AnalysisData, Dict[str, Any]]
    task_id: Optional[str] = None
    ui_action: Optional[UIAction] = None


class TaskProgress(BaseModel):
    """Task progress information."""
    
    progress: float = Field(..., ge=0.0, le=100.0)
    message: str
    status: str
    updated_at: datetime


class TaskStatus(BaseModel):
    """Task status information."""
    
    task_id: str
    user_id: str
    progress: float = Field(..., ge=0.0, le=100.0)
    message: str
    status: str
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
