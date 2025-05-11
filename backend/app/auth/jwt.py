"""
JWT authentication utilities for validating Supabase tokens
"""
import os
import logging
from typing import Dict, Any, Optional, TypedDict
from datetime import datetime, timedelta

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from app.schemas.user import UserResponse as User
from app.services.supabase import SupabaseService
from app.core.config import Settings

# Set up logging
logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()


class TokenData(TypedDict):
    """Type definition for token data"""
    sub: str
    email: Optional[str]
    name: Optional[str]
    exp: int
    aud: str


class TokenPayload(BaseModel):
    """Pydantic model for token payload validation"""
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    exp: int
    aud: str = "authenticated"


def get_jwt_secret() -> str:
    """
    Get the JWT secret from environment variables
    
    Returns:
        The JWT secret
        
    Raises:
        ValueError: If JWT secret is not set
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable is not set")
    return jwt_secret


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        The encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 24 hours instead of 30 minutes to reduce "Signature has expired" errors
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    
    # Debug: Print the token data
    print("Creating token with data:", to_encode)
    
    # Get the JWT secret
    jwt_secret = get_jwt_secret()
    
    # Create the token
    encoded_jwt = jwt.encode(to_encode, jwt_secret, algorithm="HS256")
    return encoded_jwt


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    Validate a JWT token from the Authorization header
    
    Args:
        credentials: The HTTP Authorization credentials
        
    Returns:
        Dictionary with user ID and claims
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        # Get the JWT secret
        jwt_secret = get_jwt_secret()
        
        # Decode and validate the token
        payload = jwt.decode(
            token, 
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Validate payload with Pydantic
        token_data = TokenPayload(**payload)
        
        # Return the validated token data
        return TokenData(
            sub=token_data.sub,
            email=token_data.email,
            name=token_data.name,
            exp=token_data.exp,
            aud=token_data.aud
        )
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        logger.error(f"JWT secret error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error",
        )


async def get_current_user_id(
    token_data: TokenData = Depends(validate_token)
) -> str:
    """
    Extract the user ID from the token data
    
    Args:
        token_data: The validated token data
        
    Returns:
        The user ID
    """
    return token_data["sub"]


async def get_current_user(
    token_data: TokenData = Depends(validate_token),
    supabase_service: SupabaseService = Depends(),
) -> User:
    """
    Get the current user from the token data
    
    Args:
        token_data: The validated token data
        supabase_service: The Supabase service
        
    Returns:
        The current user
        
    Raises:
        HTTPException: If user not found
    """
    user_id = token_data["sub"]
    user_data = await supabase_service.get_user(user_id)
    
    if not user_data:
        # Create a default profile for the user if it doesn't exist
        email = token_data.get("email", "")
        if not email:
            # Generate a default email if not provided in the token
            email = f"user_{user_id}@example.com"
        
        # Get name from token
        name = token_data.get("name", "")
            
        default_user_data = {
            "id": user_id,
            "email": email,  # Use email from token or generated default
            "username": "",
            "full_name": name,  # Use name from token
            "avatar_url": "",
            "credits": 10  # Default credits
        }
        user_data = await supabase_service.create_user(default_user_data)
        
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User not found and could not be created",
            )
    
    # Create a User object from the user data
    user = User(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data.get("full_name", ""),
        avatar_url=user_data.get("avatar_url", ""),
        role="user",  # Default role since it's not in the schema
        credits=user_data.get("credits", 0),
    )
    
    return user


async def get_current_user_ws(token: str, settings: Settings) -> User:
    """
    Authenticate a WebSocket connection.
    
    Args:
        token: The JWT token
        settings: Application settings
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Validate the token
        token_data = await validate_token(token)
        
        # Get the user ID
        user_id = token_data["sub"]
        
        # Get the user from Supabase
        supabase_service = SupabaseService()
        user_data = await supabase_service.get_user(user_id)
        
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Create a User object
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("full_name", ""),
            avatar_url=user_data.get("avatar_url", ""),
            role="user",
            credits=user_data.get("credits", 0),
        )
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )
