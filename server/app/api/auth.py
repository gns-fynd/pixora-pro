"""
Authentication API for Pixora AI Video Creation Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Import services
from ..services.auth import auth_service
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Security scheme
security = HTTPBearer()

# Models
class TokenExchangeRequest(BaseModel):
    token: str

class TokenResponse(BaseModel):
    session_token: str
    expires_at: int

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

# Token exchange endpoint
@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    request: Optional[TokenExchangeRequest] = None,
    response: Response = Response(),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """
    Exchange a Supabase JWT token for a session token.
    This allows the client to authenticate with our WebSocket connections.
    
    The token can be provided either in the request body or as a Bearer token in the Authorization header.
    """
    try:
        # Get the token from either the request body or the Authorization header
        token = None
        if request and hasattr(request, 'token'):
            token = request.token
        elif credentials:
            token = credentials.credentials
        
        if not token:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"error": "No token provided. Please provide a token in the request body or as a Bearer token."}
        
        # Verify the Supabase token
        user_data = await auth_service.verify_supabase_token(token)
        
        if not user_data:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"error": "Invalid token"}
        
        # Create a session token for WebSocket authentication
        session_token = auth_service.create_session_token(user_data)
        
        if not session_token:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"error": "Failed to create session token"}
        
        # Get the expiry timestamp
        expires_at = auth_service.get_expiry_timestamp(session_token)
        
        return {
            "session_token": session_token,
            "expires_at": expires_at
        }
    except Exception as e:
        logger.error(f"Token exchange error: {str(e)}")
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Invalid token"}

# User info endpoint
@router.get("/me", response_model=UserResponse)
async def get_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get information about the authenticated user.
    """
    try:
        # Verify the session token
        payload = auth_service.verify_session_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Return the user info
        return {
            "id": payload["sub"],
            "email": payload["email"],
            "name": payload.get("name")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Dependency for getting the authenticated user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get the authenticated user from the session token.
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Dict[str, Any]: User data
        
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        # Verify the session token
        payload = auth_service.verify_session_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Return the user data
        return {
            "id": payload["sub"],
            "email": payload["email"],
            "name": payload.get("name")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
