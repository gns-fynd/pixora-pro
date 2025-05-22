"""
Video generation agent for Pixora AI Video Creation Platform
"""
import logging
import json
from typing import Dict, Any, Optional, List, Union

# Import base agent
from .base_agent import BaseAgent

# Import tools
from ..tools.fal_tools import (
    create_scene_video_with_motion
)
from ..tools.video_tools import (
    normalize_duration,
    apply_transition,
    stitch_video
)

# Import telemetry
from ..utils.telemetry import traced, log_event

# Configure logging
logger = logging.getLogger(__name__)

class VideoAgent(BaseAgent):
    """
    Agent for generating and stitching videos.
    """
    
    def __init__(self):
        """Initialize the video agent."""
        instructions = """You are a video generation agent for a video creation platform.
        
        Your task is to generate and stitch videos:
        1. Create scene videos with motion from scene images and audio
        2. Apply transitions between scenes
        3. Stitch scenes together with background music
        
        For scene videos, you should use motion generation to create engaging videos.
        For transitions, you should choose appropriate transitions based on the scene content.
        For stitching, you should ensure smooth transitions and proper audio mixing.
        """
        
        # Define the tools
        tools = [
            create_scene_video_with_motion,
            normalize_duration,
            apply_transition,
            stitch_video
        ]
        
        # Initialize the base agent
        super().__init__(name="VideoAgent", instructions=instructions, tools=tools)
        
        logger.info("Video agent initialized")
    
    @traced("create_scene_videos")
    async def create_scene_videos(
        self,
        task_id: str,
        scenes: List[Dict[str, Any]],
        scene_images: Dict[str, Dict[str, Any]],
        scene_audio: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Create scene videos with motion from scene images and audio.
        
        Args:
            task_id: ID of the task
            scenes: List of scenes with index, title, and video_prompt
            scene_images: Dictionary of scene indexes to image results
            scene_audio: Dictionary of scene indexes to audio results
            
        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: Dictionary of scene indexes to video results
        """
        try:
            results = {}
            
            for scene in scenes:
                scene_index = scene.get("index") or scene.get("scene", {}).get("index")
                if not scene_index:
                    logger.warning(f"No scene index found for scene: {scene}")
                    continue
                
                # Get the scene image
                scene_image_result = scene_images.get(str(scene_index))
                if not scene_image_result:
                    logger.warning(f"No scene image found for scene: {scene_index}")
                    continue
                
                # Get the scene audio
                scene_audio_result = scene_audio.get(str(scene_index))
                if not scene_audio_result:
                    logger.warning(f"No scene audio found for scene: {scene_index}")
                    continue
                
                # Get the scene image URL
                scene_image_url = scene_image_result.get("url")
                if not scene_image_url:
                    # Try to get the FAL URL
                    scene_image_url = scene_image_result.get("fal_url")
                    if not scene_image_url:
                        logger.warning(f"No scene image URL found for scene: {scene_index}")
                        continue
                
                # Get the scene audio URL
                scene_audio_url = scene_audio_result.get("url")
                if not scene_audio_url:
                    logger.warning(f"No scene audio URL found for scene: {scene_index}")
                    continue
                
                # Get the video prompt
                video_prompt = scene.get("video_prompt") or scene.get("scene", {}).get("video_prompt")
                if not video_prompt:
                    logger.warning(f"No video prompt found for scene: {scene_index}")
                    continue
                
                # Get the scene duration
                scene_duration = scene.get("duration") or scene.get("scene", {}).get("duration", 10)
                
                # Create the scene video with motion
                result = await create_scene_video_with_motion(
                    task_id=task_id,
                    scene_index=scene_index,
                    scene_image=scene_image_url,
                    audio_url=scene_audio_url,
                    prompt=video_prompt,
                    duration=scene_duration
                )
                
                # Store the result
                results[str(scene_index)] = result
                
                # Log the scene video generation
                log_event(
                    event_type="scene_video_generated",
                    message=f"Scene video generated for scene: {scene_index}",
                    data={
                        "task_id": task_id,
                        "scene_index": scene_index,
                        "url": result.get("url"),
                        "has_motion": result.get("has_motion", False),
                        "duration": result.get("duration")
                    }
                )
            
            return {"videos": results}
        except Exception as e:
            logger.error(f"Error creating scene videos: {str(e)}")
            raise
    
    @traced("apply_transitions")
    async def apply_transitions(
        self,
        task_id: str,
        scenes: List[Dict[str, Any]],
        scene_videos: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply transitions between scene videos.
        
        Args:
            task_id: ID of the task
            scenes: List of scenes with index, title, and transition
            scene_videos: Dictionary of scene indexes to video results
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of transition IDs to transition results
        """
        try:
            results = []
            
            # Sort scenes by index
            sorted_scenes = sorted(scenes, key=lambda s: s.get("index") or s.get("scene", {}).get("index", 0))
            
            # Apply transitions between consecutive scenes
            for i in range(len(sorted_scenes) - 1):
                scene1 = sorted_scenes[i]
                scene2 = sorted_scenes[i + 1]
                
                scene1_index = scene1.get("index") or scene1.get("scene", {}).get("index")
                scene2_index = scene2.get("index") or scene2.get("scene", {}).get("index")
                
                # Get the transition type
                transition_type = scene2.get("transition") or scene2.get("scene", {}).get("transition", "fade")
                
                # Get the scene videos
                scene1_video = scene_videos.get(str(scene1_index))
                scene2_video = scene_videos.get(str(scene2_index))
                
                if not scene1_video or not scene2_video:
                    logger.warning(f"Missing video for scene {scene1_index} or {scene2_index}")
                    continue
                
                # Get the video URLs
                scene1_url = scene1_video.get("url")
                scene2_url = scene2_video.get("url")
                
                if not scene1_url or not scene2_url:
                    logger.warning(f"Missing video URL for scene {scene1_index} or {scene2_index}")
                    continue
                
                # Apply the transition
                result = await apply_transition(
                    task_id=task_id,
                    video1_url=scene1_url,
                    video2_url=scene2_url,
                    transition_type=transition_type
                )
                
                # Store the result
                result["scene1_index"] = scene1_index
                result["scene2_index"] = scene2_index
                result["transition_type"] = transition_type
                results.append(result)
                
                # Log the transition application
                log_event(
                    event_type="transition_applied",
                    message=f"Transition applied between scenes {scene1_index} and {scene2_index}",
                    data={
                        "task_id": task_id,
                        "scene1_index": scene1_index,
                        "scene2_index": scene2_index,
                        "transition_type": transition_type,
                        "url": result.get("url")
                    }
                )
            
            return {"transitions": results}
        except Exception as e:
            logger.error(f"Error applying transitions: {str(e)}")
            raise
    
    @traced("stitch_final_video")
    async def stitch_final_video(
        self,
        task_id: str,
        scenes: List[Dict[str, Any]],
        scene_videos: Dict[str, Dict[str, Any]],
        transitions: Optional[List[Dict[str, Any]]] = None,
        music: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Stitch scene videos with transitions and music into a final video.
        
        Args:
            task_id: ID of the task
            scenes: List of scenes with index, title, and transition
            scene_videos: Dictionary of scene indexes to video results
            transitions: Optional list of transition results
            music: Optional list of music results
            
        Returns:
            Dict[str, Any]: Final video result
        """
        try:
            # Sort scenes by index
            sorted_scenes = sorted(scenes, key=lambda s: s.get("index") or s.get("scene", {}).get("index", 0))
            
            # Get the scene video URLs
            scene_video_urls = []
            for scene in sorted_scenes:
                scene_index = scene.get("index") or scene.get("scene", {}).get("index")
                scene_video = scene_videos.get(str(scene_index))
                
                if not scene_video:
                    logger.warning(f"Missing video for scene {scene_index}")
                    continue
                
                scene_url = scene_video.get("url")
                if not scene_url:
                    logger.warning(f"Missing video URL for scene {scene_index}")
                    continue
                
                scene_video_urls.append(scene_url)
            
            # Get the transition types
            transition_types = []
            for i in range(len(sorted_scenes) - 1):
                scene = sorted_scenes[i + 1]
                transition_type = scene.get("transition") or scene.get("scene", {}).get("transition", "fade")
                transition_types.append(transition_type)
            
            # Get the music URL
            music_url = None
            if music and len(music) > 0:
                music_url = music[0].get("url")
            
            # Stitch the video
            result = await stitch_video(
                task_id=task_id,
                scene_videos=scene_video_urls,
                transitions=transition_types,
                music_url=music_url
            )
            
            # Log the video stitching
            log_event(
                event_type="final_video_stitched",
                message=f"Final video stitched for task: {task_id}",
                data={
                    "task_id": task_id,
                    "scene_count": len(scene_video_urls),
                    "transition_count": len(transition_types),
                    "has_music": music_url is not None,
                    "url": result.get("url")
                }
            )
            
            return result
        except Exception as e:
            logger.error(f"Error stitching final video: {str(e)}")
            raise
    
    @traced("generate_video")
    async def generate_video(
        self,
        task_id: str,
        script_data: Dict[str, Any],
        assets: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a complete video from script and assets.
        
        Args:
            task_id: ID of the task
            script_data: Script data with clips and music
            assets: Asset data with scenes, audio, and music
            
        Returns:
            Dict[str, Any]: Final video result
        """
        try:
            # Extract scenes from clips
            scenes = []
            for clip in script_data.get("clips", []):
                if "scene" in clip:
                    scenes.append(clip["scene"])
            
            # Create scene videos
            scene_videos_result = await self.create_scene_videos(
                task_id=task_id,
                scenes=scenes,
                scene_images=assets.get("scenes", {}),
                scene_audio=assets.get("audio", {})
            )
            
            scene_videos = scene_videos_result.get("videos", {})
            
            # Apply transitions
            transitions_result = await self.apply_transitions(
                task_id=task_id,
                scenes=scenes,
                scene_videos=scene_videos
            )
            
            transitions = transitions_result.get("transitions", [])
            
            # Stitch final video
            final_video = await self.stitch_final_video(
                task_id=task_id,
                scenes=scenes,
                scene_videos=scene_videos,
                transitions=transitions,
                music=assets.get("music", [])
            )
            
            # Log the video generation
            log_event(
                event_type="video_generated",
                message=f"Video generated for task: {task_id}",
                data={
                    "task_id": task_id,
                    "scene_count": len(scenes),
                    "url": final_video.get("url")
                }
            )
            
            return {
                "task_id": task_id,
                "scene_videos": scene_videos,
                "transitions": transitions,
                "final_video": final_video
            }
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise
    
    async def _run_with_direct_api(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with direct OpenAI API calls.
        
        Args:
            input_text: Input text for the agent
            context: Context for the agent
            
        Returns:
            Dict[str, Any]: Response from the agent
        """
        try:
            # Check if we have a task_id in the context
            task_id = context.get("task_id")
            if not task_id:
                # Generate a new task_id
                import uuid
                task_id = str(uuid.uuid4())
                context["task_id"] = task_id
            
            # Check if we have a script and assets in the context
            script_data = context.get("script")
            assets = context.get("assets")
            
            if "generate video" in input_text.lower() or "create video" in input_text.lower():
                if not script_data:
                    return {
                        "status": "error",
                        "error": "No script found in context. Please create a script first."
                    }
                
                if not assets:
                    return {
                        "status": "error",
                        "error": "No assets found in context. Please generate assets first."
                    }
                
                # Generate the video
                results = await self.generate_video(
                    task_id=task_id,
                    script_data=script_data,
                    assets=assets
                )
                
                return {
                    "status": "success",
                    "output": "Video generated successfully.",
                    "data": results
                }
            elif "create scene videos" in input_text.lower():
                if not script_data or not script_data.get("clips"):
                    return {
                        "status": "error",
                        "error": "No scenes found in script. Please create a script with scenes first."
                    }
                
                if not assets or not assets.get("scenes") or not assets.get("audio"):
                    return {
                        "status": "error",
                        "error": "Missing scene images or audio. Please generate assets first."
                    }
                
                # Extract scenes from clips
                scenes = []
                for clip in script_data.get("clips", []):
                    if "scene" in clip:
                        scenes.append(clip["scene"])
                
                # Create scene videos
                results = await self.create_scene_videos(
                    task_id=task_id,
                    scenes=scenes,
                    scene_images=assets.get("scenes", {}),
                    scene_audio=assets.get("audio", {})
                )
                
                return {
                    "status": "success",
                    "output": f"Scene videos created successfully for {len(results.get('videos', {}))} scenes.",
                    "data": results
                }
            elif "apply transitions" in input_text.lower():
                if not script_data or not script_data.get("clips"):
                    return {
                        "status": "error",
                        "error": "No scenes found in script. Please create a script with scenes first."
                    }
                
                if not context.get("scene_videos"):
                    return {
                        "status": "error",
                        "error": "No scene videos found in context. Please create scene videos first."
                    }
                
                # Extract scenes from clips
                scenes = []
                for clip in script_data.get("clips", []):
                    if "scene" in clip:
                        scenes.append(clip["scene"])
                
                # Apply transitions
                results = await self.apply_transitions(
                    task_id=task_id,
                    scenes=scenes,
                    scene_videos=context.get("scene_videos", {})
                )
                
                return {
                    "status": "success",
                    "output": f"Transitions applied successfully for {len(results.get('transitions', []))} scene pairs.",
                    "data": results
                }
            elif "stitch video" in input_text.lower() or "stitch final video" in input_text.lower():
                if not script_data or not script_data.get("clips"):
                    return {
                        "status": "error",
                        "error": "No scenes found in script. Please create a script with scenes first."
                    }
                
                if not context.get("scene_videos"):
                    return {
                        "status": "error",
                        "error": "No scene videos found in context. Please create scene videos first."
                    }
                
                # Extract scenes from clips
                scenes = []
                for clip in script_data.get("clips", []):
                    if "scene" in clip:
                        scenes.append(clip["scene"])
                
                # Stitch final video
                result = await self.stitch_final_video(
                    task_id=task_id,
                    scenes=scenes,
                    scene_videos=context.get("scene_videos", {}),
                    transitions=context.get("transitions", []),
                    music=assets.get("music", []) if assets else None
                )
                
                return {
                    "status": "success",
                    "output": "Final video stitched successfully.",
                    "data": {"final_video": result}
                }
            else:
                return {
                    "status": "error",
                    "error": "Unknown command. Please specify what video operation to perform."
                }
        except Exception as e:
            logger.error(f"Error running video agent: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Create a global instance of the video agent
video_agent = VideoAgent()
