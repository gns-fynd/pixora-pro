"""
Task models for managing video generation tasks.
"""
import time
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List, Callable

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStage(str, Enum):
    """Stages of video generation."""
    INITIALIZING = "initializing"
    SCENE_BREAKDOWN = "scene_breakdown"
    CHARACTER_GENERATION = "character_generation"
    ASSET_GENERATION = "asset_generation"
    MUSIC_GENERATION = "music_generation"
    VIDEO_COMPOSITION = "video_composition"
    FINALIZING = "finalizing"


class Task(BaseModel):
    """Model for a video generation task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = Field(TaskStatus.PENDING)
    stage: TaskStage = Field(TaskStage.INITIALIZING)
    progress: int = Field(0, description="Progress percentage (0-100)")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = Field(None)
    
    # Input parameters
    prompt: str
    script: str
    duration: int
    style: str
    
    # Results
    video_url: Optional[str] = Field(None)
    error: Optional[str] = Field(None)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Scene data
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Script data
    script: Optional[Dict[str, Any]] = Field(default=None)
    
    # Asset URLs
    assets: Dict[str, Any] = Field(default_factory=dict)
    
    # User ID for tracking ownership
    user_id: Optional[str] = Field(None)
    
    class Config:
        arbitrary_types_allowed = True
    
    def update_progress(self, progress: int, stage: Optional[TaskStage] = None):
        """Update the progress of the task."""
        self.progress = progress
        if stage:
            self.stage = stage
        self.updated_at = time.time()
    
    def complete(self, video_url: str):
        """Mark the task as completed."""
        self.status = TaskStatus.COMPLETED
        self.progress = 100
        self.stage = TaskStage.FINALIZING
        self.video_url = video_url
        self.completed_at = time.time()
        self.updated_at = time.time()
    
    def fail(self, error: str):
        """Mark the task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = time.time()
    
    def cancel(self):
        """Mark the task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary for storage."""
        return {
            "id": self.id,
            "status": self.status.value,
            "stage": self.stage.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "prompt": self.prompt,
            "duration": self.duration,
            "style": self.style,
            "video_url": self.video_url,
            "error": self.error,
            "metadata": self.metadata,
            "scenes": self.scenes,
            "script": self.script,
            "assets": self.assets,
            "user_id": self.user_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create a task from a dictionary."""
        # Convert string status and stage to enum values
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        if "stage" in data and isinstance(data["stage"], str):
            data["stage"] = TaskStage(data["stage"])
        
        return cls(**data)


# Type for progress callback functions
ProgressCallback = Callable[[int, Optional[str]], None]
