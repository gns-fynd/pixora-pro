"""
Enhanced task context for the OpenAI Assistants SDK.

This module provides an enhanced task context for the OpenAI Assistants SDK,
with improved progress tracking, message history management, and asset URL management.
"""
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic

from pydantic import BaseModel, Field

from app.services.redis_client import RedisClient


# Set up logging
logger = logging.getLogger(__name__)


class ProgressUpdate(BaseModel):
    """Model for a progress update."""
    progress: float = Field(..., description="Progress percentage (0-100)")
    stage: str = Field(..., description="Current stage of processing")
    substage: Optional[str] = Field(None, description="Current substage of processing")
    message: str = Field(..., description="Progress message")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of the update")
    eta: Optional[float] = Field(None, description="Estimated time of completion (timestamp)")


class Message(BaseModel):
    """Model for a message in the task context."""
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of the message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Asset(BaseModel):
    """Model for an asset in the task context."""
    url: str = Field(..., description="URL of the asset")
    type: str = Field(..., description="Type of the asset (image, audio, video)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: float = Field(default_factory=time.time, description="Timestamp of creation")
    scene_index: Optional[int] = Field(None, description="Index of the scene this asset belongs to")


T = TypeVar('T')


class TaskContext(Generic[T]):
    """
    Enhanced task context for the OpenAI Assistants SDK.
    
    This class provides methods for:
    - Storing and retrieving data
    - Tracking progress with detailed stages and substages
    - Managing message history
    - Managing asset URLs
    - Persisting data to Redis
    """
    
    def __init__(
        self, 
        task_id: str, 
        user_id: Optional[str] = None,
        redis_client: Optional[RedisClient] = None
    ):
        """
        Initialize the task context.
        
        Args:
            task_id: The task ID
            user_id: Optional user ID
            redis_client: Optional Redis client for persistence
        """
        self.task_id = task_id
        self.user_id = user_id
        self.redis_client = redis_client
        self._data: Dict[str, Any] = {}
        self._progress_history: List[ProgressUpdate] = []
        self._messages: List[Message] = []
        self._assets: Dict[str, Asset] = {}
        self._scene_data: Dict[int, Dict[str, Any]] = {}
        self._start_time = time.time()
        
        # Initialize with a system message
        self.add_message(
            role="system",
            content=f"Task {task_id} initialized"
        )
    
    # Basic data storage methods
    
    def get(self, key: str, default: Optional[T] = None) -> Union[T, None]:
        """
        Get a value from the context.
        
        Args:
            key: The key to get
            default: Default value if key doesn't exist
            
        Returns:
            The value, or default if not found
        """
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context.
        
        Args:
            key: The key to set
            value: The value to set
        """
        self._data[key] = value
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_data_to_redis()
    
    def delete(self, key: str) -> None:
        """
        Delete a key from the context.
        
        Args:
            key: The key to delete
        """
        if key in self._data:
            del self._data[key]
            
            # Persist to Redis if available
            if self.redis_client:
                self._persist_data_to_redis()
    
    def has(self, key: str) -> bool:
        """
        Check if a key exists in the context.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in self._data
    
    def clear(self) -> None:
        """Clear all data from the context."""
        self._data.clear()
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_data_to_redis()
    
    # Progress tracking methods
    
    def set_progress(
        self, 
        progress: float, 
        stage: str, 
        message: str,
        substage: Optional[str] = None,
        eta: Optional[float] = None
    ) -> None:
        """
        Set the current progress.
        
        Args:
            progress: Progress percentage (0-100)
            stage: Current stage of processing
            message: Progress message
            substage: Optional substage of processing
            eta: Optional estimated time of completion (timestamp)
        """
        # Create progress update
        update = ProgressUpdate(
            progress=progress,
            stage=stage,
            substage=substage,
            message=message,
            timestamp=time.time(),
            eta=eta
        )
        
        # Add to history
        self._progress_history.append(update)
        
        # Store current progress in data
        self._data["current_progress"] = update.dict()
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_progress_to_redis(update)
    
    def get_current_progress(self) -> Optional[ProgressUpdate]:
        """
        Get the current progress.
        
        Returns:
            The current progress, or None if not set
        """
        progress_data = self._data.get("current_progress")
        if progress_data:
            return ProgressUpdate(**progress_data)
        return None
    
    def get_progress_history(self, limit: Optional[int] = None) -> List[ProgressUpdate]:
        """
        Get the progress history.
        
        Args:
            limit: Optional limit on the number of items to return
            
        Returns:
            List of progress updates
        """
        if limit:
            return self._progress_history[-limit:]
        return self._progress_history
    
    def calculate_eta(self, current_progress: float) -> Optional[float]:
        """
        Calculate the estimated time of completion based on current progress.
        
        Args:
            current_progress: Current progress percentage (0-100)
            
        Returns:
            Estimated timestamp of completion, or None if not enough data
        """
        if current_progress <= 0:
            return None
        
        elapsed_time = time.time() - self._start_time
        if elapsed_time <= 0:
            return None
        
        # Calculate time per percentage point
        time_per_percent = elapsed_time / current_progress
        
        # Calculate remaining time
        remaining_percent = 100 - current_progress
        remaining_time = remaining_percent * time_per_percent
        
        # Return estimated completion time
        return time.time() + remaining_time
    
    # Message history methods
    
    def add_message(
        self, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the history.
        
        Args:
            role: Role of the message sender (user, assistant, system)
            content: Content of the message
            metadata: Optional additional metadata
        """
        # Create message
        message = Message(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        # Add to history
        self._messages.append(message)
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_messages_to_redis()
    
    def get_messages(
        self, 
        limit: Optional[int] = None, 
        roles: Optional[List[str]] = None
    ) -> List[Message]:
        """
        Get messages from the history.
        
        Args:
            limit: Optional limit on the number of messages to return
            roles: Optional filter by roles
            
        Returns:
            List of messages
        """
        # Filter by roles if provided
        if roles:
            filtered_messages = [m for m in self._messages if m.role in roles]
        else:
            filtered_messages = self._messages
        
        # Apply limit if provided
        if limit:
            return filtered_messages[-limit:]
        
        return filtered_messages
    
    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get the chat history in a format suitable for the OpenAI API.
        
        Args:
            limit: Optional limit on the number of messages to return
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        # Filter out system messages and convert to dictionaries
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in self._messages
            if m.role in ["user", "assistant"]
        ]
        
        # Apply limit if provided
        if limit:
            return chat_messages[-limit:]
        
        return chat_messages
    
    def clear_messages(self) -> None:
        """Clear all messages from the history."""
        self._messages.clear()
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_messages_to_redis()
    
    # Asset management methods
    
    def add_asset(
        self, 
        asset_id: str, 
        url: str, 
        asset_type: str, 
        metadata: Optional[Dict[str, Any]] = None,
        scene_index: Optional[int] = None
    ) -> None:
        """
        Add an asset to the context.
        
        Args:
            asset_id: Unique identifier for the asset
            url: URL of the asset
            asset_type: Type of the asset (image, audio, video)
            metadata: Optional additional metadata
            scene_index: Optional index of the scene this asset belongs to
        """
        # Create asset
        asset = Asset(
            url=url,
            type=asset_type,
            metadata=metadata or {},
            scene_index=scene_index
        )
        
        # Add to assets
        self._assets[asset_id] = asset
        
        # If scene_index is provided, add to scene data
        if scene_index is not None:
            if scene_index not in self._scene_data:
                self._scene_data[scene_index] = {}
            
            if "assets" not in self._scene_data[scene_index]:
                self._scene_data[scene_index]["assets"] = {}
            
            self._scene_data[scene_index]["assets"][asset_id] = asset.dict()
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_assets_to_redis()
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """
        Get an asset by ID.
        
        Args:
            asset_id: The asset ID
            
        Returns:
            The asset, or None if not found
        """
        asset_data = self._assets.get(asset_id)
        if asset_data:
            return asset_data
        return None
    
    def get_assets_by_type(self, asset_type: str) -> List[Asset]:
        """
        Get all assets of a specific type.
        
        Args:
            asset_type: The asset type
            
        Returns:
            List of assets
        """
        return [a for a in self._assets.values() if a.type == asset_type]
    
    def get_scene_assets(self, scene_index: int) -> Dict[str, Asset]:
        """
        Get all assets for a specific scene.
        
        Args:
            scene_index: The scene index
            
        Returns:
            Dictionary of asset IDs to assets
        """
        return {
            asset_id: asset
            for asset_id, asset in self._assets.items()
            if asset.scene_index == scene_index
        }
    
    def delete_asset(self, asset_id: str) -> None:
        """
        Delete an asset by ID.
        
        Args:
            asset_id: The asset ID
        """
        if asset_id in self._assets:
            asset = self._assets[asset_id]
            
            # Remove from scene data if applicable
            if asset.scene_index is not None:
                if (
                    asset.scene_index in self._scene_data
                    and "assets" in self._scene_data[asset.scene_index]
                    and asset_id in self._scene_data[asset.scene_index]["assets"]
                ):
                    del self._scene_data[asset.scene_index]["assets"][asset_id]
            
            # Remove from assets
            del self._assets[asset_id]
            
            # Persist to Redis if available
            if self.redis_client:
                self._persist_assets_to_redis()
    
    # Scene data methods
    
    def set_scene_data(self, scene_index: int, key: str, value: Any) -> None:
        """
        Set data for a specific scene.
        
        Args:
            scene_index: The scene index
            key: The key to set
            value: The value to set
        """
        if scene_index not in self._scene_data:
            self._scene_data[scene_index] = {}
        
        self._scene_data[scene_index][key] = value
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_scene_data_to_redis()
    
    def get_scene_data(self, scene_index: int, key: str, default: Optional[T] = None) -> Union[T, None]:
        """
        Get data for a specific scene.
        
        Args:
            scene_index: The scene index
            key: The key to get
            default: Default value if key doesn't exist
            
        Returns:
            The value, or default if not found
        """
        if scene_index not in self._scene_data:
            return default
        
        return self._scene_data[scene_index].get(key, default)
    
    def get_all_scene_data(self, scene_index: int) -> Dict[str, Any]:
        """
        Get all data for a specific scene.
        
        Args:
            scene_index: The scene index
            
        Returns:
            Dictionary of scene data
        """
        return self._scene_data.get(scene_index, {})
    
    def get_all_scenes(self) -> Dict[int, Dict[str, Any]]:
        """
        Get data for all scenes.
        
        Returns:
            Dictionary of scene indices to scene data
        """
        return self._scene_data
    
    def delete_scene_data(self, scene_index: int, key: str) -> None:
        """
        Delete data for a specific scene.
        
        Args:
            scene_index: The scene index
            key: The key to delete
        """
        if scene_index in self._scene_data and key in self._scene_data[scene_index]:
            del self._scene_data[scene_index][key]
            
            # Persist to Redis if available
            if self.redis_client:
                self._persist_scene_data_to_redis()
    
    # Redis persistence methods
    
    async def load_from_redis(self) -> bool:
        """
        Load data from Redis.
        
        Returns:
            True if data was loaded, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Load data
            data = await self.redis_client.get_json(f"task:{self.task_id}:context")
            if data:
                self._data = data
            
            # Load progress history
            progress_history = await self.redis_client.get_json(f"task:{self.task_id}:progress_history")
            if progress_history:
                self._progress_history = [ProgressUpdate(**p) for p in progress_history]
            
            # Load messages
            messages = await self.redis_client.get_json(f"task:{self.task_id}:messages")
            if messages:
                self._messages = [Message(**m) for m in messages]
            
            # Load assets
            assets = await self.redis_client.get_json(f"task:{self.task_id}:assets")
            if assets:
                self._assets = {k: Asset(**v) for k, v in assets.items()}
            
            # Load scene data
            scene_data = await self.redis_client.get_json(f"task:{self.task_id}:scene_data")
            if scene_data:
                # Convert string keys to integers
                self._scene_data = {int(k): v for k, v in scene_data.items()}
            
            return True
        except Exception as e:
            logger.error(f"Error loading data from Redis: {e}")
            return False
    
    def _persist_data_to_redis(self) -> None:
        """Persist data to Redis."""
        if not self.redis_client:
            return
        
        # Create a task to avoid blocking
        import asyncio
        asyncio.create_task(self._async_persist_data_to_redis())
    
    async def _async_persist_data_to_redis(self) -> None:
        """Asynchronously persist data to Redis."""
        try:
            await self.redis_client.set_json(
                f"task:{self.task_id}:context",
                self._data
            )
        except Exception as e:
            logger.error(f"Error persisting data to Redis: {e}")
    
    def _persist_progress_to_redis(self, update: ProgressUpdate) -> None:
        """
        Persist progress update to Redis.
        
        Args:
            update: The progress update
        """
        if not self.redis_client:
            return
        
        # Create a task to avoid blocking
        import asyncio
        asyncio.create_task(self._async_persist_progress_to_redis(update))
    
    async def _async_persist_progress_to_redis(self, update: ProgressUpdate) -> None:
        """
        Asynchronously persist progress update to Redis.
        
        Args:
            update: The progress update
        """
        try:
            # Store current progress
            await self.redis_client.set_json(
                f"task:{self.task_id}:progress",
                update.dict()
            )
            
            # Store progress history
            await self.redis_client.set_json(
                f"task:{self.task_id}:progress_history",
                [p.dict() for p in self._progress_history]
            )
        except Exception as e:
            logger.error(f"Error persisting progress to Redis: {e}")
    
    def _persist_messages_to_redis(self) -> None:
        """Persist messages to Redis."""
        if not self.redis_client:
            return
        
        # Create a task to avoid blocking
        import asyncio
        asyncio.create_task(self._async_persist_messages_to_redis())
    
    async def _async_persist_messages_to_redis(self) -> None:
        """Asynchronously persist messages to Redis."""
        try:
            await self.redis_client.set_json(
                f"task:{self.task_id}:messages",
                [m.dict() for m in self._messages]
            )
        except Exception as e:
            logger.error(f"Error persisting messages to Redis: {e}")
    
    def _persist_assets_to_redis(self) -> None:
        """Persist assets to Redis."""
        if not self.redis_client:
            return
        
        # Create a task to avoid blocking
        import asyncio
        asyncio.create_task(self._async_persist_assets_to_redis())
    
    async def _async_persist_assets_to_redis(self) -> None:
        """Asynchronously persist assets to Redis."""
        try:
            await self.redis_client.set_json(
                f"task:{self.task_id}:assets",
                {k: v.dict() for k, v in self._assets.items()}
            )
        except Exception as e:
            logger.error(f"Error persisting assets to Redis: {e}")
    
    def _persist_scene_data_to_redis(self) -> None:
        """Persist scene data to Redis."""
        if not self.redis_client:
            return
        
        # Create a task to avoid blocking
        import asyncio
        asyncio.create_task(self._async_persist_scene_data_to_redis())
    
    async def _async_persist_scene_data_to_redis(self) -> None:
        """Asynchronously persist scene data to Redis."""
        try:
            # Convert integer keys to strings for JSON serialization
            scene_data = {str(k): v for k, v in self._scene_data.items()}
            
            await self.redis_client.set_json(
                f"task:{self.task_id}:scene_data",
                scene_data
            )
        except Exception as e:
            logger.error(f"Error persisting scene data to Redis: {e}")
