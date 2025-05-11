"""
AI chat router for interacting with the AI agent.

This module provides API endpoints for chatting with the AI agent.
"""
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.ai.agent import AgentOrchestrator
from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    responses={404: {"description": "Not found"}},
)


class ChatRequest(BaseModel):
    """
    Request model for AI chat.
    """
    message: str = Field(..., description="The user's message")
    video_id: str = Field(..., description="The video ID")


class ChatResponse(BaseModel):
    """
    Response model for AI chat.
    """
    message: str = Field(..., description="The AI's response message")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Suggested actions")
    video_updates: Optional[Dict[str, Any]] = Field(None, description="Updates to the video")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: AgentOrchestrator = Depends(),
):
    """
    Chat with the AI agent about a video.
    """
    try:
        # Process the message with the AI agent
        response = await agent_orchestrator.process_chat_message(
            message=request.message,
            video_id=request.video_id,
            user_id=current_user.id
        )
        
        # Create the response
        chat_response = ChatResponse(
            message=response.get("message", "I understand your request."),
            actions=response.get("actions"),
            video_updates=response.get("video_updates")
        )
        
        return chat_response
        
    except Exception as e:
        logger.error(f"Error in AI chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat failed: {str(e)}"
        )


class ContextualResponseRequest(BaseModel):
    """
    Request model for contextual responses.
    """
    context_type: str = Field(..., description="The type of context")
    prompt: Optional[str] = Field(None, description="The user's prompt (if applicable)")
    scene_number: Optional[int] = Field(None, description="The scene number (if applicable)")
    voice_type: Optional[str] = Field(None, description="The voice type (if applicable)")
    music_style: Optional[str] = Field(None, description="The music style (if applicable)")


class ContextualResponseResponse(BaseModel):
    """
    Response model for contextual responses.
    """
    message: str = Field(..., description="The AI's contextual response")


@router.post("/contextual-response", response_model=ContextualResponseResponse)
async def get_contextual_response(
    request: ContextualResponseRequest,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: AgentOrchestrator = Depends(),
):
    """
    Get a contextual response from the AI agent based on the current state.
    """
    try:
        # Prepare context data
        context_data = {}
        if request.prompt:
            context_data["prompt"] = request.prompt
        if request.scene_number:
            context_data["scene_number"] = request.scene_number
        if request.voice_type:
            context_data["voice_type"] = request.voice_type
        if request.music_style:
            context_data["style"] = request.music_style
        
        # Get the contextual response
        if request.context_type == "scene_breakdown_intro":
            message = await agent_orchestrator.get_scene_breakdown_intro(request.prompt or "")
        elif request.context_type == "generation_started":
            message = await agent_orchestrator.get_generation_started_message()
        elif request.context_type == "generation_completed":
            message = await agent_orchestrator.get_generation_completed_message()
        else:
            # Use the generic contextual response method
            message = await agent_orchestrator.prompt_analyzer.generate_contextual_response(
                request.context_type,
                context_data
            )
        
        return ContextualResponseResponse(message=message)
        
    except Exception as e:
        logger.error(f"Error getting contextual response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get contextual response: {str(e)}"
        )


@router.get("/voices")
async def get_available_voices(
    current_user: User = Depends(get_current_user),
):
    """
    Get available voice options.
    """
    try:
        # In a real implementation, this would fetch available voices from a database
        # For now, we'll return mock voices
        voices = [
            {
                "id": "voice_1",
                "name": "Professional Male",
                "gender": "male",
                "tone": "professional",
                "preview_url": "https://example.com/voice_1_preview.mp3"
            },
            {
                "id": "voice_2",
                "name": "Professional Female",
                "gender": "female",
                "tone": "professional",
                "preview_url": "https://example.com/voice_2_preview.mp3"
            },
            {
                "id": "voice_3",
                "name": "Casual Male",
                "gender": "male",
                "tone": "casual",
                "preview_url": "https://example.com/voice_3_preview.mp3"
            },
            {
                "id": "voice_4",
                "name": "Casual Female",
                "gender": "female",
                "tone": "casual",
                "preview_url": "https://example.com/voice_4_preview.mp3"
            },
            {
                "id": "voice_5",
                "name": "Energetic",
                "gender": "neutral",
                "tone": "energetic",
                "preview_url": "https://example.com/voice_5_preview.mp3"
            }
        ]
        
        return voices
        
    except Exception as e:
        logger.error(f"Error getting available voices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available voices: {str(e)}"
        )
