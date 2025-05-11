"""
WebSocket router for Pixora AI.

This module provides WebSocket endpoints for real-time communication
with the Pixora AI video generation system.
"""
import json
import asyncio
import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from starlette.websockets import WebSocketState
from agents import Runner, RunResultStreaming

from app.core.config import Settings, get_settings
from app.services.redis_client import RedisClient
from app.auth.jwt import get_current_user_ws
from app.schemas.user import UserResponse as User
from app.ai.websocket_manager import ConnectionManager
from app.ai.sdk.context import TaskContext
from app.ai.sdk.agent import video_agent, get_agent_for_stage
from app.ai.tasks.enhanced_task_manager import EnhancedTaskManager


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    responses={404: {"description": "Not found"}},
)

# Create connection manager
connection_manager = ConnectionManager()


@router.websocket("/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings)
):
    """
    WebSocket endpoint for real-time communication.
    
    Args:
        websocket: The WebSocket connection
        task_id: The task ID
        redis_client: Redis client for persistence
        settings: Application settings
    """
    # Accept the connection
    await websocket.accept()
    
    try:
        # Authenticate the user
        token = await websocket.receive_text()
        user = await get_current_user_ws(token, settings)
        
        # Register the connection
        await connection_manager.connect(task_id, websocket, str(user.id))
        
        # Create task manager
        task_manager = EnhancedTaskManager(redis_client=redis_client)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Pixora AI",
            "task_id": task_id,
            "user_id": str(user.id)
        })
        
        # Check if there's an existing task
        task_data = await task_manager.get_task(task_id)
        if task_data:
            # Send the existing task data
            await websocket.send_json({
                "type": "task_state",
                "data": task_data
            })
            
            # If there's a scene breakdown, send it
            scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
            if scene_breakdown:
                await websocket.send_json({
                    "type": "scene_breakdown",
                    "data": scene_breakdown
                })
            
            # Send current status
            status = await task_manager.get_task_status(task_id)
            if status:
                await websocket.send_json({
                    "type": "status_update",
                    "data": status
                })
        
        # Main WebSocket loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process based on message type
            if data["type"] == "chat_message":
                # Process chat message
                await process_chat_message(
                    task_id=task_id,
                    user_id=str(user.id),
                    message=data["message"],
                    websocket=websocket,
                    redis_client=redis_client,
                    task_manager=task_manager
                )
            
            elif data["type"] == "command":
                # Process command
                await process_command(
                    task_id=task_id,
                    user_id=str(user.id),
                    command=data["command"],
                    params=data.get("params", {}),
                    websocket=websocket,
                    redis_client=redis_client,
                    task_manager=task_manager
                )
            
            elif data["type"] == "pause_task":
                # Pause the task
                await process_pause_command(
                    task_id=task_id,
                    user_id=str(user.id),
                    websocket=websocket,
                    task_manager=task_manager
                )
            
            elif data["type"] == "resume_task":
                # Resume the task
                await process_resume_command(
                    task_id=task_id,
                    user_id=str(user.id),
                    params=data.get("params", {}),
                    websocket=websocket,
                    task_manager=task_manager
                )
            
            elif data["type"] == "cancel_task":
                # Cancel the task
                await process_cancel_command(
                    task_id=task_id,
                    user_id=str(user.id),
                    websocket=websocket,
                    task_manager=task_manager
                )
            
            elif data["type"] == "feedback_response":
                # Process feedback response
                await process_feedback_response(
                    task_id=task_id,
                    user_id=str(user.id),
                    request_id=data.get("request_id", ""),
                    response=data.get("response", {}),
                    websocket=websocket,
                    task_manager=task_manager
                )
            
            else:
                # Unknown message type
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {data['type']}",
                        "error_type": "unknown_message_type"
                    }
                })
    
    except WebSocketDisconnect:
        # Handle client disconnect
        logger.info(f"Client disconnected: {task_id}")
    except Exception as e:
        # Handle errors
        logger.error(f"Error in websocket: {str(e)}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"An error occurred: {str(e)}",
                    "error_type": "server_error"
                }
            })
    finally:
        # Remove the connection from active connections
        await connection_manager.disconnect(task_id, websocket, str(user.id) if 'user' in locals() else None)


async def process_chat_message(
    task_id: str,
    user_id: str,
    message: str,
    websocket: WebSocket,
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
):
    """
    Process a chat message from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        message: The message content
        websocket: The WebSocket connection
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
    """
    try:
        # Create or get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            # Create new task
            task_data = await task_manager.create_task(
                task_id=task_id,
                user_id=user_id,
                task_type="chat",
                initial_data={}
            )
        
        # Check if task is paused
        status = await task_manager.get_task_status(task_id)
        if status and status.get("status") == "paused":
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "Task is paused. Resume the task to continue.",
                    "error_type": "task_paused",
                    "recovery_options": [
                        {
                            "action": "resume_task",
                            "label": "Resume Task"
                        }
                    ]
                }
            })
            return
        
        # Add message to history
        await task_manager.add_message(
            task_id=task_id,
            role="user",
            content=message
        )
        
        # Determine the current stage
        stage = task_data.get("stage", "initial")
        
        # Get the appropriate agent for the stage
        agent = get_agent_for_stage(stage)
        
        # Create context
        context = TaskContext(task_id=task_id, user_id=user_id)
        
        # Load existing state if available
        scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
        if scene_breakdown:
            context.set("scene_breakdown", scene_breakdown)
        
        # Update task status
        await task_manager.update_task_status(
            task_id=task_id,
            status="processing",
            progress=0,
            stage="chat_processing",
            message="Processing your message..."
        )
        
        # Run the agent with streaming
        result_stream = Runner.run_streamed(
            agent,
            message,
            context=context
        )
        
        # Stream events back to client
        token_buffer = ""
        async for event in result_stream.stream_events():
            if event.type == "raw_response_event":
                # Stream tokens
                if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content') and event.data.delta.content:
                    token = event.data.delta.content
                    token_buffer += token
                    
                    # Send token
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })
                    
                    # If we have a complete sentence, update progress
                    if token in ['.', '!', '?'] and len(token_buffer) > 20:
                        # Reset buffer
                        token_buffer = ""
                        
                        # Update progress (simulate progress)
                        progress = min(90, await task_manager.get_task_progress(task_id) + 10)
                        await task_manager.update_task_progress(
                            task_id=task_id,
                            progress=progress,
                            message="Generating response..."
                        )
            
            elif event.type == "run_item_stream_event":
                # Handle different item types
                item = event.item
                
                if hasattr(item, 'type') and item.type == "tool_call":
                    # Tool call
                    tool_data = {
                        "tool": item.name,
                        "parameters": json.loads(item.parameters) if hasattr(item, 'parameters') else {}
                    }
                    
                    # Send tool call
                    await websocket.send_json({
                        "type": "tool_call",
                        "data": tool_data
                    })
                    
                    # Update task status
                    await task_manager.update_task_status(
                        task_id=task_id,
                        status="processing",
                        progress=50,
                        stage="tool_execution",
                        substage=item.name,
                        message=f"Executing tool: {item.name}"
                    )
                    
                    # Send detailed progress
                    await connection_manager.send_detailed_progress(
                        task_id=task_id,
                        progress=50,
                        stage="tool_execution",
                        substage=item.name,
                        message=f"Executing tool: {item.name}",
                        current_step=item.name
                    )
                
                elif hasattr(item, 'type') and item.type == "tool_result":
                    # Tool result
                    tool_result = {
                        "tool": item.name if hasattr(item, 'name') else "",
                        "result": item.result if hasattr(item, 'result') else ""
                    }
                    
                    # Send tool result
                    await websocket.send_json({
                        "type": "tool_result",
                        "data": tool_result
                    })
                    
                    # Update task status
                    await task_manager.update_task_status(
                        task_id=task_id,
                        status="processing",
                        progress=70,
                        stage="processing_result",
                        message="Processing tool result..."
                    )
                    
                    # Send tool execution update
                    await connection_manager.send_tool_execution(
                        task_id=task_id,
                        tool_name=tool_result["tool"],
                        parameters={},  # We don't have parameters in the result
                        result=tool_result["result"]
                    )
        
        # Get the final result
        final_output = result_stream.final_output
        
        # Add assistant message to history
        await task_manager.add_message(
            task_id=task_id,
            role="assistant",
            content=final_output
        )
        
        # Update task status
        await task_manager.update_task_status(
            task_id=task_id,
            status="completed",
            progress=100,
            stage="completed",
            message="Response complete"
        )
        
        # Send final message
        await connection_manager.send_chat_message(
            task_id=task_id,
            role="assistant",
            content=final_output
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        
        # Update task status
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message=f"Error: {str(e)}"
        )
        
        # Send error
        await connection_manager.send_error(
            task_id=task_id,
            error=f"Error processing message: {str(e)}",
            error_type="chat_processing_error",
            recovery_options=[
                {
                    "action": "retry",
                    "label": "Retry",
                    "params": {"message": message}
                }
            ]
        )


async def process_command(
    task_id: str,
    user_id: str,
    command: str,
    params: Dict[str, Any],
    websocket: WebSocket,
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
):
    """
    Process a command from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        command: The command to execute
        params: Command parameters
        websocket: The WebSocket connection
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
    """
    try:
        # Get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Task {task_id} not found",
                    "error_type": "task_not_found"
                }
            })
            return
        
        # Check if the task belongs to the user
        if task_data.get("user_id") != user_id:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "You don't have permission to access this task",
                    "error_type": "permission_denied"
                }
            })
            return
        
        # Check if task is paused
        status = await task_manager.get_task_status(task_id)
        if status and status.get("status") == "paused":
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "Task is paused. Resume the task to continue.",
                    "error_type": "task_paused",
                    "recovery_options": [
                        {
                            "action": "resume_task",
                            "label": "Resume Task"
                        }
                    ]
                }
            })
            return
        
        # Process the command
        if command == "generate_scene_breakdown":
            # Generate scene breakdown
            result = await handle_generate_scene_breakdown(
                task_id=task_id,
                user_id=user_id,
                params=params,
                redis_client=redis_client,
                task_manager=task_manager
            )
            
            # Update task stage
            await task_manager.update_task_data(
                task_id=task_id,
                updates={"stage": "scene_breakdown"}
            )
            
            # Send result
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "data": result
            })
        
        elif command == "update_scene":
            # Update scene
            result = await handle_update_scene(
                task_id=task_id,
                user_id=user_id,
                params=params,
                redis_client=redis_client,
                task_manager=task_manager
            )
            
            # Send result
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "data": result
            })
        
        elif command == "generate_video":
            # Generate video
            result = await handle_generate_video(
                task_id=task_id,
                user_id=user_id,
                params=params,
                redis_client=redis_client,
                task_manager=task_manager
            )
            
            # Update task stage
            await task_manager.update_task_data(
                task_id=task_id,
                updates={"stage": "video_generation"}
            )
            
            # Send result
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "data": result
            })
        
        elif command == "check_generation_status":
            # Check generation status
            result = await handle_check_generation_status(
                task_id=task_id,
                user_id=user_id,
                task_manager=task_manager
            )
            
            # Send result
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "data": result
            })
        
        elif command == "adjust_scene_duration":
            # Adjust scene duration
            result = await handle_adjust_scene_duration(
                task_id=task_id,
                user_id=user_id,
                params=params,
                redis_client=redis_client,
                task_manager=task_manager
            )
            
            # Send result
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "data": result
            })
        
        else:
            # Unknown command
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Unknown command: {command}",
                    "error_type": "unknown_command"
                }
            })
    
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        
        # Update task status
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message=f"Error: {str(e)}"
        )
        
        # Send error
        await connection_manager.send_error(
            task_id=task_id,
            error=f"Error processing command: {str(e)}",
            error_type="command_processing_error",
            recovery_options=[
                {
                    "action": "retry_command",
                    "label": "Retry",
                    "params": {"command": command, "params": params}
                }
            ]
        )


async def process_pause_command(
    task_id: str,
    user_id: str,
    websocket: WebSocket,
    task_manager: EnhancedTaskManager
):
    """
    Process a pause command from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        websocket: The WebSocket connection
        task_manager: Task manager for task operations
    """
    try:
        # Get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Task {task_id} not found",
                    "error_type": "task_not_found"
                }
            })
            return
        
        # Check if the task belongs to the user
        if task_data.get("user_id") != user_id:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "You don't have permission to access this task",
                    "error_type": "permission_denied"
                }
            })
            return
        
        # Pause the task
        result = await task_manager.pause_task(task_id)
        
        # Send task control message
        await connection_manager.send_task_control(
            task_id=task_id,
            action="pause",
            params={"timestamp": time.time()}
        )
        
        # Send result
        await websocket.send_json({
            "type": "command_result",
            "command": "pause_task",
            "data": {
                "status": "paused",
                "message": "Task paused successfully"
            }
        })
        
    except Exception as e:
        logger.error(f"Error pausing task: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"Error pausing task: {str(e)}",
                "error_type": "pause_error"
            }
        })


async def process_resume_command(
    task_id: str,
    user_id: str,
    params: Dict[str, Any],
    websocket: WebSocket,
    task_manager: EnhancedTaskManager
):
    """
    Process a resume command from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        params: Command parameters
        websocket: The WebSocket connection
        task_manager: Task manager for task operations
    """
    try:
        # Get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Task {task_id} not found",
                    "error_type": "task_not_found"
                }
            })
            return
        
        # Check if the task belongs to the user
        if task_data.get("user_id") != user_id:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "You don't have permission to access this task",
                    "error_type": "permission_denied"
                }
            })
            return
        
        # Resume the task
        result = await task_manager.resume_task(task_id, params)
        
        # Send task control message
        await connection_manager.send_task_control(
            task_id=task_id,
            action="resume",
            params={"timestamp": time.time(), **params}
        )
        
        # Send result
        await websocket.send_json({
            "type": "command_result",
            "command": "resume_task",
            "data": {
                "status": "resumed",
                "message": "Task resumed successfully"
            }
        })
        
    except Exception as e:
        logger.error(f"Error resuming task: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"Error resuming task: {str(e)}",
                "error_type": "resume_error"
            }
        })


async def process_cancel_command(
    task_id: str,
    user_id: str,
    websocket: WebSocket,
    task_manager: EnhancedTaskManager
):
    """
    Process a cancel command from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        websocket: The WebSocket connection
        task_manager: Task manager for task operations
    """
    try:
        # Get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Task {task_id} not found",
                    "error_type": "task_not_found"
                }
            })
            return
        
        # Check if the task belongs to the user
        if task_data.get("user_id") != user_id:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "You don't have permission to access this task",
                    "error_type": "permission_denied"
                }
            })
            return
        
        # Cancel the task
        result = await task_manager.cancel_task(task_id)
        
        # Send task control message
        await connection_manager.send_task_control(
            task_id=task_id,
            action="cancel",
            params={"timestamp": time.time()}
        )
        
        # Send result
        await websocket.send_json({
            "type": "command_result",
            "command": "cancel_task",
            "data": {
                "status": "cancelled",
                "message": "Task cancelled successfully"
            }
        })
        
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"Error cancelling task: {str(e)}",
                "error_type": "cancel_error"
            }
        })


async def process_feedback_response(
    task_id: str,
    user_id: str,
    request_id: str,
    response: Dict[str, Any],
    websocket: WebSocket,
    task_manager: EnhancedTaskManager
):
    """
    Process a feedback response from the client.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        request_id: The feedback request ID
        response: The feedback response
        websocket: The WebSocket connection
        task_manager: Task manager for task operations
    """
    try:
        # Get task data
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Task {task_id} not found",
                    "error_type": "task_not_found"
                }
            })
            return
        
        # Check if the task belongs to the user
        if task_data.get("user_id") != user_id:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "You don't have permission to access this task",
                    "error_type": "permission_denied"
                }
            })
            return
        
        # Store the feedback response
        await task_manager.store_feedback(
            task_id=task_id,
            request_id=request_id,
            response=response
        )
        
        # Send acknowledgement
        await websocket.send_json({
            "type": "feedback_acknowledgement",
            "data": {
                "request_id": request_id,
                "status": "received",
                "message": "Feedback received successfully"
            }
        })
        
        # Process the feedback based on the response
        action = response.get("action", "")
        
        if action == "approve":
            # Continue with the next step
            await websocket.send_json({
                "type": "status_update",
                "data": {
                    "status": "processing",
                    "message": "Continuing with approved content",
                    "timestamp": time.time()
                }
            })
        
        elif action == "regenerate":
            # Regenerate the content
            item_type = response.get("item_type", "")
            item_id = response.get("item_id", "")
            
            await websocket.send_json({
                "type": "status_update",
                "data": {
                    "status": "processing",
                    "message": f"Regenerating {item_type} {item_id}",
                    "timestamp": time.time()
                }
            })
            
            # In a real implementation, this would trigger the regeneration
            # For now, we'll just acknowledge it
            
        elif action == "adjust":
            # Adjust the content based on feedback
            adjustments = response.get("adjustments", {})
            
            await websocket.send_json({
                "type": "status_update",
                "data": {
                    "status": "processing",
                    "message": "Adjusting content based on feedback",
                    "timestamp": time.time()
                }
            })
            
            # In a real implementation, this would apply the adjustments
            # For now, we'll just acknowledge it
        
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"Error processing feedback: {str(e)}",
                "error_type": "feedback_error"
            }
        })


async def handle_generate_scene_breakdown(
    task_id: str,
    user_id: str,
    params: Dict[str, Any],
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
) -> Dict[str, Any]:
    """
    Handle the generate_scene_breakdown command.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        params: Command parameters
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
        
    Returns:
        The result of the command
    """
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="processing",
        progress=0,
        stage="scene_breakdown",
        message="Generating scene breakdown..."
    )
    
    # Create context
    context = TaskContext(task_id=task_id, user_id=user_id)
    
    # Get the scene breakdown agent
    agent = get_agent_for_stage("scene_breakdown")
    
    # Extract parameters
    prompt = params.get("prompt", "")
    style = params.get("style", "cinematic")
    duration = params.get("duration", 60)
    aspect_ratio = params.get("aspect_ratio", "16:9")
    
    # Create a message that will trigger the generate_scene_breakdown_tool
    message = f"Generate a scene breakdown for a {style} video about {prompt} with a duration of {duration} seconds and aspect ratio {aspect_ratio}."
    
    # Send detailed progress update
    await connection_manager.send_detailed_progress(
        task_id=task_id,
        progress=10,
        stage="scene_breakdown",
        message="Analyzing prompt and generating scene breakdown..."
    )
    
    # Run the agent
    result = await Runner.run(
        agent,
        message,
        context=context
    )
    
    # Extract the scene breakdown from the context
    scene_breakdown = context.get("scene_breakdown")
    
    # If no scene breakdown was generated, return an error
    if not scene_breakdown:
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message="Failed to generate scene breakdown. Please try again with a different prompt."
        )
        
        # Return error
        return {
            "error": "Failed to generate scene breakdown",
            "error_type": "generation_failure",
            "message": "The system was unable to generate a scene breakdown from your prompt. Please try again with a more detailed or different prompt."
        }
    
    # Store in Redis
    await redis_client.set_json(
        f"task:{task_id}:scene_breakdown", 
        scene_breakdown
    )
    
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="completed",
        progress=100,
        stage="scene_breakdown",
        message="Scene breakdown generated successfully"
    )
    
    return {
        "scene_breakdown": scene_breakdown,
        "message": "Scene breakdown generated successfully"
    }


async def handle_update_scene(
    task_id: str,
    user_id: str,
    params: Dict[str, Any],
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
) -> Dict[str, Any]:
    """
    Handle the update_scene command.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        params: Command parameters
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
        
    Returns:
        The result of the command
    """
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="processing",
        progress=0,
        stage="scene_update",
        message="Updating scene..."
    )
    
    # Get scene breakdown
    scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
    if not scene_breakdown:
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message="No scene breakdown found. Generate one first."
        )
        
        # Return error
        return {
            "error": "No scene breakdown found",
            "error_type": "missing_scene_breakdown",
            "message": "No scene breakdown found. You need to generate a scene breakdown before generating a video."
        }
    
    # Extract parameters
    scene_index = params.get("scene_index", 1)
    new_content = params.get("new_content", "")
    update_type = params.get("update_type", "both")
    
    # Adjust for 0-based indexing
    idx = scene_index - 1
    if idx < 0 or idx >= len(scene_breakdown["scenes"]):
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message=f"Scene index {scene_index} is out of range"
        )
        
        # Return error
        return {
            "error": f"Scene index {scene_index} is out of range",
            "error_type": "invalid_scene_index",
            "message": f"The scene index {scene_index} is out of range. Valid indices are 1 to {len(scene_breakdown['scenes'])}."
        }
    
    # Update the scene based on update_type
    if update_type in ["script", "both"]:
        scene_breakdown["scenes"][idx]["script"] = new_content
    
    if update_type in ["visual", "both"]:
        scene_breakdown["scenes"][idx]["video_prompt"] = new_content
    
    # Store in Redis
    await redis_client.set_json(
        f"task:{task_id}:scene_breakdown", 
        scene_breakdown
    )
    
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="completed",
        progress=100,
        stage="scene_update",
        message="Scene updated successfully"
    )
    
    return {
        "scene_breakdown": scene_breakdown,
        "message": f"Scene {scene_index} updated successfully"
    }


async def handle_generate_video(
    task_id: str,
    user_id: str,
    params: Dict[str, Any],
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
) -> Dict[str, Any]:
    """
    Handle the generate_video command.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        params: Command parameters
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
        
    Returns:
        The result of the command
    """
    # Get scene breakdown
    scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
    if not scene_breakdown:
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message="No scene breakdown found. Generate one first."
        )
        
        # Return error
        return {
            "error": "No scene breakdown found",
            "error_type": "missing_scene_breakdown",
            "message": "No scene breakdown found. You need to generate a scene breakdown before generating a video."
        }
    
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="processing",
        progress=0,
        stage="video_generation",
        message="Starting video generation..."
    )
    
    # In a real implementation, this would start the video generation pipeline
    # For now, we'll simulate progress updates
    asyncio.create_task(
        simulate_video_generation(task_id, task_manager, redis_client)
    )
    
    return {
        "status": "started",
        "estimated_time": "3-5 minutes",
        "message": "Video generation has started. You will receive updates as the process progresses."
    }


async def handle_check_generation_status(
    task_id: str,
    user_id: str,
    task_manager: EnhancedTaskManager
) -> Dict[str, Any]:
    """
    Handle the check_generation_status command.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        task_manager: Task manager for task operations
        
    Returns:
        The result of the command
    """
    # Get generation status
    status = await task_manager.get_task_status(task_id)
    if not status:
        return {
            "status": "unknown",
            "progress": 0,
            "message": "No generation status found"
        }
    
    return status


async def handle_adjust_scene_duration(
    task_id: str,
    user_id: str,
    params: Dict[str, Any],
    redis_client: RedisClient,
    task_manager: EnhancedTaskManager
) -> Dict[str, Any]:
    """
    Handle the adjust_scene_duration command.
    
    Args:
        task_id: The task ID
        user_id: The user ID
        params: Command parameters
        redis_client: Redis client for persistence
        task_manager: Task manager for task operations
        
    Returns:
        The result of the command
    """
    from app.ai.utils.duration import SceneDurationManager
    
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="processing",
        progress=0,
        stage="duration_adjustment",
        message="Adjusting scene durations..."
    )
    
    # Get scene breakdown
    scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
    if not scene_breakdown:
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message="No scene breakdown found. Generate one first."
        )
        
        # Return error
        return {
            "error": "No scene breakdown found",
            "error_type": "missing_scene_breakdown",
            "message": "No scene breakdown found. You need to generate a scene breakdown before adjusting scene durations."
        }
    
    # Extract parameters
    scene_index = params.get("scene_index")
    new_duration = params.get("duration")
    total_duration = params.get("total_duration")
    
    # Get current durations
    scenes = scene_breakdown.get("scenes", [])
    current_durations = [scene.get("duration", 5.0) for scene in scenes]
    
    # If total_duration is provided, recalculate all durations
    if total_duration:
        target_durations = SceneDurationManager.calculate_scene_durations(
            scenes=scenes,
            total_duration=float(total_duration),
            min_scene_duration=3.0
        )
    # If scene_index and new_duration are provided, adjust that specific scene
    elif scene_index is not None and new_duration is not None:
        # Adjust for 0-based indexing
        idx = int(scene_index) - 1
        if idx < 0 or idx >= len(scenes):
            # Update task status to error
            await task_manager.update_task_status(
                task_id=task_id,
                status="error",
                progress=100,
                stage="error",
                message=f"Scene index {scene_index} is out of range"
            )
            
            # Return error
            return {
                "error": f"Scene index {scene_index} is out of range",
                "error_type": "invalid_scene_index",
                "message": f"The scene index {scene_index} is out of range. Valid indices are 1 to {len(scenes)}."
            }
        
        target_durations = SceneDurationManager.redistribute_durations(
            current_durations=current_durations,
            index=idx,
            operation="modify",
            new_duration=float(new_duration),
            min_scene_duration=3.0
        )
    else:
        # Update task status to error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message="Missing required parameters for scene duration adjustment"
        )
        
        # Return error
        return {
            "error": "Missing required parameters",
            "error_type": "missing_parameters",
            "message": "Either scene_index and duration, or total_duration must be provided to adjust scene durations."
        }
    
    # Update scene durations
    updated_scenes = SceneDurationManager.adjust_scene_durations(
        scenes=scenes,
        target_durations=target_durations
    )
    
    # Update scene breakdown
    scene_breakdown["scenes"] = updated_scenes
    scene_breakdown["estimated_duration"] = sum(target_durations)
    
    # Store in Redis
    await redis_client.set_json(
        f"task:{task_id}:scene_breakdown", 
        scene_breakdown
    )
    
    # Update task status
    await task_manager.update_task_status(
        task_id=task_id,
        status="completed",
        progress=100,
        stage="duration_adjustment",
        message="Scene durations adjusted successfully"
    )
    
    return {
        "scene_breakdown": scene_breakdown,
        "message": "Scene durations adjusted successfully",
        "durations": target_durations
    }


async def simulate_video_generation(
    task_id: str, 
    task_manager: EnhancedTaskManager,
    redis_client: RedisClient
):
    """
    Simulate video generation progress.
    
    Args:
        task_id: The task ID
        task_manager: Task manager for task operations
        redis_client: Redis client for persistence
    """
    try:
        # Get scene breakdown
        scene_breakdown = await redis_client.get_json(f"task:{task_id}:scene_breakdown")
        if not scene_breakdown:
            await task_manager.update_task_status(
                task_id=task_id,
                status="error",
                progress=100,
                stage="error",
                message="No scene breakdown found"
            )
            return
        
        # Get number of scenes
        num_scenes = len(scene_breakdown.get("scenes", []))
        
        # Simulate progress updates
        stages = [
            {"progress": 10, "stage": "video_generation", "substage": "character_generation", "message": "Generating character profiles"},
            {"progress": 20, "stage": "video_generation", "substage": "scene_images", "message": "Generating scene images"},
            {"progress": 40, "stage": "video_generation", "substage": "scene_audio", "message": "Generating scene audio"},
            {"progress": 60, "stage": "video_generation", "substage": "background_music", "message": "Generating background music"},
            {"progress": 80, "stage": "video_generation", "substage": "composing", "message": "Composing final video"},
            {"progress": 100, "stage": "video_generation", "substage": "completed", "message": "Video generation complete"}
        ]
        
        # Calculate ETA
        start_time = time.time()
        estimated_duration = 15  # seconds
        eta = start_time + estimated_duration
        
        # Simulate steps
        completed_steps = []
        pending_steps = ["Character Generation", "Scene Images", "Scene Audio", "Background Music", "Video Composition"]
        
        for i, stage in enumerate(stages):
            # Update status
            await task_manager.update_task_status(
                task_id=task_id,
                status="processing" if stage["progress"] < 100 else "completed",
                progress=stage["progress"],
                stage=stage["stage"],
                substage=stage["substage"],
                message=stage["message"]
            )
            
            # Update steps
            if i > 0:
                completed_steps.append(pending_steps[0])
                pending_steps = pending_steps[1:]
            
            current_step = pending_steps[0] if pending_steps else None
            
            # Broadcast to all connections
            await connection_manager.send_detailed_progress(
                task_id=task_id,
                progress=stage["progress"],
                stage=stage["stage"],
                substage=stage["substage"],
                message=stage["message"],
                eta=eta,
                completed_steps=completed_steps,
                current_step=current_step,
                pending_steps=pending_steps[1:] if len(pending_steps) > 1 else []
            )
            
            # Wait a bit
            await asyncio.sleep(3)
        
        # Set the final video URL
        await redis_client.set_json(
            f"task:{task_id}:result",
            {
                "video_url": f"https://example.com/videos/{task_id}.mp4",
                "thumbnail_url": f"https://example.com/thumbnails/{task_id}.jpg",
                "created_at": time.time()
            }
        )
        
        # Send completion message
        await connection_manager.send_completion(
            task_id=task_id,
            result={
                "video_url": f"https://example.com/videos/{task_id}.mp4",
                "thumbnail_url": f"https://example.com/thumbnails/{task_id}.jpg",
                "message": "Video generation complete"
            }
        )
        
    except Exception as e:
        logger.error(f"Error simulating video generation: {str(e)}")
        
        # Update status with error
        await task_manager.update_task_status(
            task_id=task_id,
            status="error",
            progress=100,
            stage="error",
            message=f"Error: {str(e)}"
        )
        
        # Send error message
        await connection_manager.send_error(
            task_id=task_id,
            error=f"Error generating video: {str(e)}"
        )
