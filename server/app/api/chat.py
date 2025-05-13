"""
Chat API for Pixora AI Video Creation Platform
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json
import asyncio

# Import services
from ..services.auth import auth_service
from ..utils.websocket_manager import connection_manager
from ..agents.chat_agent import chat_agent

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Security scheme
security = HTTPBearer()

# Models
class ChatRequest(BaseModel):
    message: str
    task_id: Optional[str] = None

class ChatResponse(BaseModel):
    type: str
    content: str
    task_id: str
    function_call: Optional[Dict[str, Any]] = None
    function_response: Optional[Dict[str, Any]] = None

# REST endpoint for chat
@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Process a chat message and return a response.
    """
    try:
        # Verify the token
        payload = auth_service.verify_session_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get the user ID from the token
        user_id = payload["sub"]
        
        # Process the message
        response = await chat_agent.process_message(user_id, request.message, request.task_id)
        
        # Return the response
        return ChatResponse(
            type=response["type"],
            content=response["content"],
            task_id=response["task_id"],
            function_call=response.get("function_call"),
            function_response=response.get("function_response")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )

# WebSocket endpoint for chat
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    """
    try:
        # Get the token from the query parameters
        token = websocket.query_params.get("token")
        
        if not token:
            await websocket.send_json({"error": "Token is required"})
            await websocket.close()
            return
        
        # Verify the token
        payload = auth_service.verify_session_token(token)
        
        if not payload:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
        
        # Get the user ID from the token
        user_id = payload["sub"]
        
        # Connect the client to the connection manager
        connection_id = await connection_manager.connect(websocket, user_id)
        
        # Send a welcome message
        await connection_manager.send_message(connection_id, {
            "type": "system",
            "content": "Connected to Pixora AI WebSocket server"
        })
        
        # Define the message handler
        async def handle_message(user_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
            # Extract the message content
            if "message" not in message_data:
                return {"type": "error", "content": "Message field is required"}
            
            # Process the message
            response = await chat_agent.process_message(
                user_id,
                message_data["message"],
                message_data.get("task_id")
            )
            
            # Update the task status if a task ID is present
            if "task_id" in response:
                connection_manager.update_task_status(
                    response["task_id"],
                    "processing",
                    {"message": response["content"]}
                )
            
            return response
        
        # Handle messages
        await connection_manager.handle_websocket(websocket, user_id, handle_message)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error handling WebSocket connection: {str(e)}")
        await websocket.close()

# Task status endpoint
@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get the status of a task.
    """
    try:
        # Verify the token
        payload = auth_service.verify_session_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get the user ID from the token
        user_id = payload["sub"]
        
        # Get the task
        task = connection_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if the task belongs to the user
        if task["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Return the task status
        return {
            "id": task["id"],
            "status": task["status"],
            "metadata": task.get("metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )

# User tasks endpoint
@router.get("/tasks")
async def get_user_tasks(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get all tasks for a user.
    """
    try:
        # Verify the token
        payload = auth_service.verify_session_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get the user ID from the token
        user_id = payload["sub"]
        
        # Get the user's tasks
        tasks = connection_manager.get_user_tasks(user_id)
        
        # Return the tasks
        return {
            "tasks": [
                {
                    "id": task["id"],
                    "status": task["status"],
                    "metadata": task.get("metadata", {})
                }
                for task in tasks
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user tasks: {str(e)}"
        )
