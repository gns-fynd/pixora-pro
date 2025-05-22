"""
Supabase service for Pixora AI Video Creation Platform
"""
import os
import uuid
from typing import Dict, Any, Optional, List, Union
import logging
import httpx
import json
from pathlib import Path
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Service for interacting with Supabase.
    """
    
    def initialize(self):
        """
        Initialize the Supabase service.
        This method is called by the application startup event.
        It's a no-op since initialization is already done in the constructor.
        """
        # Initialization is already done in the constructor
        # This method exists for compatibility with the application startup flow
        logger.info("Supabase service initialization called (no-op)")
        pass
    
    def __init__(self):
        """Initialize the Supabase service."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY") or self.key
        self.bucket_name = os.getenv("STORAGE_VIDEOS_BUCKET", "videos")
        
        if not self.url or not self.key:
            logger.warning("Supabase URL or key not set. Supabase integration will not work.")
            self.client = None
            self.storage = None
        else:
            try:
                # Set up headers for API calls
                self.headers = {
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                }
                
                # Admin headers for operations that need to bypass RLS
                self.admin_headers = {
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                }
                
                # Create a storage interface
                self.storage = SupabaseStorage(self)
                
                logger.info(f"Supabase client initialized with URL: {self.url}")
                
                # Ensure the bucket exists
                self._ensure_bucket_exists()
            except Exception as e:
                logger.error(f"Error initializing Supabase client: {str(e)}")
                self.client = None
                self.storage = None
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists."""
        if not self.storage:
            return
        
        try:
            # Get list of buckets
            buckets = self.storage.list_buckets()
            
            # Check if the bucket exists
            bucket_exists = any(bucket["name"] == self.bucket_name for bucket in buckets)
            
            # Create the bucket if it doesn't exist
            if not bucket_exists:
                self.storage.create_bucket(self.bucket_name, {"public": True})
                logger.info(f"Created Supabase storage bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {str(e)}")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Optional[Dict[str, Any]]: User data if the token is valid, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot verify token.")
            return None
        
        try:
            logger.debug(f"Making request to Supabase to verify token (URL: {self.url}/auth/v1/user)")
            
            # Get user data from the token
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {token}"
            }
            
            response = httpx.get(
                f"{self.url}/auth/v1/user",
                headers=headers
            )
            
            logger.debug(f"Supabase token verification response status: {response.status_code}")
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Log successful verification
                logger.debug(f"Successfully verified token for user ID: {user_data.get('id', 'unknown')}")
                
                # Check if essential user data is present
                if not user_data.get('id'):
                    logger.warning("Token verification succeeded but user ID is missing")
                
                return user_data
            else:
                # Log detailed error information
                logger.error(f"Error verifying token: {response.status_code} - {response.text}")
                
                # Try to parse the error response for more details
                try:
                    error_data = response.json()
                    logger.error(f"Supabase error details: {error_data}")
                except:
                    logger.error("Could not parse error response as JSON")
                
                return None
        except httpx.RequestError as e:
            logger.error(f"Network error verifying token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from the database.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Optional[Dict[str, Any]]: User data if found, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get user.")
            return None
        
        try:
            # Query the users table
            response = httpx.get(
                f"{self.url}/rest/v1/profiles?id=eq.{user_id}&select=*",
                headers=self.admin_headers
            )
            
            # Return the user data
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
                else:
                    logger.warning(f"User not found: {user_id}")
                    return None
            else:
                logger.error(f"Error getting user: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def create_task(self, user_id: str, task_id: str, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Create a new task in the database.
        
        Args:
            user_id: ID of the user
            task_id: ID of the task
            prompt: User prompt for the task
            
        Returns:
            Optional[Dict[str, Any]]: Task data if created, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot create task.")
            return None
        
        try:
            # Create the task
            task_data = {
                "id": task_id,
                "user_id": user_id,
                "prompt": prompt,
                "status": "created"
            }
            
            # Insert the task into the database
            response = httpx.post(
                f"{self.url}/rest/v1/tasks",
                headers=self.admin_headers,
                json=task_data
            )
            
            # Return the task data
            if response.status_code == 201:
                return task_data
            else:
                logger.warning(f"Failed to create task: {task_id} - {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return None
    
    def update_task_status(self, task_id: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the status of a task.
        
        Args:
            task_id: ID of the task
            status: New status of the task
            metadata: Optional metadata to update
            
        Returns:
            bool: True if the task was updated, False otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot update task status.")
            return False
        
        try:
            # Create the update data
            update_data = {"status": status}
            
            # Add metadata if provided
            if metadata:
                update_data["metadata"] = json.dumps(metadata)
            
            # Update the task in the database
            response = httpx.patch(
                f"{self.url}/rest/v1/tasks?id=eq.{task_id}",
                headers=self.admin_headers,
                json=update_data
            )
            
            # Return success
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task data from the database.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Optional[Dict[str, Any]]: Task data if found, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get task.")
            return None
        
        try:
            # Query the tasks table
            response = httpx.get(
                f"{self.url}/rest/v1/tasks?id=eq.{task_id}&select=*",
                headers=self.admin_headers
            )
            
            # Return the task data
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
                else:
                    logger.warning(f"Task not found: {task_id}")
                    return None
            else:
                logger.error(f"Error getting task: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting task: {str(e)}")
            return None
    
    def update_user_credits(self, user_id: str, credits: int) -> Optional[Dict[str, Any]]:
        """
        Update user credits in the database.
        
        Args:
            user_id: ID of the user
            credits: New credit amount
            
        Returns:
            Optional[Dict[str, Any]]: Updated user data if successful, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot update user credits.")
            return None
        
        try:
            # Update the user's credits
            response = httpx.patch(
                f"{self.url}/rest/v1/profiles?id=eq.{user_id}",
                headers=self.admin_headers,
                json={"credits": credits}
            )
            
            # Check if the update was successful
            if response.status_code == 204:
                # Get the updated user data
                user_data = self.get_user(user_id)
                if user_data is None:
                    # Create a minimal user data object if get_user returns None
                    logger.warning(f"Could not retrieve updated user data for user {user_id}, returning minimal data")
                    return {"id": user_id, "credits": credits}
                return user_data
            else:
                logger.error(f"Error updating user credits: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error updating user credits: {str(e)}")
            return None
    
    def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List[Dict[str, Any]]: List of task data
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get user tasks.")
            return []
        
        try:
            # Query the tasks table
            response = httpx.get(
                f"{self.url}/rest/v1/tasks?user_id=eq.{user_id}&select=*",
                headers=self.admin_headers
            )
            
            # Return the task data
            if response.status_code == 200:
                return response.json() or []
            else:
                logger.error(f"Error getting user tasks: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting user tasks: {str(e)}")
            return []
    
    # Conversation Management Methods
    
    def create_conversation(self, user_id: str, video_id: Optional[str] = None, 
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a new conversation in the database.
        
        Args:
            user_id: ID of the user
            video_id: Optional ID of the associated video
            metadata: Optional metadata for the conversation
            
        Returns:
            Optional[str]: ID of the created conversation, or None if creation failed
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot create conversation.")
            return None
        
        try:
            # Create the conversation data
            conversation_data = {
                "user_id": user_id,
                "updated_at": datetime.now().isoformat()
            }
            
            # Add video_id if provided
            if video_id:
                conversation_data["video_id"] = video_id
            
            # Add metadata if provided
            if metadata:
                conversation_data["metadata"] = json.dumps(metadata)
            
            # Insert the conversation into the database
            response = httpx.post(
                f"{self.url}/rest/v1/conversations",
                headers=self.admin_headers,
                json=conversation_data
            )
            
            # Check if the insertion was successful
            if response.status_code == 201:
                # Get the ID of the created conversation
                # Supabase returns the ID in the Location header
                location = response.headers.get("Location")
                if location:
                    # Extract the ID from the Location header
                    conversation_id = location.split("/")[-1]
                    logger.info(f"Created conversation: {conversation_id}")
                    return conversation_id
                
                # If Location header is not available, query the database
                logger.warning("Location header not found in response, querying database")
                
                # Query the database for the most recent conversation
                get_response = httpx.get(
                    f"{self.url}/rest/v1/conversations?user_id=eq.{user_id}&order=created_at.desc&limit=1",
                    headers=self.admin_headers
                )
                
                if get_response.status_code == 200:
                    conversations = get_response.json()
                    if conversations and len(conversations) > 0:
                        conversation_id = conversations[0]["id"]
                        logger.info(f"Retrieved conversation ID: {conversation_id}")
                        return conversation_id
                
                logger.warning("Could not retrieve conversation ID")
                return None
            else:
                logger.error(f"Error creating conversation: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            return None
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation data from the database.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Optional[Dict[str, Any]]: Conversation data if found, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get conversation.")
            return None
        
        try:
            # Query the conversations table
            response = httpx.get(
                f"{self.url}/rest/v1/conversations?id=eq.{conversation_id}&select=*",
                headers=self.admin_headers
            )
            
            # Return the conversation data
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
                else:
                    logger.warning(f"Conversation not found: {conversation_id}")
                    return None
            else:
                logger.error(f"Error getting conversation: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of conversations for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to return
            offset: Offset for pagination
            
        Returns:
            List[Dict[str, Any]]: List of conversation data
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get user conversations.")
            return []
        
        try:
            # Query the conversations table
            response = httpx.get(
                f"{self.url}/rest/v1/conversations?user_id=eq.{user_id}&order=updated_at.desc&limit={limit}&offset={offset}",
                headers=self.admin_headers
            )
            
            # Return the conversation data
            if response.status_code == 200:
                return response.json() or []
            else:
                logger.error(f"Error getting user conversations: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            return []
    
    def add_message(self, conversation_id: str, role: str, content: str, 
                   name: Optional[str] = None, function_call: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            role: Role of the message sender ('system', 'user', 'assistant', 'function')
            content: Content of the message
            name: Optional name for function messages
            function_call: Optional function call data for assistant messages
            
        Returns:
            Optional[str]: ID of the created message, or None if creation failed
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot add message.")
            return None
        
        try:
            # Get the current sequence order
            sequence_response = httpx.get(
                f"{self.url}/rest/v1/conversation_messages?conversation_id=eq.{conversation_id}&select=sequence_order&order=sequence_order.desc&limit=1",
                headers=self.admin_headers
            )
            
            # Determine the next sequence order
            next_sequence = 1
            if sequence_response.status_code == 200:
                data = sequence_response.json()
                if data and len(data) > 0:
                    next_sequence = data[0]["sequence_order"] + 1
            
            # Create the message data
            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "sequence_order": next_sequence
            }
            
            # Add name if provided
            if name:
                message_data["name"] = name
            
            # Add function_call if provided
            if function_call:
                message_data["function_call"] = json.dumps(function_call)
            
            # Insert the message into the database
            response = httpx.post(
                f"{self.url}/rest/v1/conversation_messages",
                headers=self.admin_headers,
                json=message_data
            )
            
            # Update the conversation's updated_at timestamp
            self._update_conversation_timestamp(conversation_id)
            
            # Check if the insertion was successful
            if response.status_code == 201:
                # Get the ID of the created message
                location = response.headers.get("Location")
                if location:
                    # Extract the ID from the Location header
                    message_id = location.split("/")[-1]
                    return message_id
                
                logger.warning("Location header not found in response")
                return None
            else:
                logger.error(f"Error adding message: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            return None
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List[Dict[str, Any]]: List of message data
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot get conversation messages.")
            return []
        
        try:
            # Query the conversation_messages table
            response = httpx.get(
                f"{self.url}/rest/v1/conversation_messages?conversation_id=eq.{conversation_id}&order=sequence_order.asc",
                headers=self.admin_headers
            )
            
            # Return the message data
            if response.status_code == 200:
                return response.json() or []
            else:
                logger.error(f"Error getting conversation messages: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting conversation messages: {str(e)}")
            return []
    
    def update_conversation_metadata(self, conversation_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update the metadata for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            metadata: New metadata for the conversation
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot update conversation metadata.")
            return False
        
        try:
            # Update the conversation metadata
            response = httpx.patch(
                f"{self.url}/rest/v1/conversations?id=eq.{conversation_id}",
                headers=self.admin_headers,
                json={
                    "metadata": json.dumps(metadata),
                    "updated_at": datetime.now().isoformat()
                }
            )
            
            # Return success
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Error updating conversation metadata: {str(e)}")
            return False
    
    def _update_conversation_timestamp(self, conversation_id: str) -> bool:
        """
        Update the updated_at timestamp for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        if not self.url:
            return False
        
        try:
            # Update the conversation timestamp
            response = httpx.patch(
                f"{self.url}/rest/v1/conversations?id=eq.{conversation_id}",
                headers=self.admin_headers,
                json={"updated_at": datetime.now().isoformat()}
            )
            
            # Return success
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Error updating conversation timestamp: {str(e)}")
            return False
    
    def save_asset(self, task_id: str, asset_type: str, url: str, storage_path: str, 
                  scene_index: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Save an asset to the database.
        
        Args:
            task_id: ID of the task
            asset_type: Type of asset ('character', 'scene_image', 'audio', 'music', 'video')
            url: URL of the asset
            storage_path: Path to the asset in storage
            scene_index: Optional index of the scene
            metadata: Optional metadata for the asset
            
        Returns:
            Optional[Dict[str, Any]]: Asset data if created, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot save asset.")
            return None
        
        try:
            # Create the asset data
            asset_data = {
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "asset_type": asset_type,
                "url": url,
                "storage_path": storage_path
            }
            
            # Add scene_index if provided
            if scene_index is not None:
                asset_data["scene_index"] = str(scene_index)
            
            # Add metadata if provided
            if metadata:
                asset_data["metadata"] = json.dumps(metadata)
            
            # Insert the asset into the database
            response = httpx.post(
                f"{self.url}/rest/v1/assets",
                headers=self.admin_headers,
                json=asset_data
            )
            
            # Return the asset data
            if response.status_code == 201:
                return asset_data
            else:
                logger.warning(f"Failed to save asset: {asset_data['id']} - {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error saving asset: {str(e)}")
            return None
    
    def save_video(self, task_id: str, url: str, storage_path: str, duration: float) -> Optional[Dict[str, Any]]:
        """
        Save a video to the database.
        
        Args:
            task_id: ID of the task
            url: URL of the video
            storage_path: Path to the video in storage
            duration: Duration of the video in seconds
            
        Returns:
            Optional[Dict[str, Any]]: Video data if created, None otherwise
        """
        if not self.url:
            logger.warning("Supabase URL not set. Cannot save video.")
            return None
        
        try:
            # Create the video data
            video_data = {
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "url": url,
                "storage_path": storage_path,
                "duration": duration
            }
            
            # Insert the video into the database
            response = httpx.post(
                f"{self.url}/rest/v1/videos",
                headers=self.admin_headers,
                json=video_data
            )
            
            # Return the video data
            if response.status_code == 201:
                return video_data
            else:
                logger.warning(f"Failed to save video: {video_data['id']} - {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error saving video: {str(e)}")
            return None
    
    def download_file(self, path: str, bucket: Optional[str] = None) -> Optional[bytes]:
        """
        Download a file from Supabase storage.
        
        Args:
            path: Path to the file in Supabase storage
            bucket: Optional bucket name (defaults to self.bucket_name)
            
        Returns:
            Optional[bytes]: Content of the file, or None if download failed
        """
        if not self.storage:
            logger.warning("Supabase storage not initialized. Cannot download file.")
            return None
        
        # Ensure bucket is not None
        actual_bucket = bucket if bucket is not None else self.bucket_name
        
        return self.storage.download(path, actual_bucket)


class SupabaseStorage:
    """
    Interface for Supabase Storage API
    """
    
    def __init__(self, service: SupabaseService):
        """
        Initialize the storage interface
        
        Args:
            service: Supabase service
        """
        self.service = service
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """
        List all storage buckets
        
        Returns:
            List of buckets
        """
        try:
            response = httpx.get(
                f"{self.service.url}/storage/v1/bucket",
                headers=self.service.admin_headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error listing buckets: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error listing buckets: {str(e)}")
            return []
    
    def create_bucket(self, name: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a storage bucket
        
        Args:
            name: Bucket name
            options: Bucket options
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {"name": name, "id": name}
            if options:
                data.update(options)
            
            response = httpx.post(
                f"{self.service.url}/storage/v1/bucket",
                headers=self.service.admin_headers,
                json=data
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error creating bucket: {str(e)}")
            return False
    
    def from_(self, bucket: str) -> 'BucketOperations':
        """
        Get operations for a specific bucket
        
        Args:
            bucket: Bucket name
            
        Returns:
            Bucket operations
        """
        return BucketOperations(self.service, bucket)
    
    def download(self, path: str, bucket: str) -> Optional[bytes]:
        """
        Download a file
        
        Args:
            path: File path
            bucket: Bucket name
            
        Returns:
            File content or None if download failed
        """
        try:
            response = httpx.get(
                f"{self.service.url}/storage/v1/object/{bucket}/{path}",
                headers=self.service.headers
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Error downloading file: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return None


class BucketOperations:
    """
    Operations for a specific bucket
    """
    
    def __init__(self, service: SupabaseService, bucket: str):
        """
        Initialize bucket operations
        
        Args:
            service: Supabase service
            bucket: Bucket name
        """
        self.service = service
        self.bucket = bucket
    
    def upload(self, path: str, file_content: bytes) -> bool:
        """
        Upload a file
        
        Args:
            path: File path
            file_content: File content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create headers without Content-Type to let the browser set it
            headers = {
                "apikey": self.service.key,
                "Authorization": f"Bearer {self.service.key}",
            }
            
            response = httpx.post(
                f"{self.service.url}/storage/v1/object/{self.bucket}/{path}",
                headers=headers,
                content=file_content
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
    
    def get_public_url(self, path: str) -> str:
        """
        Get public URL for a file
        
        Args:
            path: File path
            
        Returns:
            Public URL
        """
        return f"{self.service.url}/storage/v1/object/public/{self.bucket}/{path}"
    
    def list(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List files in the bucket
        
        Args:
            prefix: Path prefix
            
        Returns:
            List of files
        """
        try:
            response = httpx.get(
                f"{self.service.url}/storage/v1/object/list/{self.bucket}",
                headers=self.service.headers,
                params={"prefix": prefix}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error listing files: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def remove(self, paths: List[str]) -> bool:
        """
        Remove files from the bucket
        
        Args:
            paths: List of file paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = httpx.delete(
                f"{self.service.url}/storage/v1/object/{self.bucket}",
                headers=self.service.headers,
                params={"prefixes": ",".join(paths)}
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error removing files: {str(e)}")
            return False


# Create a global instance of the Supabase service
supabase_service = SupabaseService()
