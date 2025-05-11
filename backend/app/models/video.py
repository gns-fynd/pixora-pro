"""
Video generation models for the Pixora AI application.

This module contains the Pydantic models used for video generation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime


class TransitionType(str, Enum):
    """
    Types of transitions between scenes in a video.
    """
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    FADE_TO_BLACK = "fade_to_black"
    CROSSFADE = "crossfade"


class Scene(BaseModel):
    """
    A scene in a video script.
    
    Attributes:
        index: The position of the scene in the script
        title: The title of the scene
        script: The narration text for the scene
        video_prompt: The visual description for image generation
        transition: The transition to use after this scene
    """
    index: int
    title: str
    script: str
    video_prompt: str
    transition: TransitionType = TransitionType.FADE


class Clip(BaseModel):
    """
    A clip in a video, containing a scene.
    
    Attributes:
        scene: The scene in this clip
    """
    scene: Scene


class MusicPrompt(BaseModel):
    """
    A prompt for generating background music for specific scenes.
    
    Attributes:
        prompt: The description of the desired music
        scene_indexes: The indexes of scenes that use this music
    """
    prompt: str
    scene_indexes: List[int]


class CharacterProfile(BaseModel):
    """
    A character profile for consistent character generation.
    
    Attributes:
        name: The name of the character
        image_prompt: The description for generating character images
        image_urls: Optional dictionary of image URLs for different views
    """
    name: str
    image_prompt: str
    image_urls: Optional[Dict[str, str]] = None


class ScriptBreakdown(BaseModel):
    """
    A complete script breakdown for a video.
    
    Attributes:
        user_prompt: The original user prompt
        rewritten_prompt: The enhanced, detailed prompt
        voice_character: Optional URL to a voice sample
        character_consistency: Whether to maintain consistent characters
        music: List of music prompts for different scenes
        character_profiles: List of character profiles
        clips: List of clips in the video
        expected_duration: Estimated duration in seconds
        task_id: Unique ID for the script generation task
        user_id: ID of the user who created the script
    """
    user_prompt: str
    rewritten_prompt: str
    voice_character: Optional[str] = None
    character_consistency: bool = False
    music: List[MusicPrompt]
    character_profiles: List[CharacterProfile] = []
    clips: List[Clip]
    expected_duration: Optional[float] = None
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str


class ProjectStatus(str, Enum):
    """
    Status of a video generation project.
    """
    DRAFT = "draft"
    SCRIPT_GENERATED = "script_generated"
    SCRIPT_APPROVED = "script_approved"
    GENERATING_ASSETS = "generating_assets"
    STITCHING_VIDEO = "stitching_video"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """
    A video generation project.
    
    Attributes:
        id: Unique ID for the project
        title: The title of the project
        description: Optional description of the project
        user_id: ID of the user who created the project
        status: Current status of the project
        script: Optional script breakdown for the project
        created_at: When the project was created
        updated_at: When the project was last updated
        video_url: Optional URL to the generated video
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    user_id: str
    status: ProjectStatus = ProjectStatus.DRAFT
    script: Optional[ScriptBreakdown] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    video_url: Optional[str] = None


class AssetGenerationStatus(str, Enum):
    """
    Status of an asset generation task.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetGeneration(BaseModel):
    """
    An asset generation task.
    
    Attributes:
        id: Unique ID for the asset generation
        project_id: ID of the project this asset belongs to
        scene_index: Optional index of the scene this asset is for
        asset_type: Type of asset (character, scene, audio, music, video)
        status: Current status of the asset generation
        result_url: Optional URL to the generated asset
        error_message: Optional error message if generation failed
        created_at: When the asset generation was created
        updated_at: When the asset generation was last updated
        metadata: Optional metadata for the asset
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    scene_index: Optional[int] = None
    asset_type: str  # "character", "scene", "audio", "music", "video"
    status: AssetGenerationStatus = AssetGenerationStatus.PENDING
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class PromptRequest(BaseModel):
    """
    A request to generate a script from a prompt.
    
    Attributes:
        prompt: The user's prompt describing the desired video
        user_id: ID of the user making the request
        character_consistency: Whether to maintain consistent characters
        voice_character: Optional URL to a voice sample
    """
    prompt: str
    user_id: str
    character_consistency: bool = False
    voice_character: Optional[str] = None
