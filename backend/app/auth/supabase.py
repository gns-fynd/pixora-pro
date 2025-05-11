"""
Supabase JWT authentication utilities
"""
import logging
from typing import Dict, Any, Optional

from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError

from app.core.config import get_settings
from app.services.supabase import SupabaseService

settings = get_settings()
logger = logging.getLogger(__name__)


async def verify_supabase_token(token: str) -> Optional[Dict[str, str]]:
    """
    Verify a Supabase JWT token and extract the user ID and email
    
    Args:
        token: Supabase JWT token
        
    Returns:
        Dictionary with user ID and email if token is valid, None otherwise
    """
    try:
        # Get the JWT secret from Supabase
        jwt_secret = settings.SUPABASE_JWT_SECRET
        
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET is not set in environment variables")
            return None
        
        # Decode and validate the token
        payload = jwt.decode(
            token, 
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Debug: Print the entire payload to see its structure
        print("Token payload:", payload)
        
        # Extract user ID from the token
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            return None
        
        # Extract email from the token
        # Try different possible locations for the email
        email = None
        
        # Check standard location
        if "email" in payload:
            email = payload["email"]
        # Check user metadata
        elif "user_metadata" in payload and "email" in payload["user_metadata"]:
            email = payload["user_metadata"]["email"]
        # Check app metadata
        elif "app_metadata" in payload and "email" in payload["app_metadata"]:
            email = payload["app_metadata"]["email"]
        
        print(f"Extracted email from token: {email}")
        
        # If still no email, use a default with the user ID to make it unique
        if not email:
            email = f"user_{user_id}@example.com"
            print(f"Using default email: {email}")
        
        # Extract name from the token
        name = None
        
        # Check user metadata for name or full_name
        if "user_metadata" in payload:
            if "name" in payload["user_metadata"]:
                name = payload["user_metadata"]["name"]
            elif "full_name" in payload["user_metadata"]:
                name = payload["user_metadata"]["full_name"]
            elif "preferred_username" in payload["user_metadata"]:
                name = payload["user_metadata"]["preferred_username"]
        
        # Check standard location
        if not name and "name" in payload:
            name = payload["name"]
        
        print(f"Extracted name from token: {name}")
        
        # Return user ID, email, and name
        return {
            "user_id": user_id,
            "email": email,
            "name": name
        }
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        return None


async def validate_supabase_token(request: Request) -> Dict[str, Any]:
    """
    Validate a Supabase JWT token from the Authorization header
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with user ID and email
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.replace("Bearer ", "")
    try:
        # Get the JWT secret from Supabase
        # Note: This needs to be the JWT secret from Supabase project settings
        jwt_secret = settings.SUPABASE_JWT_SECRET
        
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET is not set in environment variables")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error",
            )
        
        # Decode and validate the token
        payload = jwt.decode(
            token, 
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Debug: Print the entire payload to see its structure
        print("Validate token payload:", payload)
        
        # Extract user ID from the token
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract email from the token
        # Try different possible locations for the email
        email = None
        
        # Check standard location
        if "email" in payload:
            email = payload["email"]
        # Check user metadata
        elif "user_metadata" in payload and "email" in payload["user_metadata"]:
            email = payload["user_metadata"]["email"]
        # Check app metadata
        elif "app_metadata" in payload and "email" in payload["app_metadata"]:
            email = payload["app_metadata"]["email"]
        
        print(f"Validate token - extracted email: {email}")
        
        # Extract name from the token
        name = None
        
        # Check user metadata for name or full_name
        if "user_metadata" in payload:
            if "name" in payload["user_metadata"]:
                name = payload["user_metadata"]["name"]
            elif "full_name" in payload["user_metadata"]:
                name = payload["user_metadata"]["full_name"]
            elif "preferred_username" in payload["user_metadata"]:
                name = payload["user_metadata"]["preferred_username"]
        
        # Check standard location
        if not name and "name" in payload:
            name = payload["name"]
        
        print(f"Validate token - extracted name: {name}")
            
        return {
            "sub": user_id,
            "email": email,
            "name": name,
            "exp": payload.get("exp")
        }
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_supabase(
    token_data: Dict[str, Any] = Depends(validate_supabase_token),
    supabase_service: SupabaseService = Depends(SupabaseService)
) -> Dict[str, Any]:
    """
    Get the current user from a Supabase token
    
    Args:
        token_data: Token data from validate_supabase_token
        supabase_service: Supabase service for fetching user data
        
    Returns:
        User data from Supabase
        
    Raises:
        HTTPException: If user not found
    """
    try:
        user = await supabase_service.get_user(token_data["sub"])
        
        if not user:
            # If user doesn't exist in our database but has a valid token,
            # create a profile for them (handles OAuth users)
            logger.info(f"Creating new user profile for {token_data['sub']}")
            user_data = {
                "id": token_data["sub"],
                "email": token_data.get("email", ""),
                "full_name": token_data.get("name", ""),  # Use name from token
                "credits": 10  # Initial credits
            }
            user = await supabase_service.create_user(user_data)
            
        return user
    except Exception as e:
        logger.error(f"Error fetching user {token_data['sub']}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {str(e)}",
        )
