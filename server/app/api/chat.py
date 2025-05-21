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
        # Accept the connection first
        await websocket.accept()
        
        # Get the token from cookies
        cookies = websocket.cookies
        token = cookies.get("pixora_auth_token")
        
        if not token:
            # Try to get token from query parameters as fallback
            token = websocket.query_params.get("token")
            
        if not token:
            logger.warning("WebSocket connection attempt without token")
            await websocket.send_json({"type": "error", "content": "Authentication token is required"})
            await websocket.close()
            return
        
        # Verify the token
        payload = auth_service.verify_session_token(token)
        
        if not payload:
            logger.warning("WebSocket connection attempt with invalid token")
            await websocket.send_json({"type": "error", "content": "Invalid authentication token"})
            await websocket.close()
            return
            
        logger.info(f"WebSocket connection authenticated for user: {payload['sub']}")
        
        # Get the user ID from the token
        user_id = payload["sub"]
        
        # Define the message handler
        async def handle_message(user_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
            # Extract the message content
            if "message" not in message_data:
                return {"type": "error", "content": "Message field is required"}
            
            # Extract context data
            context = message_data.get("context", {})
            
            # Log the message and context for debugging
            logger.info(f"Received message: {message_data['message'][:50]}... with context: {context}")
            
            # Check if this is a scene breakdown request with prompt data
            if "scene breakdown" in message_data["message"].lower() and context and "prompt" in context:
                logger.info(f"Generating script with prompt: {context['prompt'][:50]}...")
                
                try:
                    # Generate script with the prompt data
                    script_data = await chat_agent._generate_script(
                        prompt=context["prompt"],
                        character_consistency=False,
                        duration=context.get("duration", 60),
                        aspect_ratio=context.get("aspect_ratio", "16:9"),
                        style=context.get("style", "cinematic")
                    )
                    
                    # Create a task for tracking
                    task_id = script_data["task_id"]
                    connection_manager.create_task(
                        user_id=user_id,
                        task_type="scene_breakdown",
                        metadata={"prompt": context["prompt"]}
                    )
                    
                    # Update task status
                    connection_manager.update_task_status(
                        task_id,
                        "completed",
                        {"script": script_data}
                    )
                    
                    # Transform the script data to match the client's expected format
                    client_format = {
                        "scenes": [],
                        "script": {
                            "title": "Scene Breakdown",
                            "prompt": context["prompt"],
                            "style": context.get("style", "cinematic"),
                            "duration": context.get("duration", 60),
                            "aspect_ratio": context.get("aspect_ratio", "16:9")
                        }
                    }
                    
                    # Extract scenes from the clips
                    if "clips" in script_data:
                        for i, clip in enumerate(script_data["clips"]):
                            if "scene" in clip:
                                scene = clip["scene"]
                                client_format["scenes"].append({
                                    "id": str(i + 1),
                                    "visual": scene.get("video_prompt", ""),
                                    "audio": scene.get("script", ""),
                                    "narration": scene.get("script", ""),
                                    "duration": scene.get("duration", 5)
                                })
                    
                    # Return the transformed script data
                    return {
                        "type": "agent_message",
                        "content": "Here's the scene breakdown for your video.",
                        "data": client_format,
                        "task_id": task_id
                    }
                except Exception as e:
                    logger.error(f"Error generating script: {str(e)}")
                    return {
                        "type": "error",
                        "content": f"Failed to generate script: {str(e)}"
                    }
            
            # If not a scene breakdown request or no prompt data, process normally
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
        
        # Connection is already accepted, no need to accept again
        
        # Handle messages directly without creating a separate connection
        try:
            # Send a welcome message directly
            await websocket.send_json({
                "type": "system",
                "content": "Connected to Pixora AI WebSocket server"
            })
            
            # Handle messages in a loop
            while True:
                # Receive a message
                message = await websocket.receive_text()
                
                # Parse the message
                try:
                    message_data = json.loads(message)
                    
                    # Ensure context is properly formatted
                    if "context" in message_data and message_data["context"] is None:
                        message_data["context"] = {}
                    
                    # Handle task status requests
                    if message_data.get("type") == "task_status" and message_data.get("task_id"):
                        task_id = message_data["task_id"]
                        logger.info(f"Received task status request for task {task_id} from user {user_id}")
                        
                        # Get the task
                        task = connection_manager.get_task(task_id)
                        
                        if not task:
                            await websocket.send_json({
                                "type": "task_status",
                                "task_id": task_id,
                                "status": "error",
                                "message": "Task not found"
                            })
                            continue
                        
                        # Check if the task belongs to the user
                        if task["user_id"] != user_id:
                            await websocket.send_json({
                                "type": "task_status",
                                "task_id": task_id,
                                "status": "error",
                                "message": "Access denied"
                            })
                            continue
                        
                        # Send the task status
                        await websocket.send_json({
                            "type": "task_status",
                            "task_id": task_id,
                            "status": task["status"],
                            "progress": task.get("metadata", {}).get("progress", 0),
                            "message": task.get("metadata", {}).get("message"),
                            "video_url": task.get("metadata", {}).get("video_url")
                        })
                        continue
                    
                    # Handle regular messages
                    response = await handle_message(user_id, message_data)
                    
                    # Send the response
                    if response:
                        await websocket.send_json(response)
                
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid JSON"
                    })
                    continue
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Error processing message: {str(e)}"
                    })
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {user_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {str(e)}")
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
