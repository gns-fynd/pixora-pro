"""
Users API for Pixora AI Video Creation Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Import services
from ..services.auth import auth_service
from ..services.supabase import supabase_service
from .auth import get_current_user, AUTH_COOKIE_NAME

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/users", tags=["users"])

# Security scheme
security = HTTPBearer(auto_error=False)

# Models
class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    credits: int = 0

class CreditsResponse(BaseModel):
    credits: int

# Get current user endpoint
@router.get("/me", response_model=UserResponse)
async def get_user_info(
    user_data: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get information about the authenticated user.
    """
    try:
        # Get the user ID from the user data
        user_id = user_data["id"]
        
        # Get the user from Supabase
        supabase_user = supabase_service.get_user(user_id)
        
        if not supabase_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return the user info
        return {
            "id": user_id,
            "email": user_data.get("email", ""),
            "name": user_data.get("name", ""),
            "credits": supabase_user.get("credits", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Get user credits endpoint
@router.get("/me/credits", response_model=CreditsResponse)
async def get_user_credits(
    user_data: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the credits for the authenticated user.
    """
    try:
        # Get the user ID from the user data
        user_id = user_data["id"]
        
        # Get the user's credits from Supabase
        supabase_user = supabase_service.get_user(user_id)
        
        if not supabase_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return the credits
        return {
            "credits": supabase_user.get("credits", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Update user credits endpoint
@router.post("/me/credits", response_model=CreditsResponse)
async def update_user_credits(
    request: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the credits for the authenticated user.
    """
    try:
        # Get the user ID from the user data
        user_id = user_data["id"]
        
        # Get the credits from the request
        credits = request.get("credits")
        
        if credits is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credits field is required"
            )
        
        # Update the user's credits in Supabase
        updated_user = supabase_service.update_user_credits(user_id, credits)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update credits"
            )
        
        # Return the updated credits
        return {
            "credits": updated_user.get("credits", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
