"""
AI agent orchestrator.

This module provides the main agent orchestrator for the Pixora AI platform.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
import os

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services import (
    TextToImageService,
    ImageToVideoService,
    TextToSpeechService,
    TextToMusicService,
    CreditService,
    StorageManager,
)
from app.ai.prompt_analyzer import PromptAnalyzer


# Set up logging
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    AI agent orchestrator for the Pixora AI platform.
    """
    
    def __init__(
        self, 
        text_to_image_service: TextToImageService = Depends(),
        image_to_video_service: ImageToVideoService = Depends(),
        text_to_speech_service: TextToSpeechService = Depends(),
        text_to_music_service: TextToMusicService = Depends(),
        credit_service: CreditService = Depends(),
        storage_manager: StorageManager = Depends(),
        prompt_analyzer: PromptAnalyzer = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the agent orchestrator.
        
        Args:
            text_to_image_service: The text-to-image service
            image_to_video_service: The image-to-video service
            text_to_speech_service: The text-to-speech service
            text_to_music_service: The text-to-music service
            credit_service: The credit service
            storage_manager: The storage manager
            prompt_analyzer: The prompt analyzer for OpenAI integration
            settings: Application settings
        """
        self.text_to_image_service = text_to_image_service
        self.image_to_video_service = image_to_video_service
        self.text_to_speech_service = text_to_speech_service
        self.text_to_music_service = text_to_music_service
        self.credit_service = credit_service
        self.storage_manager = storage_manager
        self.prompt_analyzer = prompt_analyzer
        self.settings = settings
        
        # OpenAI API key
        self.openai_api_key = settings.OPENAI_API_KEY
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        
        # Progress tracking
        self.progress = {}
    
    async def create_video(
        self, 
        prompt: str,
        user_id: str,
        aspect_ratio: str = "16:9",
        duration: int = 30,
        style: Optional[str] = None,
        callback: Optional[Callable[[str, float, Optional[str]], None]] = None
    ) -> Dict[str, Any]:
        """
        Create a video from a prompt.
        
        Args:
            prompt: The prompt to generate the video from
            user_id: The user ID
            aspect_ratio: The aspect ratio of the video
            duration: The duration of the video in seconds
            style: Optional style for the video
            callback: Optional callback function for progress updates
            
        Returns:
            The video creation result
        """
        try:
            # Initialize progress
            video_id = f"video_{user_id}_{prompt[:10]}"
            self._update_progress(video_id, 0, "Starting video creation", callback)
            
            # Calculate total cost
            total_cost = await self._calculate_total_cost(prompt, duration, aspect_ratio)
            
            # Deduct credits
            await self.credit_service.deduct_credits(
                user_id=user_id,
                amount=total_cost,
                reason=f"Video creation: {prompt[:30]}"
            )
            
            # Step 1: Analyze the prompt and generate a script
            self._update_progress(video_id, 5, "Analyzing prompt", callback)
            script = await self._analyze_prompt(prompt, style)
            self._update_progress(video_id, 10, "Generated script", callback)
            
            # Step 2: Generate voiceover first to determine timing
            self._update_progress(video_id, 15, "Generating voiceover", callback)
            voiceover_result = await self._generate_voiceover(script, user_id)
            voiceover_url = voiceover_result["url"]
            audio_duration = voiceover_result["duration"]
            self._update_progress(video_id, 25, f"Generated voiceover ({audio_duration}s)", callback)
            
            # Step 3: Break down the script into scenes based on audio duration
            self._update_progress(video_id, 30, "Breaking down script into scenes", callback)
            scenes = await self._break_down_script(script, audio_duration)
            self._update_progress(video_id, 35, "Generated scene breakdown", callback)
            
            # Step 4: Generate background music based on audio duration
            self._update_progress(video_id, 40, "Generating background music", callback)
            music = await self._generate_background_music(script, audio_duration, user_id)
            self._update_progress(video_id, 50, "Generated background music", callback)
            
            # Step 5: Generate images for each scene
            self._update_progress(video_id, 55, "Generating scene images", callback)
            scene_images = await self._generate_scene_images(scenes, user_id)
            self._update_progress(video_id, 70, "Generated scene images", callback)
            
            # Step 6: Generate videos for each scene
            self._update_progress(video_id, 75, "Generating scene videos", callback)
            scene_videos = await self._generate_scene_videos(scenes, scene_images, user_id, aspect_ratio)
            self._update_progress(video_id, 90, "Generated scene videos", callback)
            
            # Step 7: Prepare the final result
            self._update_progress(video_id, 95, "Preparing final result", callback)
            result = {
                "video_id": video_id,
                "prompt": prompt,
                "script": script,
                "scenes": scenes,
                "scene_images": scene_images,
                "scene_videos": scene_videos,
                "voiceover": voiceover_result,
                "music": music,
                "aspect_ratio": aspect_ratio,
                "duration": audio_duration,  # Use the actual audio duration
                "style": style,
            }
            self._update_progress(video_id, 100, "Video creation complete", callback)
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            # If credits were deducted, refund them
            try:
                await self.credit_service.add_credits(
                    user_id=user_id,
                    amount=total_cost,
                    reason=f"Refund for failed video creation: {prompt[:30]}"
                )
            except Exception as refund_error:
                logger.error(f"Error refunding credits: {str(refund_error)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video creation failed: {str(e)}"
            )
    
    async def _calculate_total_cost(self, prompt: str, duration: int, aspect_ratio: str) -> int:
        """
        Calculate the total cost of creating a video.
        
        Args:
            prompt: The prompt
            duration: The duration in seconds
            aspect_ratio: The aspect ratio
            
        Returns:
            The total cost in credits
        """
        # Base cost for a video
        base_cost = 50
        
        # Additional cost based on duration
        duration_cost = max(1, duration // 10)
        
        # Total cost
        total_cost = base_cost * duration_cost
        
        return total_cost
    
    async def _analyze_prompt(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the prompt and generate a script using OpenAI.
        
        Args:
            prompt: The prompt
            style: Optional style
            
        Returns:
            The script
        """
        try:
            # Use the PromptAnalyzer to generate a script
            script = await self.prompt_analyzer.analyze_prompt(prompt, style)
            return script
        except Exception as e:
            logger.error(f"Error using OpenAI for prompt analysis: {str(e)}")
            # Fallback to a simple script if OpenAI fails
            return {
                "title": f"Video based on: {prompt}",
                "description": prompt,
                "style": style or "default",
                "narration": f"This is a video about {prompt}. It showcases various aspects of the topic.",
            }
    
    async def _break_down_script(self, script: Dict[str, Any], duration: int) -> List[Dict[str, Any]]:
        """
        Break down the script into scenes using OpenAI.
        
        Args:
            script: The script
            duration: The duration in seconds
            
        Returns:
            The scenes
        """
        try:
            # Use the PromptAnalyzer to generate a scene breakdown
            scenes = await self.prompt_analyzer.generate_scene_breakdown(script, duration)
            return scenes
        except Exception as e:
            logger.error(f"Error using OpenAI for scene breakdown: {str(e)}")
            # Fallback to a simple scene breakdown if OpenAI fails
            num_scenes = max(1, duration // 10)
            scenes = []
            
            for i in range(num_scenes):
                scene = {
                    "id": f"scene_{i+1}",
                    "title": f"Scene {i+1}",
                    "description": f"This is scene {i+1} of the video.",
                    "duration": 10,  # 10 seconds per scene
                    "narration": f"In this scene, we explore aspect {i+1} of {script['description']}.",
                }
                scenes.append(scene)
            
            return scenes
    
    async def _generate_scene_images(self, scenes: List[Dict[str, Any]], user_id: str) -> Dict[str, str]:
        """
        Generate images for each scene using optimized prompts from OpenAI.
        
        Args:
            scenes: The scenes
            user_id: The user ID
            
        Returns:
            A dictionary mapping scene IDs to image URLs
        """
        from app.services.fal_ai import TextToImageRequest, ImageSize
        
        scene_images = {}
        
        try:
            # Generate optimized image prompts for each scene
            image_prompts = await self.prompt_analyzer.generate_image_prompts(scenes)
            
            # Generate images for each scene
            for scene in scenes:
                scene_id = scene["id"]
                
                # Get the optimized prompt or fall back to the scene description
                prompt = image_prompts.get(scene_id, scene["description"])
                
                # Create the request
                request = TextToImageRequest(
                    prompt=prompt,
                    image_size=ImageSize.LANDSCAPE_16_9,
                    num_inference_steps=28,
                    guidance_scale=3.5,
                    num_images=1
                )
                
                # Generate the image
                response = await self.text_to_image_service.generate_image(
                    request=request,
                    user_id=user_id
                )
                
                # Store the image URL
                scene_images[scene_id] = response.images[0]
                
        except Exception as e:
            logger.error(f"Error generating optimized image prompts: {str(e)}")
            # Fall back to using scene descriptions directly
            for scene in scenes:
                # Create the request
                request = TextToImageRequest(
                    prompt=scene["description"],
                    image_size=ImageSize.LANDSCAPE_16_9,
                    num_inference_steps=28,
                    guidance_scale=3.5,
                    num_images=1
                )
                
                # Generate the image
                response = await self.text_to_image_service.generate_image(
                    request=request,
                    user_id=user_id
                )
                
                # Store the image URL
                scene_images[scene["id"]] = response.images[0]
        
        return scene_images
    
    async def _generate_scene_videos(
        self, 
        scenes: List[Dict[str, Any]], 
        scene_images: Dict[str, str],
        user_id: str,
        aspect_ratio: str
    ) -> Dict[str, str]:
        """
        Generate videos for each scene.
        
        Args:
            scenes: The scenes
            scene_images: The scene images
            user_id: The user ID
            aspect_ratio: The aspect ratio
            
        Returns:
            A dictionary mapping scene IDs to video URLs
        """
        from app.services.fal_ai import ImageToVideoRequest, AspectRatio, Duration
        
        scene_videos = {}
        
        # Map aspect ratio string to enum
        aspect_ratio_map = {
            "16:9": AspectRatio.LANDSCAPE_16_9,
            "9:16": AspectRatio.PORTRAIT_9_16,
            "1:1": AspectRatio.SQUARE_1_1,
        }
        aspect_ratio_enum = aspect_ratio_map.get(aspect_ratio, AspectRatio.LANDSCAPE_16_9)
        
        for scene in scenes:
            # Get the image URL
            image_url = scene_images.get(scene["id"])
            if not image_url:
                continue
            
            # Create the request
            request = ImageToVideoRequest(
                prompt=scene["description"],
                image_url=image_url,
                duration=Duration.SECONDS_5,
                aspect_ratio=aspect_ratio_enum
            )
            
            # Generate the video
            response = await self.image_to_video_service.generate_video_from_url(
                request=request,
                user_id=user_id
            )
            
            # Store the video URL
            scene_videos[scene["id"]] = response.video_url
        
        return scene_videos
    
    async def _generate_voiceover(self, script: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Generate voiceover for the script.
        
        Args:
            script: The script
            user_id: The user ID
            
        Returns:
            Dictionary containing the voiceover URL and duration
        """
        from app.services.fal_ai import TextToSpeechRequest
        
        try:
            # For now, we'll use a default voice ID
            # In a real implementation, we would either:
            # 1. Use a default voice
            # 2. Let the user choose a voice
            # 3. Clone the user's voice if they've uploaded a sample
            voice_id = "default_voice_id"  # This would be replaced with a real voice ID
            
            # Create the request
            request = TextToSpeechRequest(
                text=script["narration"],
                voice_id=voice_id,
                speed=1.0
            )
            
            # Generate the speech
            # In a real implementation, this would call the text_to_speech_service
            # For now, we'll simulate it
            
            # Calculate an estimated duration based on the text length
            # A rough estimate is 150 words per minute, or 2.5 words per second
            word_count = len(script["narration"].split())
            estimated_duration = max(10, word_count / 2.5)  # At least 10 seconds
            
            # Return a mock result
            return {
                "url": "https://example.com/voiceover.mp3",
                "duration": int(estimated_duration),
                "word_count": word_count,
                "voice_id": voice_id
            }
            
        except Exception as e:
            logger.error(f"Error generating voiceover: {str(e)}")
            # Return a fallback result
            return {
                "url": "https://example.com/fallback-voiceover.mp3",
                "duration": 30,  # Default 30 seconds
                "error": str(e)
            }
    
    async def _generate_background_music(self, script: Dict[str, Any], duration: int, user_id: str) -> str:
        """
        Generate background music for the video.
        
        Args:
            script: The script
            duration: The duration in seconds
            user_id: The user ID
            
        Returns:
            The music URL
        """
        from app.services.fal_ai import TextToMusicRequest
        
        # Create the request
        request = TextToMusicRequest(
            text=f"Background music for a video about {script['description']}",
            duration=min(30.0, float(duration)),
            prompt_influence=0.7
        )
        
        # Generate the music
        response = await self.text_to_music_service.generate_music(
            request=request,
            user_id=user_id
        )
        
        # Return the music URL
        return response.audio_url
    
    def _update_progress(
        self, 
        task_id: str, 
        progress: float, 
        message: Optional[str] = None,
        callback: Optional[Callable[[str, float, Optional[str]], None]] = None
    ):
        """
        Update the progress of a task.
        
        Args:
            task_id: The task ID
            progress: The progress (0-100)
            message: Optional message
            callback: Optional callback function
        """
        self.progress[task_id] = {
            "progress": progress,
            "message": message or f"Processing: {progress:.0f}%",
        }
        
        # Call the callback if provided
        if callback:
            callback(task_id, progress, message)
    
    async def get_scene_breakdown_intro(self, prompt: str) -> str:
        """
        Generate an introduction message when scene breakdown starts.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            An introduction message
        """
        try:
            return await self.prompt_analyzer.generate_contextual_response(
                "scene_breakdown_intro", 
                {"prompt": prompt}
            )
        except Exception as e:
            logger.error(f"Error generating scene breakdown intro: {str(e)}")
            return "I'm analyzing your prompt to break it down into scenes. This will help us create a well-structured video."
    
    async def get_generation_started_message(self) -> str:
        """
        Generate a message when video generation starts.
        
        Returns:
            A message about the generation process starting
        """
        try:
            return await self.prompt_analyzer.generate_contextual_response("generation_started")
        except Exception as e:
            logger.error(f"Error generating generation started message: {str(e)}")
            return "I'm starting the video generation process now. This will take a few minutes, but you can chat with me while you wait."
    
    async def get_generation_completed_message(self) -> str:
        """
        Generate a message when video generation completes.
        
        Returns:
            A message about the generation process completing
        """
        try:
            return await self.prompt_analyzer.generate_contextual_response("generation_completed")
        except Exception as e:
            logger.error(f"Error generating generation completed message: {str(e)}")
            return "Your video has been generated successfully! You can now view it, download it, or edit it further."
    
    async def process_chat_message(
        self, 
        message: str,
        video_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process a chat message from the user.
        
        Args:
            message: The user's message
            video_id: The video ID
            user_id: The user ID
            
        Returns:
            The AI response with any actions or video updates
        """
        try:
            # Get the video and scenes
            video = await self._get_video(video_id)
            scenes = await self._get_scenes(video_id)
            
            # Analyze the message to determine intent
            intent = await self.prompt_analyzer.analyze_chat_message(message, video, scenes)
            
            # Handle different intents
            if intent["request_type"] == "edit_scene":
                # Edit a specific scene
                return await self._handle_scene_edit(intent, video, scenes, user_id)
                
            elif intent["request_type"] == "change_voice":
                # Change the voice
                return await self._handle_voice_change(intent, video, user_id)
                
            elif intent["request_type"] == "change_music":
                # Change the background music
                return await self._handle_music_change(intent, video, user_id)
                
            elif intent["request_type"] == "suggestion":
                # Handle suggestion
                return {
                    "message": intent["response"],
                    "actions": self._generate_suggestion_actions(intent, video, scenes)
                }
                
            else:
                # General question or unrecognized intent
                return {
                    "message": intent["response"]
                }
                
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return {
                "message": f"I encountered an error while processing your request: {str(e)}"
            }
    
    async def _handle_scene_edit(
        self, 
        intent: Dict[str, Any], 
        video: Dict[str, Any], 
        scenes: List[Dict[str, Any]], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle a scene edit request.
        
        Args:
            intent: The analyzed intent
            video: The video data
            scenes: The scenes data
            user_id: The user ID
            
        Returns:
            The response with any updates
        """
        scene_id = intent.get("scene_id")
        action = intent.get("action")
        parameters = intent.get("parameters", {})
        
        # Find the scene
        scene = next((s for s in scenes if s["id"] == scene_id), None)
        if not scene:
            return {
                "message": f"I couldn't find the scene you're referring to. Please specify a valid scene."
            }
        
        # Handle different actions
        if action == "regenerate_image":
            # Regenerate the scene image
            from app.services.fal_ai import TextToImageRequest, ImageSize
            
            # Create a more detailed prompt if provided
            prompt = parameters.get("prompt", scene["description"])
            
            # Create the request
            request = TextToImageRequest(
                prompt=prompt,
                image_size=ImageSize.LANDSCAPE_16_9,
                num_inference_steps=28,
                guidance_scale=3.5,
                num_images=1
            )
            
            # Generate the image
            response = await self.text_to_image_service.generate_image(
                request=request,
                user_id=user_id
            )
            
            # Update the scene image
            scene_index = next((i for i, s in enumerate(scenes) if s["id"] == scene_id), None)
            if scene_index is not None:
                scenes[scene_index]["image_url"] = response.images[0]
                
                # Update the scene in the database
                await self._update_scene(scene_id, {"image_url": response.images[0]})
            
            return {
                "message": f"I've regenerated the image for scene {scene['title']}.",
                "video_updates": {
                    "scenes": scenes
                },
                "actions": [
                    {
                        "type": "view_scene",
                        "scene_id": scene_id,
                        "label": f"View Scene {scene['title']}"
                    }
                ]
            }
            
        elif action == "change_description":
            # Update the scene description
            new_description = parameters.get("description", "")
            if not new_description:
                return {
                    "message": "I need a new description to update the scene. Please provide one."
                }
            
            # Update the scene
            scene_index = next((i for i, s in enumerate(scenes) if s["id"] == scene_id), None)
            if scene_index is not None:
                scenes[scene_index]["description"] = new_description
                
                # Update the scene in the database
                await self._update_scene(scene_id, {"description": new_description})
            
            return {
                "message": f"I've updated the description for scene {scene['title']}.",
                "video_updates": {
                    "scenes": scenes
                }
            }
            
        elif action == "adjust_duration":
            # Update the scene duration
            new_duration = parameters.get("duration")
            if not new_duration or not isinstance(new_duration, (int, float)) or new_duration <= 0:
                return {
                    "message": "I need a valid duration to update the scene. Please provide a positive number in seconds."
                }
            
            # Update the scene
            scene_index = next((i for i, s in enumerate(scenes) if s["id"] == scene_id), None)
            if scene_index is not None:
                scenes[scene_index]["duration"] = new_duration
                
                # Update the scene in the database
                await self._update_scene(scene_id, {"duration": new_duration})
            
            return {
                "message": f"I've updated the duration for scene {scene['title']} to {new_duration} seconds.",
                "video_updates": {
                    "scenes": scenes
                }
            }
            
        else:
            # Unrecognized action
            return {
                "message": f"I'm not sure how to {action} for a scene. Could you try a different edit?"
            }
    
    async def _handle_voice_change(
        self, 
        intent: Dict[str, Any], 
        video: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle a voice change request.
        
        Args:
            intent: The analyzed intent
            video: The video data
            user_id: The user ID
            
        Returns:
            The response with any updates
        """
        # For now, we'll simulate voice selection
        voice_selection = await self.prompt_analyzer.select_voice(video)
        
        return {
            "message": f"I've selected a {voice_selection['gender']} voice with a {voice_selection['tone']} tone for your video. {voice_selection['reasoning']}",
            "video_updates": {
                "voice_id": voice_selection["voice_id"]
            }
        }
    
    async def _handle_music_change(
        self, 
        intent: Dict[str, Any], 
        video: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle a music change request.
        
        Args:
            intent: The analyzed intent
            video: The video data
            user_id: The user ID
            
        Returns:
            The response with any updates
        """
        parameters = intent.get("parameters", {})
        style = parameters.get("style", "")
        
        # Generate new background music
        from app.services.fal_ai import TextToMusicRequest
        
        # Create a prompt based on the style and video content
        music_prompt = f"Background music for a {style} video about {video['description']}"
        
        # Create the request
        request = TextToMusicRequest(
            text=music_prompt,
            duration=min(30.0, float(video.get("duration", 30))),
            prompt_influence=0.7
        )
        
        # Generate the music
        response = await self.text_to_music_service.generate_music(
            request=request,
            user_id=user_id
        )
        
        return {
            "message": f"I've generated new {style} background music for your video.",
            "video_updates": {
                "music_url": response.audio_url
            }
        }
    
    def _generate_suggestion_actions(
        self, 
        intent: Dict[str, Any], 
        video: Dict[str, Any], 
        scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestion actions based on the intent.
        
        Args:
            intent: The analyzed intent
            video: The video data
            scenes: The scenes data
            
        Returns:
            List of suggested actions
        """
        actions = []
        
        # Add actions based on the suggestion type
        suggestion_type = intent.get("suggestion_type", "")
        
        if suggestion_type == "regenerate_images":
            # Add actions to regenerate images for scenes
            for scene in scenes[:3]:  # Limit to first 3 scenes
                actions.append({
                    "type": "regenerate_image",
                    "scene_id": scene["id"],
                    "label": f"Regenerate image for {scene['title']}"
                })
                
        elif suggestion_type == "change_voice":
            # Add action to change voice
            actions.append({
                "type": "change_voice",
                "label": "Select a new voice"
            })
            
        elif suggestion_type == "change_music":
            # Add actions for different music styles
            for style in ["energetic", "calm", "dramatic", "inspirational"]:
                actions.append({
                    "type": "change_music",
                    "style": style,
                    "label": f"Try {style} music"
                })
        
        return actions
    
    async def _get_video(self, video_id: str) -> Dict[str, Any]:
        """
        Get a video by ID.
        
        Args:
            video_id: The video ID
            
        Returns:
            The video data
        """
        # In a real implementation, this would fetch the video from the database
        # For now, we'll return a mock video
        return {
            "id": video_id,
            "title": "Sample Video",
            "description": "This is a sample video",
            "style": "default",
            "duration": 30
        }
    
    async def _get_scenes(self, video_id: str) -> List[Dict[str, Any]]:
        """
        Get scenes for a video.
        
        Args:
            video_id: The video ID
            
        Returns:
            The scenes data
        """
        # In a real implementation, this would fetch the scenes from the database
        # For now, we'll return mock scenes
        return [
            {
                "id": "scene_1",
                "title": "Scene 1",
                "description": "This is scene 1",
                "duration": 10,
                "narration": "Narration for scene 1"
            },
            {
                "id": "scene_2",
                "title": "Scene 2",
                "description": "This is scene 2",
                "duration": 10,
                "narration": "Narration for scene 2"
            },
            {
                "id": "scene_3",
                "title": "Scene 3",
                "description": "This is scene 3",
                "duration": 10,
                "narration": "Narration for scene 3"
            }
        ]
    
    async def _update_scene(self, scene_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a scene in the database.
        
        Args:
            scene_id: The scene ID
            updates: The updates to apply
        """
        # In a real implementation, this would update the scene in the database
        # For now, we'll just log the update
        logger.info(f"Updating scene {scene_id} with {updates}")
    
    def get_progress(self, task_id: str) -> Dict[str, Any]:
        """
        Get the progress of a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The progress
        """
        return self.progress.get(task_id, {"progress": 0, "message": "Task not found"})
