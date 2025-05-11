"""
WebSocket connection manager for Pixora AI.

This module provides a connection manager for WebSocket connections.
"""
import logging
import time
from typing import Dict, List, Any, Optional, Set, Union

from fastapi import WebSocket
from starlette.websockets import WebSocketState

# Set up logging
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    
    This class keeps track of active WebSocket connections and provides
    methods for sending messages to connected clients.
    """
    
    def __init__(self):
        """Initialize an empty connection manager."""
        # Map task_id to list of active connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Map user_id to set of task_ids
        self.user_tasks: Dict[str, Set[str]] = {}
        # Track last activity time for each connection
        self.last_activity: Dict[str, Dict[WebSocket, float]] = {}
        
    async def connect(self, task_id: str, websocket: WebSocket, user_id: Optional[str] = None):
        """
        Register a new WebSocket connection.
        
        Args:
            task_id: The task ID associated with the connection
            websocket: The WebSocket connection
            user_id: Optional user ID for tracking user-specific connections
        """
        # Initialize the task's connection list if it doesn't exist
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
            self.last_activity[task_id] = {}
        
        # Add the connection to the list
        self.active_connections[task_id].append(websocket)
        
        # Track the last activity time
        self.last_activity[task_id][websocket] = time.time()
        
        # Track the task for the user if a user ID is provided
        if user_id:
            if user_id not in self.user_tasks:
                self.user_tasks[user_id] = set()
            self.user_tasks[user_id].add(task_id)
        
        logger.info(f"Client connected to task {task_id}")
    
    async def disconnect(self, task_id: str, websocket: WebSocket, user_id: Optional[str] = None):
        """
        Remove a WebSocket connection.
        
        Args:
            task_id: The task ID associated with the connection
            websocket: The WebSocket connection to remove
            user_id: Optional user ID for tracking user-specific connections
        """
        # Remove the connection from the task's list
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            
            # Remove the last activity time
            if task_id in self.last_activity and websocket in self.last_activity[task_id]:
                del self.last_activity[task_id][websocket]
            
            # Remove the task entry if there are no more connections
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
                if task_id in self.last_activity:
                    del self.last_activity[task_id]
        
        # Remove the task from the user's set if a user ID is provided
        if user_id and user_id in self.user_tasks:
            self.user_tasks[user_id].discard(task_id)
            
            # Remove the user entry if there are no more tasks
            if not self.user_tasks[user_id]:
                del self.user_tasks[user_id]
        
        logger.info(f"Client disconnected from task {task_id}")
    
    async def send_message(self, task_id: str, message: Any):
        """
        Send a message to all connections for a task.
        
        Args:
            task_id: The task ID to send the message to
            message: The message to send (will be JSON-encoded)
        """
        if task_id not in self.active_connections:
            logger.warning(f"No active connections for task {task_id}")
            return
        
        # Send the message to all connections for the task
        disconnected = []
        for websocket in self.active_connections[task_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                    # Update last activity time
                    if task_id in self.last_activity:
                        self.last_activity[task_id][websocket] = time.time()
                else:
                    # Mark for removal if not connected
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending message to client: {str(e)}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            if task_id in self.active_connections and websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if task_id in self.last_activity and websocket in self.last_activity[task_id]:
                del self.last_activity[task_id][websocket]
        
        # Clean up if no connections remain
        if task_id in self.active_connections and not self.active_connections[task_id]:
            del self.active_connections[task_id]
            if task_id in self.last_activity:
                del self.last_activity[task_id]
    
    async def broadcast_to_user(self, user_id: str, message: Any):
        """
        Send a message to all connections for a user.
        
        Args:
            user_id: The user ID to send the message to
            message: The message to send (will be JSON-encoded)
        """
        if user_id not in self.user_tasks:
            logger.warning(f"No active tasks for user {user_id}")
            return
        
        # Send the message to all tasks for the user
        for task_id in self.user_tasks[user_id]:
            await self.send_message(task_id, message)
    
    async def send_progress_update(
        self, 
        task_id: str, 
        progress: int, 
        stage: str, 
        message: str,
        substage: Optional[str] = None,
        eta: Optional[float] = None
    ):
        """
        Send a progress update to all connections for a task.
        
        Args:
            task_id: The task ID to send the update to
            progress: The progress value (0-100)
            stage: The current stage of the task
            message: A message describing the current status
            substage: Optional substage of the current stage
            eta: Optional estimated time of completion (timestamp)
        """
        data = {
            "progress": progress,
            "stage": stage,
            "message": message,
            "timestamp": time.time()
        }
        
        # Add optional fields if provided
        if substage:
            data["substage"] = substage
        
        if eta:
            data["eta"] = eta
            # Calculate remaining time in seconds
            remaining_time = eta - time.time()
            if remaining_time > 0:
                # Format as minutes and seconds
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                data["eta_formatted"] = f"{minutes}m {seconds}s"
        
        await self.send_message(
            task_id,
            {
                "type": "progress_update",
                "data": data
            }
        )
    
    async def send_detailed_progress(
        self,
        task_id: str,
        progress: int,
        stage: str,
        substage: Optional[str] = None,
        message: str = "",
        eta: Optional[float] = None,
        completed_steps: Optional[List[str]] = None,
        current_step: Optional[str] = None,
        pending_steps: Optional[List[str]] = None
    ):
        """
        Send a detailed progress update with steps information.
        
        Args:
            task_id: The task ID to send the update to
            progress: The progress value (0-100)
            stage: The current stage of the task
            substage: Optional substage of the current stage
            message: A message describing the current status
            eta: Optional estimated time of completion (timestamp)
            completed_steps: Optional list of completed steps
            current_step: Optional current step being processed
            pending_steps: Optional list of pending steps
        """
        data = {
            "progress": progress,
            "stage": stage,
            "message": message,
            "timestamp": time.time()
        }
        
        # Add optional fields if provided
        if substage:
            data["substage"] = substage
        
        if eta:
            data["eta"] = eta
            # Calculate remaining time in seconds
            remaining_time = eta - time.time()
            if remaining_time > 0:
                # Format as minutes and seconds
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                data["eta_formatted"] = f"{minutes}m {seconds}s"
        
        # Add steps information if provided
        steps_data = {}
        if completed_steps:
            steps_data["completed"] = completed_steps
        if current_step:
            steps_data["current"] = current_step
        if pending_steps:
            steps_data["pending"] = pending_steps
        
        if steps_data:
            data["steps"] = steps_data
        
        await self.send_message(
            task_id,
            {
                "type": "detailed_progress",
                "data": data
            }
        )
    
    async def send_tool_execution(
        self, 
        task_id: str, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        result: Union[str, Dict[str, Any]]
    ):
        """
        Send a tool execution update to all connections for a task.
        
        Args:
            task_id: The task ID to send the update to
            tool_name: The name of the tool being executed
            parameters: The parameters passed to the tool
            result: The result of the tool execution
        """
        await self.send_message(
            task_id,
            {
                "type": "tool_execution",
                "data": {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "timestamp": time.time()
                }
            }
        )
    
    async def send_chat_message(self, task_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Send a chat message to all connections for a task.
        
        Args:
            task_id: The task ID to send the message to
            role: The role of the message sender (user, assistant, system)
            content: The message content
            metadata: Optional additional metadata for the message
        """
        data = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        
        if metadata:
            data["metadata"] = metadata
        
        await self.send_message(
            task_id,
            {
                "type": "chat_message",
                "data": data
            }
        )
    
    async def send_completion(self, task_id: str, result: Dict[str, Any]):
        """
        Send a completion message to all connections for a task.
        
        Args:
            task_id: The task ID to send the message to
            result: The final result of the task
        """
        # Add timestamp if not present
        if "timestamp" not in result:
            result["timestamp"] = time.time()
        
        await self.send_message(
            task_id,
            {
                "type": "completion",
                "data": result
            }
        )
    
    async def send_error(
        self, 
        task_id: str, 
        error: str, 
        error_type: Optional[str] = None,
        recovery_options: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Send an error message to all connections for a task.
        
        Args:
            task_id: The task ID to send the message to
            error: The error message
            error_type: Optional error type for categorization
            recovery_options: Optional list of recovery options
        """
        data = {
            "message": error,
            "timestamp": time.time()
        }
        
        if error_type:
            data["error_type"] = error_type
        
        if recovery_options:
            data["recovery_options"] = recovery_options
        
        await self.send_message(
            task_id,
            {
                "type": "error",
                "data": data
            }
        )
    
    async def send_task_control(self, task_id: str, action: str, params: Optional[Dict[str, Any]] = None):
        """
        Send a task control message to all connections for a task.
        
        Args:
            task_id: The task ID to send the message to
            action: The control action (pause, resume, cancel, etc.)
            params: Optional parameters for the action
        """
        data = {
            "action": action,
            "timestamp": time.time()
        }
        
        if params:
            data["params"] = params
        
        await self.send_message(
            task_id,
            {
                "type": "task_control",
                "data": data
            }
        )
    
    async def send_feedback_request(
        self,
        task_id: str,
        item_type: str,
        item_id: str,
        options: List[Dict[str, Any]],
        preview_url: Optional[str] = None,
        message: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Send a feedback request to all connections for a task.
        
        Args:
            task_id: The task ID to send the request to
            item_type: The type of item to get feedback on (scene, character, image, etc.)
            item_id: The ID of the item
            options: List of feedback options (e.g., approve, reject, regenerate)
            preview_url: Optional URL to a preview of the item
            message: Optional message to display with the request
            timeout: Optional timeout in seconds for the request
        """
        data = {
            "item_type": item_type,
            "item_id": item_id,
            "options": options,
            "request_id": f"{item_type}_{item_id}_{int(time.time())}",
            "timestamp": time.time()
        }
        
        if preview_url:
            data["preview_url"] = preview_url
        
        if message:
            data["message"] = message
        
        if timeout:
            data["timeout"] = timeout
            data["expires_at"] = time.time() + timeout
        
        await self.send_message(
            task_id,
            {
                "type": "feedback_request",
                "data": data
            }
        )
    
    def get_connection_count(self, task_id: str) -> int:
        """
        Get the number of active connections for a task.
        
        Args:
            task_id: The task ID to check
            
        Returns:
            The number of active connections
        """
        if task_id not in self.active_connections:
            return 0
        return len(self.active_connections[task_id])
    
    def get_user_task_count(self, user_id: str) -> int:
        """
        Get the number of active tasks for a user.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            The number of active tasks
        """
        if user_id not in self.user_tasks:
            return 0
        return len(self.user_tasks[user_id])
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about active connections.
        
        Returns:
            Dictionary of connection statistics
        """
        # Count total connections
        total_connections = 0
        for connections in self.active_connections.values():
            total_connections += len(connections)
        
        # Count unique tasks and users
        unique_tasks = len(self.active_connections)
        unique_users = len(self.user_tasks)
        
        # Calculate average connections per task
        avg_connections_per_task = 0
        if unique_tasks > 0:
            avg_connections_per_task = total_connections / unique_tasks
        
        # Calculate average tasks per user
        avg_tasks_per_user = 0
        if unique_users > 0:
            total_user_tasks = sum(len(tasks) for tasks in self.user_tasks.values())
            avg_tasks_per_user = total_user_tasks / unique_users
        
        # Get idle connection counts
        idle_5min = sum(len(connections) for connections in self.get_idle_connections(300).values())
        idle_15min = sum(len(connections) for connections in self.get_idle_connections(900).values())
        idle_30min = sum(len(connections) for connections in self.get_idle_connections(1800).values())
        
        return {
            "total_connections": total_connections,
            "unique_tasks": unique_tasks,
            "unique_users": unique_users,
            "avg_connections_per_task": avg_connections_per_task,
            "avg_tasks_per_user": avg_tasks_per_user,
            "idle_connections": {
                "5min": idle_5min,
                "15min": idle_15min,
                "30min": idle_30min
            },
            "timestamp": time.time()
        }
    
    def get_idle_connections(self, idle_threshold_seconds: int = 300) -> Dict[str, List[WebSocket]]:
        """
        Get connections that have been idle for longer than the threshold.
        
        Args:
            idle_threshold_seconds: The threshold in seconds
            
        Returns:
            Dictionary mapping task IDs to lists of idle WebSocket connections
        """
        now = time.time()
        idle_connections: Dict[str, List[WebSocket]] = {}
        
        for task_id, connections in self.active_connections.items():
            if task_id not in self.last_activity:
                continue
            
            for websocket in connections:
                if websocket in self.last_activity[task_id]:
                    last_active = self.last_activity[task_id][websocket]
                    if now - last_active > idle_threshold_seconds:
                        if task_id not in idle_connections:
                            idle_connections[task_id] = []
                        idle_connections[task_id].append(websocket)
        
        return idle_connections
    
    async def schedule_periodic_cleanup(self, interval_seconds: int = 300, idle_threshold_seconds: int = 600) -> None:
        """
        Schedule periodic cleanup of idle connections.
        
        Args:
            interval_seconds: The interval between cleanup runs in seconds
            idle_threshold_seconds: The threshold for considering a connection idle in seconds
        """
        import asyncio
        
        async def cleanup_loop():
            while True:
                try:
                    # Wait for the specified interval
                    await asyncio.sleep(interval_seconds)
                    
                    # Cleanup idle connections
                    closed_count = await self.cleanup_idle_connections(idle_threshold_seconds)
                    
                    if closed_count > 0:
                        logger.info(f"Periodic cleanup closed {closed_count} idle connections")
                    
                    # Get connection statistics
                    stats = self.get_connection_statistics()
                    logger.info(f"Connection statistics: {stats['total_connections']} total, {stats['unique_tasks']} tasks, {stats['unique_users']} users")
                    
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {str(e)}")
        
        # Start the cleanup loop in the background
        asyncio.create_task(cleanup_loop())
        logger.info(f"Scheduled periodic cleanup every {interval_seconds} seconds (idle threshold: {idle_threshold_seconds} seconds)")
    
    async def cleanup_idle_connections(self, idle_threshold_seconds: int = 300) -> int:
        """
        Disconnect connections that have been idle for longer than the threshold.
        
        Args:
            idle_threshold_seconds: The threshold in seconds
            
        Returns:
            Number of connections closed
        """
        idle_connections = self.get_idle_connections(idle_threshold_seconds)
        count = 0
        
        for task_id, connections in idle_connections.items():
            for websocket in connections:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.close(code=1000, reason="Connection idle")
                    
                    # Remove from active connections
                    if task_id in self.active_connections and websocket in self.active_connections[task_id]:
                        self.active_connections[task_id].remove(websocket)
                    
                    # Remove from last activity
                    if task_id in self.last_activity and websocket in self.last_activity[task_id]:
                        del self.last_activity[task_id][websocket]
                    
                    count += 1
                except Exception as e:
                    logger.error(f"Error closing idle connection: {str(e)}")
        
        # Clean up empty task entries
        for task_id in list(self.active_connections.keys()):
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
                if task_id in self.last_activity:
                    del self.last_activity[task_id]
        
        return count
