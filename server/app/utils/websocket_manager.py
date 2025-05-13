"""
WebSocket Connection Manager for Pixora AI Video Creation Platform
"""
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import uuid

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and message routing.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}  # Maps user_id to connection_ids
        self.connection_user: Dict[str, str] = {}  # Maps connection_id to user_id
        self.tasks: Dict[str, Dict[str, Any]] = {}  # Maps task_id to task info
        self.user_tasks: Dict[str, List[str]] = {}  # Maps user_id to task_ids
        
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """
        Connect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
            user_id: The ID of the user
            
        Returns:
            str: The connection ID
        """
        # Accept the connection
        await websocket.accept()
        
        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store the connection
        self.active_connections[connection_id] = websocket
        
        # Associate the connection with the user
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Associate the connection with the user
        self.connection_user[connection_id] = user_id
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket client.
        
        Args:
            connection_id: The ID of the connection to disconnect
        """
        # Check if the connection exists
        if connection_id not in self.active_connections:
            logger.warning(f"Attempted to disconnect non-existent connection: {connection_id}")
            return
        
        # Get the user ID associated with the connection
        user_id = self.connection_user.get(connection_id)
        
        # Remove the connection from active connections
        self.active_connections.pop(connection_id)
        
        # Remove the connection from the user's connections
        if user_id and user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            
            # If the user has no more connections, remove the user
            if not self.user_connections[user_id]:
                self.user_connections.pop(user_id)
        
        # Remove the connection from the connection-user mapping
        if connection_id in self.connection_user:
            self.connection_user.pop(connection_id)
        
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: The ID of the connection to send the message to
            message: The message to send
        """
        # Check if the connection exists
        if connection_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent connection: {connection_id}")
            return
        
        # Get the WebSocket connection
        websocket = self.active_connections[connection_id]
        
        # Send the message
        try:
            await websocket.send_json(message)
            logger.debug(f"Message sent to connection {connection_id}: {message}")
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            # Disconnect the client if there's an error
            self.disconnect(connection_id)
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all connections for a specific user.
        
        Args:
            user_id: The ID of the user to broadcast to
            message: The message to broadcast
        """
        # Check if the user has any connections
        if user_id not in self.user_connections:
            logger.warning(f"Attempted to broadcast to user with no connections: {user_id}")
            return
        
        # Get the user's connections
        connection_ids = self.user_connections[user_id]
        
        # Send the message to each connection
        for connection_id in connection_ids:
            await self.send_message(connection_id, message)
    
    async def broadcast_to_task(self, task_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all users associated with a specific task.
        
        Args:
            task_id: The ID of the task to broadcast to
            message: The message to broadcast
        """
        # Check if the task exists
        if task_id not in self.tasks:
            logger.warning(f"Attempted to broadcast to non-existent task: {task_id}")
            return
        
        # Get the task info
        task_info = self.tasks[task_id]
        
        # Get the user ID associated with the task
        user_id = task_info.get("user_id")
        
        # Broadcast to the user
        if user_id:
            await self.broadcast_to_user(user_id, message)
    
    def create_task(self, user_id: str, task_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new task.
        
        Args:
            user_id: The ID of the user creating the task
            task_type: The type of task
            metadata: Optional metadata for the task
            
        Returns:
            str: The task ID
        """
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Create the task info
        task_info = {
            "id": task_id,
            "user_id": user_id,
            "type": task_type,
            "status": "created",
            "metadata": metadata or {},
            "created_at": asyncio.get_event_loop().time()
        }
        
        # Store the task
        self.tasks[task_id] = task_info
        
        # Associate the task with the user
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = []
        self.user_tasks[user_id].append(task_id)
        
        logger.info(f"Task created: {task_id} for user {user_id}")
        
        return task_id
    
    def update_task_status(self, task_id: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Update the status of a task.
        
        Args:
            task_id: The ID of the task to update
            status: The new status of the task
            metadata: Optional metadata to update
        """
        # Check if the task exists
        if task_id not in self.tasks:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return
        
        # Update the task status
        self.tasks[task_id]["status"] = status
        
        # Update the task metadata if provided
        if metadata:
            self.tasks[task_id]["metadata"].update(metadata)
        
        logger.info(f"Task updated: {task_id} status={status}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a task.
        
        Args:
            task_id: The ID of the task to get
            
        Returns:
            Optional[Dict[str, Any]]: The task info, or None if the task doesn't exist
        """
        return self.tasks.get(task_id)
    
    def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific user.
        
        Args:
            user_id: The ID of the user to get tasks for
            
        Returns:
            List[Dict[str, Any]]: A list of task info dictionaries
        """
        # Check if the user has any tasks
        if user_id not in self.user_tasks:
            return []
        
        # Get the user's task IDs
        task_ids = self.user_tasks[user_id]
        
        # Get the task info for each task
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
    
    async def handle_client_message(self, connection_id: str, message_data: Dict[str, Any], 
                                   message_handler: Callable[[str, Dict[str, Any]], Any]):
        """
        Handle a message from a client.
        
        Args:
            connection_id: The ID of the connection that sent the message
            message_data: The message data
            message_handler: A function to handle the message
        """
        # Get the user ID associated with the connection
        user_id = self.connection_user.get(connection_id)
        
        if not user_id:
            logger.warning(f"Received message from connection with no user ID: {connection_id}")
            await self.send_message(connection_id, {
                "type": "error",
                "content": "User ID not found for connection"
            })
            return
        
        # Get the task ID from the message
        task_id = message_data.get("task_id")
        
        # If a task ID is provided, verify that the task exists and belongs to the user
        if task_id and (task_id not in self.tasks or self.tasks[task_id]["user_id"] != user_id):
            logger.warning(f"User {user_id} attempted to access task {task_id} that doesn't exist or doesn't belong to them")
            await self.send_message(connection_id, {
                "type": "error",
                "content": "Task not found or access denied"
            })
            return
        
        # Handle the message
        try:
            # Call the message handler
            response = await message_handler(user_id, message_data)
            
            # If the response is a dictionary, send it back to the client
            if isinstance(response, dict):
                await self.send_message(connection_id, response)
        except Exception as e:
            logger.error(f"Error handling message from connection {connection_id}: {str(e)}")
            await self.send_message(connection_id, {
                "type": "error",
                "content": f"Error processing message: {str(e)}"
            })
    
    async def handle_websocket(self, websocket: WebSocket, user_id: str, 
                              message_handler: Callable[[str, Dict[str, Any]], Any]):
        """
        Handle a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: The ID of the user
            message_handler: A function to handle messages
        """
        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store the connection
        self.active_connections[connection_id] = websocket
        
        # Associate the connection with the user
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Associate the connection with the user
        self.connection_user[connection_id] = user_id
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        
        try:
            # Send a welcome message
            await self.send_message(connection_id, {
                "type": "system",
                "content": "Connected to Pixora AI WebSocket server"
            })
            
            # Handle messages
            while True:
                # Receive a message
                message = await websocket.receive_text()
                
                # Parse the message
                try:
                    message_data = json.loads(message)
                except json.JSONDecodeError:
                    await self.send_message(connection_id, {
                        "type": "error",
                        "content": "Invalid JSON"
                    })
                    continue
                
                # Handle the message
                await self.handle_client_message(connection_id, message_data, message_handler)
        except WebSocketDisconnect:
            # Disconnect the client
            self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Error handling WebSocket connection {connection_id}: {str(e)}")
            # Disconnect the client
            self.disconnect(connection_id)

# Create a global instance of the connection manager
connection_manager = ConnectionManager()
