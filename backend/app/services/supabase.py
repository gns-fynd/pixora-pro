"""
Supabase service for interacting with Supabase
"""
from typing import Dict, Any, Optional, List

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings


class SupabaseClient:
    """
    Client for interacting with Supabase
    """
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize Supabase client
        
        Args:
            settings: Application settings
        """
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.supabase_service_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        
        # Regular headers for normal operations
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }
        
        # Admin headers for operations that need to bypass RLS
        self.admin_headers = {
            "apikey": self.supabase_service_key,
            "Authorization": f"Bearer {self.supabase_service_key}",
            "Content-Type": "application/json",
        }
    
    def from_(self, table: str):
        """
        Create a query builder for a table
        
        Args:
            table: Table name
            
        Returns:
            Query builder
        """
        return QueryBuilder(self, table)


class QueryBuilder:
    """
    Query builder for Supabase
    """
    def __init__(self, client: SupabaseClient, table: str):
        """
        Initialize query builder
        
        Args:
            client: Supabase client
            table: Table name
        """
        self.client = client
        self.table = table
        self.query_params = {}
        self.filters = []
    
    def select(self, columns: str):
        """
        Select columns
        
        Args:
            columns: Columns to select
            
        Returns:
            Query builder
        """
        self.query_params["select"] = columns
        return self
    
    def eq(self, column: str, value: Any):
        """
        Add equality filter
        
        Args:
            column: Column name
            value: Value to compare
            
        Returns:
            Query builder
        """
        self.filters.append((column, "eq", value))
        return self
    
    def update(self, data: Dict[str, Any]):
        """
        Update data
        
        Args:
            data: Data to update
            
        Returns:
            Query builder
        """
        self.update_data = data
        return self
    
    def insert(self, data: Dict[str, Any]):
        """
        Insert data
        
        Args:
            data: Data to insert
            
        Returns:
            Query builder
        """
        self.insert_data = data
        return self
    
    def range(self, start: int, end: int):
        """
        Add range filter
        
        Args:
            start: Start index
            end: End index
            
        Returns:
            Query builder
        """
        self.query_params["range"] = f"{start}-{end}"
        return self
    
    def order(self, column: str, options: Dict[str, Any] = None):
        """
        Add order by
        
        Args:
            column: Column to order by
            options: Order options
            
        Returns:
            Query builder
        """
        self.query_params["order"] = column
        if options and options.get("ascending") is False:
            self.query_params["order"] += ".desc"
        return self
    
    def gte(self, column: str, value: Any):
        """
        Add greater than or equal filter
        
        Args:
            column: Column name
            value: Value to compare
            
        Returns:
            Query builder
        """
        self.filters.append((column, "gte", value))
        return self
    
    def lte(self, column: str, value: Any):
        """
        Add less than or equal filter
        
        Args:
            column: Column name
            value: Value to compare
            
        Returns:
            Query builder
        """
        self.filters.append((column, "lte", value))
        return self
    
    async def execute(self):
        """
        Execute the query
        
        Returns:
            Query result
        """
        # Build the URL
        url = f"{self.client.supabase_url}/rest/v1/{self.table}"
        
        # Add filters to query params using PostgREST format
        for column, op, value in self.filters:
            self.query_params[f"{column}"] = f"{op}.{value}"
        
        # Determine the HTTP method and data
        method = "GET"
        data = None
        
        if hasattr(self, "update_data"):
            method = "PATCH"
            data = self.update_data
        elif hasattr(self, "insert_data"):
            method = "POST"
            data = self.insert_data
        
        # Execute the request
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    url,
                    params=self.query_params,
                    headers=self.client.admin_headers,
                )
            elif method == "PATCH":
                response = await client.patch(
                    url,
                    params=self.query_params,
                    json=data,
                    headers=self.client.admin_headers,
                )
            elif method == "POST":
                response = await client.post(
                    url,
                    json=data,
                    headers=self.client.admin_headers,
                )
            
            # Parse the response
            if response.status_code in [200, 201, 204]:
                if response.status_code == 204:
                    return type("Response", (), {"data": None})
                
                # Try to parse JSON response, but handle empty responses
                try:
                    if response.content and len(response.content.strip()) > 0:
                        return type("Response", (), {"data": response.json()})
                    else:
                        return type("Response", (), {"data": None})
                except Exception as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    return type("Response", (), {"data": None})
            else:
                # Handle error
                print(f"Error: {response.status_code} - {response.text}")
                return type("Response", (), {"data": None, "error": response.text})


class SupabaseService:
    """
    Service for interacting with Supabase
    """
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize Supabase service
        
        Args:
            settings: Application settings
        """
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.supabase_service_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        
        # Regular headers for normal operations
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }
        
        # Admin headers for operations that need to bypass RLS
        self.admin_headers = {
            "apikey": self.supabase_service_key,
            "Authorization": f"Bearer {self.supabase_service_key}",
            "Content-Type": "application/json",
        }
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user from Supabase
        
        Args:
            user_id: User ID
            
        Returns:
            User data or None if not found
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/profiles?id=eq.{user_id}&select=*",
                headers=self.admin_headers,  # Use admin headers to bypass RLS
            )
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    return users[0]
            
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create user in Supabase
        
        Args:
            user_data: User data
            
        Returns:
            Created user data or None if creation failed
        """
        try:
            # Ensure required fields are present
            if "id" not in user_data:
                print("Error: 'id' is required for user creation")
                return None
                
            if "email" not in user_data:
                print("Error: 'email' is required for user creation")
                return None
            
            # First, try to get the user - they might already exist
            user = await self.get_user(user_data["id"])
            if user:
                print(f"User {user_data['id']} already exists, returning existing user")
                return user
            
            async with httpx.AsyncClient() as client:
                # Use admin headers to bypass RLS
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/profiles",
                    headers=self.admin_headers,
                    json=user_data,
                )
                
                if response.status_code == 201:
                    # Return the created user
                    return await self.get_user(user_data["id"])
                
                # Check for duplicate key error (user already exists)
                if response.status_code == 409 and "23505" in response.text:
                    print(f"User {user_data['id']} was created by another request, fetching existing user")
                    # User was created by another concurrent request, try to get it again
                    return await self.get_user(user_data["id"])
                
                # Log error details
                print(f"Error creating user: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception creating user: {str(e)}")
            return None
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user in Supabase
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Updated user data or None if update failed
        """
        try:
            # Map name to full_name if present
            if "name" in user_data and "full_name" not in user_data:
                user_data["full_name"] = user_data.pop("name")
            
            async with httpx.AsyncClient() as client:
                # Use admin headers to bypass RLS
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/profiles?id=eq.{user_id}",
                    headers=self.admin_headers,
                    json=user_data,
                )
                
                if response.status_code == 204:
                    # Return the updated user
                    return await self.get_user(user_id)
                
                # Log error details
                print(f"Error updating user: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception updating user: {str(e)}")
            return None
    
    async def get_user_credits(self, user_id: str) -> int:
        """
        Get user credits
        
        Args:
            user_id: User ID
            
        Returns:
            User credits
        """
        user = await self.get_user(user_id)
        return user.get("credits", 0) if user else 0
    
    async def update_user_credits(self, user_id: str, credits: int) -> Optional[Dict[str, Any]]:
        """
        Update user credits
        
        Args:
            user_id: User ID
            credits: New credit amount
            
        Returns:
            Updated user data or None if update failed
        """
        try:
            return await self.update_user(user_id, {"credits": credits})
        except Exception as e:
            print(f"Exception updating user credits: {str(e)}")
            return None


def get_supabase_client(settings: Settings = Depends(get_settings)) -> SupabaseClient:
    """
    Get Supabase client
    
    Args:
        settings: Application settings
        
    Returns:
        Supabase client
    """
    return SupabaseClient(settings)
