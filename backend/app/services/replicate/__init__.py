"""
Replicate services package.

This package provides services for interacting with Replicate models.
"""
from app.services.replicate.base import ReplicateService, ProgressCallback
from app.services.replicate.music_generation import MusicGenerationService, MusicGenerationRequest, MusicGenerationResponse
from app.services.replicate.tts import VoiceCloneTTSService, TTSRequest, TTSResponse

__all__ = [
    "ReplicateService",
    "ProgressCallback",
    "MusicGenerationService",
    "MusicGenerationRequest",
    "MusicGenerationResponse",
    "VoiceCloneTTSService",
    "TTSRequest",
    "TTSResponse",
]
