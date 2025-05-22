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
import uuid

# Import services
from ..services.auth import auth_service
from ..utils.websocket_manager import connection_manager
from ..services.supabase import supabase_service
from ..agents.chat_agent import chat_agent
from ..agents.script_agent import script_agent
from ..agents.asset_agent import asset_agent
from ..agents.video_agent import video_agent

# Import telemetry
from ..utils.telemetry import traced, log_event

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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    video_id: Optional[str] = None
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
        
        # Create a task for tracking if no task ID is provided
        task_id = request.task_id
        if not task_id:
            task_id = connection_manager.create_task(
                user_id=user_id,
                task_type="chat",
                metadata={"message": request.message, "video_id": video_id}
            )
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "processing",
            {"message": "Processing message..."}
        )
        
        # Process the message
        response = await chat_agent.process_message(user_id, request.message, task_id, video_id)
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "completed",
            {"message": response["content"]}
        )
        
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
        
        # Authenticate the user
        user_data = await auth_service.get_current_user_ws(websocket)
        
        if not user_data:
            logger.warning("WebSocket connection authentication failed")
            await websocket.send_json({"type": "error", "content": "Authentication failed"})
            await websocket.close()
            return
            
        # Get the user ID
        user_id = user_data["id"]
        
        # Define the message handler
        async def handle_message(user_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
            # Extract the message content
            if "message" not in message_data:
                return {"type": "error", "content": "Message field is required"}
            
            # Extract context data
            context = message_data.get("context", {})
            
            # Extract video_id if present
            video_id = context.get("video_id")
            
            # Log the message and context for debugging
            logger.info(f"Received message: {message_data['message'][:50]}... with context: {context}")
            
            # Check if this is a scene breakdown request with prompt data
            if "scene breakdown" in message_data["message"].lower() and context and "prompt" in context:
                logger.info(f"Generating script with prompt: {context['prompt'][:50]}...")
                
                try:
                    # Generate script with the prompt data using script_agent
                    script_data = await script_agent.create_script(
                        prompt=context["prompt"],
                        character_consistency=False,
                        duration=context.get("duration", 60),
                        aspect_ratio=context.get("aspect_ratio", "16:9"),
                        style=context.get("style", "cinematic")
                    )
                    
                    # Create a task for tracking
                    task_id = script_data["task_id"]
                    # Create a task in the connection manager
                    connection_manager.create_task(
                        user_id=user_id,
                        task_type="scene_breakdown",
                        metadata={"prompt": context["prompt"], "task_id": task_id}
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
            
            # Handle task status requests
            if message_data.get("type") == "task_status" and message_data.get("task_id"):
                task_id = message_data["task_id"]
                logger.info(f"Received task status request for task {task_id} from user {user_id}")
                
                # Get the task
                task = connection_manager.get_task(task_id)
                
                if not task:
                    return {
                        "type": "task_status",
                        "task_id": task_id,
                        "status": "error",
                        "message": "Task not found"
                    }
                
                # Check if the task belongs to the user
                if task["user_id"] != user_id:
                    return {
                        "type": "task_status",
                        "task_id": task_id,
                        "status": "error",
                        "message": "Access denied"
                    }
                
                # Return the task status
                return {
                    "type": "task_status",
                    "task_id": task_id,
                    "status": task["status"],
                    "progress": task.get("metadata", {}).get("progress", 0),
                    "message": task.get("metadata", {}).get("message"),
                    "video_url": task.get("metadata", {}).get("video_url")
                }
            
            # If not a scene breakdown request or task status request, process normally
            response = await chat_agent.process_message(
                user_id,
                message_data["message"],
                message_data.get("task_id"),
                video_id
            )
            
            # Update the task status if a task ID is present
            if "task_id" in response:
                connection_manager.update_task_status(
                    response["task_id"],
                    "processing",
                    {"message": response["content"]}
                )
            
            return response
        
        # Use the connection manager to handle the WebSocket connection
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

# Generate video endpoint
@router.post("/generate-video")
@traced("generate_video_endpoint")
async def generate_video(
    request: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Generate a complete video from a script.
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
        
        # Extract the script data from the request
        script_data = request.get("script")
        if not script_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Script data is required"
            )
        
        # Extract the task ID from the request or generate a new one
        task_id = request.get("task_id")
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # Create a task for tracking
        created_task_id = connection_manager.create_task(
            user_id=user_id,
            task_type="video_generation",
            metadata={"prompt": script_data.get("rewritten_prompt", script_data.get("user_prompt", "")), "task_id": task_id}
        )
        
        # Use the created task ID if we didn't have one
        if not task_id:
            task_id = created_task_id
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "processing",
            {"message": "Generating assets..."}
        )
        
        # Generate assets asynchronously
        asyncio.create_task(
            _generate_video_async(user_id, task_id, script_data)
        )
        
        # Return the task ID
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Video generation started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate video: {str(e)}"
        )

# Asynchronous video generation function
async def _generate_video_async(user_id: str, task_id: str, script_data: Dict[str, Any]):
    """
    Generate a video asynchronously.
    """
    try:
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "processing",
            {"message": "Generating character images...", "progress": 10}
        )
        
        # Generate assets
        assets = await asset_agent.generate_all_assets(
            task_id=task_id,
            script_data=script_data
        )
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "processing",
            {"message": "Generating scene videos...", "progress": 50}
        )
        
        # Generate video
        video_result = await video_agent.generate_video(
            task_id=task_id,
            script_data=script_data,
            assets=assets
        )
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "completed",
            {
                "message": "Video generation completed",
                "progress": 100,
                "video_url": video_result.get("final_video", {}).get("url")
            }
        )
        
        # Update the task in the database with the video result
        if hasattr(supabase_service, 'client') and supabase_service.client:
            supabase_service.update_task_status(
                task_id=task_id,
                status="completed",
                metadata={
                    "video_url": video_result.get("final_video", {}).get("url"),
                    "prompt": script_data.get("rewritten_prompt", script_data.get("user_prompt", "")),
                    "script": script_data,
                    "assets": assets,
                    "video": video_result
                }
            )
    except Exception as e:
        logger.error(f"Error generating video asynchronously: {str(e)}")
        
        # Update task status
        connection_manager.update_task_status(
            task_id,
            "failed",
            {"message": f"Video generation failed: {str(e)}"}
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
