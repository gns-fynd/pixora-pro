"""
Prompt analyzer for generating video scripts.

This module provides a service for analyzing prompts and generating video scripts
using OpenAI's GPT models.
"""
import logging
import json
from typing import Dict, Any, Optional, List
import os

from fastapi import Depends, HTTPException, status
import openai
from openai import OpenAI

from app.core.config import Settings, get_settings


# Set up logging
logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Prompt analyzer for generating video scripts.
    """
    
    def __init__(self, settings: Settings = Depends(get_settings)):
        """
        Initialize the prompt analyzer.
        
        Args:
            settings: Application settings
        """
        self.openai_api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.openai_api_key)
    
    async def analyze_prompt(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a prompt and generate a video script.
        
        Args:
            prompt: The prompt to analyze
            style: Optional style for the video
            
        Returns:
            The generated script
        """
        try:
            # Create the system message
            system_message = """
            You are a professional video scriptwriter. Your task is to create a detailed video script based on the given prompt.
            The script should include:
            1. A catchy title
            2. A brief description of the video
            3. A narrative structure with a clear beginning, middle, and end
            4. Detailed narration text that will be spoken in the video
            
            Format your response as a JSON object with the following structure:
            {
                "title": "The video title",
                "description": "Brief description of the video",
                "style": "The style of the video (e.g., educational, dramatic, comedic)",
                "narration": "The full narration text for the video",
                "tone": "The tone of the video (e.g., serious, light-hearted, inspirational)",
                "target_audience": "The target audience for the video",
                "key_points": ["Key point 1", "Key point 2", "Key point 3"]
            }
            """
            
            # Create the user message
            user_message = f"Create a video script for the following prompt: {prompt}"
            if style:
                user_message += f"\nThe style of the video should be: {style}"
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            # Parse the response
            script = self._parse_response(response, prompt, style)
            
            return script
            
        except Exception as e:
            logger.error(f"Error analyzing prompt: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prompt analysis failed: {str(e)}"
            )
    
    async def generate_scene_breakdown(self, script: Dict[str, Any], duration: int) -> List[Dict[str, Any]]:
        """
        Generate a scene breakdown from a script.
        
        Args:
            script: The script
            duration: The duration of the video in seconds
            
        Returns:
            The scene breakdown
        """
        try:
            # Create the system message
            system_message = """
            You are a professional video director. Your task is to break down a video script into individual scenes.
            Each scene should have:
            1. A unique ID
            2. A title
            3. A description of what happens in the scene
            4. The duration of the scene in seconds
            5. The narration text for the scene
            
            Format your response as a JSON array of scene objects with the following structure:
            [
                {
                    "id": "scene_1",
                    "title": "Scene 1 title",
                    "description": "Description of what happens in scene 1",
                    "duration": 10,
                    "narration": "The narration text for scene 1"
                },
                {
                    "id": "scene_2",
                    "title": "Scene 2 title",
                    "description": "Description of what happens in scene 2",
                    "duration": 15,
                    "narration": "The narration text for scene 2"
                }
            ]
            
            The total duration of all scenes should add up to the specified video duration.
            """
            
            # Create the user message
            user_message = f"""
            Break down the following video script into scenes:
            
            Title: {script.get('title', 'Untitled')}
            Description: {script.get('description', '')}
            Narration: {script.get('narration', '')}
            
            The total video duration should be {duration} seconds.
            """
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            # Parse the response
            scenes = self._parse_scenes(response, duration)
            
            return scenes
            
        except Exception as e:
            logger.error(f"Error generating scene breakdown: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scene breakdown generation failed: {str(e)}"
            )
    
    async def analyze_chat_message(
        self, 
        message: str, 
        video: Dict[str, Any], 
        scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a chat message from the user and determine the intent.
        
        Args:
            message: The user's message
            video: The video data
            scenes: The scenes data
            
        Returns:
            The analyzed intent with action details
        """
        try:
            # Create the system message
            system_message = """
            You are an AI video production assistant helping a user create and edit their video project. Your job is to:
            1. Understand the user's requests about their video project
            2. Provide helpful information about video creation
            3. Execute specific editing commands when requested
            4. Make suggestions to improve the video quality

            The user may ask you to:
            - Edit specific scenes (change descriptions, regenerate images, adjust durations)
            - Change the voice or music for the video
            - Provide explanations about the video creation process
            - Make creative suggestions for improving their video

            For editing commands, identify:
            1. The specific scene being referenced (if any)
            2. The exact change requested
            3. Any parameters or details for the change

            Format your thinking as JSON to help process the request:
            {
                "request_type": "edit_scene|change_voice|change_music|general_question|suggestion",
                "scene_id": "scene_1", // if applicable
                "action": "regenerate_image|change_description|adjust_duration|etc", // if applicable
                "parameters": {}, // any specific parameters for the action
                "response": "Your helpful response to the user"
            }

            Always be helpful, creative, and supportive of the user's vision for their video.
            """
            
            # Create the user message with context
            user_message = f"""
            User message: {message}
            
            Video context:
            Title: {video.get('title', 'Untitled')}
            Description: {video.get('description', '')}
            Style: {video.get('style', 'default')}
            
            Scenes:
            {json.dumps(scenes, indent=2)}
            """
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            # Parse the response
            try:
                intent = json.loads(response)
                
                # Ensure all required fields are present
                if "request_type" not in intent:
                    intent["request_type"] = "general_question"
                
                if "response" not in intent:
                    intent["response"] = "I understand your request. How else can I help with your video?"
                
                return intent
                
            except json.JSONDecodeError:
                # If the response is not valid JSON, create a default intent
                logger.warning(f"Failed to parse chat analysis as JSON: {response}")
                
                return {
                    "request_type": "general_question",
                    "response": response  # Use the raw response
                }
                
        except Exception as e:
            logger.error(f"Error analyzing chat message: {str(e)}")
            return {
                "request_type": "error",
                "response": f"I'm having trouble understanding your request. Could you please rephrase it?"
            }
    
    async def generate_contextual_response(
        self, 
        context_type: str, 
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a contextual response based on the current state of the video generation process.
        
        Args:
            context_type: The type of context (e.g., 'scene_breakdown_intro', 'generation_started')
            context_data: Optional data to provide context
            
        Returns:
            A contextual response
        """
        try:
            # Create the system message
            system_message = """
            You are an AI video production assistant helping a user create a video. Your job is to provide
            helpful, informative, and encouraging messages at different stages of the video creation process.
            
            Your responses should be:
            1. Conversational and friendly
            2. Informative about what's happening in the process
            3. Encouraging and supportive
            4. Specific to the current context
            
            Do not use generic responses. Tailor your message to the specific context and stage of the process.
            """
            
            # Create the user message based on the context type
            user_message = ""
            
            if context_type == "scene_breakdown_intro":
                prompt = context_data.get("prompt", "") if context_data else ""
                user_message = f"""
                The user has just submitted a prompt for video creation: "{prompt}"
                
                I'm about to analyze this prompt and break it down into scenes. Generate a friendly, informative
                message explaining what I'm doing and what the user can expect next.
                """
            
            elif context_type == "generation_started":
                user_message = """
                The user has just started the video generation process. Generate a friendly, informative message
                explaining what's happening and what the user can expect during the generation process.
                """
            
            elif context_type == "generation_completed":
                user_message = """
                The video generation has just completed successfully. Generate a friendly, celebratory message
                informing the user that their video is ready and suggesting what they might want to do next
                (view it, download it, or edit it further).
                """
            
            elif context_type == "scene_regenerated":
                scene_number = context_data.get("scene_number", "a") if context_data else "a"
                user_message = f"""
                Scene {scene_number} has just been regenerated with new content. Generate a friendly message
                informing the user that the scene has been updated and suggesting they review the changes.
                """
            
            elif context_type == "voice_changed":
                voice_type = context_data.get("voice_type", "new") if context_data else "new"
                user_message = f"""
                The voice for the video has been changed to a {voice_type} voice. Generate a friendly message
                informing the user about the voice change and how it might enhance their video.
                """
            
            elif context_type == "music_changed":
                music_style = context_data.get("style", "new") if context_data else "new"
                user_message = f"""
                The background music for the video has been changed to a {music_style} style. Generate a friendly
                message informing the user about the music change and how it might enhance their video.
                """
            
            else:
                # Default context
                user_message = """
                Generate a friendly, helpful message for a user who is creating a video with an AI assistant.
                """
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {str(e)}")
            
            # Return a fallback response
            if context_type == "scene_breakdown_intro":
                return "I'm analyzing your prompt to break it down into scenes. This will help us create a well-structured video."
            elif context_type == "generation_started":
                return "I'm starting the video generation process now. This will take a few minutes, but you can chat with me while you wait."
            elif context_type == "generation_completed":
                return "Your video has been generated successfully! You can now view it, download it, or edit it further."
            else:
                return "I'm here to help with your video project. Let me know what you'd like to do next."
    
    async def select_voice(self, video_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically select an appropriate voice based on video content.
        
        Args:
            video_content: The video content (prompt, style, scenes)
            
        Returns:
            Voice selection details including voice_id and reasoning
        """
        try:
            # Create the system message
            system_message = """
            You are an AI voice casting director. Your task is to select the most appropriate voice for a video based on its content.
            
            Analyze the video's content, style, tone, and target audience to determine:
            1. The gender of the voice (male, female, neutral)
            2. The age range (child, young adult, adult, senior)
            3. The tone (professional, casual, energetic, calm, etc.)
            4. Any accent or regional characteristics if relevant
            
            Format your response as a JSON object with the following structure:
            {
                "voice_id": "default_voice", // This will be replaced with actual voice IDs in production
                "gender": "male|female|neutral",
                "age": "child|young_adult|adult|senior",
                "tone": "professional|casual|energetic|calm|etc",
                "reasoning": "Brief explanation of why this voice type was selected"
            }
            """
            
            # Create the user message with context
            user_message = f"""
            Select an appropriate voice for the following video:
            
            Title: {video_content.get('title', 'Untitled')}
            Description: {video_content.get('description', '')}
            Style: {video_content.get('style', 'default')}
            Tone: {video_content.get('tone', 'neutral')}
            Target Audience: {video_content.get('target_audience', 'general')}
            
            Narration sample:
            {video_content.get('narration', '')[:300]}...
            """
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            # Parse the response
            try:
                voice_selection = json.loads(response)
                
                # Ensure all required fields are present
                if "voice_id" not in voice_selection:
                    voice_selection["voice_id"] = "default_voice"
                
                if "reasoning" not in voice_selection:
                    voice_selection["reasoning"] = "Selected based on video content and style."
                
                return voice_selection
                
            except json.JSONDecodeError:
                # If the response is not valid JSON, create a default selection
                logger.warning(f"Failed to parse voice selection as JSON: {response}")
                
                return {
                    "voice_id": "default_voice",
                    "gender": "neutral",
                    "age": "adult",
                    "tone": "professional",
                    "reasoning": "Default voice selected due to processing error."
                }
                
        except Exception as e:
            logger.error(f"Error selecting voice: {str(e)}")
            return {
                "voice_id": "default_voice",
                "reasoning": "Default voice selected due to an error in the selection process."
            }
    
    async def generate_image_prompts(self, scenes: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate image prompts for each scene.
        
        Args:
            scenes: The scenes
            
        Returns:
            A dictionary mapping scene IDs to image prompts
        """
        try:
            # Create the system message
            system_message = """
            You are a professional image prompt engineer. Your task is to create detailed image prompts for each scene in a video.
            Each image prompt should:
            1. Be detailed and descriptive
            2. Include the main elements that should appear in the image
            3. Specify the style, mood, and atmosphere
            4. Be optimized for text-to-image generation models
            
            Format your response as a JSON object mapping scene IDs to image prompts:
            {
                "scene_1": "Detailed image prompt for scene 1",
                "scene_2": "Detailed image prompt for scene 2"
            }
            """
            
            # Create the user message
            user_message = "Generate image prompts for the following scenes:\n\n"
            for scene in scenes:
                user_message += f"""
                Scene ID: {scene.get('id', '')}
                Title: {scene.get('title', '')}
                Description: {scene.get('description', '')}
                
                """
            
            # Call the OpenAI API
            response = await self._call_openai(system_message, user_message)
            
            # Parse the response
            image_prompts = self._parse_image_prompts(response, scenes)
            
            return image_prompts
            
        except Exception as e:
            logger.error(f"Error generating image prompts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image prompt generation failed: {str(e)}"
            )
    
    async def _call_openai(self, system_message: str, user_message: str) -> str:
        """
        Call the OpenAI API.
        
        Args:
            system_message: The system message
            user_message: The user message
            
        Returns:
            The response from the API
        """
        try:
            # Create the messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Call the API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    def _parse_response(self, response: str, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse the response from the OpenAI API.
        
        Args:
            response: The response from the API
            prompt: The original prompt
            style: The optional style
            
        Returns:
            The parsed script
        """
        try:
            # Try to parse the response as JSON
            script = json.loads(response)
            
            # Ensure all required fields are present
            if "title" not in script:
                script["title"] = f"Video about {prompt}"
            
            if "description" not in script:
                script["description"] = prompt
            
            if "style" not in script:
                script["style"] = style or "default"
            
            if "narration" not in script:
                script["narration"] = f"This is a video about {prompt}."
            
            return script
            
        except json.JSONDecodeError:
            # If the response is not valid JSON, create a default script
            logger.warning(f"Failed to parse OpenAI response as JSON: {response}")
            
            return {
                "title": f"Video about {prompt}",
                "description": prompt,
                "style": style or "default",
                "narration": response,  # Use the raw response as narration
                "tone": "neutral",
                "target_audience": "general",
                "key_points": [prompt]
            }
    
    def _parse_scenes(self, response: str, duration: int) -> List[Dict[str, Any]]:
        """
        Parse the scene breakdown from the OpenAI API.
        
        Args:
            response: The response from the API
            duration: The total duration in seconds
            
        Returns:
            The parsed scenes
        """
        try:
            # Try to parse the response as JSON
            scenes = json.loads(response)
            
            # Ensure the result is a list
            if not isinstance(scenes, list):
                raise ValueError("Expected a list of scenes")
            
            # Ensure all scenes have the required fields
            for i, scene in enumerate(scenes):
                if "id" not in scene:
                    scene["id"] = f"scene_{i+1}"
                
                if "title" not in scene:
                    scene["title"] = f"Scene {i+1}"
                
                if "description" not in scene:
                    scene["description"] = f"Scene {i+1} of the video"
                
                if "duration" not in scene:
                    # Distribute remaining duration evenly
                    scene["duration"] = duration // len(scenes)
                
                if "narration" not in scene:
                    scene["narration"] = f"Narration for scene {i+1}"
            
            # Adjust durations to match the total duration
            total_duration = sum(scene["duration"] for scene in scenes)
            if total_duration != duration:
                # Adjust the last scene to make the total match
                scenes[-1]["duration"] += (duration - total_duration)
            
            return scenes
            
        except (json.JSONDecodeError, ValueError) as e:
            # If the response is not valid JSON or not a list, create default scenes
            logger.warning(f"Failed to parse OpenAI scene breakdown: {response}")
            
            # Create default scenes
            num_scenes = max(1, duration // 10)
            scenes = []
            
            for i in range(num_scenes):
                scene_duration = duration // num_scenes
                if i == num_scenes - 1:
                    # Adjust the last scene to account for rounding
                    scene_duration = duration - (scene_duration * (num_scenes - 1))
                
                scene = {
                    "id": f"scene_{i+1}",
                    "title": f"Scene {i+1}",
                    "description": f"Scene {i+1} of the video",
                    "duration": scene_duration,
                    "narration": f"Narration for scene {i+1}"
                }
                scenes.append(scene)
            
            return scenes
    
    def _parse_image_prompts(self, response: str, scenes: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Parse the image prompts from the OpenAI API.
        
        Args:
            response: The response from the API
            scenes: The original scenes
            
        Returns:
            The parsed image prompts
        """
        try:
            # Try to parse the response as JSON
            image_prompts = json.loads(response)
            
            # Ensure the result is a dictionary
            if not isinstance(image_prompts, dict):
                raise ValueError("Expected a dictionary of image prompts")
            
            # Ensure all scenes have an image prompt
            for scene in scenes:
                scene_id = scene["id"]
                if scene_id not in image_prompts:
                    image_prompts[scene_id] = scene["description"]
            
            return image_prompts
            
        except (json.JSONDecodeError, ValueError):
            # If the response is not valid JSON or not a dictionary, create default prompts
            logger.warning(f"Failed to parse OpenAI image prompts: {response}")
            
            # Create default image prompts
            image_prompts = {}
            for scene in scenes:
                image_prompts[scene["id"]] = scene["description"]
            
            return image_prompts
