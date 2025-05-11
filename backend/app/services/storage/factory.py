"""
Factory functions for storage services.

This module provides factory functions for creating storage service instances.
"""
from typing import Union
from fastapi import Depends
from app.core.config import Settings, get_settings
from app.services.storage.base import StorageService
from app.services.storage.supabase import SupabaseStorageService
from app.services.storage.local import LocalStorageService


def get_storage_service(settings: Settings = Depends(get_settings)) -> Union[LocalStorageService, SupabaseStorageService]:
    """
    Factory function to get the appropriate storage service implementation.
    
    Args:
        settings: Application settings
        
    Returns:
        A concrete instance of a StorageService implementation (either LocalStorageService or SupabaseStorageService)
    """
    # Choose implementation based on settings
    storage_type = getattr(settings, "STORAGE_TYPE", "local")
    
    if storage_type.lower() == "supabase":
        return SupabaseStorageService(settings)
    else:
        return LocalStorageService(settings)
