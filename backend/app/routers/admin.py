"""
Admin router for the Pixora AI platform.

This module provides API endpoints for admin operations.
"""
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.auth.jwt import get_current_user, get_admin_user
from app.schemas.user import UserResponse as User
from app.services.credits import CreditService
from app.services.supabase import SupabaseClient, get_supabase_client


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)


class UserListResponse(BaseModel):
    """
    Response model for user list.
    """
    id: str = Field(..., description="The user ID")
    email: str = Field(..., description="The user's email")
    name: Optional[str] = Field(None, description="The user's name")
    avatar_url: Optional[str] = Field(None, description="The user's avatar URL")
    credits: int = Field(0, description="The user's credit balance")
    created_at: str = Field(..., description="The user's creation timestamp")


class CreditAdjustmentRequest(BaseModel):
    """
    Request model for credit adjustment.
    """
    user_id: str = Field(..., description="The user ID")
    amount: int = Field(..., description="The amount to adjust (positive to add, negative to deduct)")
    reason: str = Field(..., description="The reason for the adjustment")


class VoiceModel(BaseModel):
    """
    Model for a voice.
    """
    id: str = Field(..., description="The voice ID")
    name: str = Field(..., description="The voice name")
    gender: str = Field(..., description="The voice gender (male, female, neutral)")
    tone: str = Field(..., description="The voice tone (professional, casual, energetic, etc.)")
    preview_url: str = Field(..., description="URL to a preview audio file")
    is_default: bool = Field(False, description="Whether this is a default voice")


class VoiceCreateRequest(BaseModel):
    """
    Request model for voice creation.
    """
    name: str = Field(..., description="The voice name")
    gender: str = Field(..., description="The voice gender (male, female, neutral)")
    tone: str = Field(..., description="The voice tone (professional, casual, energetic, etc.)")
    audio_url: str = Field(..., description="URL to the source audio file for cloning")
    is_default: bool = Field(False, description="Whether this should be a default voice")


@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    current_user: User = Depends(get_admin_user),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
):
    """
    List all users.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Get all users from Supabase
        response = await supabase_client.table("profiles").select("*").execute()
        
        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching users: {response['error']}"
            )
        
        # Format the response
        users = []
        for user_data in response.data:
            # Get the user's auth data
            auth_response = await supabase_client.auth.admin.get_user_by_id(user_data["id"])
            
            if "error" in auth_response:
                logger.error(f"Error fetching auth data for user {user_data['id']}: {auth_response['error']}")
                continue
            
            # Combine profile and auth data
            user = {
                "id": user_data["id"],
                "email": auth_response.user.email,
                "name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
                "credits": user_data.get("credits", 0),
                "created_at": auth_response.user.created_at,
            }
            
            users.append(user)
        
        return users
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserListResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_admin_user),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
):
    """
    Get a user by ID.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Get the user's profile from Supabase
        profile_response = await supabase_client.table("profiles").select("*").eq("id", user_id).execute()
        
        if "error" in profile_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching user profile: {profile_response['error']}"
            )
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = profile_response.data[0]
        
        # Get the user's auth data
        auth_response = await supabase_client.auth.admin.get_user_by_id(user_id)
        
        if "error" in auth_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching user auth data: {auth_response['error']}"
            )
        
        # Combine profile and auth data
        user = {
            "id": user_data["id"],
            "email": auth_response.user.email,
            "name": user_data.get("name"),
            "avatar_url": user_data.get("avatar_url"),
            "credits": user_data.get("credits", 0),
            "created_at": auth_response.user.created_at,
        }
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.post("/credits", response_model=Dict[str, Any])
async def adjust_credits(
    request: CreditAdjustmentRequest,
    current_user: User = Depends(get_admin_user),
    credit_service: CreditService = Depends(),
):
    """
    Adjust a user's credits.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Check if the amount is positive or negative
        if request.amount > 0:
            # Add credits
            await credit_service.add_credits(
                user_id=request.user_id,
                amount=request.amount,
                reason=f"Admin adjustment: {request.reason}"
            )
        elif request.amount < 0:
            # Deduct credits
            await credit_service.deduct_credits(
                user_id=request.user_id,
                amount=abs(request.amount),
                reason=f"Admin adjustment: {request.reason}"
            )
        
        # Get the updated credit balance
        balance = await credit_service.get_credit_balance(request.user_id)
        
        return {
            "user_id": request.user_id,
            "credits": balance,
            "adjustment": request.amount,
            "reason": request.reason
        }
        
    except Exception as e:
        logger.error(f"Error adjusting credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to adjust credits: {str(e)}"
        )


@router.get("/voices", response_model=List[VoiceModel])
async def list_voices(
    current_user: User = Depends(get_admin_user),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
):
    """
    List all voice models.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Get all voices from Supabase
        response = await supabase_client.table("voices").select("*").execute()
        
        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching voices: {response['error']}"
            )
        
        return response.data
        
    except Exception as e:
        logger.error(f"Error listing voices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list voices: {str(e)}"
        )


@router.post("/voices", response_model=VoiceModel)
async def create_voice(
    request: VoiceCreateRequest,
    current_user: User = Depends(get_admin_user),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new voice model.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Import the text-to-speech service
        from app.services.fal_ai import TextToSpeechService, VoiceCloneRequest
        from app.services.storage import StorageManager
        
        # Create the service
        storage_manager = StorageManager(settings)
        tts_service = TextToSpeechService(storage_manager=storage_manager, settings=settings)
        
        # Clone the voice
        voice_request = VoiceCloneRequest(
            audio_url=request.audio_url,
            noise_reduction=True,
            volume_normalization=True
        )
        
        voice_response = await tts_service.clone_voice(
            request=voice_request,
            user_id=current_user.id
        )
        
        # Create a preview audio
        from app.services.fal_ai import TextToSpeechRequest
        
        preview_request = TextToSpeechRequest(
            text="This is a preview of the voice that will be used for your video narration.",
            voice_id=voice_response.voice_id,
            speed=1.0
        )
        
        preview_response = await tts_service.generate_speech(
            request=preview_request,
            user_id=current_user.id
        )
        
        # Create the voice in the database
        voice_data = {
            "id": voice_response.voice_id,
            "name": request.name,
            "gender": request.gender,
            "tone": request.tone,
            "preview_url": preview_response.audio_url,
            "is_default": request.is_default
        }
        
        # Insert the voice into Supabase
        response = await supabase_client.table("voices").insert(voice_data).execute()
        
        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating voice: {response['error']}"
            )
        
        return voice_data
        
    except Exception as e:
        logger.error(f"Error creating voice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create voice: {str(e)}"
        )


@router.delete("/voices/{voice_id}", response_model=Dict[str, Any])
async def delete_voice(
    voice_id: str,
    current_user: User = Depends(get_admin_user),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
):
    """
    Delete a voice model.
    
    This endpoint is only accessible to admin users.
    """
    try:
        # Delete the voice from Supabase
        response = await supabase_client.table("voices").delete().eq("id", voice_id).execute()
        
        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting voice: {response['error']}"
            )
        
        return {
            "id": voice_id,
            "deleted": True
        }
        
    except Exception as e:
        logger.error(f"Error deleting voice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete voice: {str(e)}"
        )
