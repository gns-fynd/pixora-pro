"""
Agent chat router for Pixora AI.

This module provides WebSocket endpoints for agent chat.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from starlette.websockets import WebSocketState

from app.core.config import Settings, get_settings
from app.services.redis_client import RedisClient
from app.auth.jwt import get_current_user_ws
from app.schemas.user import UserResponse as User
from app.ai.agent.controller import AgentController


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


# Store active connections
active_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/ws/{user_id}")
async def agent_websocket(
    websocket: WebSocket,
    user_id: str,
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings)
):
    """
    WebSocket endpoint for agent chat.
    
    Args:
        websocket: The WebSocket connection
        user_id: The user ID
        redis_client: Redis client for persistence
        settings: Application settings
    """
    # Accept the connection
    await websocket.accept()
    
    try:
        # Authenticate the user
        token = await websocket.receive_text()
        user = await get_current_user_ws(token, settings)
        
        # Verify that the user ID matches
        if user.id != user_id:
            await websocket.send_json({
                "type": "error",
                "message": "User ID mismatch"
            })
            await websocket.close()
            return
        
        # Add the connection to active connections
        if user_id not in active_connections:
            active_connections[user_id] = []
        active_connections[user_id].append(websocket)
        
        # Initialize agent controller
        agent_controller = AgentController(user_id, redis_client, settings)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to agent"
        })
        
        # Main WebSocket loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Extract message and context
            message = data.get("message", "")
            task_id = data.get("task_id")
            context = data.get("context", {})
            
            # Define progress callback
            async def progress_callback(task_id: str, progress: float, status: str):
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({
                        "type": "progress",
                        "task_id": task_id,
                        "progress": progress,
                        "status": status
                    })
            
            # Process the message asynchronously
            task = await agent_controller.process_message_async(
                message=message,
                task_id=task_id,
                context=context,
                progress_callback=progress_callback
            )
            
            # Send initial acknowledgment
            await websocket.send_json({
                "type": "ack",
                "task_id": task.task_id,
                "message": "Processing your request..."
            })
            
            # Wait for task to complete or provide updates
            while not task.is_complete:
                # Check if there are any updates to send
                if task.has_updates:
                    await websocket.send_json({
                        "type": "update",
                        "task_id": task.task_id,
                        "message": task.current_message,
                        "actions": task.current_actions,
                        "progress": task.progress,
                        "status": task.status
                    })
                    task.clear_updates()
                
                # Sleep briefly to avoid tight loop
                await asyncio.sleep(0.1)
                
                # Check if the WebSocket is still connected
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
            
            # Send final result if the task is complete and the WebSocket is still connected
            if task.is_complete and websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "type": "result",
                    "task_id": task.task_id,
                    "message": task.result_message,
                    "actions": task.actions,
                    "result": task.result,
                    "progress": 100,
                    "status": "completed"
                })
    
    except WebSocketDisconnect:
        # Handle client disconnect
        logger.info(f"Client disconnected: {user_id}")
    except Exception as e:
        # Handle errors
        logger.error(f"Error in websocket: {str(e)}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "message": f"An error occurred: {str(e)}"
            })
    finally:
        # Remove the connection from active connections
        if user_id in active_connections:
            active_connections[user_id].remove(websocket)
            if not active_connections[user_id]:
                del active_connections[user_id]


@router.get("/tasks")
async def get_user_tasks(
    user: User = Depends(get_current_user_ws),
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings)
):
    """
    Get all tasks for the current user.
    
    Args:
        user: The current user
        redis_client: Redis client for persistence
        settings: Application settings
        
    Returns:
        A list of task IDs
    """
    # Initialize agent controller
    agent_controller = AgentController(user.id, redis_client, settings)
    
    # Get all tasks for the user
    tasks = await agent_controller.list_user_tasks()
    
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user_ws),
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings)
):
    """
    Get the status of a task.
    
    Args:
        task_id: The task ID
        user: The current user
        redis_client: Redis client for persistence
        settings: Application settings
        
    Returns:
        The task status
    """
    # Initialize agent controller
    agent_controller = AgentController(user.id, redis_client, settings)
    
    # Get the task status
    task_status = await agent_controller.get_task_status(task_id)
    
    # Check if the task exists
    if task_status["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if the task belongs to the user
    if task_status.get("user_id") != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )
    
    return task_status


@router.delete("/memory")
async def clear_memory(
    user: User = Depends(get_current_user_ws),
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings)
):
    """
    Clear the conversation memory for the current user.
    
    Args:
        user: The current user
        redis_client: Redis client for persistence
        settings: Application settings
        
    Returns:
        Success message
    """
    # Initialize agent controller
    agent_controller = AgentController(user.id, redis_client, settings)
    
    # Clear the memory
    await agent_controller.clear_memory()
    
    return {"message": "Memory cleared successfully"}
