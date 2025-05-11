"""
Generation router for AI-generated content.

This module provides API endpoints for generating content using AI models.
"""
import logging
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.services import (
    TextToImageService,
    ImageToVideoService,
    TextToSpeechService,
    TextToMusicService,
    MusicGenerationService,
    CreditService,
)
from app.ai.video_generator import VideoGenerator
from app.schemas.generation import (
    GenerationRequest,
    GenerationStatusResponse,
    GenerationStatus,
    GenerationStep,
    GenerationTaskInfo,
)
from app.services.fal_ai import (
    TextToImageRequest,
    TextToImageResponse,
    ImageToVideoRequest,
    ImageToVideoResponse,
    TextToSpeechRequest,
    TextToSpeechResponse,
    VoiceCloneRequest,
    VoiceCloneResponse,
    TextToMusicRequest,
    TextToMusicResponse,
    ImageSize,
    AspectRatio,
    Duration,
)
from app.services.replicate import (
    MusicGenerationRequest,
    MusicGenerationResponse,
)
from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User


# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/generation",
    tags=["generation"],
    responses={404: {"description": "Not found"}},
)


# Progress tracking
generation_progress = {}


def track_progress(task_id: str, progress: float, message: Optional[str] = None):
    """
    Track progress of a generation task.
    
    Args:
        task_id: The task ID
        progress: The progress (0-100)
        message: Optional message
    """
    generation_progress[task_id] = {
        "progress": progress,
        "message": message or f"Processing: {progress:.0f}%",
    }


@router.post("/image", response_model=TextToImageResponse)
async def generate_image(
    request: TextToImageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    text_to_image_service: TextToImageService = Depends(),
    credit_service: CreditService = Depends(),
):
    """
    Generate an image from a text prompt.
    """
    try:
        # Generate a task ID
        task_id = f"image_{current_user.id}_{request.prompt[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting image generation")
        
        # Calculate the cost of the operation
        cost = await credit_service.calculate_cost("text_to_image", request.dict())
        
        # Deduct credits from the user's account
        await credit_service.deduct_credits(
            user_id=current_user.id,
            amount=cost,
            reason=f"Image generation: {request.prompt[:30]}"
        )
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the image
        response = await text_to_image_service.generate_image(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Image generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}"
        )


@router.post("/video/from-image", response_model=ImageToVideoResponse)
async def generate_video_from_image(
    request: ImageToVideoRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    image_to_video_service: ImageToVideoService = Depends(),
):
    """
    Generate a video from an image URL.
    """
    try:
        # Generate a task ID
        task_id = f"video_{current_user.id}_{request.prompt[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting video generation")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the video
        response = await image_to_video_service.generate_video_from_url(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Video generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video generation failed: {str(e)}"
        )


@router.post("/video/from-file", response_model=ImageToVideoResponse)
async def generate_video_from_file(
    prompt: str = Form(...),
    image_file: UploadFile = File(...),
    duration: Duration = Form(Duration.SECONDS_5),
    aspect_ratio: AspectRatio = Form(AspectRatio.LANDSCAPE_16_9),
    negative_prompt: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    image_to_video_service: ImageToVideoService = Depends(),
):
    """
    Generate a video from an uploaded image file.
    """
    try:
        # Generate a task ID
        task_id = f"video_{current_user.id}_{prompt[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting video generation")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the video
        response = await image_to_video_service.generate_video_from_file(
            prompt=prompt,
            image_file=image_file,
            duration=duration,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Video generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating video from file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video generation from file failed: {str(e)}"
        )


@router.post("/voice/clone", response_model=VoiceCloneResponse)
async def clone_voice(
    request: VoiceCloneRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    text_to_speech_service: TextToSpeechService = Depends(),
):
    """
    Clone a voice from an audio URL.
    """
    try:
        # Generate a task ID
        task_id = f"voice_{current_user.id}_clone"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting voice cloning")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Clone the voice
        response = await text_to_speech_service.clone_voice(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Voice cloning complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error cloning voice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice cloning failed: {str(e)}"
        )


@router.post("/voice/clone-from-file", response_model=VoiceCloneResponse)
async def clone_voice_from_file(
    audio_file: UploadFile = File(...),
    noise_reduction: bool = Form(True),
    volume_normalization: bool = Form(True),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    text_to_speech_service: TextToSpeechService = Depends(),
):
    """
    Clone a voice from an uploaded audio file.
    """
    try:
        # Generate a task ID
        task_id = f"voice_{current_user.id}_clone"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting voice cloning")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Clone the voice
        response = await text_to_speech_service.clone_voice_from_file(
            audio_file=audio_file,
            noise_reduction=noise_reduction,
            volume_normalization=volume_normalization,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Voice cloning complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error cloning voice from file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice cloning from file failed: {str(e)}"
        )


@router.post("/speech", response_model=TextToSpeechResponse)
async def generate_speech(
    request: TextToSpeechRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    text_to_speech_service: TextToSpeechService = Depends(),
):
    """
    Generate speech from text.
    """
    try:
        # Generate a task ID
        task_id = f"speech_{current_user.id}_{request.text[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting speech generation")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the speech
        response = await text_to_speech_service.generate_speech(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Speech generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech generation failed: {str(e)}"
        )


@router.post("/music", response_model=TextToMusicResponse)
async def generate_music(
    request: TextToMusicRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    text_to_music_service: TextToMusicService = Depends(),
):
    """
    Generate music from text.
    """
    try:
        # Generate a task ID
        task_id = f"music_{current_user.id}_{request.text[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting music generation")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the music
        response = await text_to_music_service.generate_music(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Music generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating music: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Music generation failed: {str(e)}"
        )


@router.post("/sound-effect", response_model=TextToMusicResponse)
async def generate_sound_effect(
    description: str,
    duration: float = 3.0,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    text_to_music_service: TextToMusicService = Depends(),
):
    """
    Generate a sound effect from a description.
    """
    try:
        # Generate a task ID
        task_id = f"sfx_{current_user.id}_{description[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting sound effect generation")
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the sound effect
        response = await text_to_music_service.generate_sound_effect(
            description=description,
            duration=duration,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Sound effect generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating sound effect: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sound effect generation failed: {str(e)}"
        )


@router.post("/music/meta", response_model=MusicGenerationResponse)
async def generate_music_with_meta(
    request: MusicGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    music_generation_service: MusicGenerationService = Depends(),
    credit_service: CreditService = Depends(),
):
    """
    Generate music from a text prompt using Meta's MusicGen model.
    
    This endpoint uses Meta's MusicGen model via Replicate to generate high-quality music
    based on a text prompt. It supports various parameters for fine-tuning the generation,
    including model version, duration, and audio quality settings.
    """
    try:
        # Generate a task ID
        task_id = f"meta_music_{current_user.id}_{request.prompt[:10]}"
        
        # Set initial progress
        track_progress(task_id, 0, "Starting music generation with Meta MusicGen")
        
        # Calculate the cost of the operation (higher cost for premium model)
        cost = 50  # Base cost
        if request.model_version == "stereo-large":
            cost += 50  # Additional cost for the large model
        cost += request.duration * 5  # Cost scales with duration
        
        # Deduct credits from the user's account
        await credit_service.deduct_credits(
            user_id=current_user.id,
            amount=cost,
            reason=f"Meta MusicGen: {request.prompt[:30]}"
        )
        
        # Define progress callback
        def progress_callback(progress: float, message: Optional[str] = None):
            track_progress(task_id, progress, message)
        
        # Generate the music
        response = await music_generation_service.generate_music(
            request=request,
            user_id=current_user.id,
            progress_callback=progress_callback
        )
        
        # Set final progress
        track_progress(task_id, 100, "Music generation complete")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating music with Meta MusicGen: {str(e)}")
        
        # Refund credits if an error occurred
        try:
            await credit_service.add_credits(
                user_id=current_user.id,
                amount=cost,
                reason=f"Refund for failed Meta MusicGen: {request.prompt[:30]}"
            )
        except Exception as refund_error:
            logger.error(f"Error refunding credits: {str(refund_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Music generation with Meta MusicGen failed: {str(e)}"
        )


# Store for generation tasks
generation_tasks: Dict[str, GenerationTaskInfo] = {}


@router.post("/start", response_model=GenerationStatusResponse)
async def start_generation(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    video_generator: VideoGenerator = Depends(),
    credit_service: CreditService = Depends(),
):
    """
    Start a video generation task.
    """
    try:
        # Generate a task ID
        task_id = f"full_video_{str(uuid.uuid4())[:8]}_{current_user.id}"
        
        # Create task info
        now = time.time()
        task_info = GenerationTaskInfo(
            task_id=task_id,
            video_id=request.video_id,
            user_id=current_user.id,
            prompt=request.prompt,
            status=GenerationStatus.PENDING,
            progress=0,
            message="Initializing video generation",
            created_at=now,
            updated_at=now,
            steps=[
                {
                    "id": "analyze",
                    "label": "Analyzing prompt",
                    "status": "pending",
                    "progress": 0
                },
                {
                    "id": "images",
                    "label": "Creating visuals",
                    "status": "pending",
                    "progress": 0
                },
                {
                    "id": "audio",
                    "label": "Generating audio",
                    "status": "pending",
                    "progress": 0
                },
                {
                    "id": "music",
                    "label": "Creating background music",
                    "status": "pending",
                    "progress": 0
                },
                {
                    "id": "assembly",
                    "label": "Assembling video",
                    "status": "pending",
                    "progress": 0
                }
            ]
        )
        
        # Store task info
        generation_tasks[task_id] = task_info
        
        # Calculate the cost of the operation
        cost = 100  # Base cost for a full video generation
        
        # Deduct credits from the user's account
        await credit_service.deduct_credits(
            user_id=current_user.id,
            amount=cost,
            reason=f"Full video generation: {request.prompt[:30]}"
        )
        
        # Start the generation in the background
        background_tasks.add_task(
            generate_video_in_background,
            task_id=task_id,
            request=request,
            user_id=current_user.id,
            video_generator=video_generator
        )
        
        # Return the initial status
        return GenerationStatusResponse(
            task_id=task_id,
            video_id=request.video_id,
            status=GenerationStatus.PENDING,
            progress=0,
            message="Video generation started",
            steps=task_info.steps
        )
        
    except Exception as e:
        logger.error(f"Error starting video generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start video generation: {str(e)}"
        )


async def generate_video_in_background(
    task_id: str,
    request: GenerationRequest,
    user_id: str,
    video_generator: VideoGenerator
):
    """
    Generate a video in the background.
    """
    task_info = generation_tasks[task_id]
    
    try:
        # Update task status
        task_info.status = GenerationStatus.PROCESSING
        task_info.updated_at = time.time()
        
        # Step 1: Analyze prompt
        task_info.current_step = GenerationStep.ANALYZING_PROMPT
        task_info.message = "Analyzing prompt"
        task_info.steps[0]["status"] = "processing"
        
        # Simulate progress updates
        for progress in range(0, 101, 10):
            task_info.step_progress = float(progress)
            task_info.steps[0]["progress"] = progress
            task_info.progress = 0 + (progress * 0.2)  # 0-20% of total progress
            await asyncio.sleep(0.5)  # Simulate work
        
        task_info.steps[0]["status"] = "completed"
        task_info.steps[0]["progress"] = 100
        
        # Step 2: Generate images
        task_info.current_step = GenerationStep.GENERATING_IMAGES
        task_info.message = "Generating images"
        task_info.steps[1]["status"] = "processing"
        
        # Simulate progress updates
        for progress in range(0, 101, 5):
            task_info.step_progress = float(progress)
            task_info.steps[1]["progress"] = progress
            task_info.progress = 20 + (progress * 0.2)  # 20-40% of total progress
            await asyncio.sleep(0.5)  # Simulate work
        
        task_info.steps[1]["status"] = "completed"
        task_info.steps[1]["progress"] = 100
        
        # Step 3: Generate audio
        task_info.current_step = GenerationStep.GENERATING_AUDIO
        task_info.message = "Generating audio"
        task_info.steps[2]["status"] = "processing"
        
        # Simulate progress updates
        for progress in range(0, 101, 10):
            task_info.step_progress = float(progress)
            task_info.steps[2]["progress"] = progress
            task_info.progress = 40 + (progress * 0.2)  # 40-60% of total progress
            await asyncio.sleep(0.5)  # Simulate work
        
        task_info.steps[2]["status"] = "completed"
        task_info.steps[2]["progress"] = 100
        
        # Step 4: Generate music
        task_info.current_step = GenerationStep.GENERATING_MUSIC
        task_info.message = "Generating background music"
        task_info.steps[3]["status"] = "processing"
        
        # Simulate progress updates
        for progress in range(0, 101, 10):
            task_info.step_progress = float(progress)
            task_info.steps[3]["progress"] = progress
            task_info.progress = 60 + (progress * 0.2)  # 60-80% of total progress
            await asyncio.sleep(0.5)  # Simulate work
        
        task_info.steps[3]["status"] = "completed"
        task_info.steps[3]["progress"] = 100
        
        # Step 5: Assemble video
        task_info.current_step = GenerationStep.ASSEMBLING_VIDEO
        task_info.message = "Assembling final video"
        task_info.steps[4]["status"] = "processing"
        
        # Simulate progress updates
        for progress in range(0, 101, 5):
            task_info.step_progress = float(progress)
            task_info.steps[4]["progress"] = progress
            task_info.progress = 80 + (progress * 0.2)  # 80-100% of total progress
            await asyncio.sleep(0.5)  # Simulate work
        
        task_info.steps[4]["status"] = "completed"
        task_info.steps[4]["progress"] = 100
        
        # Complete the task
        task_info.status = GenerationStatus.COMPLETED
        task_info.progress = 100
        task_info.message = "Video generation completed"
        task_info.current_step = None
        task_info.step_progress = None
        task_info.updated_at = time.time()
        task_info.result = {
            "video_url": f"https://example.com/videos/{task_info.video_id}.mp4",
            "thumbnail_url": f"https://example.com/thumbnails/{task_info.video_id}.jpg",
            "duration": 30.0
        }
        
    except Exception as e:
        logger.error(f"Error in background video generation: {str(e)}")
        
        # Update task status to failed
        task_info.status = GenerationStatus.FAILED
        task_info.message = f"Video generation failed: {str(e)}"
        task_info.error = str(e)
        task_info.updated_at = time.time()
        
        # Mark current step as failed
        if task_info.current_step:
            step_index = {
                GenerationStep.ANALYZING_PROMPT: 0,
                GenerationStep.GENERATING_IMAGES: 1,
                GenerationStep.GENERATING_AUDIO: 2,
                GenerationStep.GENERATING_MUSIC: 3,
                GenerationStep.ASSEMBLING_VIDEO: 4
            }.get(task_info.current_step, 0)
            
            task_info.steps[step_index]["status"] = "error"


@router.get("/status/{task_id}", response_model=GenerationStatusResponse)
async def get_generation_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a video generation task.
    """
    # Get the task info
    task_info = generation_tasks.get(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if the task belongs to the current user
    if task_info.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )
    
    # Return the status
    return GenerationStatusResponse(
        task_id=task_info.task_id,
        video_id=task_info.video_id,
        status=task_info.status,
        progress=task_info.progress,
        current_step=task_info.current_step,
        step_progress=task_info.step_progress,
        message=task_info.message,
        error=task_info.error,
        result=task_info.result,
        steps=task_info.steps
    )


@router.get("/progress/{task_id}")
async def get_generation_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the progress of a generation task.
    """
    # Check if the task ID belongs to the current user
    if not task_id.startswith(f"{current_user.id}_") and not task_id.endswith(f"_{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task"
        )
    
    # Get the progress
    progress = generation_progress.get(task_id)
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return progress
