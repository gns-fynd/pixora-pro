"""
Tasks router for the Pixora AI platform.

This module provides API endpoints for task management.
"""
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User
from app.services.redis_client import RedisClient

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


class TaskStatusResponse(BaseModel):
    """
    Response model for task status.
    """
    task_id: str = Field(..., description="The task ID")
    user_id: str = Field(..., description="The user ID")
    status: str = Field(..., description="The status of the task")
    progress: float = Field(..., description="The progress of the task (0-100)")
    message: Optional[str] = Field(None, description="A message describing the current status")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the task")
    created_at: float = Field(..., description="The creation timestamp")
    updated_at: float = Field(..., description="The last update timestamp")


class TaskSummaryResponse(BaseModel):
    """
    Response model for task summary.
    """
    task_id: str = Field(..., description="The task ID")
    status: str = Field(..., description="The status of the task")
    progress: float = Field(..., description="The progress of the task (0-100)")
    created_at: float = Field(..., description="The creation timestamp")
    updated_at: float = Field(..., description="The last update timestamp")


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a task.
    """
    # Create Redis client directly
    from app.core.config import get_settings
    redis_client = RedisClient(get_settings())
    
    # Get the task data
    task_data = await redis_client.get_task(task_id)
    
    if not task_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if the task belongs to the current user
    if task_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )
    
    return task_data


@router.get("/user", response_model=List[TaskSummaryResponse])
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
):
    """
    Get all tasks for the current user.
    """
    # Create Redis client directly
    from app.core.config import get_settings
    redis_client = RedisClient(get_settings())
    
    # Get the task IDs for the user
    task_ids = await redis_client.get_user_tasks(current_user.id)
    
    # Get the task data for each task
    tasks = []
    for task_id in task_ids:
        task_data = await redis_client.get_task(task_id)
        if task_data:
            # Create a summary of the task
            tasks.append({
                "task_id": task_id,
                "status": task_data.get("status", "unknown"),
                "progress": task_data.get("progress", 0),
                "created_at": task_data.get("created_at", 0),
                "updated_at": task_data.get("updated_at", 0)
            })
    
    # Sort tasks by creation time (newest first)
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return tasks
