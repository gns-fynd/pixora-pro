"""
Agent router for the Pixora AI application.

This module provides the API endpoints for the unified agent interface.
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User
from app.services.credits import CreditService
from app.ai.agents.chat_agent import ChatAgent, ChatResponse, ChatAction

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentRequest(BaseModel):
    """
    Request to the agent.
    """
    message: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """
    Response from the agent.
    """
    message: str
    task_id: Optional[str] = None
    video_url: Optional[str] = None
    actions: Optional[List[ChatAction]] = None


@router.post("", response_model=AgentResponse)
async def agent_endpoint(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
    chat_agent: ChatAgent = Depends(),
    credits_service: CreditService = Depends(),
):
    """
    Process a message from the user and return a response.
    
    Args:
        request: The request
        current_user: The current user
        chat_agent: The chat agent
        credits_service: The credits service
        
    Returns:
        Response from the agent
    """
    try:
        # Check if the user has enough credits
        if not await credits_service.has_sufficient_credits(current_user.id, "chat"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits"
            )
        
        # Process the message
        response = await chat_agent.process_message(
            user_id=str(current_user.id),
            content=request.message,
            context=request.context
        )
        
        # Deduct credits
        await credits_service.deduct_credits(current_user.id, "chat")
        
        # Return the response
        return AgentResponse(
            message=response.message,
            task_id=response.task_id,
            video_url=response.video_url,
            actions=response.actions
        )
    except Exception as e:
        logger.error(f"Error processing agent request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing agent request: {str(e)}"
        )


@router.websocket("/ws/{user_id}")
async def agent_websocket(
    websocket: WebSocket,
    user_id: str,
    chat_agent: ChatAgent = Depends(),
):
    """
    WebSocket endpoint for real-time communication with the agent.
    
    Args:
        websocket: The WebSocket connection
        user_id: The ID of the user
        chat_agent: The chat agent
    """
    await websocket.accept()
    
    try:
        # Authenticate the user
        # In a real implementation, we would validate the user_id against a token
        # For now, we'll just use the user_id as is
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                
                if "message" not in message_data:
                    await websocket.send_json({"error": "Message field is required"})
                    continue
                
                # Process the message
                await chat_agent.handle_websocket_message(
                    user_id=user_id,
                    content=message_data["message"],
                    websocket=websocket
                )
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({"error": f"Error processing message: {str(e)}"})
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
