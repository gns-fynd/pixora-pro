"""
Asset generation agent for Pixora AI Video Creation Platform
"""
import logging
import json
from typing import Dict, Any, Optional, List, Union

# Import base agent
from .base_agent import BaseAgent

# Import tools
from ..tools.openai_tools import (
    generate_character_images,
    generate_scene_images
)
from ..tools.fal_tools import (
    generate_voice_over,
    upload_file_to_fal
)
from ..tools.replicate_tools import (
    generate_music
)

# Import telemetry
from ..utils.telemetry import traced, log_event

# Configure logging
logger = logging.getLogger(__name__)

class AssetAgent(BaseAgent):
    """
    Agent for generating assets like character images, scene images, voice-overs, and music.
    """
    
    def __init__(self):
        """Initialize the asset agent."""
        instructions = """You are an asset generation agent for a video creation platform.
        
        Your task is to generate various assets for video production:
        1. Character images with consistent appearance across different views
        2. Scene images based on detailed prompts
        3. Voice-over audio from script text
        4. Background music that matches the mood of scenes
        
        For character images, you should create a 2x2 grid showing different views of the character.
        For scene images, you should include motion cues in the prompt.
        For voice-over, you should ensure the text is clear and well-paced.
        For music, you should match the mood and duration of the scenes.
        """
        
        # Define the tools
        tools = [
            generate_character_images,
            generate_scene_images,
            generate_voice_over,
            generate_music,
            upload_file_to_fal
        ]
        
        # Initialize the base agent
        super().__init__(name="AssetAgent", instructions=instructions, tools=tools)
        
        logger.info("Asset agent initialized")
    
    @traced("generate_character_assets")
    async def generate_character_assets(
        self,
        task_id: str,
        character_profiles: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate character images for all character profiles.
        
        Args:
            task_id: ID of the task
            character_profiles: List of character profiles with name and image_prompt
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of character IDs to image results
        """
        try:
            results = {}
            
            for profile in character_profiles:
                character_id = profile.get("id") or profile.get("name").lower().replace(" ", "_")
                image_prompt = profile.get("image_prompt")
                
                if not image_prompt:
                    logger.warning(f"No image prompt found for character: {character_id}")
                    continue
                
                # Generate character images
                result = await generate_character_images(
                    task_id=task_id,
                    character_id=character_id,
                    image_prompt=image_prompt
                )
                
                # Store the result
                results[character_id] = result
                
                # Log the character image generation
                log_event(
                    event_type="character_images_generated",
                    message=f"Character images generated for: {character_id}",
                    data={
                        "task_id": task_id,
                        "character_id": character_id,
                        "url": result.get("url")
                    }
                )
            
            return {"characters": results}
        except Exception as e:
            logger.error(f"Error generating character assets: {str(e)}")
            raise
    
    @traced("generate_scene_assets")
    async def generate_scene_assets(
        self,
        task_id: str,
        scenes: List[Dict[str, Any]],
        character_urls: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Generate scene images for all scenes.
        
        Args:
            task_id: ID of the task
            scenes: List of scenes with index, title, and video_prompt
            character_urls: Optional dictionary of character IDs to image URLs
            
        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: Dictionary of scene indexes to image results
        """
        try:
            results = {}
            
            for scene in scenes:
                scene_index = scene.get("index") or scene.get("scene", {}).get("index")
                if not scene_index:
                    logger.warning(f"No scene index found for scene: {scene}")
                    continue
                
                # Get the video prompt
                video_prompt = scene.get("video_prompt") or scene.get("scene", {}).get("video_prompt")
                if not video_prompt:
                    logger.warning(f"No video prompt found for scene: {scene_index}")
                    continue
                
                # Get character references if available
                character_references = None
                if character_urls and scene.get("characters"):
                    character_references = [
                        character_urls.get(character_id)
                        for character_id in scene.get("characters")
                        if character_id in character_urls
                    ]
                
                # Generate scene image
                result = await generate_scene_images(
                    task_id=task_id,
                    scene_index=scene_index,
                    video_prompt=video_prompt,
                    character_references=character_references
                )
                
                # Store the result
                results[str(scene_index)] = result
                
                # Log the scene image generation
                log_event(
                    event_type="scene_image_generated",
                    message=f"Scene image generated for scene: {scene_index}",
                    data={
                        "task_id": task_id,
                        "scene_index": scene_index,
                        "url": result.get("url")
                    }
                )
            
            return {"scenes": results}
        except Exception as e:
            logger.error(f"Error generating scene assets: {str(e)}")
            raise
    
    @traced("generate_audio_assets")
    async def generate_audio_assets(
        self,
        task_id: str,
        scenes: List[Dict[str, Any]],
        voice_sample: Optional[str] = None
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Generate voice-over audio for all scenes.
        
        Args:
            task_id: ID of the task
            scenes: List of scenes with index, title, and script
            voice_sample: Optional URL to a voice sample to clone
            
        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: Dictionary of scene indexes to audio results
        """
        try:
            results = {}
            
            for scene in scenes:
                scene_index = scene.get("index") or scene.get("scene", {}).get("index")
                if not scene_index:
                    logger.warning(f"No scene index found for scene: {scene}")
                    continue
                
                # Get the script
                script = scene.get("script") or scene.get("scene", {}).get("script")
                if not script:
                    logger.warning(f"No script found for scene: {scene_index}")
                    continue
                
                # Generate voice-over
                result = await generate_voice_over(
                    task_id=task_id,
                    scene_index=scene_index,
                    text=script,
                    voice_sample=voice_sample
                )
                
                # Store the result
                results[str(scene_index)] = result
                
                # Log the voice-over generation
                log_event(
                    event_type="voice_over_generated",
                    message=f"Voice-over generated for scene: {scene_index}",
                    data={
                        "task_id": task_id,
                        "scene_index": scene_index,
                        "url": result.get("url"),
                        "duration": result.get("duration")
                    }
                )
            
            return {"audio": results}
        except Exception as e:
            logger.error(f"Error generating audio assets: {str(e)}")
            raise
    
    @traced("generate_music_assets")
    async def generate_music_assets(
        self,
        task_id: str,
        music_specs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate background music for scenes.
        
        Args:
            task_id: ID of the task
            music_specs: List of music specifications with prompt, scene_indexes, and duration
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary of music IDs to music results
        """
        try:
            results = []
            
            for spec in music_specs:
                prompt = spec.get("prompt")
                scene_indexes = spec.get("scene_indexes")
                
                if not prompt or not scene_indexes:
                    logger.warning(f"Missing prompt or scene_indexes in music spec: {spec}")
                    continue
                
                # Calculate duration based on scene durations
                duration = spec.get("duration", 30)  # Default to 30 seconds
                
                # Generate music
                result = await generate_music(
                    task_id=task_id,
                    prompt=prompt,
                    duration=duration,
                    scene_indexes=scene_indexes
                )
                
                # Store the result
                results.append(result)
                
                # Log the music generation
                log_event(
                    event_type="music_generated",
                    message=f"Music generated for scenes: {scene_indexes}",
                    data={
                        "task_id": task_id,
                        "scene_indexes": scene_indexes,
                        "url": result.get("url"),
                        "duration": result.get("duration")
                    }
                )
            
            return {"music": results}
        except Exception as e:
            logger.error(f"Error generating music assets: {str(e)}")
            raise
    
    @traced("generate_all_assets")
    async def generate_all_assets(
        self,
        task_id: str,
        script_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate all assets for a script.
        
        Args:
            task_id: ID of the task
            script_data: Script data with character_profiles, clips, and music
            
        Returns:
            Dict[str, Any]: Dictionary of all generated assets
        """
        try:
            results = {"task_id": task_id}
            
            # Extract scenes from clips
            scenes = []
            for clip in script_data.get("clips", []):
                if "scene" in clip:
                    scenes.append(clip["scene"])
            
            # Generate character assets
            if script_data.get("character_profiles"):
                character_results = await self.generate_character_assets(
                    task_id=task_id,
                    character_profiles=script_data["character_profiles"]
                )
                results.update(character_results)
                
                # Extract character URLs for scene generation
                character_urls = {}
                for character_id, result in character_results.get("characters", {}).items():
                    character_urls[character_id] = result.get("url")
                
                # Generate scene assets with character references
                scene_results = await self.generate_scene_assets(
                    task_id=task_id,
                    scenes=scenes,
                    character_urls=character_urls
                )
                results.update(scene_results)
            else:
                # Generate scene assets without character references
                scene_results = await self.generate_scene_assets(
                    task_id=task_id,
                    scenes=scenes
                )
                results.update(scene_results)
            
            # Generate audio assets
            audio_results = await self.generate_audio_assets(
                task_id=task_id,
                scenes=scenes,
                voice_sample=script_data.get("voice_sample")
            )
            results.update(audio_results)
            
            # Generate music assets
            if script_data.get("music"):
                music_results = await self.generate_music_assets(
                    task_id=task_id,
                    music_specs=script_data["music"]
                )
                results.update(music_results)
            
            # Log the asset generation
            log_event(
                event_type="all_assets_generated",
                message=f"All assets generated for task: {task_id}",
                data={
                    "task_id": task_id,
                    "character_count": len(results.get("characters", {})),
                    "scene_count": len(results.get("scenes", {})),
                    "audio_count": len(results.get("audio", {})),
                    "music_count": len(results.get("music", []))
                }
            )
            
            return results
        except Exception as e:
            logger.error(f"Error generating all assets: {str(e)}")
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
            
            # Check if we have a script in the context
            script_data = context.get("script")
            
            if "generate all assets" in input_text.lower():
                if not script_data:
                    return {
                        "status": "error",
                        "error": "No script found in context. Please create a script first."
                    }
                
                # Generate all assets
                results = await self.generate_all_assets(
                    task_id=task_id,
                    script_data=script_data
                )
                
                return {
                    "status": "success",
                    "output": "All assets generated successfully.",
                    "data": results
                }
            elif "generate character" in input_text.lower():
                if not script_data or not script_data.get("character_profiles"):
                    return {
                        "status": "error",
                        "error": "No character profiles found in script. Please create a script with character profiles first."
                    }
                
                # Generate character assets
                results = await self.generate_character_assets(
                    task_id=task_id,
                    character_profiles=script_data["character_profiles"]
                )
                
                return {
                    "status": "success",
                    "output": f"Character assets generated successfully for {len(results.get('characters', {}))} characters.",
                    "data": results
                }
            elif "generate scene" in input_text.lower() or "generate image" in input_text.lower():
                if not script_data or not script_data.get("clips"):
                    return {
                        "status": "error",
                        "error": "No scenes found in script. Please create a script with scenes first."
                    }
                
                # Extract scenes from clips
                scenes = []
                for clip in script_data.get("clips", []):
                    if "scene" in clip:
                        scenes.append(clip["scene"])
                
                # Generate scene assets
                results = await self.generate_scene_assets(
                    task_id=task_id,
                    scenes=scenes
                )
                
                return {
                    "status": "success",
                    "output": f"Scene assets generated successfully for {len(results.get('scenes', {}))} scenes.",
                    "data": results
                }
            elif "generate voice" in input_text.lower() or "generate audio" in input_text.lower():
                if not script_data or not script_data.get("clips"):
                    return {
                        "status": "error",
                        "error": "No scenes found in script. Please create a script with scenes first."
                    }
                
                # Extract scenes from clips
                scenes = []
                for clip in script_data.get("clips", []):
                    if "scene" in clip:
                        scenes.append(clip["scene"])
                
                # Generate audio assets
                results = await self.generate_audio_assets(
                    task_id=task_id,
                    scenes=scenes,
                    voice_sample=script_data.get("voice_sample")
                )
                
                return {
                    "status": "success",
                    "output": f"Audio assets generated successfully for {len(results.get('audio', {}))} scenes.",
                    "data": results
                }
            elif "generate music" in input_text.lower():
                if not script_data or not script_data.get("music"):
                    return {
                        "status": "error",
                        "error": "No music specifications found in script. Please create a script with music specifications first."
                    }
                
                # Generate music assets
                results = await self.generate_music_assets(
                    task_id=task_id,
                    music_specs=script_data["music"]
                )
                
                return {
                    "status": "success",
                    "output": f"Music assets generated successfully for {len(results.get('music', []))} music specifications.",
                    "data": results
                }
            else:
                return {
                    "status": "error",
                    "error": "Unknown command. Please specify what assets to generate."
                }
        except Exception as e:
            logger.error(f"Error running asset agent: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Create a global instance of the asset agent
asset_agent = AssetAgent()
