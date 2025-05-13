"""
Authentication service for Pixora AI Video Creation Platform
"""
import os
import time
from typing import Dict, Any, Optional
import logging
import jwt
from datetime import datetime, timedelta

# Import Supabase service
from .supabase import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

class AuthService:
    """
    Service for handling authentication.
    """
    
    def __init__(self):
        """Initialize the authentication service."""
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
        
        if not self.jwt_secret:
            logger.warning("JWT secret not set. Authentication will not work.")
    
    def create_session_token(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a session token for a user.
        
        Args:
            user_data: User data to include in the token
            
        Returns:
            Optional[str]: Session token, or None if token creation failed
        """
        if not self.jwt_secret:
            logger.warning("JWT secret not set. Cannot create session token.")
            return None
        
        try:
            # Create the token payload
            payload = {
                "sub": user_data["id"],
                "email": user_data.get("email", ""),
                "name": user_data.get("user_metadata", {}).get("full_name", ""),
                "exp": datetime.utcnow() + timedelta(minutes=self.jwt_expiration_minutes),
                "iat": datetime.utcnow()
            }
            
            # Create the token
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.info(f"Created session token for user: {user_data['id']}")
            
            return token
        except Exception as e:
            logger.error(f"Error creating session token: {str(e)}")
            return None
    
    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session token.
        
        Args:
            token: Session token to verify
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if the token is valid, None otherwise
        """
        if not self.jwt_secret:
            logger.warning("JWT secret not set. Cannot verify session token.")
            return None
        
        try:
            # Verify the token with more lenient options
            # Skip audience validation which is causing issues
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm],
                options={
                    "verify_aud": False,  # Skip audience validation
                    "verify_signature": True,  # Still verify the signature
                    "verify_exp": True,  # Still verify expiration
                }
            )
            
            logger.debug(f"Verified session token for user: {payload['sub']}")
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying session token: {str(e)}")
            return None
    
    def get_expiry_timestamp(self, token: str) -> Optional[int]:
        """
        Get the expiry timestamp of a token.
        
        Args:
            token: Token to get the expiry timestamp for
            
        Returns:
            Optional[int]: Expiry timestamp in seconds since the epoch, or None if the token is invalid
        """
        if not self.jwt_secret:
            logger.warning("JWT secret not set. Cannot get expiry timestamp.")
            return None
        
        try:
            # Decode the token without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Return the expiry timestamp
            return payload.get("exp")
        except Exception as e:
            logger.error(f"Error getting expiry timestamp: {str(e)}")
            return None
    
    async def verify_supabase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Supabase JWT token.
        
        Args:
            token: Supabase JWT token to verify
            
        Returns:
            Optional[Dict[str, Any]]: User data if the token is valid, None otherwise
        """
        # Verify the token using the Supabase service
        user_data = supabase_service.verify_token(token)
        
        if not user_data:
            logger.warning("Invalid Supabase token")
            return None
        
        logger.info(f"Verified Supabase token for user: {user_data['id']}")
        
        return user_data

# Create a global instance of the authentication service
auth_service = AuthService()
