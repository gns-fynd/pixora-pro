"""
Authentication API for Pixora AI Video Creation Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime, timedelta

# Import services
from ..services.auth import auth_service
from ..services.supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Security scheme
security = HTTPBearer(auto_error=False)

# Constants
AUTH_COOKIE_NAME = "pixora_auth_token"
AUTH_EXPIRY_COOKIE_NAME = "pixora_auth_expiry"

# Models
class TokenExchangeRequest(BaseModel):
    token: str

class TokenResponse(BaseModel):
    success: bool
    expires_at: Optional[int] = None
    expires_in: Optional[int] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

# Token exchange endpoint
@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    request: Optional[TokenExchangeRequest] = None,
    response: Response = Response(),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Exchange a Supabase JWT token for a session token.
    This allows the client to authenticate with our WebSocket connections.
    
    The token can be provided either in the request body or as a Bearer token in the Authorization header.
    The session token is set as an HTTP-only cookie.
    """
    try:
        # Get the token from either the request body or the Authorization header
        token = None
        if request and hasattr(request, 'token'):
            token = request.token
            logger.debug("Using token from request body")
        elif credentials:
            token = credentials.credentials
            logger.debug("Using token from Authorization header")
        
        if not token:
            logger.warning("No token provided in request")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"success": False, "error": "No token provided. Please provide a token in the request body or as a Bearer token."}
        
        # Log token length for debugging (don't log the actual token for security)
        logger.debug(f"Token received, length: {len(token)}")
        
        # Verify the Supabase token
        user_data = await auth_service.verify_supabase_token(token)
        
        if not user_data:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"success": False, "error": "Invalid token"}
        
        # Create a session token for WebSocket authentication
        session_token = auth_service.create_session_token(user_data)
        
        if not session_token:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"success": False, "error": "Failed to create session token"}
        
        # Get the expiry timestamp
        expiry_timestamp = auth_service.get_expiry_timestamp(session_token)
        expiry_date = datetime.utcfromtimestamp(expiry_timestamp) if expiry_timestamp else datetime.utcnow() + timedelta(hours=1)
        
        # Instead of using datetime objects, use max_age in seconds to avoid datetime issues
        max_age = int(expiry_timestamp - time.time()) if expiry_timestamp else 3600
        logger.debug(f"Setting cookies with max_age: {max_age} seconds")
        
        # Set HTTP-only cookie using max_age instead of expires
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=max_age,
            path="/"
        )
        
        # Also set a non-httpOnly cookie for expiry time (for UI purposes)
        response.set_cookie(
            key=AUTH_EXPIRY_COOKIE_NAME,
            value=str(expiry_timestamp),
            httponly=False,
            secure=True,
            samesite="strict",
            max_age=max_age,
            path="/"
        )
        
        # Calculate expires_in in seconds
        expires_in = (expiry_timestamp - int(time.time())) if expiry_timestamp else 3600
        
        return {
            "success": True,
            "expires_at": expiry_timestamp,
            "expires_in": expires_in
        }
    except Exception as e:
        logger.error(f"Token exchange error: {str(e)}")
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"success": False, "error": f"Invalid token: {str(e)}"}

# Logout endpoint
@router.post("/logout")
async def logout(response: Response):
    """
    Logout the user by clearing the auth cookies.
    """
    # Clear the auth cookies
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/"
    )
    response.delete_cookie(
        key=AUTH_EXPIRY_COOKIE_NAME,
        path="/"
    )
    
    return {"success": True}

# Dependency for getting the authenticated user
async def get_current_user(
    request: Request,
    auth_token: Optional[str] = Cookie(None, alias=AUTH_COOKIE_NAME),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Get the authenticated user from the session token.
    First checks for a cookie, then falls back to the Authorization header.
    
    Args:
        request: The request object
        auth_token: The auth token cookie
        credentials: HTTP Authorization credentials
        
    Returns:
        Dict[str, Any]: User data
        
    Raises:
        HTTPException: If the token is invalid
    """
    token = None
    
    # First try to get the token from the cookie
    if auth_token:
        token = auth_token
    # Then try to get it from the Authorization header
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Verify the session token
        payload = auth_service.verify_session_token(token)
        
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

# User info endpoint
@router.get("/me", response_model=UserResponse)
async def get_user_info(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get information about the authenticated user.
    """
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name")
    }
