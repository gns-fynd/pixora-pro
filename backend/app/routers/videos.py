"""
Video-related API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt import get_current_user_id
from app.services.supabase import SupabaseService

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/")
async def get_videos(
    current_user_id: str = Depends(get_current_user_id),
    supabase_service: SupabaseService = Depends(),
) -> List[dict]:
    """
    Get user's videos
    
    Args:
        current_user_id: Current user ID from token
        supabase_service: Supabase service
        
    Returns:
        List of user's videos
    """
    # This is a placeholder implementation
    # In a real implementation, we would fetch videos from Supabase
    return [
        {
            "id": "1",
            "title": "Sample Video",
            "description": "This is a sample video",
            "status": "completed",
            "created_at": "2025-04-21T12:00:00Z",
            "user_id": current_user_id,
        }
    ]


@router.get("/{video_id}")
async def get_video(
    video_id: str,
    current_user_id: str = Depends(get_current_user_id),
    supabase_service: SupabaseService = Depends(),
) -> dict:
    """
    Get video by ID
    
    Args:
        video_id: Video ID
        current_user_id: Current user ID from token
        supabase_service: Supabase service
        
    Returns:
        Video data
        
    Raises:
        HTTPException: If video not found or not authorized
    """
    # This is a placeholder implementation
    # In a real implementation, we would fetch the video from Supabase
    # and check if the user has access to it
    
    # Simulate video not found
    if video_id != "1":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    
    return {
        "id": video_id,
        "title": "Sample Video",
        "description": "This is a sample video",
        "status": "completed",
        "created_at": "2025-04-21T12:00:00Z",
        "user_id": current_user_id,
    }
