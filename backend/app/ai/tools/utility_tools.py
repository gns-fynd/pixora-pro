"""
Utility tools for Pixora AI Agent.

This module provides utility tools for task management, progress tracking, etc.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from app.ai.tools.base import Tool
from app.services.redis_client import RedisClient


# Set up logging
logger = logging.getLogger(__name__)


class ProgressTrackingTool(Tool):
    """Tool for tracking progress of a task."""
    
    def __init__(self, redis_client: RedisClient):
        super().__init__(
            name="track_progress",
            description="Tracks progress of a task",
            parameters_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to track"
                    },
                    "progress": {
                        "type": "number",
                        "description": "Progress value (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "status": {
                        "type": "string",
                        "description": "Status message"
                    },
                    "step": {
                        "type": "string",
                        "description": "Current step name"
                    }
                },
                "required": ["task_id", "progress"]
            }
        )
        self.redis_client = redis_client
        
    async def execute(
        self, 
        task_id: str, 
        progress: float, 
        status: str = "", 
        step: Optional[str] = None
    ) -> str:
        """
        Track progress of a task.
        
        Args:
            task_id: ID of the task to track
            progress: Progress value (0-100)
            status: Status message
            step: Current step name
            
        Returns:
            JSON string containing the updated progress information
        """
        try:
            # Update the task progress in Redis
            updates = {
                "progress": progress,
                "status": status or f"Processing: {progress:.0f}%"
            }
            
            if step:
                updates["step"] = step
                
            await self.redis_client.update_task(task_id, updates)
            
            # Return the updated progress
            return json.dumps({
                "task_id": task_id,
                "progress": progress,
                "status": status or f"Processing: {progress:.0f}%",
                "step": step
            })
        except Exception as e:
            logger.error(f"Error tracking progress: {str(e)}")
            return json.dumps({
                "error": f"Progress tracking failed: {str(e)}"
            })


class TaskManagementTool(Tool):
    """Tool for managing tasks."""
    
    def __init__(self, task_manager):
        super().__init__(
            name="manage_task",
            description="Manages tasks (get status, list tasks, etc.)",
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform",
                        "enum": ["get_status", "list_tasks", "get_task"]
                    },
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task (for get_status and get_task actions)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "ID of the user (for list_tasks action)"
                    }
                },
                "required": ["action"]
            }
        )
        self.task_manager = task_manager
        
    async def execute(
        self, 
        action: str, 
        task_id: Optional[str] = None, 
        user_id: Optional[str] = None
    ) -> str:
        """
        Manage tasks.
        
        Args:
            action: Action to perform
            task_id: ID of the task (for get_status and get_task actions)
            user_id: ID of the user (for list_tasks action)
            
        Returns:
            JSON string containing the action result
        """
        try:
            if action == "get_status" and task_id:
                # Get the task status
                status = await self.task_manager.get_task_status(task_id)
                return json.dumps(status)
                
            elif action == "list_tasks" and user_id:
                # List tasks for the user
                tasks = await self.task_manager.list_user_tasks(user_id)
                return json.dumps({"tasks": tasks})
                
            elif action == "get_task" and task_id:
                # Get the task
                task = await self.task_manager.get_task(task_id)
                if task:
                    return json.dumps({
                        "task_id": task.task_id,
                        "prompt": task.prompt,
                        "progress": task.progress,
                        "status": task.status,
                        "is_complete": task.is_complete,
                        "error": task.error
                    })
                else:
                    return json.dumps({"error": "Task not found"})
                    
            else:
                return json.dumps({"error": "Invalid action or missing required parameters"})
        except Exception as e:
            logger.error(f"Error managing task: {str(e)}")
            return json.dumps({
                "error": f"Task management failed: {str(e)}"
            })


class UserPreferenceTool(Tool):
    """Tool for managing user preferences."""
    
    def __init__(self, user_id: str, redis_client: RedisClient):
        super().__init__(
            name="manage_preferences",
            description="Manages user preferences",
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform",
                        "enum": ["get", "set", "delete"]
                    },
                    "key": {
                        "type": "string",
                        "description": "Preference key"
                    },
                    "value": {
                        "type": "object",
                        "description": "Preference value (for set action)"
                    }
                },
                "required": ["action", "key"]
            }
        )
        self.user_id = user_id
        self.redis_client = redis_client
        
    async def execute(
        self, 
        action: str, 
        key: str, 
        value: Optional[Any] = None
    ) -> str:
        """
        Manage user preferences.
        
        Args:
            action: Action to perform
            key: Preference key
            value: Preference value (for set action)
            
        Returns:
            JSON string containing the action result
        """
        try:
            # Construct the Redis key for the preference
            pref_key = f"user:{self.user_id}:pref:{key}"
            
            if action == "get":
                # Get the preference
                pref_value = await self.redis_client.get(pref_key)
                return json.dumps({
                    "key": key,
                    "value": pref_value
                })
                
            elif action == "set" and value is not None:
                # Set the preference
                await self.redis_client.set(pref_key, value)
                return json.dumps({
                    "key": key,
                    "value": value,
                    "message": "Preference set successfully"
                })
                
            elif action == "delete":
                # Delete the preference
                await self.redis_client.delete(pref_key)
                return json.dumps({
                    "key": key,
                    "message": "Preference deleted successfully"
                })
                
            else:
                return json.dumps({"error": "Invalid action or missing required parameters"})
        except Exception as e:
            logger.error(f"Error managing preference: {str(e)}")
            return json.dumps({
                "error": f"Preference management failed: {str(e)}"
            })


class ErrorHandlingTool(Tool):
    """Tool for handling errors."""
    
    def __init__(self):
        super().__init__(
            name="handle_error",
            description="Handles errors and provides recovery options",
            parameters_schema={
                "type": "object",
                "properties": {
                    "error_message": {
                        "type": "string",
                        "description": "Error message"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "Type of error",
                        "enum": ["api_error", "validation_error", "resource_error", "timeout_error", "unknown_error"]
                    },
                    "context": {
                        "type": "object",
                        "description": "Context information about the error"
                    },
                    "recovery_strategy": {
                        "type": "string",
                        "description": "Strategy for recovery",
                        "enum": ["retry", "fallback", "abort", "user_intervention"]
                    }
                },
                "required": ["error_message"]
            }
        )
        
    async def execute(
        self, 
        error_message: str, 
        error_type: str = "unknown_error", 
        context: Optional[Dict[str, Any]] = None,
        recovery_strategy: str = "fallback"
    ) -> str:
        """
        Handle an error.
        
        Args:
            error_message: Error message
            error_type: Type of error
            context: Context information about the error
            recovery_strategy: Strategy for recovery
            
        Returns:
            JSON string containing the error handling result
        """
        try:
            # Log the error
            logger.error(f"Error handled by ErrorHandlingTool: {error_message} (Type: {error_type})")
            
            # Prepare the response based on the recovery strategy
            if recovery_strategy == "retry":
                response = {
                    "message": "Retrying the operation",
                    "user_message": "I encountered an issue, but I'm trying again.",
                    "should_retry": True
                }
            elif recovery_strategy == "fallback":
                response = {
                    "message": "Using fallback option",
                    "user_message": "I encountered an issue, so I'm using an alternative approach.",
                    "should_fallback": True
                }
            elif recovery_strategy == "abort":
                response = {
                    "message": "Aborting the operation",
                    "user_message": f"I'm unable to complete this operation due to an error: {error_message}",
                    "should_abort": True
                }
            elif recovery_strategy == "user_intervention":
                response = {
                    "message": "Requesting user intervention",
                    "user_message": f"I need your help to resolve an issue: {error_message}. Could you provide more information or try a different approach?",
                    "should_ask_user": True
                }
            else:
                response = {
                    "message": "Unknown recovery strategy",
                    "user_message": f"I encountered an error: {error_message}",
                    "should_abort": True
                }
                
            # Add error details to the response
            response.update({
                "error_message": error_message,
                "error_type": error_type,
                "context": context or {}
            })
            
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error in error handling: {str(e)}")
            return json.dumps({
                "error": f"Error handling failed: {str(e)}",
                "original_error": error_message
            })
