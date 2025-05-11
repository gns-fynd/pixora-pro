"""
Redis client for task tracking and caching.

This module provides a Redis client for managing task progress and results.
"""
import json
import logging
from typing import Any, Dict, Optional, List, Union

import redis.asyncio as redis
from fastapi import Depends

from app.core.config import get_settings, Settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for JSON operations."""
    
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the Redis client.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.redis_url = settings.REDIS_URL
        
        try:
            # Create connection pool
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,  # Automatically decode responses to strings
                max_connections=10,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            logger.info("Redis connection pool created")
            
        except Exception as e:
            logger.error(f"Error initializing Redis client: {str(e)}", exc_info=True)
            self.pool = None
            self.client = None
            
    async def set_json(self, key: str, value: Union[Dict[str, Any], List[Any]]) -> bool:
        """
        Set a JSON value in Redis.
        
        Args:
            key: The Redis key
            value: The JSON value
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False
            
        try:
            json_str = json.dumps(value)
            await self.client.set(key, json_str)
            return True
        except Exception as e:
            logger.error(f"Error setting JSON in Redis for key {key}: {str(e)}")
            return False
    
    async def get_json(self, key: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """
        Get a JSON value from Redis.
        
        Args:
            key: The Redis key
            
        Returns:
            The JSON value, or None if not found or error
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return None
            
        try:
            json_str = await self.client.get(key)
            if not json_str:
                return None
                
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error getting JSON from Redis for key {key}: {str(e)}")
            return None
    
    async def set_json_with_ttl(
        self, 
        key: str, 
        value: Union[Dict[str, Any], List[Any]], 
        ttl_seconds: int
    ) -> bool:
        """
        Set a JSON value in Redis with a TTL.
        
        Args:
            key: The Redis key
            value: The JSON value
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False
            
        try:
            json_str = json.dumps(value)
            await self.client.setex(key, ttl_seconds, json_str)
            return True
        except Exception as e:
            logger.error(f"Error setting JSON with TTL in Redis for key {key}: {str(e)}")
            return False
    
    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: The Redis key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False
            
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return False
    
    async def get_keys(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: The pattern to match
            
        Returns:
            List of matching keys
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return []
            
        try:
            keys = await self.client.keys(pattern)
            return keys
        except Exception as e:
            logger.error(f"Error getting keys matching pattern {pattern} from Redis: {str(e)}")
            return []
            
    async def update_json(
        self, 
        key: str, 
        updates: Dict[str, Any], 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Update a JSON value in Redis.
        
        Args:
            key: The Redis key
            updates: The updates to apply
            ttl_seconds: Optional TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Redis client not initialized")
            return False
            
        try:
            # Get existing value
            existing = await self.get_json(key)
            if existing is None:
                # If no existing value, create new
                return await self.set_json_with_ttl(key, updates, ttl_seconds) if ttl_seconds else await self.set_json(key, updates)
                
            # Merge updates
            if isinstance(existing, dict) and isinstance(updates, dict):
                existing.update(updates)
                
                # Set with or without TTL
                if ttl_seconds:
                    return await self.set_json_with_ttl(key, existing, ttl_seconds)
                else:
                    return await self.set_json(key, existing)
            else:
                logger.error(f"Cannot update JSON for key {key}: existing or updates is not a dict")
                return False
                
        except Exception as e:
            logger.error(f"Error updating JSON in Redis for key {key}: {str(e)}")
            return False
            
    async def close(self):
        """Close the Redis client."""
        if self.client:
            await self.client.close()
            logger.info("Redis client closed")
