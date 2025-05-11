"""
Task manager for handling asynchronous video generation tasks.
"""
import asyncio
import logging
import time
import json
from typing import Dict, Optional, List, Callable, Any, Union
from datetime import datetime

from app.core.config import get_settings
from app.ai.models.task import Task, TaskStatus, TaskStage, ProgressCallback
from app.services.redis_client import RedisClient

# Set up logging
logger = logging.getLogger(__name__)


class TaskManager:
    """Manager for asynchronous video generation tasks."""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize the task manager.
        
        Args:
            redis_client: Optional Redis client for task persistence
        """
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.settings = get_settings()
        self.semaphore = asyncio.Semaphore(5)  # Default to 5 concurrent tasks
        self.redis_client = redis_client
    
    def create_task(self, prompt: str, duration: int, style: str, user_id: Optional[str] = None) -> Task:
        """
        Create a new task and return it.
        
        Args:
            prompt: The prompt for the video
            duration: The duration of the video in seconds
            style: The style of the video
            user_id: Optional user ID for tracking ownership
            
        Returns:
            The created task
        """
        task = Task(
            prompt=prompt,
            duration=duration,
            style=style,
            user_id=user_id,
        )
        self.tasks[task.id] = task
        logger.info(f"Created task {task.id}")
        
        # Store the task in Redis if available
        if self.redis_client:
            asyncio.create_task(self._store_task_in_redis(task))
        
        return task
    
    async def _store_task_in_redis(self, task: Task) -> None:
        """
        Store a task in Redis.
        
        Args:
            task: The task to store
        """
        if not self.redis_client:
            return
        
        try:
            # Store the task data
            await self.redis_client.set_json(f"task:{task.id}", task.to_dict())
            
            # Store the initial progress
            await self.redis_client.set_json(
                f"task:{task.id}:progress",
                {
                    "progress": task.progress,
                    "message": "Task created",
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "updated_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error storing task in Redis: {e}")
    
    async def get_task_from_redis(self, task_id: str) -> Optional[Task]:
        """
        Get a task from Redis.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task, or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            # Get the task data
            task_data = await self.redis_client.get_json(f"task:{task_id}")
            if not task_data:
                return None
            
            # Create a task from the data
            return Task.from_dict(task_data)
        except Exception as e:
            logger.error(f"Error getting task from Redis: {e}")
            return None
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task, or None if not found
        """
        # First check in-memory cache
        task = self.tasks.get(task_id)
        if task:
            return task
        
        # If not found and Redis is available, try to get from Redis
        if self.redis_client:
            # Create a task to get the task from Redis
            asyncio.create_task(self._get_task_from_redis_and_cache(task_id))
        
        return None
    
    async def _get_task_from_redis_and_cache(self, task_id: str) -> None:
        """
        Get a task from Redis and cache it in memory.
        
        Args:
            task_id: The task ID
        """
        task = await self.get_task_from_redis(task_id)
        if task:
            self.tasks[task_id] = task
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks.
        
        Returns:
            List of all tasks
        """
        return list(self.tasks.values())
    
    def get_active_tasks(self) -> List[Task]:
        """
        Get all active tasks (pending or processing).
        
        Returns:
            List of active tasks
        """
        return [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]
        ]
    
    async def start_task(
        self, 
        task_id: str, 
        process_func: Callable[[Task, ProgressCallback], Any],
        timeout_seconds: int = 3600
    ):
        """
        Start processing a task asynchronously.
        
        Args:
            task_id: The task ID
            process_func: The function to process the task
            timeout_seconds: Timeout in seconds
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        if task.status != TaskStatus.PENDING:
            logger.warning(f"Task {task_id} is already {task.status}")
            return
        
        # Update task status
        task.status = TaskStatus.PROCESSING
        task.update_progress(0, TaskStage.INITIALIZING)
        
        # Update task in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task)
        
        # Create progress callback
        async def progress_callback(progress: int, message: Optional[str] = None):
            if message:
                logger.info(f"Task {task_id}: {message} ({progress}%)")
            
            # Update task progress
            task.update_progress(progress)
            
            # Update progress in Redis if available
            if self.redis_client:
                try:
                    await self.redis_client.set_json(
                        f"task:{task_id}:progress",
                        {
                            "progress": progress,
                            "message": message or f"Processing: {progress}%",
                            "status": task.status.value,
                            "stage": task.stage.value,
                            "updated_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating progress in Redis: {e}")
        
        # Start the task with semaphore to limit concurrent tasks
        async def run_with_semaphore():
            async with self.semaphore:
                try:
                    # Set timeout for the task
                    await asyncio.wait_for(
                        process_func(task, progress_callback),
                        timeout=timeout_seconds
                    )
                    
                    # Update task in Redis if available
                    if self.redis_client:
                        await self._store_task_in_redis(task)
                        
                        # Store the result if completed
                        if task.status == TaskStatus.COMPLETED and task.video_url:
                            await self.redis_client.set_json(
                                f"task:{task_id}:result",
                                {
                                    "video_url": task.video_url,
                                    "task_id": task.id,
                                    "user_id": task.user_id,
                                    "prompt": task.prompt,
                                    "duration": task.duration,
                                    "style": task.style,
                                    "created_at": datetime.now().isoformat()
                                }
                            )
                    
                except asyncio.TimeoutError:
                    task.fail("Task timed out")
                    logger.error(f"Task {task_id} timed out after {timeout_seconds} seconds")
                    
                    # Update task in Redis if available
                    if self.redis_client:
                        await self._store_task_in_redis(task)
                        
                except Exception as e:
                    task.fail(str(e))
                    logger.exception(f"Error processing task {task_id}: {e}")
                    
                    # Update task in Redis if available
                    if self.redis_client:
                        await self._store_task_in_redis(task)
                        
                        # Store the error
                        await self.redis_client.set_json(
                            f"task:{task_id}:result",
                            {"error": str(e)}
                        )
                
                finally:
                    # Clean up
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
        
        # Store the running task
        self.running_tasks[task_id] = asyncio.create_task(run_with_semaphore())
        logger.info(f"Started task {task_id}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            logger.warning(f"Task {task_id} is already {task.status}")
            return False
        
        # Cancel the running task if it exists
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Update task status
        task.cancel()
        logger.info(f"Cancelled task {task_id}")
        
        # Update task in Redis if available
        if self.redis_client:
            await self._store_task_in_redis(task)
        
        return True
    
    async def cleanup_old_tasks(self, max_age_seconds: int = 86400) -> int:
        """
        Remove old completed or failed tasks.
        
        Args:
            max_age_seconds: Maximum age of tasks to keep in seconds
            
        Returns:
            Number of tasks removed
        """
        current_time = time.time()
        task_ids_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task_age = current_time - task.updated_at
                if task_age > max_age_seconds:
                    task_ids_to_remove.append(task_id)
        
        # Remove tasks from memory
        for task_id in task_ids_to_remove:
            del self.tasks[task_id]
            logger.info(f"Removed old task {task_id} from memory")
        
        # Remove tasks from Redis if available
        if self.redis_client:
            for task_id in task_ids_to_remove:
                try:
                    await self.redis_client.delete(f"task:{task_id}")
                    await self.redis_client.delete(f"task:{task_id}:progress")
                    await self.redis_client.delete(f"task:{task_id}:result")
                    logger.info(f"Removed old task {task_id} from Redis")
                except Exception as e:
                    logger.error(f"Error removing task {task_id} from Redis: {e}")
        
        return len(task_ids_to_remove)
