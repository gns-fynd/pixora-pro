"""
Supabase service for Pixora AI Video Creation Platform
"""
import os
from typing import Dict, Any, Optional, List, Union
import logging
import httpx
import json
from pathlib import Path

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
                update_data["metadata"] = metadata
            
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
