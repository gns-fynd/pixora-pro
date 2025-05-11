"""
Fal.ai services package.

This package provides services for interacting with Fal.ai models.
"""
from app.services.fal_ai.base import FalAiService, ProgressCallback
from app.services.fal_ai.text_to_image import TextToImageService, TextToImageRequest, TextToImageResponse, ImageSize
from app.services.fal_ai.image_to_video import ImageToVideoService, ImageToVideoRequest, ImageToVideoResponse, AspectRatio, Duration
from app.services.fal_ai.text_to_speech import TextToSpeechService, TextToSpeechRequest, TextToSpeechResponse, VoiceCloneRequest, VoiceCloneResponse
from app.services.fal_ai.text_to_music import TextToMusicService, TextToMusicRequest, TextToMusicResponse

__all__ = [
    "FalAiService",
    "ProgressCallback",
    "TextToImageService",
    "TextToImageRequest",
    "TextToImageResponse",
    "ImageSize",
    "ImageToVideoService",
    "ImageToVideoRequest",
    "ImageToVideoResponse",
    "AspectRatio",
    "Duration",
    "TextToSpeechService",
    "TextToSpeechRequest",
    "TextToSpeechResponse",
    "VoiceCloneRequest",
    "VoiceCloneResponse",
    "TextToMusicService",
    "TextToMusicRequest",
    "TextToMusicResponse",
]
