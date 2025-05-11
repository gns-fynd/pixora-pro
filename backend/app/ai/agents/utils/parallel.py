"""
Utilities for parallel execution of tasks.
"""
import asyncio
import logging
import time
from typing import List, Callable, Any, TypeVar, Awaitable, Optional, Dict

# Set up logging
logger = logging.getLogger(__name__)

# Generic type for the result of a task
T = TypeVar('T')


class ParallelExecutor:
    """Utility for executing tasks in parallel."""
    
    def __init__(self, max_concurrency: int = 5):
        """
        Initialize the parallel executor.
        
        Args:
            max_concurrency: Maximum number of tasks to execute concurrently
        """
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def execute(self, tasks: List[Awaitable[T]]) -> List[T]:
        """
        Execute a list of tasks in parallel.
        
        Args:
            tasks: List of awaitable tasks to execute
            
        Returns:
            List of results from the tasks
        """
        async def _execute_with_semaphore(task: Awaitable[T]) -> T:
            async with self.semaphore:
                return await task
        
        # Create tasks with semaphore
        tasks_with_semaphore = [_execute_with_semaphore(task) for task in tasks]
        
        # Execute tasks and gather results
        results = await asyncio.gather(*tasks_with_semaphore, return_exceptions=True)
        
        # Check for exceptions
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed with error: {result}")
                errors.append((i, result))
        
        # If there are errors, raise the first one
        if errors:
            i, error = errors[0]
            logger.error(f"Parallel execution failed: Task {i} raised {type(error).__name__}: {error}")
            raise error
        
        return results
    
    async def execute_with_progress(
        self,
        tasks: List[Awaitable[T]],
        progress_callback: Optional[Callable[[int, Optional[str]], None]] = None,
        retry_count: int = 3,
        retry_delay: float = 2.0,
    ) -> List[T]:
        """
        Execute a list of tasks in parallel with progress reporting and retry logic.
        
        Args:
            tasks: List of awaitable tasks to execute
            progress_callback: Callback for progress updates
            retry_count: Number of times to retry failed tasks
            retry_delay: Delay between retries in seconds (will be doubled for each retry)
            
        Returns:
            List of results from the tasks
        """
        total_tasks = len(tasks)
        completed_tasks = 0
        results: List[Optional[T]] = [None] * total_tasks
        failed_indices: List[int] = []
        
        # Track task completion status
        task_status: Dict[int, str] = {i: "pending" for i in range(total_tasks)}
        
        if progress_callback:
            progress_callback(0, f"Starting execution of {total_tasks} tasks")
        
        # Create a list to track task futures
        task_futures = []
        
        # Function to execute a single task with retry logic
        async def execute_task_with_retry(task_factory: Callable[[], Awaitable[T]], index: int) -> T:
            nonlocal completed_tasks
            
            current_retry = 0
            current_delay = retry_delay
            
            while current_retry <= retry_count:
                try:
                    async with self.semaphore:
                        if progress_callback and task_status[index] == "pending":
                            progress = int((completed_tasks / total_tasks) * 100)
                            progress_callback(progress, f"Processing task {index + 1}/{total_tasks}")
                        
                        # Create a new task instance for each attempt
                        task = task_factory()
                        
                        # Execute the task
                        result = await task
                        
                        # Update status and count
                        task_status[index] = "completed"
                        completed_tasks += 1
                        
                        if progress_callback:
                            progress = int((completed_tasks / total_tasks) * 100)
                            progress_callback(progress, f"Completed task {index + 1}/{total_tasks}")
                        
                        # Store the result
                        results[index] = result
                        
                        return result
                
                except Exception as e:
                    current_retry += 1
                    logger.warning(f"Task {index} failed (attempt {current_retry}/{retry_count}): {e}")
                    
                    if current_retry <= retry_count:
                        # Update status for retry
                        task_status[index] = "retrying"
                        
                        if progress_callback:
                            progress = int((completed_tasks / total_tasks) * 100)
                            progress_callback(
                                progress, 
                                f"Retrying task {index + 1}/{total_tasks} (attempt {current_retry}/{retry_count})"
                            )
                        
                        # Wait before retrying with exponential backoff
                        await asyncio.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                    else:
                        # Max retries reached, mark as failed
                        task_status[index] = "failed"
                        logger.error(f"Task {index} failed after {retry_count} retries: {e}")
                        failed_indices.append(index)
                        raise
            
            # This should not be reached, but just in case
            raise RuntimeError(f"Task {index} failed for unknown reasons")
        
        # Create and start all tasks
        for i, task in enumerate(tasks):
            # Create a factory function that returns a new task each time it's called
            task_factory = lambda t=task: t
            task_future = asyncio.create_task(execute_task_with_retry(task_factory, i))
            task_futures.append(task_future)
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*task_futures, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error during parallel execution: {e}")
        
        # Check for failed tasks
        if failed_indices:
            failed_count = len(failed_indices)
            logger.error(f"{failed_count} tasks failed after retries")
            
            # If all tasks failed, raise an exception
            if failed_count == total_tasks:
                raise RuntimeError(f"All {total_tasks} tasks failed")
        
        if progress_callback:
            final_progress = int((completed_tasks / total_tasks) * 100)
            progress_callback(
                final_progress, 
                f"Completed {completed_tasks}/{total_tasks} tasks ({len(failed_indices)} failed)"
            )
        
        # Filter out None results (from failed tasks)
        return [r for r in results if r is not None]
    
    @staticmethod
    async def map(
        func: Callable[[Any], Awaitable[T]],
        items: List[Any],
        max_concurrency: int = 5,
        progress_callback: Optional[Callable[[int, Optional[str]], None]] = None,
        retry_count: int = 3,
    ) -> List[T]:
        """
        Apply a function to each item in a list in parallel.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            max_concurrency: Maximum number of tasks to execute concurrently
            progress_callback: Callback for progress updates
            retry_count: Number of times to retry failed tasks
            
        Returns:
            List of results from applying the function to each item
        """
        executor = ParallelExecutor(max_concurrency)
        tasks = [func(item) for item in items]
        
        if progress_callback:
            return await executor.execute_with_progress(
                tasks, 
                progress_callback=progress_callback,
                retry_count=retry_count
            )
        else:
            return await executor.execute(tasks)
