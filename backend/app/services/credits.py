"""
Credit management service.

This module provides a service for managing user credits.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.supabase import SupabaseService, SupabaseClient, get_supabase_client
import uuid

# Set up logging
logger = logging.getLogger(__name__)


class CreditService:
    """
    Service for managing user credits.
    """
    
    def __init__(
        self, 
        supabase_service: SupabaseService = Depends(),
        supabase: SupabaseClient = Depends(get_supabase_client),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the credit service.
        
        Args:
            supabase_service: The Supabase service
            supabase: The Supabase client
            settings: Application settings
        """
        self.supabase_service = supabase_service
        self.supabase = supabase
        self.settings = settings
    
    # Compatibility method for old code using get_credits()
    async def get_credits(self, user_id: str) -> int:
        """
        Get the current credit balance for a user (compatibility method).
        
        Args:
            user_id: The user ID
            
        Returns:
            The credit balance
        """
        return await self.get_credit_balance(user_id)
    
    async def get_credit_balance(self, user_id: str) -> int:
        """
        Get the credit balance for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            The credit balance
        """
        try:
            # Get the user's credit balance
            credits = await self.supabase_service.get_user_credits(user_id)
            
            logger.info(f"Retrieved credit balance for user {user_id}: {credits}")
            return credits
            
        except Exception as e:
            logger.error(f"Error getting credit balance for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get credit balance: {str(e)}"
            )
    
    async def add_credits(self, user_id: str, amount: int, reason: str) -> int:
        """
        Add credits to a user's account.
        
        Args:
            user_id: The user ID
            amount: The amount of credits to add
            reason: The reason for adding credits
            
        Returns:
            The new credit balance
        """
        try:
            # Get the current credit balance
            current_credits = await self.get_credit_balance(user_id)
            
            # Calculate the new balance
            new_balance = current_credits + amount
            
            # Update the user's credit balance
            await self.supabase_service.update_user_credits(user_id, new_balance)
            
            # Log the transaction
            await self._log_transaction(user_id, amount, reason)
            
            logger.info(f"Added {amount} credits to user {user_id}. New balance: {new_balance}")
            return new_balance
            
        except Exception as e:
            logger.error(f"Error adding credits for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add credits: {str(e)}"
            )
    
    async def deduct_credits(self, user_id: str, amount: int, reason: str) -> int:
        """
        Deduct credits from a user's account.
        
        Args:
            user_id: The user ID
            amount: The amount of credits to deduct
            reason: The reason for deducting credits
            
        Returns:
            The new credit balance
        """
        try:
            # Get the current credit balance
            current_credits = await self.get_credit_balance(user_id)
            
            # Check if the user has enough credits
            if current_credits < amount:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. Required: {amount}, Available: {current_credits}"
                )
            
            # Calculate the new balance
            new_balance = current_credits - amount
            
            # Update the user's credit balance
            await self.supabase_service.update_user_credits(user_id, new_balance)
            
            # Log the transaction
            await self._log_transaction(user_id, -amount, reason)
            
            logger.info(f"Deducted {amount} credits from user {user_id}. New balance: {new_balance}")
            return new_balance
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error deducting credits for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deduct credits: {str(e)}"
            )
    
    async def _log_transaction(self, user_id: str, amount: int, reason: str) -> None:
        """
        Log a credit transaction.
        
        Args:
            user_id: The user ID
            amount: The amount of credits (positive for additions, negative for deductions)
            reason: The reason for the transaction
        """
        try:
            # Create the transaction record
            transaction_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            
            # Try to insert into the database using the Supabase client
            if hasattr(self, 'supabase') and self.supabase:
                try:
                    await self.supabase.from_("credit_transactions").insert({
                        "id": transaction_id,
                        "user_id": user_id,
                        "amount": amount,
                        "description": reason,
                        "created_at": created_at
                    }).execute()
                    return
                except Exception as e:
                    logger.warning(f"Failed to log transaction using Supabase client: {str(e)}")
                    # Fall back to logging
            
            # If we get here, either the Supabase client failed or isn't available
            # Just log the transaction
            transaction = {
                "user_id": user_id,
                "amount": amount,
                "reason": reason,
                "created_at": created_at,
            }
            logger.info(f"Credit transaction: {json.dumps(transaction)}")
            
        except Exception as e:
            logger.error(f"Error logging credit transaction: {str(e)}")
            # We don't want to fail the main operation if logging fails
            # So we just log the error and continue
    
    async def get_transactions(
        self, 
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get credit transactions for a user.
        
        Args:
            user_id: The user ID
            start_date: Optional start date for filtering (ISO format)
            end_date: Optional end date for filtering (ISO format)
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            
        Returns:
            List of transactions
        """
        try:
            # Check if we have a Supabase client
            if hasattr(self, 'supabase') and self.supabase:
                # Start building the query
                query = self.supabase.from_("credit_transactions").select("*").eq("user_id", user_id)
                
                # Apply date filters if provided
                if start_date:
                    query = query.gte("created_at", start_date)
                if end_date:
                    query = query.lte("created_at", end_date)
                
                # Apply ordering, offset, and limit
                query = query.order("created_at", options={"ascending": False})
                query = query.range(offset, offset + limit - 1)
                
                # Execute query
                response = await query.execute()
                
                if not response.data:
                    return []
                    
                return response.data
            else:
                # If no Supabase client, return empty list
                logger.warning("No Supabase client available to get transactions")
                return []
                
        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting transactions: {str(e)}"
            )
    
    async def calculate_cost(self, operation: str, parameters: Dict[str, Any]) -> int:
        """
        Calculate the cost of an operation in credits.
        
        Args:
            operation: The operation type
            parameters: The operation parameters
            
        Returns:
            The cost in credits
        """
        # Define base costs for different operations
        base_costs = {
            "text_to_image": 5,
            "image_to_video": 10,
            "text_to_speech": 3,
            "voice_clone": 15,
            "text_to_music": 5,
            "sound_effect": 2,
        }
        
        # Get the base cost for the operation
        base_cost = base_costs.get(operation, 1)
        
        # Apply modifiers based on parameters
        cost = base_cost
        
        if operation == "text_to_image":
            # More images cost more
            num_images = parameters.get("num_images", 1)
            cost = base_cost * num_images
            
        elif operation == "image_to_video":
            # Longer videos cost more
            duration = parameters.get("duration", "5")
            if duration == "10":
                cost = base_cost * 2
                
        elif operation == "text_to_speech":
            # Longer text costs more
            text = parameters.get("text", "")
            # Roughly estimate 100 characters per credit
            text_length = len(text)
            text_cost = max(1, text_length // 100)
            cost = base_cost + text_cost
            
        elif operation == "text_to_music":
            # Longer duration costs more
            duration = parameters.get("duration", 5.0)
            # Each additional 5 seconds costs 1 more credit
            duration_cost = max(1, int(duration / 5))
            cost = base_cost * duration_cost
        
        logger.info(f"Calculated cost for {operation}: {cost} credits")
        return cost
