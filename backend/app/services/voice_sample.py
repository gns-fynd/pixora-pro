"""
Voice sample service.

This module provides a service for managing voice samples.
"""
import logging
import uuid
from typing import List, Optional, Dict, Any, Union
import json

from fastapi import Depends, UploadFile, HTTPException, status
from supabase import Client

from app.core.config import Settings, get_settings
from app.schemas.voice_sample import (
    VoiceSampleCreate,
    VoiceSampleUpdate,
    VoiceSample,
    VoiceSampleList,
)
from app.services.storage import StorageManager, StorageService
from app.services.dependencies import get_storage_service_dependency


# Set up logging
logger = logging.getLogger(__name__)


class VoiceSampleService:
    """
    Service for managing voice samples.
    """
    
    def __init__(
        self,
        storage_manager: StorageManager = Depends(),
        storage_service: StorageService = Depends(get_storage_service_dependency),
        settings: Settings = Depends(get_settings),
    ):
        """
        Initialize the voice sample service.
        
        Args:
            storage_manager: Storage manager
            storage_service: Storage service implementation
            settings: Application settings
        """
        self.storage_manager = storage_manager
        self.storage_service = storage_service
        self.settings = settings
        
        # Get Supabase client from the storage service if it's a SupabaseStorageService
        from app.services.storage.supabase import SupabaseStorageService
        
        if isinstance(storage_service, SupabaseStorageService):
            self.supabase = storage_service.admin_client
        else:
            # For other storage services, we need to handle this differently
            # For now, we'll use a direct Supabase client if settings are available
            if hasattr(settings, 'SUPABASE_URL') and hasattr(settings, 'SUPABASE_SERVICE_KEY'):
                from supabase import create_client
                self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY)
            else:
                # If no Supabase settings are available, log a warning
                logger.warning("No Supabase client available for VoiceSampleService. Some features may not work.")
                self.supabase = None
        
        # Define the voice samples bucket
        self.voice_samples_bucket = 'voice-samples'
    
    async def create_voice_sample(
        self,
        data: VoiceSampleCreate,
        audio_file: UploadFile,
        user_id: uuid.UUID,
    ) -> VoiceSample:
        """
        Create a new voice sample.
        
        Args:
            data: Voice sample data
            audio_file: The audio file
            user_id: ID of the user creating the voice sample
            
        Returns:
            The created voice sample
        """
        try:
            # Upload the audio file
            file_data = await audio_file.read()
            sample_url = await self.storage_manager.upload_audio(
                file_data=file_data,
                filename=audio_file.filename,
                content_type=audio_file.content_type,
                user_id=str(user_id),
            )
            
            # Create the voice sample record in the database
            voice_sample_data = {
                "name": data.name,
                "description": data.description,
                "gender": data.gender,
                "tone": data.tone,
                "is_default": data.is_default,
                "is_public": data.is_public,
                "sample_url": sample_url,
                "user_id": str(user_id),
            }
            
            # Insert into the voice_samples table
            result = self.supabase.table('voice_samples').insert(voice_sample_data).execute()
            
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create voice sample",
                )
            
            voice_sample = result.data[0]
            
            # If this is set as default, unset other defaults for this user
            if data.is_default:
                await self._unset_other_defaults(voice_sample["id"], str(user_id))
                
            # Update settings if this is public and default
            if data.is_public and data.is_default:
                await self._update_default_voice_sample_url(sample_url)
            
            # Convert to Pydantic model
            return self._map_to_schema(voice_sample)
            
        except Exception as e:
            logger.error(f"Error creating voice sample: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Voice sample creation failed: {str(e)}",
            )
    
    async def get_voice_samples(
        self,
        user_id: Optional[uuid.UUID] = None,
        include_public: bool = True,
        gender: Optional[str] = None,
        tone: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> VoiceSampleList:
        """
        Get voice samples.
        
        Args:
            user_id: Optional user ID to filter by
            include_public: Whether to include public voice samples
            gender: Optional gender to filter by
            tone: Optional tone to filter by
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of voice samples
        """
        try:
            # Start building the query
            query = self.supabase.table('voice_samples')
            count_query = self.supabase.table('voice_samples')
            
            # Add filters
            if user_id:
                if include_public:
                    query = query.or_(f'user_id.eq.{str(user_id)},is_public.eq.true')
                    count_query = count_query.or_(f'user_id.eq.{str(user_id)},is_public.eq.true')
                else:
                    query = query.eq('user_id', str(user_id))
                    count_query = count_query.eq('user_id', str(user_id))
            elif not include_public:
                # If no user_id and not including public, return empty list
                return VoiceSampleList(items=[], total=0)
            else:
                # If no user_id but including public, only show public samples
                query = query.eq('is_public', True)
                count_query = count_query.eq('is_public', True)
            
            # Add gender filter
            if gender:
                query = query.eq('gender', gender)
                count_query = count_query.eq('gender', gender)
            
            # Add tone filter
            if tone:
                query = query.eq('tone', tone)
                count_query = count_query.eq('tone', tone)
            
            # Get count first (with same filters but no pagination)
            count_result = count_query.select('id, count').execute()
            total = len(count_result.data) if count_result.data else 0
            
            # Add sorting and pagination for the main query
            query = query.order('is_default', desc=True).order('created_at', desc=True)
            query = query.range(offset, offset + limit - 1)
            
            # Execute the query
            result = query.execute()
            
            # Map to schema
            voice_samples = [self._map_to_schema(item) for item in result.data]
            
            return VoiceSampleList(
                items=voice_samples,
                total=total,
            )
            
        except Exception as e:
            logger.error(f"Error getting voice samples: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get voice samples: {str(e)}",
            )
    
    async def get_voice_sample(
        self,
        voice_sample_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> VoiceSample:
        """
        Get a voice sample by ID.
        
        Args:
            voice_sample_id: The voice sample ID
            user_id: Optional user ID for permission checking
            
        Returns:
            The voice sample
        """
        try:
            # Build the query
            query = self.supabase.table('voice_samples').eq('id', str(voice_sample_id))
            
            # Add user check if provided
            if user_id:
                query = query.or_(f'user_id.eq.{str(user_id)},is_public.eq.true')
            
            # Execute the query
            result = query.execute()
            
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Voice sample not found",
                )
            
            # Map to schema
            return self._map_to_schema(result.data[0])
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting voice sample: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get voice sample: {str(e)}",
            )
    
    async def update_voice_sample(
        self,
        voice_sample_id: uuid.UUID,
        data: VoiceSampleUpdate,
        user_id: uuid.UUID,
        audio_file: Optional[UploadFile] = None,
    ) -> VoiceSample:
        """
        Update a voice sample.
        
        Args:
            voice_sample_id: The voice sample ID
            data: The updated data
            user_id: ID of the user updating the voice sample
            audio_file: Optional new audio file
            
        Returns:
            The updated voice sample
        """
        try:
            # Check if the voice sample exists and belongs to the user
            result = self.supabase.table('voice_samples') \
                .select('*') \
                .eq('id', str(voice_sample_id)) \
                .eq('user_id', str(user_id)) \
                .execute()
            
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Voice sample not found or you don't have permission to update it",
                )
            
            voice_sample = result.data[0]
            
            # Upload new audio file if provided
            sample_url = voice_sample["sample_url"]
            if audio_file:
                file_data = await audio_file.read()
                sample_url = await self.storage_manager.upload_audio(
                    file_data=file_data,
                    filename=audio_file.filename,
                    content_type=audio_file.content_type,
                    user_id=str(user_id),
                )
            
            # Build the update data
            update_data = {}
            
            # Add fields to update
            if data.name is not None:
                update_data["name"] = data.name
                
            if data.description is not None:
                update_data["description"] = data.description
                
            if data.gender is not None:
                update_data["gender"] = data.gender
                
            if data.tone is not None:
                update_data["tone"] = data.tone
                
            if data.is_default is not None:
                update_data["is_default"] = data.is_default
                
            if data.is_public is not None:
                update_data["is_public"] = data.is_public
                
            if audio_file or data.sample_url:
                update_data["sample_url"] = data.sample_url or sample_url
            
            # If there are no fields to update, return the voice sample as is
            if not update_data and not audio_file:
                return self._map_to_schema(voice_sample)
            
            # Execute the update
            result = self.supabase.table('voice_samples') \
                .update(update_data) \
                .eq('id', str(voice_sample_id)) \
                .execute()
                
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update voice sample",
                )
                
            updated_voice_sample = result.data[0]
            
            # If this is set as default, unset other defaults for this user
            if data.is_default:
                await self._unset_other_defaults(str(voice_sample_id), str(user_id))
                
            # Update settings if this is public and default
            is_public = data.is_public if data.is_public is not None else voice_sample["is_public"]
            is_default = data.is_default if data.is_default is not None else voice_sample["is_default"]
            
            if is_public and is_default:
                await self._update_default_voice_sample_url(sample_url)
            
            # Map to schema
            return self._map_to_schema(updated_voice_sample)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating voice sample: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update voice sample: {str(e)}",
            )
    
    async def delete_voice_sample(
        self,
        voice_sample_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Delete a voice sample.
        
        Args:
            voice_sample_id: The voice sample ID
            user_id: ID of the user deleting the voice sample
            
        Returns:
            A success message
        """
        try:
            # Check if the voice sample exists and belongs to the user
            result = self.supabase.table('voice_samples') \
                .select('*') \
                .eq('id', str(voice_sample_id)) \
                .eq('user_id', str(user_id)) \
                .execute()
            
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Voice sample not found or you don't have permission to delete it",
                )
            
            voice_sample = result.data[0]
            
            # Delete the voice sample from the database
            self.supabase.table('voice_samples') \
                .delete() \
                .eq('id', str(voice_sample_id)) \
                .execute()
            
            # Update the default voice sample URL if needed
            if voice_sample["is_default"] and voice_sample["is_public"]:
                # Find another default public voice sample
                result = self.supabase.table('voice_samples') \
                    .select('sample_url') \
                    .eq('is_default', True) \
                    .eq('is_public', True) \
                    .limit(1) \
                    .execute()
                
                if result.data and len(result.data) > 0:
                    await self._update_default_voice_sample_url(result.data[0]["sample_url"])
            
            # Return success message
            return {
                "message": "Voice sample deleted successfully",
                "id": str(voice_sample_id),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting voice sample: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete voice sample: {str(e)}",
            )
    
    async def _unset_other_defaults(self, current_id: str, user_id: str) -> None:
        """
        Unset the default flag on other voice samples for this user.
        
        Args:
            current_id: The ID of the current voice sample (to exclude)
            user_id: The user ID
        """
        try:
            # Update all other default voice samples for this user
            self.supabase.table('voice_samples') \
                .update({"is_default": False}) \
                .eq('user_id', user_id) \
                .neq('id', current_id) \
                .eq('is_default', True) \
                .execute()
        except Exception as e:
            logger.error(f"Error unsetting other default voice samples: {str(e)}")
    
    async def _update_default_voice_sample_url(self, url: str) -> None:
        """
        Update the default voice sample URL in settings.
        
        Args:
            url: The URL to set as default
        """
        try:
            # Check if settings table exists and has the record
            result = self.supabase.table('settings') \
                .select('*') \
                .eq('key', 'default_voice_sample_url') \
                .execute()
            
            if result.data and len(result.data) > 0:
                # Update existing record
                self.supabase.table('settings') \
                    .update({"value": url}) \
                    .eq('key', 'default_voice_sample_url') \
                    .execute()
            else:
                # Create new record
                self.supabase.table('settings') \
                    .insert({"key": "default_voice_sample_url", "value": url}) \
                    .execute()
                
        except Exception as e:
            logger.error(f"Error updating default voice sample URL: {str(e)}")
    
    def _map_to_schema(self, db_item: Dict[str, Any]) -> VoiceSample:
        """
        Map a database row to a VoiceSample schema.
        
        Args:
            db_item: The database row
            
        Returns:
            The VoiceSample schema
        """
        return VoiceSample(
            id=uuid.UUID(db_item["id"]) if isinstance(db_item["id"], str) else db_item["id"],
            name=db_item["name"],
            description=db_item["description"],
            gender=db_item["gender"],
            tone=db_item["tone"],
            is_default=db_item["is_default"],
            is_public=db_item["is_public"],
            sample_url=db_item["sample_url"],
            user_id=uuid.UUID(db_item["user_id"]) if db_item.get("user_id") and isinstance(db_item["user_id"], str) else db_item.get("user_id"),
            created_at=db_item["created_at"],
            updated_at=db_item["updated_at"],
        )
