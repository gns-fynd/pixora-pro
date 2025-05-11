"""
Video agent for the Pixora AI application.

This module provides the video agent for generating videos.
"""
import logging
import os
import tempfile
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

from fastapi import Depends

from app.models import (
    Scene, Project, ProjectStatus, AssetGeneration, AssetGenerationStatus,
    TransitionType
)
from app.services.openai import OpenAIService
from app.services.fal_ai import FalAiService
from app.services.replicate import ReplicateService
from app.services.storage import StorageService
from app.services.dependencies import get_storage_service_dependency
from app.services.redis_client import RedisClient
from app.ai.tools.asset_tools import (
    generate_scene_image, generate_voice_over, generate_music,
    generate_assets_for_scene, generate_music_for_scenes
)
from app.ai.tools.video_tools import (
    create_scene_video_with_motion, stitch_video, create_video_for_scene
)

# Set up logging
logger = logging.getLogger(__name__)

# Type for progress callback
ProgressCallback = Callable[[int, Optional[str]], None]


class VideoAgent:
    """
    Agent for generating videos.
    """

    def __init__(
        self,
        openai_service: OpenAIService = Depends(),
        fal_ai_service: FalAiService = Depends(),
        replicate_service: ReplicateService = Depends(),
        storage_service: StorageService = Depends(get_storage_service_dependency),
        redis_client: RedisClient = Depends(),
    ):
        """
        Initialize the video agent.

        Args:
            openai_service: The OpenAI service
            fal_ai_service: The FAL AI service
            replicate_service: The Replicate service
            storage_service: The storage service
            redis_client: The Redis client
        """
        self.openai_service = openai_service
        self.fal_ai_service = fal_ai_service
        self.replicate_service = replicate_service
        self.storage_service = storage_service
        self.redis_client = redis_client

    async def generate_assets(
        self,
        project: Project,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        Generate assets for a project.

        Args:
            project: The project
            progress_callback: Optional progress callback

        Returns:
            Dictionary with asset URLs and metadata
        """
        try:
            logger.info(f"Generating assets for project: {project.id}")
            
            # Update project status
            project.status = ProjectStatus.GENERATING_ASSETS
            
            # Get the script
            if not project.script_id:
                raise ValueError("Project has no script")
            
            script_data = await self.redis_client.get_json(f"task:{project.script_id}:script")
            if not script_data:
                raise ValueError(f"Script not found: {project.script_id}")
            
            # Get the scenes from the script
            scenes = []
            for clip_data in script_data.get("clips", []):
                scene_data = clip_data.get("scene", {})
                scene = Scene(
                    index=scene_data.get("index", 1),
                    title=scene_data.get("title", "Untitled Scene"),
                    script=scene_data.get("script", ""),
                    video_prompt=scene_data.get("video_prompt", ""),
                    transition=TransitionType(scene_data.get("transition", "fade"))
                )
                scenes.append(scene)
            
            # Sort scenes by index
            scenes.sort(key=lambda s: s.index)
            
            # Get the voice character
            voice_character = script_data.get("voice_character")
            
            # Get the style
            style = project.style or "cinematic"
            
            # Create asset generation record
            asset_generation = AssetGeneration(
                project_id=str(project.id),
                status=AssetGenerationStatus.IN_PROGRESS
            )
            
            # Generate assets for each scene
            scene_assets = {}
            total_scenes = len(scenes)
            
            for i, scene in enumerate(scenes):
                # Update progress
                progress = int((i / total_scenes) * 100)
                if progress_callback:
                    await progress_callback(progress, f"Generating assets for scene {i+1}/{total_scenes}")
                
                # Generate assets for the scene
                scene_asset = await generate_assets_for_scene(
                    scene=scene,
                    style=style,
                    voice_character=voice_character,
                    storage_service=self.storage_service,
                    openai_service=self.openai_service,
                    replicate_service=self.replicate_service
                )
                
                # Store the assets
                scene_assets[scene.index] = scene_asset
            
            # Generate music for scenes
            music_prompts = []
            for music_data in script_data.get("music", []):
                music_prompt = {
                    "prompt": music_data.get("prompt", ""),
                    "scene_indexes": music_data.get("scene_indexes", [])
                }
                music_prompts.append(music_prompt)
            
            # Update progress
            if progress_callback:
                await progress_callback(90, "Generating music")
            
            # Generate music
            scene_music = await generate_music_for_scenes(
                music_prompts=music_prompts,
                scene_count=len(scenes),
                storage_service=self.storage_service,
                replicate_service=self.replicate_service
            )
            
            # Update asset generation record
            asset_generation.status = AssetGenerationStatus.COMPLETED
            asset_generation.scene_assets = scene_assets
            asset_generation.scene_music = scene_music
            
            # Update progress
            if progress_callback:
                await progress_callback(100, "Asset generation complete")
            
            logger.info(f"Generated assets for project: {project.id}")
            
            return {
                "scene_assets": scene_assets,
                "scene_music": scene_music
            }
        except Exception as e:
            logger.error(f"Error generating assets: {str(e)}")
            
            # Update asset generation record
            if asset_generation:
                asset_generation.status = AssetGenerationStatus.FAILED
                asset_generation.error = str(e)
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Error generating assets: {str(e)}")
            
            raise

    async def create_video(
        self,
        project: Project,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Create a video for a project.

        Args:
            project: The project
            progress_callback: Optional progress callback

        Returns:
            URL to the generated video
        """
        try:
            logger.info(f"Creating video for project: {project.id}")
            
            # Update project status
            project.status = ProjectStatus.GENERATING_VIDEO
            
            # Get the script
            if not project.script_id:
                raise ValueError("Project has no script")
            
            script_data = await self.redis_client.get_json(f"task:{project.script_id}:script")
            if not script_data:
                raise ValueError(f"Script not found: {project.script_id}")
            
            # Get the scenes from the script
            scenes = []
            for clip_data in script_data.get("clips", []):
                scene_data = clip_data.get("scene", {})
                scene = Scene(
                    index=scene_data.get("index", 1),
                    title=scene_data.get("title", "Untitled Scene"),
                    script=scene_data.get("script", ""),
                    video_prompt=scene_data.get("video_prompt", ""),
                    transition=TransitionType(scene_data.get("transition", "fade"))
                )
                scenes.append(scene)
            
            # Sort scenes by index
            scenes.sort(key=lambda s: s.index)
            
            # Get the assets
            asset_generation = project.asset_generation
            if not asset_generation:
                raise ValueError("Project has no asset generation")
            
            scene_assets = asset_generation.scene_assets
            scene_music = asset_generation.scene_music
            
            # Create a temporary directory for the videos
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create videos for each scene
                scene_videos = {}
                total_scenes = len(scenes)
                
                for i, scene in enumerate(scenes):
                    # Update progress
                    progress = int((i / total_scenes) * 80)
                    if progress_callback:
                        await progress_callback(progress, f"Creating video for scene {i+1}/{total_scenes}")
                    
                    # Get the assets for the scene
                    scene_asset = scene_assets.get(str(scene.index))
                    if not scene_asset:
                        raise ValueError(f"No assets found for scene {scene.index}")
                    
                    # Create a temporary file for the scene video
                    scene_video_path = os.path.join(temp_dir, f"scene_{scene.index}.mp4")
                    
                    # Create the video for the scene
                    await create_video_for_scene(
                        scene=scene,
                        scene_image_url=scene_asset.get("scene_image_url"),
                        voice_over_url=scene_asset.get("voice_over_url"),
                        output_path=scene_video_path,
                        motion_type="pan",
                        fal_ai_service=self.fal_ai_service,
                        storage_service=self.storage_service
                    )
                    
                    # Store the video path
                    scene_videos[scene.index] = scene_video_path
                
                # Update progress
                if progress_callback:
                    await progress_callback(80, "Stitching videos")
                
                # Get the video paths in order
                video_paths = [scene_videos[scene.index] for scene in scenes]
                
                # Get the transition types in order
                transition_types = [scene.transition for scene in scenes[:-1]]
                
                # Create a temporary file for the final video
                final_video_path = os.path.join(temp_dir, "final_video.mp4")
                
                # Get the background music for the first scene
                background_music_path = None
                if scene_music and str(scenes[0].index) in scene_music:
                    background_music_url = scene_music[str(scenes[0].index)]
                    background_music_data = await self.storage_service.get_file(background_music_url)
                    if background_music_data:
                        background_music_path = os.path.join(temp_dir, "background_music.mp3")
                        with open(background_music_path, "wb") as f:
                            f.write(background_music_data)
                
                # Stitch the videos together
                await stitch_video(
                    video_paths=video_paths,
                    transition_types=transition_types,
                    output_path=final_video_path,
                    background_music_path=background_music_path
                )
                
                # Update progress
                if progress_callback:
                    await progress_callback(90, "Uploading video")
                
                # Read the final video
                with open(final_video_path, "rb") as f:
                    final_video_data = f.read()
                
                # Upload the video
                file_info = await self.storage_service.save_file(
                    file_content=final_video_data,
                    file_type="video",
                    file_id=f"project_{project.id}",
                    file_extension=".mp4"
                )
                
                # Get the video URL
                video_url = file_info["file_url"]
                
                # Update project status
                project.status = ProjectStatus.COMPLETED
                project.video_url = video_url
                
                # Update progress
                if progress_callback:
                    await progress_callback(100, "Video generation complete")
                
                logger.info(f"Created video for project: {project.id}")
                
                return video_url
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            
            # Update project status
            project.status = ProjectStatus.FAILED
            project.error = str(e)
            
            # Update progress
            if progress_callback:
                await progress_callback(100, f"Error creating video: {str(e)}")
            
            raise


async def process_video_request(
    task: Any,
    progress_callback: Optional[ProgressCallback] = None,
    openai_service: OpenAIService = None,
    fal_ai_service: FalAiService = None,
    replicate_service: ReplicateService = None,
    storage_service: StorageService = None,
) -> str:
    """
    Process a video request.

    Args:
        task: The task
        progress_callback: Optional progress callback
        openai_service: The OpenAI service
        fal_ai_service: The FAL AI service
        replicate_service: The Replicate service
        storage_service: The storage service

    Returns:
        URL to the generated video
    """
    try:
        logger.info(f"Processing video request for task: {task.id}")
        
        # Create a video agent
        video_agent = get_video_agent(
            openai_service=openai_service,
            fal_ai_service=fal_ai_service,
            replicate_service=replicate_service,
            storage_service=storage_service
        )
        
        # Create a project
        project = Project(
            title=f"Video: {task.prompt[:30]}...",
            description=task.prompt,
            user_id=task.user_id,
            style=task.style,
            script_id=task.id
        )
        
        # Generate assets
        async def asset_progress_callback(progress: int, message: Optional[str] = None):
            # Scale progress to 0-50%
            scaled_progress = progress // 2
            if progress_callback:
                await progress_callback(scaled_progress, message)
        
        await video_agent.generate_assets(
            project=project,
            progress_callback=asset_progress_callback
        )
        
        # Create video
        async def video_progress_callback(progress: int, message: Optional[str] = None):
            # Scale progress to 50-100%
            scaled_progress = 50 + (progress // 2)
            if progress_callback:
                await progress_callback(scaled_progress, message)
        
        video_url = await video_agent.create_video(
            project=project,
            progress_callback=video_progress_callback
        )
        
        logger.info(f"Processed video request for task: {task.id}")
        
        return video_url
    except Exception as e:
        logger.error(f"Error processing video request: {str(e)}")
        raise


def get_video_agent(
    openai_service: OpenAIService = None,
    fal_ai_service: FalAiService = None,
    replicate_service: ReplicateService = None,
    storage_service: StorageService = None,
    redis_client: RedisClient = None,
) -> VideoAgent:
    """
    Get a video agent.

    Args:
        openai_service: The OpenAI service
        fal_ai_service: The FAL AI service
        replicate_service: The Replicate service
        storage_service: The storage service
        redis_client: The Redis client

    Returns:
        The video agent
    """
    return VideoAgent(
        openai_service=openai_service,
        fal_ai_service=fal_ai_service,
        replicate_service=replicate_service,
        storage_service=storage_service,
        redis_client=redis_client
    )
