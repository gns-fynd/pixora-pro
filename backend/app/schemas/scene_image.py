"""
Scene image schemas for the Pixora AI platform.

This module provides Pydantic models for scene image generation.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class SceneImageRequest(BaseModel):
    """
    Request model for scene image generation.
    """
    id: str = Field(..., description="The scene ID")
    description: str = Field(..., description="The scene description")


class SceneImageResponse(BaseModel):
    """
    Response model for scene image generation.
    """
    scene_id: str = Field(..., description="The scene ID")
    image_url: str = Field(..., description="The URL of the generated image")
    is_fallback: Optional[bool] = Field(False, description="Whether this is a fallback image")
