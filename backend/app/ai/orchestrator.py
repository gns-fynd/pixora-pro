"""
AI agent orchestrator for video generation.

This module provides the main agent orchestrator for the Pixora AI platform,
integrating the POC agent implementation with a project-based approach.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
import os
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.credits import CreditService
from app.services.redis_client import RedisClient
from app.models import (
    Project, ProjectStatus, ScriptBreakdown, Scene, Clip, MusicPrompt,
    CharacterProfile, AssetGeneration, AssetGenerationStatus, PromptRequest
)
from app.services.openai import OpenAIService
from app.services.fal_ai import FalAiService
from app.services.replicate import ReplicateService
from app.services.storage import StorageService
from app.services.dependencies import get_storage_service_dependency

# Set up logging
logger = logging.getLogger(__name__)


class VideoOrchestrator:
    """
    AI agent orchestrator for video generation using a project-based approach.
    """

    def __init__(
        self,
        credit_service: CreditService = Depends(),
        redis_client: RedisClient = Depends(),
        settings: Settings = Depends(get_settings),
        openai_service: OpenAIService = Depends(),
        fal_ai_service: FalAiService = Depends(),
        replicate_service: ReplicateService = Depends(),
        storage_service: StorageService = Depends(get_storage_service_dependency),
    ):
        """
        Initialize the video orchestrator.

        Args:
            credit_service: The credit service
            redis_client: The Redis client for task progress tracking
            settings: Application settings
            openai_service: The OpenAI service
            fal_ai_service: The FAL AI service
            replicate_service: The Replicate service
            storage_service: The storage service
        """
        self.credit_service = credit_service
        self.redis_client = redis_client
        self.settings = settings
        self.openai_service = openai_service
        self.fal_ai_service = fal_ai_service
        self.replicate_service = replicate_service
        self.storage_service = storage_service

        # In-memory storage for projects and assets (will be replaced with database)
        self.projects_db = {}
        self.scripts_db = {}
        self.assets_db = {}

    async def create_project(
        self,
        title: str,
        description: Optional[str] = None,
        user_id: str = None,
    ) -> Project:
        """
        Create a new video generation project.

        Args:
            title: The title of the project
            description: Optional description of the project
            user_id: The ID of the user creating the project

        Returns:
            The created project
        """
        try:
            # Create a new project
            project = Project(
                title=title,
                description=description,
                user_id=user_id,
                status=ProjectStatus.DRAFT,
            )
            
            # Store the project in the database
            # For now, we'll use in-memory storage
            self.projects_db[str(project.id)] = project
            
            return project
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Project creation failed: {str(e)}"
            )

    async def get_project(
        self,
        project_id: str,
        user_id: str,
    ) -> Project:
        """
        Get a project by ID.

        Args:
            project_id: The ID of the project
            user_id: The ID of the user requesting the project

        Returns:
            The project
        """
        try:
            # Get the project from the database
            # For now, we'll use in-memory storage
            if project_id not in self.projects_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project {project_id} not found"
                )
            
            project = self.projects_db[project_id]
            
            # Check if the project belongs to the user
            if project.user_id and project.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this project"
                )
            
            return project
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error getting project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting project: {str(e)}"
            )

    async def list_projects(
        self,
        user_id: str,
    ) -> List[Project]:
        """
        List all projects for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List of projects
        """
        try:
            # Get all projects for the user from the database
            # For now, we'll use in-memory storage
            user_projects = [
                project for project in self.projects_db.values()
                if project.user_id == user_id
            ]
            
            return user_projects
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing projects: {str(e)}"
            )

    async def update_project(
        self,
        project_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
    ) -> Project:
        """
        Update a project.

        Args:
            project_id: The ID of the project
            user_id: The ID of the user updating the project
            title: Optional new title for the project
            description: Optional new description for the project
            status: Optional new status for the project

        Returns:
            The updated project
        """
        try:
            # Get the project
            project = await self.get_project(project_id, user_id)
            
            # Update the project
            if title is not None:
                project.title = title
            if description is not None:
                project.description = description
            if status is not None:
                project.status = status
            
            # Update the timestamp
            project.updated_at = datetime.now()
            
            # Store the updated project in the database
            # For now, we'll use in-memory storage
            self.projects_db[project_id] = project
            
            return project
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating project: {str(e)}"
            )

    async def delete_project(
        self,
        project_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a project.

        Args:
            project_id: The ID of the project
            user_id: The ID of the user deleting the project

        Returns:
            True if the project was deleted
        """
        try:
            # Get the project
            project = await self.get_project(project_id, user_id)
            
            # Delete the project from the database
            # For now, we'll use in-memory storage
            del self.projects_db[project_id]
            
            return True
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting project: {str(e)}"
            )

    async def generate_script(
        self,
        request: PromptRequest,
        task_id: str,
    ) -> ScriptBreakdown:
        """
        Generate a script from a prompt.

        Args:
            request: The prompt request
            task_id: The ID of the task

        Returns:
            The generated script
        """
        try:
            # Define a progress callback that updates Redis
            async def progress_callback(progress: int, message: Optional[str] = None):
                try:
                    # Update the progress in Redis
                    await self.redis_client.set_json(
                        f"task:{task_id}:progress",
                        {
                            "progress": progress,
                            "message": message or f"Processing: {progress}%",
                            "status": "processing" if progress < 100 else "completed",
                            "updated_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating progress in Redis: {e}")
            
            # Update progress
            await progress_callback(10, "Generating script...")
            
            # In a real implementation, this would use the ScriptBreakdownAgent
            # For now, we'll create a mock script
            
            # Create a mock script
            script = ScriptBreakdown(
                user_prompt=request.prompt,
                rewritten_prompt=f"Create an engaging and informative video about {request.prompt} that captures the essence of the topic and presents it in a visually appealing way.",
                voice_character=request.voice_character,
                character_consistency=request.character_consistency,
                music=[
                    MusicPrompt(
                        prompt="Upbeat electronic music with positive energy and a modern feel",
                        scene_indexes=[1, 2]
                    ),
                    MusicPrompt(
                        prompt="Calm ambient music with soft piano and gentle strings",
                        scene_indexes=[3]
                    )
                ],
                character_profiles=[
                    CharacterProfile(
                        name="Narrator",
                        image_prompt="Professional narrator in business casual attire, neutral expression, well-lit studio setting, high-quality professional appearance, 4K detail"
                    )
                ] if request.character_consistency else [],
                clips=[
                    Clip(
                        scene=Scene(
                            index=1,
                            title="Introduction",
                            script=f"Welcome to our video about {request.prompt}. Today we'll explore this fascinating topic and discover why it matters.",
                            video_prompt=f"Opening scene showing {request.prompt} with title text overlay, professional lighting, cinematic quality, 4K resolution",
                            transition="fade"
                        )
                    ),
                    Clip(
                        scene=Scene(
                            index=2,
                            title="Main Content",
                            script=f"Let's dive deeper into {request.prompt} and understand its key aspects and why it's important in today's world.",
                            video_prompt=f"Detailed visuals of {request.prompt} from multiple angles, informative graphics and data visualizations, professional composition, 4K quality",
                            transition="slide_left"
                        )
                    ),
                    Clip(
                        scene=Scene(
                            index=3,
                            title="Conclusion",
                            script=f"Thank you for watching our video about {request.prompt}. We hope you found it informative and gained new insights into this important topic.",
                            video_prompt=f"Closing scene with summary text about {request.prompt}, professional ending with call to action, cinematic lighting, 4K resolution",
                            transition="fade_to_black"
                        )
                    )
                ],
                expected_duration=60.0,  # seconds
                task_id=task_id,
                user_id=request.user_id
            )
            
            # Store the script in the database
            # For now, we'll use in-memory storage
            self.scripts_db[task_id] = script
            
            # Update progress
            await progress_callback(100, "Script generation complete")
            
            # Store the result in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:result",
                    script.dict()
                )
                logger.debug(f"Stored script result in Redis for task {task_id}")
            except Exception as e:
                logger.error(f"Error storing script result in Redis: {str(e)}")
            
            return script
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            # Update the task status in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error: {str(e)}",
                        "status": "error",
                        "updated_at": datetime.now().isoformat()
                    }
                )
            except Exception as redis_error:
                logger.error(f"Error updating progress in Redis: {redis_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Script generation failed: {str(e)}"
            )

    async def refine_script(
        self,
        script_id: str,
        feedback: str,
        user_id: str,
    ) -> ScriptBreakdown:
        """
        Refine a script based on user feedback.

        Args:
            script_id: The ID of the script to refine
            feedback: The user's feedback
            user_id: The ID of the user

        Returns:
            The refined script
        """
        try:
            # Get the script from the database
            # For now, we'll use in-memory storage
            if script_id not in self.scripts_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Script {script_id} not found"
                )
            
            script = self.scripts_db[script_id]
            
            # Check if the script belongs to the user
            if script.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to refine this script"
                )
            
            # In a real implementation, this would use the ScriptBreakdownAgent
            # For now, we'll create a mock refined script
            
            # Create a new task ID for the refined script
            new_task_id = str(uuid.uuid4())
            
            # Create a mock refined script
            refined_script = ScriptBreakdown(
                user_prompt=f"{script.user_prompt} (with feedback: {feedback})",
                rewritten_prompt=f"{script.rewritten_prompt} (refined based on feedback)",
                voice_character=script.voice_character,
                character_consistency=script.character_consistency,
                music=script.music,
                character_profiles=script.character_profiles,
                clips=script.clips,
                expected_duration=script.expected_duration,
                task_id=new_task_id,
                user_id=user_id
            )
            
            # Store the refined script in the database
            # For now, we'll use in-memory storage
            self.scripts_db[new_task_id] = refined_script
            
            return refined_script
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error refining script: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error refining script: {str(e)}"
            )

    async def approve_script(
        self,
        script_id: str,
        project_id: str,
        user_id: str,
    ) -> Project:
        """
        Approve a script and associate it with a project.

        Args:
            script_id: The ID of the script
            project_id: The ID of the project
            user_id: The ID of the user

        Returns:
            The updated project
        """
        try:
            # Get the script
            if script_id not in self.scripts_db:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Script {script_id} not found"
                )
            
            script = self.scripts_db[script_id]
            
            # Get the project
            project = await self.get_project(project_id, user_id)
            
            # Update the project with the approved script
            project.script = script
            project.status = ProjectStatus.SCRIPT_APPROVED
            project.updated_at = datetime.now()
            
            # Store the updated project in the database
            # For now, we'll use in-memory storage
            self.projects_db[project_id] = project
            
            return project
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error approving script: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error approving script: {str(e)}"
            )

    async def generate_assets(
        self,
        project_id: str,
        user_id: str,
        task_id: str,
    ) -> List[AssetGeneration]:
        """
        Generate assets for a project.

        Args:
            project_id: The ID of the project
            user_id: The ID of the user
            task_id: The ID of the task

        Returns:
            List of asset generations
        """
        try:
            # Get the project
            project = await self.get_project(project_id, user_id)
            
            # Check if the project has a script
            if not project.script:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project has no script"
                )
            
            # Define a progress callback that updates Redis
            async def progress_callback(progress: int, message: Optional[str] = None):
                try:
                    # Update the progress in Redis
                    await self.redis_client.set_json(
                        f"task:{task_id}:progress",
                        {
                            "progress": progress,
                            "message": message or f"Processing: {progress}%",
                            "status": "processing" if progress < 100 else "completed",
                            "updated_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating progress in Redis: {e}")
            
            # Update progress
            await progress_callback(10, "Generating assets...")
            
            # Update project status
            project.status = ProjectStatus.GENERATING_ASSETS
            self.projects_db[project_id] = project
            
            # In a real implementation, this would use the asset generation tools
            # For now, we'll create mock assets
            
            assets = []
            
            # Generate character assets if character consistency is enabled
            if project.script.character_consistency:
                await progress_callback(20, "Generating character images...")
                
                for character in project.script.character_profiles:
                    asset_id = str(uuid.uuid4())
                    asset = AssetGeneration(
                        id=asset_id,
                        project_id=project_id,
                        asset_type="character",
                        status=AssetGenerationStatus.COMPLETED,
                        result_url=f"https://example.com/character_{asset_id}.png",
                        metadata={
                            "name": character.name,
                            "image_prompt": character.image_prompt
                        }
                    )
                    assets.append(asset)
                    
                    # Store the asset in the database
                    # For now, we'll use in-memory storage
                    self.assets_db[asset_id] = asset
            
            # Generate scene assets
            await progress_callback(40, "Generating scene images...")
            
            for clip in project.script.clips:
                scene = clip.scene
                asset_id = str(uuid.uuid4())
                asset = AssetGeneration(
                    id=asset_id,
                    project_id=project_id,
                    scene_index=scene.index,
                    asset_type="scene",
                    status=AssetGenerationStatus.COMPLETED,
                    result_url=f"https://example.com/scene_{asset_id}.png",
                    metadata={
                        "title": scene.title,
                        "video_prompt": scene.video_prompt
                    }
                )
                assets.append(asset)
                
                # Store the asset in the database
                # For now, we'll use in-memory storage
                self.assets_db[asset_id] = asset
            
            # Generate audio assets
            await progress_callback(60, "Generating audio...")
            
            for clip in project.script.clips:
                scene = clip.scene
                asset_id = str(uuid.uuid4())
                asset = AssetGeneration(
                    id=asset_id,
                    project_id=project_id,
                    scene_index=scene.index,
                    asset_type="audio",
                    status=AssetGenerationStatus.COMPLETED,
                    result_url=f"https://example.com/audio_{asset_id}.mp3",
                    metadata={
                        "title": scene.title,
                        "script": scene.script,
                        "duration": 10.0  # Mock duration
                    }
                )
                assets.append(asset)
                
                # Store the asset in the database
                # For now, we'll use in-memory storage
                self.assets_db[asset_id] = asset
            
            # Generate music assets
            await progress_callback(80, "Generating music...")
            
            for music_prompt in project.script.music:
                asset_id = str(uuid.uuid4())
                asset = AssetGeneration(
                    id=asset_id,
                    project_id=project_id,
                    asset_type="music",
                    status=AssetGenerationStatus.COMPLETED,
                    result_url=f"https://example.com/music_{asset_id}.mp3",
                    metadata={
                        "prompt": music_prompt.prompt,
                        "scene_indexes": music_prompt.scene_indexes,
                        "duration": 30.0  # Mock duration
                    }
                )
                assets.append(asset)
                
                # Store the asset in the database
                # For now, we'll use in-memory storage
                self.assets_db[asset_id] = asset
            
            # Update progress
            await progress_callback(100, "Asset generation complete")
            
            # Store the result in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:result",
                    {
                        "assets": [asset.dict() for asset in assets]
                    }
                )
                logger.debug(f"Stored asset generation result in Redis for task {task_id}")
            except Exception as e:
                logger.error(f"Error storing asset generation result in Redis: {str(e)}")
            
            return assets
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error generating assets: {str(e)}")
            # Update the task status in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error: {str(e)}",
                        "status": "error",
                        "updated_at": datetime.now().isoformat()
                    }
                )
            except Exception as redis_error:
                logger.error(f"Error updating progress in Redis: {redis_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Asset generation failed: {str(e)}"
            )

    async def create_video(
        self,
        project_id: str,
        user_id: str,
        task_id: str,
    ) -> str:
        """
        Create a video for a project.

        Args:
            project_id: The ID of the project
            user_id: The ID of the user
            task_id: The ID of the task

        Returns:
            URL to the generated video
        """
        try:
            # Get the project
            project = await self.get_project(project_id, user_id)
            
            # Check if the project has a script
            if not project.script:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project has no script"
                )
            
            # Define a progress callback that updates Redis
            async def progress_callback(progress: int, message: Optional[str] = None):
                try:
                    # Update the progress in Redis
                    await self.redis_client.set_json(
                        f"task:{task_id}:progress",
                        {
                            "progress": progress,
                            "message": message or f"Processing: {progress}%",
                            "status": "processing" if progress < 100 else "completed",
                            "updated_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating progress in Redis: {e}")
            
            # Update progress
            await progress_callback(10, "Creating video...")
            
            # Update project status
            project.status = ProjectStatus.STITCHING_VIDEO
            self.projects_db[project_id] = project
            
            # Get all assets for the project
            # For now, we'll use in-memory storage
            project_assets = [
                asset for asset in self.assets_db.values()
                if asset.project_id == project_id
            ]
            
            # Check if we have all the required assets
            scene_assets = [asset for asset in project_assets if asset.asset_type == "scene"]
            audio_assets = [asset for asset in project_assets if asset.asset_type == "audio"]
            
            if len(scene_assets) < len(project.script.clips) or len(audio_assets) < len(project.script.clips):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required assets"
                )
            
            # In a real implementation, this would use the video generation tools
            # For now, we'll create a mock video
            
            # Create scene videos
            await progress_callback(40, "Creating scene videos...")
            
            scene_videos = []
            for clip in project.script.clips:
                scene = clip.scene
                
                # Find the scene image and audio for this scene
                scene_asset = next((asset for asset in scene_assets if asset.scene_index == scene.index), None)
                audio_asset = next((asset for asset in audio_assets if asset.scene_index == scene.index), None)
                
                if not scene_asset or not audio_asset:
                    continue
                
                # Create a video asset
                asset_id = str(uuid.uuid4())
                asset = AssetGeneration(
                    id=asset_id,
                    project_id=project_id,
                    scene_index=scene.index,
                    asset_type="video",
                    status=AssetGenerationStatus.COMPLETED,
                    result_url=f"https://example.com/video_{asset_id}.mp4",
                    metadata={
                        "title": scene.title,
                        "scene_image": scene_asset.result_url,
                        "audio_url": audio_asset.result_url,
                        "duration": audio_asset.metadata.get("duration", 10.0)
                    }
                )
                
                # Store the asset in the database
                # For now, we'll use in-memory storage
                self.assets_db[asset_id] = asset
                
                scene_videos.append(asset.result_url)
            
            # Stitch the videos together
            await progress_callback(80, "Stitching video...")
            
            # Get music assets
            music_assets = [asset for asset in project_assets if asset.asset_type == "music"]
            music_url = music_assets[0].result_url if music_assets else None
            
            # Create a final video URL
            video_id = str(uuid.uuid4())
            video_url = f"https://example.com/final_video_{video_id}.mp4"
            
            # Update the project with the video URL
            project.video_url = video_url
            project.status = ProjectStatus.COMPLETED
            project.updated_at = datetime.now()
            
            # Store the updated project in the database
            # For now, we'll use in-memory storage
            self.projects_db[project_id] = project
            
            # Update progress
            await progress_callback(100, "Video creation complete")
            
            # Store the result in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:result",
                    {
                        "video_url": video_url,
                        "project_id": project_id
                    }
                )
                logger.debug(f"Stored video creation result in Redis for task {task_id}")
            except Exception as e:
                logger.error(f"Error storing video creation result in Redis: {str(e)}")
            
            return video_url
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            # Update the task status in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error: {str(e)}",
                        "status": "error",
                        "updated_at": datetime.now().isoformat()
                    }
                )
            except Exception as redis_error:
                logger.error(f"Error updating progress in Redis: {redis_error}")
            
            # Update project status
            try:
                project = await self.get_project(project_id, user_id)
                project.status = ProjectStatus.FAILED
                project.updated_at = datetime.now()
                self.projects_db[project_id] = project
            except Exception as project_error:
                logger.error(f"Error updating project status: {project_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video creation failed: {str(e)}"
            )

    async def process_unified_request(
        self,
        request: Dict[str, Any],
        task_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Process a unified generation request.

        Args:
            request: The unified request
            task_id: The ID of the task
            user_id: The ID of the user

        Returns:
            The result
        """
        try:
            # Get the intent from the client_context if available
            intent = "generate_video"  # Default intent
            if "client_context" in request and "operation" in request["client_context"]:
                operation = request["client_context"]["operation"]
                # Map operations to intents
                operation_to_intent = {
                    "generate_script": "generate_script",
                    "generate_scene_breakdown": "generate_scene_breakdown",
                    "generate_video": "generate_video",
                    "regenerate_scene": "edit_scene",
                    "edit_scene": "edit_scene",
                    "edit_video": "edit_video"
                }
                if operation in operation_to_intent:
                    intent = operation_to_intent[operation]
            
            # Process based on intent
            if intent == "generate_script":
                # Create a prompt request
                prompt_request = PromptRequest(
                    prompt=request.get("prompt", ""),
                    user_id=user_id,
                    character_consistency=request.get("character_consistency", False),
                    voice_character=request.get("voice_character", None)
                )
                
                # Generate the script
                script = await self.generate_script(prompt_request, task_id)
                
                # Return the script
                return {
                    "response_type": "script",
                    "message": "Script generation complete",
                    "data": script.dict(),
                    "task_id": task_id
                }
                
            elif intent == "generate_scene_breakdown":
                # Create a prompt request
                prompt_request = PromptRequest(
                    prompt=request.get("prompt", ""),
                    user_id=user_id,
                    character_consistency=request.get("character_consistency", False),
                    voice_character=request.get("voice_character", None)
                )
                
                # Generate the script (which includes scene breakdown)
                script = await self.generate_script(prompt_request, task_id)
                
                # Extract scenes from the script
                scenes = [clip.scene.dict() for clip in script.clips]
                total_duration = script.expected_duration or 60.0
                
                # Return the scene breakdown
                return {
                    "response_type": "clips",
                    "message": "Scene breakdown complete",
                    "data": {
                        "scenes": scenes,
                        "total_duration": total_duration
                    },
                    "scenes": scenes,  # Add scenes at the top level as well
                    "total_duration": total_duration,  # Add total_duration at the top level as well
                    "task_id": task_id
                }
                
            elif intent == "generate_video":
                # Create a project
                project = await self.create_project(
                    title=f"Video: {request.get('prompt', '')[:30]}...",
                    description=request.get("prompt", ""),
                    user_id=user_id
                )
                
                # Create a prompt request
                prompt_request = PromptRequest(
                    prompt=request.get("prompt", ""),
                    user_id=user_id,
                    character_consistency=request.get("character_consistency", False),
                    voice_character=request.get("voice_character", None)
                )
                
                # Generate the script
                script = await self.generate_script(prompt_request, task_id)
                
                # Approve the script
                project = await self.approve_script(script.task_id, str(project.id), user_id)
                
                # Generate assets
                assets = await self.generate_assets(str(project.id), user_id, task_id)
                
                # Create the video
                video_url = await self.create_video(str(project.id), user_id, task_id)
                
                # Return the video
                return {
                    "response_type": "video",
                    "message": "Video generation complete",
                    "data": {
                        "video_url": video_url,
                        "project_id": str(project.id)
                    },
                    "task_id": task_id
                }
                
            else:
                # For now, return a not implemented response
                return {
                    "response_type": "error",
                    "message": f"This operation ({intent}) is not yet implemented in the new video agent.",
                    "data": {
                        "error": "Not implemented",
                        "intent": intent
                    },
                    "task_id": task_id
                }
                
        except Exception as e:
            logger.error(f"Error processing unified request: {str(e)}")
            # Update the task status in Redis
            try:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error: {str(e)}",
                        "status": "error",
                        "updated_at": datetime.now().isoformat()
                    }
                )
            except Exception as redis_error:
                logger.error(f"Error updating progress in Redis: {redis_error}")
            
            # Return an error response
            return {
                "response_type": "error",
                "message": f"Error processing request: {str(e)}",
                "data": {
                    "error": str(e)
                },
                "task_id": task_id
            }
