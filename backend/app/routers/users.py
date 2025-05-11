"""
User-related API endpoints
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4

from app.auth.jwt import get_current_user, get_current_user_id, TokenData, validate_token
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.user import UserResponse as User
from app.services.supabase import SupabaseService
from app.services import CreditService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token_data: TokenData = Depends(validate_token),
    supabase_service: SupabaseService = Depends(),
) -> UserResponse:
    """
    Get current user profile
    
    Args:
        token_data: Validated token data
        supabase_service: Supabase service
        
    Returns:
        Current user profile
        
    Raises:
        HTTPException: If user not found
    """
    user_id = token_data["sub"]
    user = await supabase_service.get_user(user_id)
    
    if not user:
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
        user = await supabase_service.create_user(default_user_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found and could not be created",
            )
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("full_name", ""),
        avatar_url=user.get("avatar_url", ""),
        role="user",  # Default role since it's not in the schema
        credits=user.get("credits", 0),
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user_id: str = Depends(get_current_user_id),
    supabase_service: SupabaseService = Depends(),
) -> UserResponse:
    """
    Update user profile
    
    Args:
        user_id: User ID to update
        user_update: User data to update
        current_user_id: Current user ID from token
        supabase_service: Supabase service
        
    Returns:
        Updated user profile
        
    Raises:
        HTTPException: If user not found or not authorized
    """
    # Check if user is updating their own profile
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    
    # Get current user data
    user = await supabase_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update user data
    update_data = user_update.model_dump(exclude_unset=True)
    updated_user = await supabase_service.update_user(user_id, update_data)
    
    # Check if update was successful
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile",
        )
    
    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        name=updated_user.get("full_name", ""),
        avatar_url=updated_user.get("avatar_url", ""),
        role="user",  # Default role since it's not in the schema
        credits=updated_user.get("credits", 0),
    )


@router.get("/me/credits")
async def get_credits(
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(),
):
    """
    Get current user's credit balance
    
    Args:
        current_user: Current user
        credit_service: Credit service
        
    Returns:
        Credit balance
    """
    credits = await credit_service.get_credit_balance(current_user.id)
    return {"credits": credits}


@router.post("/me/credits")
async def add_credits(
    amount: int,
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(),
):
    """
    Add credits to current user's account (for testing purposes)
    
    Args:
        amount: Amount of credits to add
        current_user: Current user
        credit_service: Credit service
        
    Returns:
        New credit balance
    """
    # This endpoint is for testing purposes only
    # In a real application, credits would be added through a payment system
    new_balance = await credit_service.add_credits(
        user_id=current_user.id,
        amount=amount,
        reason="Manual credit addition (testing)"
    )
    return {"credits": new_balance}
