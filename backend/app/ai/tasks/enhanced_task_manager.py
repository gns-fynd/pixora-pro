"""
Enhanced task manager for handling asynchronous video generation tasks.

This module provides an enhanced task manager with improved task lifecycle management,
better Redis integration, and error recovery mechanisms.
"""
import asyncio
import logging
import time
import json
import uuid
from enum import Enum
from typing import Dict, Optional, List, Callable, Any, Union, TypeVar, Generic
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.ai.models.task import Task, TaskStatus, TaskStage, ProgressCallback
from app.services.redis_client import RedisClient
from app.ai.sdk.context import TaskContext


# Set up logging
logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """Priority levels for tasks."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskState(BaseModel):
    """Model for task state."""
    id: str
    status: TaskStatus
    stage: TaskStage
    progress: int
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    priority: TaskPriority = TaskPriority.NORMAL
    paused_at: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    checkpoint: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class EnhancedTaskManager:
    """Enhanced manager for asynchronous video generation tasks."""
    
    def __init__(
        self, 
        redis_client: Optional[RedisClient] = None,
        max_concurrent_tasks: int = 5,
        task_timeout_seconds: int = 3600,
        cleanup_interval_seconds: int = 3600,
        max_task_age_days: int = 7
    ):
        """
        Initialize the enhanced task manager.
        
        Args:
            redis_client: Optional Redis client for task persistence
            max_concurrent_tasks: Maximum number of concurrent tasks
            task_timeout_seconds: Default timeout for tasks in seconds
            cleanup_interval_seconds: Interval for cleaning up old tasks
            max_task_age_days: Maximum age of completed tasks in days
        """
        self.tasks: Dict[str, TaskState] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.paused_tasks: Dict[str, TaskState] = {}
        self.settings = get_settings()
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.redis_client = redis_client
        self.task_timeout_seconds = task_timeout_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.max_task_age_days = max_task_age_days
        
        # Start the cleanup task
        if redis_client:
            asyncio.create_task(self._periodic_cleanup())
    
    async def create_task(
        self, 
        prompt: str, 
        duration: int, 
        style: str, 
        user_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskState:
        """
        Create a new task and return it.
        
        Args:
            prompt: The prompt for the video
            duration: The duration of the video in seconds
            style: The style of the video
            user_id: Optional user ID for tracking ownership
            priority: Priority level for the task
            metadata: Optional additional metadata
            
        Returns:
            The created task state
        """
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task state
        task_state = TaskState(
            id=task_id,
            status=TaskStatus.PENDING,
            stage=TaskStage.INITIALIZING,
            progress=0,
            created_at=time.time(),
            updated_at=time.time(),
            priority=priority,
            metadata=metadata or {
                "prompt": prompt,
                "duration": duration,
                "style": style,
                "user_id": user_id
            }
        )
        
        # Store in memory
        self.tasks[task_id] = task_state
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        logger.info(f"Created task {task_id} with priority {priority.name}")
        
        return task_state
    
    async def _store_task_in_redis(self, task_state: TaskState) -> None:
        """
        Store a task in Redis.
        
        Args:
            task_state: The task state to store
        """
        if not self.redis_client:
            return
        
        try:
            # Store the task data with TTL based on status
            ttl = None
            if task_state.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                # Set TTL for completed/failed/cancelled tasks
                ttl = self.max_task_age_days * 24 * 60 * 60  # days to seconds
            
            # Store the task state
            await self.redis_client.set_json(
                f"task:{task_state.id}:state",
                task_state.dict(),
                ttl=ttl
            )
            
            # Store the initial progress
            await self.redis_client.set_json(
                f"task:{task_state.id}:progress",
                {
                    "progress": task_state.progress,
                    "message": "Task created",
                    "status": task_state.status,
                    "stage": task_state.stage,
                    "updated_at": datetime.now().isoformat()
                },
                ttl=ttl
            )
            
            # Add to user's task list if user_id is provided
            user_id = task_state.metadata.get("user_id")
            if user_id:
                # Get existing user tasks
                user_tasks = await self.redis_client.get_json(f"user:{user_id}:tasks") or []
                
                # Add this task if not already in the list
                if task_state.id not in user_tasks:
                    user_tasks.append(task_state.id)
                    await self.redis_client.set_json(f"user:{user_id}:tasks", user_tasks)
        
        except Exception as e:
            logger.error(f"Error storing task in Redis: {e}")
    
    async def get_task_from_redis(self, task_id: str) -> Optional[TaskState]:
        """
        Get a task from Redis.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task state, or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            # Get the task data
            task_data = await self.redis_client.get_json(f"task:{task_id}:state")
            if not task_data:
                return None
            
            # Create a task state from the data
            return TaskState(**task_data)
        
        except Exception as e:
            logger.error(f"Error getting task from Redis: {e}")
            return None
    
    async def get_task(self, task_id: str) -> Optional[TaskState]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task state, or None if not found
        """
        # First check in-memory cache
        task_state = self.tasks.get(task_id)
        if task_state:
            return task_state
        
        # If not found and Redis is available, try to get from Redis
        if self.redis_client:
            task_state = await self.get_task_from_redis(task_id)
            if task_state:
                # Cache in memory
                self.tasks[task_id] = task_state
                return task_state
        
        return None
    
    async def get_user_tasks(self, user_id: str) -> List[TaskState]:
        """
        Get all tasks for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of task states
        """
        if not self.redis_client:
            # If Redis is not available, filter in-memory tasks
            return [
                task for task in self.tasks.values()
                if task.metadata.get("user_id") == user_id
            ]
        
        try:
            # Get task IDs from Redis
            task_ids = await self.redis_client.get_json(f"user:{user_id}:tasks") or []
            
            # Get task states
            tasks = []
            for task_id in task_ids:
                task_state = await self.get_task(task_id)
                if task_state:
                    tasks.append(task_state)
            
            return tasks
        
        except Exception as e:
            logger.error(f"Error getting user tasks from Redis: {e}")
            return []
    
    async def get_all_tasks(self) -> List[TaskState]:
        """
        Get all tasks.
        
        Returns:
            List of all task states
        """
        return list(self.tasks.values())
    
    async def get_active_tasks(self) -> List[TaskState]:
        """
        Get all active tasks (pending or processing).
        
        Returns:
            List of active task states
        """
        return [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]
        ]
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        error: Optional[str] = None
    ) -> Optional[TaskState]:
        """
        Update the status of a task.
        
        Args:
            task_id: The task ID
            status: The new status
            error: Optional error message for failed tasks
            
        Returns:
            The updated task state, or None if not found
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return None
        
        # Update status
        task_state.status = status
        task_state.updated_at = time.time()
        
        # Set completed_at if completed
        if status == TaskStatus.COMPLETED and not task_state.completed_at:
            task_state.completed_at = time.time()
        
        # Set error if provided
        if error:
            task_state.error = error
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        logger.info(f"Updated task {task_id} status to {status.name}")
        
        return task_state
    
    async def update_task_progress(
        self, 
        task_id: str, 
        progress: int, 
        stage: Optional[TaskStage] = None,
        message: Optional[str] = None
    ) -> Optional[TaskState]:
        """
        Update the progress of a task.
        
        Args:
            task_id: The task ID
            progress: The new progress percentage (0-100)
            stage: Optional new stage
            message: Optional progress message
            
        Returns:
            The updated task state, or None if not found
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return None
        
        # Update progress
        task_state.progress = progress
        task_state.updated_at = time.time()
        
        # Update stage if provided
        if stage:
            task_state.stage = stage
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
            
            # Store progress update
            if message:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": progress,
                        "message": message,
                        "status": task_state.status,
                        "stage": task_state.stage,
                        "updated_at": datetime.now().isoformat()
                    }
                )
        
        if message:
            logger.info(f"Task {task_id}: {message} ({progress}%)")
        else:
            logger.info(f"Updated task {task_id} progress to {progress}%")
        
        return task_state
    
    async def set_task_checkpoint(
        self, 
        task_id: str, 
        checkpoint: Dict[str, Any]
    ) -> Optional[TaskState]:
        """
        Set a checkpoint for a task to enable recovery.
        
        Args:
            task_id: The task ID
            checkpoint: Checkpoint data
            
        Returns:
            The updated task state, or None if not found
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return None
        
        # Update checkpoint
        task_state.checkpoint = checkpoint
        task_state.updated_at = time.time()
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
            
            # Store checkpoint separately for faster access
            await self.redis_client.set_json(
                f"task:{task_id}:checkpoint",
                checkpoint
            )
        
        logger.info(f"Set checkpoint for task {task_id}")
        
        return task_state
    
    async def get_task_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the checkpoint for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The checkpoint data, or None if not found
        """
        # First try to get from Redis for faster access
        if self.redis_client:
            checkpoint = await self.redis_client.get_json(f"task:{task_id}:checkpoint")
            if checkpoint:
                return checkpoint
        
        # Fall back to task state
        task_state = await self.get_task(task_id)
        if task_state and task_state.checkpoint:
            return task_state.checkpoint
        
        return None
    
    async def pause_task(self, task_id: str) -> bool:
        """
        Pause a running task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if the task was paused, False otherwise
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_state.status != TaskStatus.PROCESSING:
            logger.warning(f"Task {task_id} is not processing (current status: {task_state.status})")
            return False
        
        # Cancel the running task if it exists
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Update task state
        task_state.status = TaskStatus.PENDING  # Set back to pending for resume
        task_state.paused_at = time.time()
        task_state.updated_at = time.time()
        
        # Move to paused tasks
        self.paused_tasks[task_id] = task_state
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        logger.info(f"Paused task {task_id}")
        
        return True
    
    async def resume_task(
        self, 
        task_id: str, 
        process_func: Callable[[TaskContext, ProgressCallback], Any]
    ) -> bool:
        """
        Resume a paused task.
        
        Args:
            task_id: The task ID
            process_func: The function to process the task
            
        Returns:
            True if the task was resumed, False otherwise
        """
        # Check if task is in paused tasks
        if task_id not in self.paused_tasks:
            # Try to get from Redis
            task_state = await self.get_task(task_id)
            if not task_state or task_state.paused_at is None:
                logger.error(f"Task {task_id} is not paused")
                return False
        else:
            task_state = self.paused_tasks[task_id]
            # Remove from paused tasks
            del self.paused_tasks[task_id]
        
        # Update task state
        task_state.status = TaskStatus.PROCESSING
        task_state.updated_at = time.time()
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        # Start the task
        await self.start_task(
            task_id=task_id,
            process_func=process_func,
            timeout_seconds=self.task_timeout_seconds
        )
        
        logger.info(f"Resumed task {task_id}")
        
        return True
    
    async def retry_task(
        self, 
        task_id: str, 
        process_func: Callable[[TaskContext, ProgressCallback], Any]
    ) -> bool:
        """
        Retry a failed task.
        
        Args:
            task_id: The task ID
            process_func: The function to process the task
            
        Returns:
            True if the task was retried, False otherwise
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_state.status != TaskStatus.FAILED:
            logger.warning(f"Task {task_id} is not failed (current status: {task_state.status})")
            return False
        
        if task_state.retry_count >= task_state.max_retries:
            logger.warning(f"Task {task_id} has reached maximum retry count ({task_state.max_retries})")
            return False
        
        # Update task state
        task_state.status = TaskStatus.PENDING
        task_state.retry_count += 1
        task_state.error = None
        task_state.updated_at = time.time()
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        # Start the task
        await self.start_task(
            task_id=task_id,
            process_func=process_func,
            timeout_seconds=self.task_timeout_seconds
        )
        
        logger.info(f"Retrying task {task_id} (attempt {task_state.retry_count})")
        
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_state.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            logger.warning(f"Task {task_id} is already {task_state.status}")
            return False
        
        # Cancel the running task if it exists
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Remove from paused tasks if it exists
        if task_id in self.paused_tasks:
            del self.paused_tasks[task_id]
        
        # Update task state
        task_state.status = TaskStatus.CANCELLED
        task_state.updated_at = time.time()
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        logger.info(f"Cancelled task {task_id}")
        
        return True
    
    async def start_task(
        self, 
        task_id: str, 
        process_func: Callable[[TaskContext, ProgressCallback], Any],
        timeout_seconds: Optional[int] = None
    ) -> bool:
        """
        Start processing a task asynchronously.
        
        Args:
            task_id: The task ID
            process_func: The function to process the task
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            True if the task was started, False otherwise
        """
        task_state = await self.get_task(task_id)
        if not task_state:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_state.status != TaskStatus.PENDING:
            logger.warning(f"Task {task_id} is not pending (current status: {task_state.status})")
            return False
        
        # Update task status
        task_state.status = TaskStatus.PROCESSING
        task_state.updated_at = time.time()
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task_state)
        
        # Create task context
        context = TaskContext(
            task_id=task_id,
            user_id=task_state.metadata.get("user_id"),
            redis_client=self.redis_client
        )
        
        # Load context from Redis if available
        if self.redis_client:
            await context.load_from_redis()
        
        # Create progress callback
        async def progress_callback(progress: int, message: Optional[str] = None):
            await self.update_task_progress(task_id, progress, message=message)
        
        # Use provided timeout or default
        timeout = timeout_seconds or self.task_timeout_seconds
        
        # Start the task with semaphore to limit concurrent tasks
        async def run_with_semaphore():
            async with self.semaphore:
                try:
                    # Set timeout for the task
                    await asyncio.wait_for(
                        process_func(context, progress_callback),
                        timeout=timeout
                    )
                    
                    # Update task status to completed
                    await self.update_task_status(task_id, TaskStatus.COMPLETED)
                    
                except asyncio.TimeoutError:
                    # Handle timeout
                    await self.update_task_status(
                        task_id, 
                        TaskStatus.FAILED,
                        error=f"Task timed out after {timeout} seconds"
                    )
                    logger.error(f"Task {task_id} timed out after {timeout} seconds")
                    
                except asyncio.CancelledError:
                    # Handle cancellation
                    logger.info(f"Task {task_id} was cancelled")
                    
                except Exception as e:
                    # Handle other exceptions
                    await self.update_task_status(
                        task_id, 
                        TaskStatus.FAILED,
                        error=str(e)
                    )
                    logger.exception(f"Error processing task {task_id}: {e}")
                    
                finally:
                    # Clean up
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
        
        # Store the running task
        self.running_tasks[task_id] = asyncio.create_task(run_with_semaphore())
        logger.info(f"Started task {task_id}")
        
        return True
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old tasks."""
        while True:
            try:
                # Sleep first to avoid immediate cleanup on startup
                await asyncio.sleep(self.cleanup_interval_seconds)
                
                # Clean up old tasks
                await self.cleanup_old_tasks()
                
            except asyncio.CancelledError:
                # Handle cancellation
                break
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                # Sleep a bit to avoid tight loop on error
                await asyncio.sleep(60)
    
    async def cleanup_old_tasks(self) -> int:
        """
        Remove old completed, failed, or cancelled tasks.
        
        Returns:
            Number of tasks removed
        """
        # Calculate cutoff time
        cutoff_time = time.time() - (self.max_task_age_days * 24 * 60 * 60)
        
        # Find tasks to remove
        task_ids_to_remove = []
        for task_id, task_state in self.tasks.items():
            if task_state.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task_state.updated_at < cutoff_time:
                    task_ids_to_remove.append(task_id)
        
        # Remove tasks from memory
        for task_id in task_ids_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
            
            if task_id in self.paused_tasks:
                del self.paused_tasks[task_id]
            
            logger.info(f"Removed old task {task_id} from memory")
        
        # Remove tasks from Redis if available
        if self.redis_client:
            for task_id in task_ids_to_remove:
                try:
                    # Get user ID to remove from user's task list
                    task_state = await self.get_task_from_redis(task_id)
                    user_id = task_state.metadata.get("user_id") if task_state else None
                    
                    # Remove task data
                    await self.redis_client.delete(f"task:{task_id}:state")
                    await self.redis_client.delete(f"task:{task_id}:progress")
                    await self.redis_client.delete(f"task:{task_id}:progress_history")
                    await self.redis_client.delete(f"task:{task_id}:checkpoint")
                    await self.redis_client.delete(f"task:{task_id}:context")
                    await self.redis_client.delete(f"task:{task_id}:messages")
                    await self.redis_client.delete(f"task:{task_id}:assets")
                    await self.redis_client.delete(f"task:{task_id}:scene_data")
                    
                    # Remove from user's task list
                    if user_id:
                        user_tasks = await self.redis_client.get_json(f"user:{user_id}:tasks") or []
                        if task_id in user_tasks:
                            user_tasks.remove(task_id)
                            await self.redis_client.set_json(f"user:{user_id}:tasks", user_tasks)
                    
                    logger.info(f"Removed old task {task_id} from Redis")
                    
                except Exception as e:
                    logger.error(f"Error removing task {task_id} from Redis: {e}")
        
        return len(task_ids_to_remove)
