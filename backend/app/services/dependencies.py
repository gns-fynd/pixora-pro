"""
Dependency injection providers for the application.

This module provides dependency injection functions for various services.
"""
from typing import Union
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.storage.local import LocalStorageService
from app.services.storage.supabase import SupabaseStorageService
from app.services.storage.base import StorageService


def get_storage_service_dependency(settings: Settings = Depends(get_settings)) -> Union[LocalStorageService, SupabaseStorageService]:
    """
    Get a concrete implementation of the StorageService.
    
    This function explicitly returns a concrete implementation based on settings,
    avoiding any issues with abstract class instantiation.
    
    Args:
        settings: Application settings
        
    Returns:
        A concrete implementation of StorageService (either LocalStorageService or SupabaseStorageService)
    """
    storage_type = getattr(settings, "STORAGE_TYPE", "local")
    
    if storage_type.lower() == "supabase":
        return SupabaseStorageService(settings)
    else:
        return LocalStorageService(settings)
