"""
Utility for managing task dependencies and parallel execution.
"""
import asyncio
import logging
from typing import Dict, Any, List, Set, Callable, Awaitable, Optional, TypeVar, Generic

# Set up logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')  # Task ID type
R = TypeVar('R')  # Result type


class DependencyGraph(Generic[T, R]):
    """
    A directed acyclic graph (DAG) for managing task dependencies.
    
    This class allows you to define tasks with dependencies and execute them
    in parallel while respecting the dependency order.
    """
    
    def __init__(self):
        """Initialize the dependency graph."""
        self.tasks: Dict[T, Callable[..., Awaitable[R]]] = {}
        self.dependencies: Dict[T, Set[T]] = {}
        self.results: Dict[T, R] = {}
        self.in_progress: Set[T] = set()
    
    def add_task(
        self,
        task_id: T,
        task_func: Callable[..., Awaitable[R]],
        dependencies: Optional[List[T]] = None,
    ):
        """
        Add a task to the graph.
        
        Args:
            task_id: Unique identifier for the task
            task_func: Async function to execute
            dependencies: List of task IDs that this task depends on
        """
        self.tasks[task_id] = task_func
        self.dependencies[task_id] = set(dependencies or [])
    
    def get_ready_tasks(self) -> List[T]:
        """
        Get a list of tasks that are ready to execute.
        
        A task is ready if all its dependencies have been completed.
        
        Returns:
            List of task IDs that are ready to execute
        """
        ready_tasks = []
        for task_id, deps in self.dependencies.items():
            if task_id not in self.results and task_id not in self.in_progress:
                if all(dep in self.results for dep in deps):
                    ready_tasks.append(task_id)
        return ready_tasks
    
    def is_complete(self) -> bool:
        """
        Check if all tasks have been completed.
        
        Returns:
            True if all tasks have been completed, False otherwise
        """
        return len(self.results) == len(self.tasks)
    
    async def execute_task(self, task_id: T) -> R:
        """
        Execute a single task.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Result of the task
        """
        if task_id in self.results:
            return self.results[task_id]
        
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        # Mark the task as in progress
        self.in_progress.add(task_id)
        
        try:
            # Get the task function
            task_func = self.tasks[task_id]
            
            # Get the results of dependencies
            dep_results = {dep: self.results[dep] for dep in self.dependencies[task_id]}
            
            # Execute the task with dependency results
            result = await task_func(**dep_results)
            
            # Store the result
            self.results[task_id] = result
            
            # Remove from in-progress set
            self.in_progress.remove(task_id)
            
            return result
        except Exception as e:
            # Remove from in-progress set on error
            self.in_progress.remove(task_id)
            logger.error(f"Error executing task {task_id}: {e}")
            raise
    
    async def execute_all(
        self,
        max_concurrency: int = 5,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[T, R]:
        """
        Execute all tasks in the graph in dependency order.
        
        Args:
            max_concurrency: Maximum number of tasks to execute in parallel
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        total_tasks = len(self.tasks)
        completed_tasks = 0
        
        if progress_callback:
            progress_callback(0, f"Starting execution of {total_tasks} tasks")
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_with_semaphore(task_id: T):
            async with semaphore:
                return await self.execute_task(task_id)
        
        # Execute tasks until all are complete
        while not self.is_complete():
            # Get tasks that are ready to execute
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                if self.in_progress:
                    # Wait for some tasks to complete
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # No ready tasks and nothing in progress means we have a cycle
                    remaining = set(self.tasks.keys()) - set(self.results.keys())
                    raise ValueError(f"Dependency cycle detected in tasks: {remaining}")
            
            # Create tasks for execution
            tasks = [execute_with_semaphore(task_id) for task_id in ready_tasks]
            
            # Execute ready tasks in parallel
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for task_id, result in zip(ready_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {task_id} failed: {result}")
                    else:
                        completed_tasks += 1
                        if progress_callback:
                            progress = int((completed_tasks / total_tasks) * 100)
                            progress_callback(progress, f"Completed {completed_tasks}/{total_tasks} tasks")
        
        if progress_callback:
            progress_callback(100, f"All {total_tasks} tasks completed")
        
        return self.results
