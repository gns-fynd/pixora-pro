"""
Authentication-related API endpoints
"""
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel

from app.auth.jwt import create_access_token
from app.auth.supabase import verify_supabase_token
from app.services.supabase import SupabaseService

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    authorization: Optional[str] = Header(None),
    supabase_service: SupabaseService = Depends()
) -> TokenResponse:
    """
    Exchange a Supabase token for a backend token
    
    Args:
        authorization: Authorization header with Supabase token
        
    Returns:
        Backend access token
        
    Raises:
        HTTPException: If token is invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    
    # Extract token from header
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    
    # Verify Supabase token
    token_data = await verify_supabase_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user_id = token_data["user_id"]
    email = token_data["email"]
    
    # Ensure user profile exists
    user = await supabase_service.get_user(user_id)
    if not user:
        # Create a default profile for the user
        name = token_data.get("name", "")
        default_user_data = {
            "id": user_id,
            "email": email or f"user_{user_id}@example.com",  # Use email from token or generate a default
            "full_name": name,  # Use name from token
            "username": "",
            "avatar_url": "",
            "credits": 10  # Default credits
        }
        await supabase_service.create_user(default_user_data)
    
    # Create backend token with email and name included
    access_token = create_access_token(data={"sub": user_id, "email": email, "name": token_data.get("name", "")})
    
    return TokenResponse(access_token=access_token)
