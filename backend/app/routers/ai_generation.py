"""
Unified AI generation router.

This module provides a unified endpoint for all AI generation tasks.
"""
import logging
import uuid
import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse

from app.ai.orchestrator import VideoOrchestrator
from app.models import PromptRequest
from app.schemas.ai_generation import (
    UnifiedGenerationRequest,
    UnifiedGenerationResponse,
    ResponseType,
    UIAction,
    UIActionType,
    TaskStatus
)
from app.services.credits import CreditService
from app.services.redis_client import RedisClient
from app.auth.jwt import get_current_user
from app.schemas.user import UserResponse as User
from app.core.config import get_settings, Settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ai",
    tags=["ai-generation"],
    responses={404: {"description": "Not found"}},
)


from app.utils.logging_config import get_logger
from app.utils.logging_utils import (
    log_api_request, 
    log_external_api_call, 
    log_task_progress,
    log_exception_with_context,
    sanitize_log_data,
    get_context_logger
)

# Get module logger
logger = get_logger(__name__)

@router.post(
    "/generate",
    response_model=UnifiedGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified AI generation endpoint",
    description="Process natural language prompts for AI generation of various content types"
)
@log_api_request
async def generate(
    request_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: VideoOrchestrator = Depends(),
    credit_service: CreditService = Depends(),
    redis_client: RedisClient = Depends(),
    settings: Settings = Depends(get_settings),
):
    # Handle both direct and nested request formats
    if "request" in request_data:
        # Extract the nested request
        nested_request = request_data["request"]
        request = UnifiedGenerationRequest(**nested_request)
    else:
        # Use the request as is
        request = UnifiedGenerationRequest(**request_data)
    """
    Unified endpoint for AI generation based on natural language prompts.

    This endpoint acts as a smart router that:
    1. Analyzes the user's intent from their prompt
    2. Routes the request to the appropriate generator
    3. Returns results in a standardized format

    Examples:
    - "Generate a script about space exploration"
    - "Create a video showing the ocean at sunset"
    - "Generate an image of a futuristic city"
    - "Edit scene 3 to show more dramatic lighting"
    """
    try:
        # Create a task ID for tracking
        task_id = f"unified_generate_{str(uuid.uuid4())[:8]}_{int(time.time())}"

        # Step 1: Analyze the user's prompt to determine the intent
        intent_analysis = await analyze_intent(
            prompt=request.prompt,
            video_id=request.video_id,
            scene_id=request.scene_id,
            reference_files=request.reference_files,
            preferences=request.preferences,
            client_context=request.client_context
        )

        # Extract key information from the intent analysis
        intent = intent_analysis.get("intent", "unknown")
        confidence = intent_analysis.get("confidence", 0.0)
        operation = intent_analysis.get("operation", {})

        # If confidence is low, return analysis to help the user refine their prompt
        if confidence < 0.7:
            return UnifiedGenerationResponse(
                response_type=ResponseType.ANALYSIS,
                message="I'm not entirely sure what you're asking for. Here's what I understood:",
                data={
                    "analysis": intent_analysis.get("analysis", {}),
                    "possible_intents": [
                        {"intent": intent, "confidence": confidence},
                        {"intent": "generate_script", "confidence": 0.0},
                        {"intent": "generate_video", "confidence": 0.0},
                    ],
                    "suggestions": [
                        "Try being more specific about what you want to create",
                        "Mention the type of content: script, video, scene, image, etc.",
                        "Provide more details about the style or context"
                    ]
                },
                ui_action=UIAction(
                    type=UIActionType.OVERLAY,
                    target="prompt_help",
                    params={"show_suggestions": True}
                )
            )

        # Step 2: Check if the user has enough credits
        estimated_credits = operation.get("estimated_credits", 10)

        user_credits = await credit_service.get_credits(user_id=current_user.id)
        if user_credits < estimated_credits:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Not enough credits. Required: {estimated_credits}, Available: {user_credits}"
            )

        # Step 3: For video generation and related operations, process asynchronously
        if intent in ["generate_video", "edit_video", "generate_script", "generate_scene_breakdown"]:
            # Initialize the task in Redis
            task_info = {
                "task_id": task_id,
                "user_id": str(current_user.id),
                "intent": intent,
                "prompt": request.prompt,
                "status": "processing",
                "progress": 0.0,
                "message": "Task started",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "estimated_credits": estimated_credits
            }

            await redis_client.set_json(f"task:{task_id}", task_info)
            await redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 0.0,
                    "message": "Task started",
                    "status": "processing",
                    "updated_at": datetime.now().isoformat()
                }
            )

            # Add the background task
            background_tasks.add_task(
                process_video_generation_task,
                orchestrator=orchestrator,
                credit_service=credit_service,
                redis_client=redis_client,
                task_id=task_id,
                user_id=str(current_user.id),
                request=request,
                estimated_credits=estimated_credits
            )

            # Customize response based on intent
            response_type = _map_intent_to_response_type(intent)
            message = ""
            if intent == "generate_video":
                message = "Started video generation task"
            elif intent == "edit_video":
                message = "Started video editing task"
            elif intent == "generate_script":
                message = "Generating script from your prompt"
                response_type = ResponseType.SCRIPT
            elif intent == "generate_scene_breakdown":
                message = "Breaking down your script into scenes"
                response_type = ResponseType.CLIPS

            # Return that the task has been started
            response_data = {
                "task_id": task_id,
                "estimated_time": operation.get("estimated_time", "3-5 minutes"),
                "intent": intent
            }
            
            # For scene breakdown, include an empty scenes array to prevent frontend errors
            if intent == "generate_scene_breakdown":
                response_data["scenes"] = []
            
            return UnifiedGenerationResponse(
                response_type=response_type,
                message=message,
                data=response_data,
                task_id=task_id,
                ui_action=UIAction(
                    type=UIActionType.UPDATE,
                    target="progress_tracker",
                    params={"show_progress": True, "task_id": task_id}
                )
            )
        
        # Step 4: For other operations, use the legacy agent
        else:
            # For now, return a not implemented response
            return UnifiedGenerationResponse(
                response_type=_map_intent_to_response_type(intent),
                message=f"This operation ({intent}) is not yet implemented in the new video agent.",
                data={
                    "error": "Not implemented",
                    "intent": intent
                }
            )

    except HTTPException:
        # Re-raise HTTP exceptions for FastAPI to handle
        raise

    except Exception as e:
        logger.error(f"Error in unified generate endpoint: {str(e)}", exc_info=True)
        # Return a 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )


@router.get(
    "/generate/status/{task_id}",
    response_model=TaskStatus,
    status_code=status.HTTP_200_OK,
    summary="Get task status",
    description="Get the status of a generation task"
)
@log_api_request
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: VideoOrchestrator = Depends(),
    redis_client: RedisClient = Depends(),
):
    """
    Get the status of a generation task.
    """
    try:
        # Get the task info
        task_info = await redis_client.get_json(f"task:{task_id}")

        if not task_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # Check if the task belongs to the current user
        if task_info.get("user_id") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this task"
            )

        # Get the task progress
        progress_info = await redis_client.get_json(f"task:{task_id}:progress") or {}

        # Get the task result if it exists
        result = await redis_client.get_json(f"task:{task_id}:result")

        # Parse the updated_at timestamp
        updated_at_str = progress_info.get("updated_at", task_info.get("created_at"))
        try:
            updated_at = datetime.fromisoformat(updated_at_str)
        except (ValueError, TypeError):
            updated_at = datetime.now()

        # Build the response
        return TaskStatus(
            progress=progress_info.get("progress", 0.0),
            message=progress_info.get("message", "Unknown status"),
            status=progress_info.get("status", "processing"),
            task_id=task_id,
            user_id=task_info.get("user_id"),
            updated_at=updated_at,
            result=result
        )

    except HTTPException:
        # Re-raise HTTP exceptions for FastAPI to handle
        raise

    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}", exc_info=True)
        # Return a 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task status: {str(e)}"
        )


@router.post(
    "/generate/cancel/{task_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Cancel a task",
    description="Cancel a running generation task"
)
@log_api_request
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: VideoOrchestrator = Depends(),
    redis_client: RedisClient = Depends(),
):
    """
    Cancel a running generation task.
    """
    try:
        # Get the task info
        task_info = await redis_client.get_json(f"task:{task_id}")

        if not task_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # Check if the task belongs to the current user
        if task_info.get("user_id") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this task"
            )

        # Cancel the task
        cancelled = await orchestrator.cancel_task(task_id, str(current_user.id))

        # Update the task status in Redis
        await redis_client.set_json(
            f"task:{task_id}:progress",
            {
                "progress": 100.0,
                "message": "Task cancelled",
                "status": "cancelled",
                "updated_at": datetime.now().isoformat()
            }
        )

        return {
            "success": cancelled,
            "message": "Task cancelled successfully" if cancelled else "Failed to cancel task"
        }

    except HTTPException:
        # Re-raise HTTP exceptions for FastAPI to handle
        raise

    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}", exc_info=True)
        # Return a 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling task: {str(e)}"
        )


# Helper functions

def _map_intent_to_response_type(intent: str) -> ResponseType:
    """Map intent to response type."""
    intent_to_type = {
        "generate_script": ResponseType.SCRIPT,
        "generate_video": ResponseType.VIDEO,
        "edit_video": ResponseType.VIDEO,
        "generate_scene": ResponseType.CLIPS,
        "edit_scene": ResponseType.CLIPS,
        "generate_audio": ResponseType.AUDIO,
        "edit_audio": ResponseType.AUDIO,
        "generate_image": ResponseType.IMAGE,
        "edit_image": ResponseType.IMAGE,
        "analyze_content": ResponseType.ANALYSIS,
    }

    return intent_to_type.get(intent, ResponseType.ANALYSIS)


def _create_ui_action_for_intent(
    intent: str,
    result: Dict[str, Any],
    client_context: Optional[Dict[str, Any]] = None
) -> Optional[UIAction]:
    """Create UI action based on intent, result, and client context."""
    # If result already specifies a UI action, use that
    if "ui_action" in result:
        return UIAction(**result["ui_action"])

    # Default UI action is to update the main content
    ui_action = UIAction(
        type=UIActionType.UPDATE,
        target="main_content"
    )

    # Consider client context
    current_page = "home"
    if client_context:
        current_page = client_context.get("current_page", "home")

    # Customize based on intent and current page
    if intent == "generate_script":
        if current_page == "editor":
            ui_action = UIAction(
                type=UIActionType.OVERLAY,
                target="script_panel",
                preserve_state=True
            )
        else:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="script_editor",
                preserve_state=False
            )
    elif intent in ["generate_video", "edit_video"]:
        video_id = result.get("data", {}).get("video_id")
        if current_page == "editor" and video_id:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="video_player",
                params={"video_id": video_id}
            )
        else:
            ui_action = UIAction(
                type=UIActionType.REPLACE,
                target="main_content",
                params={"page": "video_player"}
            )
    elif intent in ["generate_scene", "edit_scene"]:
        scene_id = result.get("data", {}).get("scene", {}).get("id")
        if current_page == "editor" and scene_id:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="scene_editor",
                params={"scene_id": scene_id}
            )
        else:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="clips_viewer",
                params={"scene_id": scene_id}
            )
    elif intent in ["generate_audio", "edit_audio"]:
        audio_url = result.get("data", {}).get("audio_url")
        if current_page == "editor":
            ui_action = UIAction(
                type=UIActionType.MODAL,
                target="audio_player",
                params={"audio_url": audio_url}
            )
        else:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="audio_player",
                params={"audio_url": audio_url}
            )
    elif intent in ["generate_image", "edit_image"]:
        images = result.get("data", {}).get("images", [])
        if current_page == "editor":
            ui_action = UIAction(
                type=UIActionType.MODAL,
                target="image_viewer",
                params={"images": images}
            )
        else:
            ui_action = UIAction(
                type=UIActionType.UPDATE,
                target="image_viewer",
                params={"images": images}
            )

    return ui_action


# Intent analysis function
async def analyze_intent(
    prompt: str,
    video_id: Optional[uuid.UUID] = None,
    scene_id: Optional[uuid.UUID] = None,
    reference_files: Optional[List[str]] = None,
    preferences: Optional[Dict[str, Any]] = None,
    client_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze the user's prompt to determine the intent.
    
    Uses the client_context to determine the operation if provided.
    """
    # Default intent is video generation
    intent = "generate_video"
    confidence = 1.0
    estimated_credits = 50
    estimated_time = "3-5 minutes"
    
    # Check if client_context contains an operation
    if client_context and "operation" in client_context:
        operation = client_context["operation"]
        
        # Map operations to intents
        operation_to_intent = {
            "generate_script": "generate_script",
            "generate_scene_breakdown": "generate_scene_breakdown",
            "generate_scene_breakdown_with_script": "generate_scene_breakdown_with_script",
            "generate_video": "generate_video",
            "regenerate_scene": "edit_scene",
            "edit_scene": "edit_scene",
            "edit_video": "edit_video"
        }
        
        # Map operations to credit costs
        operation_to_credits = {
            "generate_script": 5,
            "generate_scene_breakdown": 10,
            "generate_scene_breakdown_with_script": 15,  # Combined operation costs more
            "generate_video": 50,
            "regenerate_scene": 15,
            "edit_scene": 15,
            "edit_video": 30
        }
        
        # Map operations to estimated times
        operation_to_time = {
            "generate_script": "10-20 seconds",
            "generate_scene_breakdown": "20-30 seconds",
            "generate_scene_breakdown_with_script": "30-40 seconds",  # Combined operation takes longer
            "generate_video": "3-5 minutes",
            "regenerate_scene": "30-60 seconds",
            "edit_scene": "30-60 seconds",
            "edit_video": "1-3 minutes"
        }
        
        # Set intent based on operation
        if operation in operation_to_intent:
            intent = operation_to_intent[operation]
            estimated_credits = operation_to_credits.get(operation, 50)
            estimated_time = operation_to_time.get(operation, "3-5 minutes")
    
    return {
        "intent": intent,
        "confidence": confidence,
        "operation": {
            "processing_type": "async",
            "estimated_time": estimated_time,
            "estimated_credits": estimated_credits
        },
        "analysis": {
            "prompt": prompt,
            "video_id": str(video_id) if video_id else None,
            "scene_id": str(scene_id) if scene_id else None,
            "has_reference_files": reference_files is not None and len(reference_files) > 0,
            "preferences": preferences or {}
        }
    }


# Background task handler for video generation
async def process_video_generation_task(
    orchestrator: VideoOrchestrator,
    credit_service: CreditService,
    redis_client: RedisClient,
    task_id: str,
    user_id: str,
    request: UnifiedGenerationRequest,
    estimated_credits: int,
) -> None:
    """Process a video generation task in the background."""
    # Create a task-specific logger with context
    
    task_logger = get_context_logger(
        __name__,
        task_id=task_id,
        user_id=user_id,
        prompt=request.prompt[:50] + "..." if len(request.prompt) > 50 else request.prompt
    )
    
    task_logger.info(f"Starting video generation task: {task_id}")
    
    # Log initial progress
    log_task_progress(
        task_id=task_id,
        progress=0.0,
        message="Task started",
        stage="initialization"
    )
    
    try:
        # Reserve the credits (temporarily deduct)
        task_logger.info(f"Reserving {estimated_credits} credits for user {user_id}")
        await credit_service.deduct_credits(
            user_id=user_id,
            amount=estimated_credits,
            reason=f"Reserved for video generation: {request.prompt[:30]}"
        )
        
        # Log progress after credit reservation
        log_task_progress(
            task_id=task_id,
            progress=5.0,
            message="Credits reserved, starting processing",
            stage="credit_reservation"
        )
        
        # Update Redis with progress
        await redis_client.set_json(
            f"task:{task_id}:progress",
            {
                "progress": 5.0,
                "message": "Credits reserved, starting processing",
                "status": "processing",
                "updated_at": datetime.now().isoformat()
            }
        )

        # Process the request
        task_logger.info(f"Processing unified request with orchestrator")
        
        # Sanitize request data for logging
        safe_request_data = sanitize_log_data(request.dict())
        task_logger.debug(f"Request data: {safe_request_data}")
        
        # Get the intent from Redis
        task_info = await redis_client.get_json(f"task:{task_id}") or {}
        intent = task_info.get("intent", "generate_video")
        
        # Process the request based on intent
        task_logger.debug(f"Processing unified request with intent: {intent}")
        
        if intent == "generate_script":
            # Create a prompt request
            prompt_request = PromptRequest(
                prompt=request.prompt,
                user_id=user_id,
                character_consistency=request.preferences.get("character_consistency", False) if request.preferences else False,
                voice_character=request.preferences.get("voice_character", None) if request.preferences else None
            )
            
            # Generate the script
            script = await orchestrator.generate_script(prompt_request, task_id)
            
            # Create the result
            result = {
                "response_type": "script",
                "message": "Script generation complete",
                "data": script.dict(),
                "task_id": task_id
            }
            
        elif intent == "generate_scene_breakdown" or intent == "generate_scene_breakdown_with_script":
            # Create a prompt request
            prompt_request = PromptRequest(
                prompt=request.prompt,
                user_id=user_id,
                character_consistency=request.preferences.get("character_consistency", False) if request.preferences else False,
                voice_character=request.preferences.get("voice_character", None) if request.preferences else None
            )
            
            # Generate the script (which includes scene breakdown)
            script = await orchestrator.generate_script(prompt_request, task_id)
            
            # Extract scenes from the script
            scenes = [clip.scene.dict() for clip in script.clips]
            total_duration = script.expected_duration or 60.0
            
            # Create the result
            if intent == "generate_scene_breakdown_with_script":
                # For combined operation, include both script and scenes
                result = {
                    "response_type": "clips",
                    "message": "Script and scene breakdown complete",
                    "data": {
                        "scenes": scenes,
                        "total_duration": total_duration,
                        "script": script.dict()  # Include the script data
                    },
                    "scenes": scenes,
                    "total_duration": total_duration,
                    "script": script.dict(),  # Include script at top level too
                    "task_id": task_id
                }
            else:
                # For regular scene breakdown, just include scenes
                result = {
                    "response_type": "clips",
                    "message": "Scene breakdown complete",
                    "data": {
                        "scenes": scenes,
                        "total_duration": total_duration
                    },
                    "scenes": scenes,
                    "total_duration": total_duration,
                    "task_id": task_id
                }
            
        elif intent == "generate_video":
            # Create a project
            project = await orchestrator.create_project(
                title=f"Video: {request.prompt[:30]}...",
                description=request.prompt,
                user_id=user_id
            )
            
            # Create a prompt request
            prompt_request = PromptRequest(
                prompt=request.prompt,
                user_id=user_id,
                character_consistency=request.preferences.get("character_consistency", False) if request.preferences else False,
                voice_character=request.preferences.get("voice_character", None) if request.preferences else None
            )
            
            # Generate the script
            script = await orchestrator.generate_script(prompt_request, task_id)
            
            # Approve the script
            project = await orchestrator.approve_script(script.task_id, str(project.id), user_id)
            
            # Generate assets
            assets = await orchestrator.generate_assets(str(project.id), user_id, task_id)
            
            # Create the video
            video_url = await orchestrator.create_video(str(project.id), user_id, task_id)
            
            # Create the result
            result = {
                "response_type": "video",
                "message": "Video generation complete",
                "data": {
                    "video_url": video_url,
                    "project_id": str(project.id)
                },
                "task_id": task_id
            }
            
        else:
            # For other intents, use the unified request processor
            result = await orchestrator.process_unified_request(
                request=request.dict(),
                task_id=task_id,
                user_id=user_id,
            )
        
        # Log the raw result for debugging
        try:
            task_logger.debug(f"Raw result from orchestrator: {json.dumps(result, default=str)}")
        except Exception as e:
            task_logger.debug(f"Could not serialize raw result: {str(e)}")
            task_logger.debug(f"Raw result type: {type(result)}, keys: {result.keys() if hasattr(result, 'keys') else 'no keys'}")
        
        # Log completion
        task_logger.info(f"Task completed successfully")
        
        # Determine the appropriate response type based on intent
        response_type = None
        if intent == "generate_script":
            response_type = ResponseType.SCRIPT
            result["message"] = "Script generation complete"
        elif intent == "generate_scene_breakdown":
            response_type = ResponseType.CLIPS
            result["message"] = "Scene breakdown complete"
            
            # Log the scene breakdown data for debugging
            try:
                scenes_data = result.get("data", {}).get("scenes", [])
                task_logger.debug(f"Scene breakdown data before conversion: {json.dumps(scenes_data, default=str)}")
                task_logger.debug(f"Number of scenes: {len(scenes_data)}")
                if scenes_data and len(scenes_data) > 0:
                    task_logger.debug(f"First scene: {json.dumps(scenes_data[0], default=str)}")
            except Exception as e:
                task_logger.debug(f"Could not log scene breakdown data: {str(e)}")
        
        # If we have a specific response type, update the result
        if response_type:
            from app.ai.utils.model_converters import video_result_to_unified_response
            task_logger.debug(f"Converting result using video_result_to_unified_response with response_type: {response_type}")
            
            # Log the data being passed to the converter
            try:
                task_logger.debug(f"Data for conversion: {json.dumps(result.get('data', {}), default=str)}")
            except Exception as e:
                task_logger.debug(f"Could not serialize data for conversion: {str(e)}")
            
            converted_result = video_result_to_unified_response(
                result=result.get("data", {}),
                task_id=task_id,
                message=result.get("message", "Task completed"),
                response_type=response_type
            )
            
            # Log the converted result
            try:
                task_logger.debug(f"Converted result: {json.dumps(converted_result.dict(), default=str)}")
            except Exception as e:
                task_logger.debug(f"Could not serialize converted result: {str(e)}")
            
            result = converted_result.dict()
        
        # Log the final result before storing in Redis
        try:
            task_logger.debug(f"Final result to store in Redis: {json.dumps(result.get('data', {}), default=str)}")
        except Exception as e:
            task_logger.debug(f"Could not serialize final result: {str(e)}")
        
        # Store the result - ensure scenes are at the top level for the frontend
        result_data = result.get("data", {})
        
        # If this is a scene breakdown, ensure scenes are at the top level
        if intent == "generate_scene_breakdown":
            # Check if scenes are in the data
            scenes = result_data.get("scenes", [])
            
            # If scenes is not a list, try to extract it from nested structures
            if not isinstance(scenes, list):
                if isinstance(result_data, dict) and "scenes" in result_data:
                    scenes = result_data["scenes"]
                elif "scenes" in result:
                    scenes = result["scenes"]
            
            # Ensure scenes is a list
            if not isinstance(scenes, list):
                task_logger.warning(f"Scenes is not a list, creating empty list. Current type: {type(scenes)}")
                scenes = []
            
            # Create a default scene if scenes list is empty
            if len(scenes) == 0:
                task_logger.warning("No scenes found, creating a default scene")
                default_scene = {
                    "id": f"default_scene_{task_id[-8:]}",
                    "title": "Default Scene",
                    "description": "This is a default scene created because no scenes were found in the result",
                    "narration": "Default narration text",
                    "duration": result_data.get("total_duration", 30) or result.get("total_duration", 30)
                }
                scenes = [default_scene]
                task_logger.debug(f"Created default scene: {json.dumps(default_scene, default=str)}")
            
            # Store the result with scenes at the top level
            await redis_client.set_json(
                f"task:{task_id}:result", 
                {
                    "scenes": scenes,
                    "total_duration": result_data.get("total_duration") or result.get("total_duration", 30)
                }
            )
        else:
            # For other intents, store the result as is
            await redis_client.set_json(f"task:{task_id}:result", result_data)
        
        # Verify the stored result
        stored_result = await redis_client.get_json(f"task:{task_id}:result")
        try:
            task_logger.debug(f"Stored result in Redis: {json.dumps(stored_result, default=str)}")
            
            # Additional verification for scene breakdown
            if intent == "generate_scene_breakdown":
                if "scenes" in stored_result:
                    scenes = stored_result["scenes"]
                    task_logger.debug(f"Verified scenes in stored result: {len(scenes)} scenes found")
                    if scenes and len(scenes) > 0:
                        task_logger.debug(f"First scene in stored result: {json.dumps(scenes[0], default=str)}")
                else:
                    task_logger.warning("No scenes found in stored result")
        except Exception as e:
            task_logger.debug(f"Could not serialize stored result: {str(e)}")

        # Update the task status
        await redis_client.set_json(
            f"task:{task_id}:progress",
            {
                "progress": 100.0,
                "message": result.get("message", "Task completed"),
                "status": "completed",
                "updated_at": datetime.now().isoformat()
            }
        )
        
        # Log final progress
        log_task_progress(
            task_id=task_id,
            progress=100.0,
            message=result.get("message", "Task completed"),
            stage="completion"
        )

    except Exception as e:
        # Log the exception with context
        log_exception_with_context(
            e,
            {
                "task_id": task_id,
                "user_id": user_id,
                "prompt": request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
                "estimated_credits": estimated_credits
            }
        )

        # Update the task status
        await redis_client.set_json(
            f"task:{task_id}:progress",
            {
                "progress": 100.0,
                "message": f"Error: {str(e)}",
                "status": "error",
                "updated_at": datetime.now().isoformat()
            }
        )

        # Store the error
        await redis_client.set_json(
            f"task:{task_id}:result",
            {"error": str(e)}
        )
        
        # Log error progress
        log_task_progress(
            task_id=task_id,
            progress=100.0,
            message=f"Error: {str(e)}",
            stage="error"
        )

        # Refund the credits
        try:
            task_logger.info(f"Refunding {estimated_credits} credits to user {user_id}")
            await credit_service.add_credits(
                user_id=user_id,
                amount=estimated_credits,
                reason=f"Refund for failed video generation: {request.prompt[:30]}"
            )
        except Exception as refund_error:
            log_exception_with_context(
                refund_error,
                {
                    "task_id": task_id,
                    "user_id": user_id,
                    "credits_to_refund": estimated_credits,
                    "operation": "credit_refund"
                }
            )
