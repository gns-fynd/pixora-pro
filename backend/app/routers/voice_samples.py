"""
Voice samples router.

This module provides API endpoints for managing voice samples.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query

from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User
from app.schemas.voice_sample import (
    VoiceSample,
    VoiceSampleCreate,
    VoiceSampleUpdate,
    VoiceSampleList,
)
from app.services.voice_sample import VoiceSampleService


router = APIRouter(
    prefix="/voice-samples",
    tags=["voice-samples"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=VoiceSample)
async def create_voice_sample(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    tone: Optional[str] = Form(None),
    is_default: bool = Form(False),
    is_public: bool = Form(False),
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: VoiceSampleService = Depends(),
):
    """
    Create a new voice sample.

    This endpoint uploads a voice sample audio file and creates a record in the database.
    The audio file must be in a common audio format (MP3, WAV, OGG).
    """
    # Validate the file type
    if audio_file.content_type not in ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file (MP3, WAV, OGG)",
        )

    # Create voice sample data
    data = VoiceSampleCreate(
        name=name,
        description=description,
        gender=gender,
        tone=tone,
        is_default=is_default,
        is_public=is_public,
    )

    # Create the voice sample
    voice_sample = await service.create_voice_sample(
        data=data,
        audio_file=audio_file,
        user_id=current_user.id,
    )

    return voice_sample


@router.get("/", response_model=VoiceSampleList)
async def get_voice_samples(
    include_public: bool = Query(True, description="Whether to include public voice samples"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    tone: Optional[str] = Query(None, description="Filter by tone"),
    limit: int = Query(100, description="Maximum number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    current_user: User = Depends(get_current_user),
    service: VoiceSampleService = Depends(),
):
    """
    Get voice samples.
    
    Returns voice samples owned by the current user and optionally public samples.
    """
    return await service.get_voice_samples(
        user_id=current_user.id,
        include_public=include_public,
        gender=gender,
        tone=tone,
        limit=limit,
        offset=offset,
    )


@router.get("/public", response_model=VoiceSampleList)
async def get_public_voice_samples(
    gender: Optional[str] = Query(None, description="Filter by gender"),
    tone: Optional[str] = Query(None, description="Filter by tone"),
    limit: int = Query(100, description="Maximum number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    service: VoiceSampleService = Depends(),
):
    """
    Get public voice samples.
    
    Returns all public voice samples. This endpoint doesn't require authentication.
    """
    return await service.get_voice_samples(
        user_id=None,
        include_public=True,
        gender=gender,
        tone=tone,
        limit=limit,
        offset=offset,
    )


@router.get("/{voice_sample_id}", response_model=VoiceSample)
async def get_voice_sample(
    voice_sample_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: VoiceSampleService = Depends(),
):
    """
    Get a voice sample by ID.
    
    Returns a voice sample by ID if it belongs to the current user or is public.
    """
    return await service.get_voice_sample(
        voice_sample_id=voice_sample_id,
        user_id=current_user.id,
    )


@router.put("/{voice_sample_id}", response_model=VoiceSample)
async def update_voice_sample(
    voice_sample_id: uuid.UUID,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    tone: Optional[str] = Form(None),
    is_default: Optional[bool] = Form(None),
    is_public: Optional[bool] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    service: VoiceSampleService = Depends(),
):
    """
    Update a voice sample.
    
    Updates a voice sample by ID if it belongs to the current user.
    """
    # Validate the file type if provided
    if audio_file and audio_file.content_type not in ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file (MP3, WAV, OGG)",
        )

    # Update data
    data = VoiceSampleUpdate(
        name=name,
        description=description,
        gender=gender,
        tone=tone,
        is_default=is_default,
        is_public=is_public,
    )

    # Update the voice sample
    return await service.update_voice_sample(
        voice_sample_id=voice_sample_id,
        data=data,
        user_id=current_user.id,
        audio_file=audio_file,
    )


@router.delete("/{voice_sample_id}")
async def delete_voice_sample(
    voice_sample_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: VoiceSampleService = Depends(),
):
    """
    Delete a voice sample.
    
    Deletes a voice sample by ID if it belongs to the current user.
    """
    return await service.delete_voice_sample(
        voice_sample_id=voice_sample_id,
        user_id=current_user.id,
    )