"""
Voice sample schemas.

This module provides schemas for voice sample management.
"""
import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class VoiceSampleBase(BaseModel):
    """Base schema for voice samples."""
    name: str = Field(..., description="Name of the voice sample")
    description: Optional[str] = Field(None, description="Description of the voice sample")
    gender: Optional[str] = Field(None, description="Gender of the voice (male, female, neutral)")
    tone: Optional[str] = Field(None, description="Tone of the voice (professional, casual, etc.)")
    is_default: bool = Field(False, description="Whether this is a default voice sample")
    is_public: bool = Field(False, description="Whether this voice sample is publicly available")


class VoiceSampleCreate(VoiceSampleBase):
    """Schema for creating a new voice sample."""
    pass


class VoiceSampleUpdate(BaseModel):
    """Schema for updating an existing voice sample."""
    name: Optional[str] = Field(None, description="Name of the voice sample")
    description: Optional[str] = Field(None, description="Description of the voice sample")
    gender: Optional[str] = Field(None, description="Gender of the voice (male, female, neutral)")
    tone: Optional[str] = Field(None, description="Tone of the voice (professional, casual, etc.)")
    is_default: Optional[bool] = Field(None, description="Whether this is a default voice sample")
    is_public: Optional[bool] = Field(None, description="Whether this voice sample is publicly available")
    sample_url: Optional[str] = Field(None, description="URL to the voice sample audio")


class VoiceSample(VoiceSampleBase):
    """Schema for a voice sample."""
    id: uuid.UUID = Field(..., description="Unique ID of the voice sample")
    sample_url: str = Field(..., description="URL to the voice sample audio")
    user_id: Optional[uuid.UUID] = Field(None, description="ID of the user who owns this voice sample")
    created_at: datetime = Field(..., description="When the voice sample was created")
    updated_at: datetime = Field(..., description="When the voice sample was last updated")

    class Config:
        """Configuration for VoiceSample model."""
        orm_mode = True


class VoiceSampleList(BaseModel):
    """Schema for a list of voice samples."""
    items: List[VoiceSample] = Field(..., description="List of voice samples")
    total: int = Field(..., description="Total number of voice samples")