"""
Application configuration settings
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings
    
    Loads settings from environment variables
    """
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Pixora AI"
    
    # Security
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_KEY: str = Field(..., description="Supabase anon/public key")
    SUPABASE_SERVICE_KEY: str = Field("", description="Supabase service role key for admin operations")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT secret for token validation")
    
    # Storage
    STORAGE_TYPE: str = Field("local", description="Storage service type (local or supabase)")
    STORAGE_VIDEOS_BUCKET: str = Field("videos", description="Supabase storage bucket for videos")
    STORAGE_IMAGES_BUCKET: str = Field("images", description="Supabase storage bucket for images")
    STORAGE_AUDIO_BUCKET: str = Field("audio", description="Supabase storage bucket for audio files")
    STORAGE_PUBLIC_URL: Optional[str] = Field(None, description="Public URL for storage assets (if different from Supabase URL)")
    
    # AI Services
    FAL_API_KEY: str = Field(..., description="Fal.ai API key")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    REPLICATE_API_TOKEN: Optional[str] = Field(None, description="Replicate API token")
    
    # Fal.ai Model Endpoints
    FAL_TEXT_TO_IMAGE_MODEL: str = Field("fal-ai/flux/dev", description="Fal.ai text-to-image model endpoint")
    FAL_IMAGE_TO_VIDEO_MODEL: str = Field("fal-ai/kling-video/v1.6/pro/image-to-video", description="Fal.ai image-to-video model endpoint")
    FAL_TEXT_TO_SPEECH_MODEL: str = Field("fal-ai/minimax-tts/voice-clone", description="Fal.ai text-to-speech model endpoint")
    FAL_TEXT_TO_MUSIC_MODEL: str = Field("fal-ai/elevenlabs/sound-effects", description="Fal.ai text-to-music model endpoint")
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    ENABLE_JSON_LOGS: bool = Field(False, description="Enable JSON format for logs")
    
    REDIS_URL: str = "redis://localhost:6379/0"
    STRICT_SESSION_SECURITY: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings
    
    Uses lru_cache to avoid loading .env file multiple times
    
    Returns:
        Settings object with configuration values
    """
    return Settings()
