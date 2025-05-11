"""
Chat agent for the Pixora AI application.

This module provides a unified chat agent that handles the entire video generation process.
"""
import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from pydantic import BaseModel

from fastapi import Depends, WebSocket, WebSocketDisconnect

from app.models import ScriptBreakdown, Project, ProjectStatus, AssetGeneration, AssetGenerationStatus
from app.services.openai import OpenAIService
from app.services.fal_ai import FalAiService
from app.services.replicate import ReplicateService
from app.services.storage import StorageService
from app.services.dependencies import get_storage_service_dependency
from app.services.redis_client import RedisClient
from app.core.config import Settings, get_settings
from app.ai.tools import (
    # Script tools
    generate_script, refine_script,
    
    # Asset tools
    generate_character_images, generate_scene_image, generate_voice_over,
    generate_music, generate_assets_for_scene, generate_music_for_scenes,
    
    # Video tools
    create_scene_video_with_motion, normalize_duration, apply_transition,
    stitch_video, create_video_for_scene
)

# Set up logging
logger = logging.getLogger(__name__)


class Message(BaseModel):
    """
    A message in a conversation.
    """
    role: str
    content: str
    function_call: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    timestamp: Optional[datetime] = None


class ChatAction(BaseModel):
    """
    An action that can be taken by the user.
    """
    type: str
    label: str
    scene_id: Optional[str] = None
    style: Optional[str] = None
    prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """
    A response from the chat agent.
    """
    message: str
    task_id: Optional[str] = None
    video_url: Optional[str] = None
    actions: Optional[List[ChatAction]] = None
    function_call: Optional[Dict[str, Any]] = None
    function_response: Optional[Dict[str, Any]] = None


class ChatAgent:
    """
    A unified agent that handles the entire video generation process through chat.
    """
    
    def __init__(
        self,
        openai_service: OpenAIService = Depends(),
        fal_ai_service: FalAiService = Depends(),
        replicate_service: ReplicateService = Depends(),
        storage_service: StorageService = Depends(get_storage_service_dependency),
        redis_client: RedisClient = Depends(),
        settings: Settings = Depends(get_settings),
    ):
        """
        Initialize the chat agent.
        
        Args:
            openai_service: The OpenAI service
            fal_ai_service: The FAL AI service
            replicate_service: The Replicate service
            storage_service: The storage service
            redis_client: The Redis client
            settings: Application settings
        """
        self.openai_service = openai_service
        self.fal_ai_service = fal_ai_service
        self.replicate_service = replicate_service
        self.storage_service = storage_service
        self.redis_client = redis_client
        self.settings = settings
        self.conversations = {}  # Store conversations by user_id
        self.tools = self._get_tools()
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """
        Define the tools available to the agent.
        
        Returns:
            List of tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "generate_script",
                    "description": "Generate a script breakdown from a user prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The user's prompt describing the desired video"
                            },
                            "character_consistency": {
                                "type": "boolean",
                                "description": "Whether to maintain consistent characters across scenes"
                            },
                            "voice_character": {
                                "type": "string",
                                "description": "Optional URL to a voice sample to clone"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_character_images",
                    "description": "Generate character images from a prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_profile": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the character"
                                    },
                                    "image_prompt": {
                                        "type": "string",
                                        "description": "Detailed description for generating character images"
                                    }
                                },
                                "required": ["name", "image_prompt"]
                            },
                            "views": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["front", "side", "back", "three_quarter"]
                                },
                                "description": "List of views to generate"
                            }
                        },
                        "required": ["character_profile"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_scene_image",
                    "description": "Generate a scene image based on the video prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scene": {
                                "type": "object",
                                "properties": {
                                    "index": {
                                        "type": "integer",
                                        "description": "Index of the scene"
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "Title of the scene"
                                    },
                                    "video_prompt": {
                                        "type": "string",
                                        "description": "Detailed description for generating the scene image"
                                    }
                                },
                                "required": ["index", "title", "video_prompt"]
                            },
                            "style": {
                                "type": "string",
                                "enum": ["cinematic", "cartoon", "realistic", "artistic"],
                                "description": "Style of the image"
                            }
                        },
                        "required": ["scene"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_voice_over",
                    "description": "Generate text-to-speech audio from script text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script": {
                                "type": "string",
                                "description": "The script text to convert to speech"
                            },
                            "voice_character": {
                                "type": "string",
                                "description": "Optional URL to a voice sample to clone"
                            }
                        },
                        "required": ["script"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_music",
                    "description": "Generate background music based on prompt and duration",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of the desired music"
                            },
                            "duration": {
                                "type": "number",
                                "description": "Desired duration in seconds"
                            }
                        },
                        "required": ["prompt", "duration"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_scene_video_with_motion",
                    "description": "Create a video with motion from a scene image and audio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scene_image_path": {
                                "type": "string",
                                "description": "Path to the scene image"
                            },
                            "audio_path": {
                                "type": "string",
                                "description": "Path to the audio file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to save the output video"
                            },
                            "motion_type": {
                                "type": "string",
                                "enum": ["pan", "zoom", "tilt", "track"],
                                "description": "Type of motion to apply"
                            }
                        },
                        "required": ["scene_image_path", "audio_path", "output_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_project",
                    "description": "Create a new video project",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title of the project"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the project"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID of the user"
                            },
                            "style": {
                                "type": "string",
                                "enum": ["cinematic", "cartoon", "realistic", "artistic"],
                                "description": "Style of the video"
                            }
                        },
                        "required": ["title", "description", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_video",
                    "description": "Generate a complete video from a script",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {
                                "type": "string",
                                "description": "ID of the project"
                            },
                            "script_id": {
                                "type": "string",
                                "description": "ID of the script"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID of the user"
                            }
                        },
                        "required": ["project_id", "script_id", "user_id"]
                    }
                }
            }
        ]
    
    def _get_conversation(self, user_id: str) -> List[Message]:
        """
        Get the conversation history for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of messages in the conversation
        """
        if user_id not in self.conversations:
            # Initialize with system message
            self.conversations[user_id] = [
                Message(
                    role="system",
                    content="""You are Pixora AI, a video generation assistant. You help users create videos from text prompts.
                    
                    Your capabilities:
                    1. Generate a script breakdown from a user's prompt
                    2. Generate character images for consistent characters
                    3. Generate scene images based on video prompts
                    4. Generate voice-over audio from script text
                    5. Generate background music
                    6. Create scene videos with motion by generating a video from a static image
                    7. Stitch multiple scene videos into a final video
                    
                    IMPORTANT: Always create videos with motion using create_scene_video_with_motion. This creates more engaging videos by animating the static images. For each scene, you must provide a motion prompt that describes the desired camera movement and animation.
                    
                    When a user asks you to create a video:
                    1. First, analyze their request and generate a script breakdown
                    2. Present the breakdown to the user and ask for confirmation
                    3. Once confirmed, generate the necessary assets (characters, scenes, audio, music)
                    4. Create scene videos with motion and stitch them together
                    5. Provide the final video to the user
                    
                    For each scene, include a motion prompt that describes how the camera should move or how elements in the scene should animate. For example:
                    - "Gentle camera movement with a slow pan from left to right"
                    - "Subtle zoom in on the main subject with slight background animation"
                    - "Camera slowly tracking forward through the scene with gentle motion in the elements"
                    
                    Be conversational, helpful, and provide updates on the progress of video generation.
                    """,
                    timestamp=datetime.now()
                )
            ]
        
        return self.conversations[user_id]
    
    def _add_message(self, user_id: str, message: Dict[str, Any]):
        """
        Add a message to the conversation history.
        
        Args:
            user_id: ID of the user
            message: Message to add
        """
        if user_id not in self.conversations:
            self._get_conversation(user_id)
        
        # Create a Message object
        msg = Message(
            role=message["role"],
            content=message["content"],
            function_call=message.get("function_call"),
            name=message.get("name"),
            timestamp=message.get("timestamp", datetime.now())
        )
        
        self.conversations[user_id].append(msg)
    
    async def process_message(self, user_id: str, content: str, context: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """
        Process a message from the user and generate a response.
        
        Args:
            user_id: ID of the user
            content: Content of the message
            context: Optional context information
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message from user {user_id}: {content}")
        
        # Add user message to conversation
        self._add_message(user_id, {"role": "user", "content": content})
        
        # Get conversation history
        conversation = self._get_conversation(user_id)
        
        # Convert to OpenAI format
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                **({"function_call": msg.function_call} if msg.function_call else {}),
                **({"name": msg.name} if msg.name else {})
            }
            for msg in conversation
        ]
        
        logger.debug(f"Sending messages to OpenAI: {json.dumps(messages, default=str)}")
        
        # Call OpenAI API
        response = await self._call_openai(messages)
        
        logger.debug(f"Received response from OpenAI: {response}")
        
        # Process the response
        message = response.choices[0].message
        logger.debug(f"Message from OpenAI: {message}")
        
        assistant_message = Message(
            role="assistant",
            content=message.content or "",
            function_call=message.function_call.model_dump() if message.function_call else None,
            timestamp=datetime.now()
        )
        
        # Add assistant message to conversation
        self._add_message(user_id, {
            "role": "assistant",
            "content": assistant_message.content,
            "function_call": assistant_message.function_call,
            "timestamp": assistant_message.timestamp
        })
        
        # Check if tool calls are present (new API format)
        if hasattr(message, 'tool_calls') and message.tool_calls:
            logger.info(f"Tool calls detected: {len(message.tool_calls)} tool calls")
            
            # Process all tool calls
            function_responses = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Processing tool call: function={function_name}, args={function_args}")
                
                # Call the function
                function_response = await self._call_function(function_name, function_args)
                function_responses.append(function_response)
                
                # Add function response to conversation
                function_message = Message(
                    role="function",
                    name=function_name,
                    content=json.dumps(function_response, default=str),
                    timestamp=datetime.now()
                )
                self._add_message(user_id, {
                    "role": "function",
                    "name": function_name,
                    "content": function_message.content,
                    "timestamp": function_message.timestamp
                })
            
            # Generate a follow-up response
            follow_up_response = await self._call_openai(
                [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        **({"function_call": msg.function_call} if msg.function_call else {}),
                        **({"name": msg.name} if msg.name else {})
                    }
                    for msg in self._get_conversation(user_id)
                ]
            )
            
            follow_up_message = follow_up_response.choices[0].message
            follow_up = Message(
                role="assistant",
                content=follow_up_message.content or "",
                function_call=follow_up_message.function_call.model_dump() if follow_up_message.function_call else None,
                timestamp=datetime.now()
            )
            
            # Add follow-up message to conversation
            self._add_message(user_id, {
                "role": "assistant",
                "content": follow_up.content,
                "function_call": follow_up.function_call,
                "timestamp": follow_up.timestamp
            })
            
            # Extract task ID and video URL if available
            task_id = None
            video_url = None
            
            for response in function_responses:
                if isinstance(response, dict):
                    if "task_id" in response:
                        task_id = response["task_id"]
                    if "video_url" in response:
                        video_url = response["video_url"]
            
            # Extract actions from the follow-up message
            actions = self._extract_actions(follow_up_message)
            
            return ChatResponse(
                message=follow_up.content,
                task_id=task_id,
                video_url=video_url,
                actions=actions,
                function_call=follow_up.function_call,
                function_response=function_responses[0] if function_responses else None
            )
        # Check if function call is required (old API format)
        elif message.function_call:
            logger.info(f"Function call detected: {message.function_call}")
            
            # Extract function details
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            # Call the function
            function_response = await self._call_function(function_name, function_args)
            
            # Add function response to conversation
            function_message = Message(
                role="function",
                name=function_name,
                content=json.dumps(function_response, default=str),
                timestamp=datetime.now()
            )
            self._add_message(user_id, {
                "role": "function",
                "name": function_name,
                "content": function_message.content,
                "timestamp": function_message.timestamp
            })
            
            # Generate a follow-up response
            follow_up_response = await self._call_openai(
                [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        **({"function_call": msg.function_call} if msg.function_call else {}),
                        **({"name": msg.name} if msg.name else {})
                    }
                    for msg in self._get_conversation(user_id)
                ]
            )
            
            follow_up_message = follow_up_response.choices[0].message
            follow_up = Message(
                role="assistant",
                content=follow_up_message.content or "",
                function_call=follow_up_message.function_call.model_dump() if follow_up_message.function_call else None,
                timestamp=datetime.now()
            )
            
            # Add follow-up message to conversation
            self._add_message(user_id, {
                "role": "assistant",
                "content": follow_up.content,
                "function_call": follow_up.function_call,
                "timestamp": follow_up.timestamp
            })
            
            # Extract task ID and video URL if available
            task_id = None
            video_url = None
            
            if isinstance(function_response, dict):
                if "task_id" in function_response:
                    task_id = function_response["task_id"]
                if "video_url" in function_response:
                    video_url = function_response["video_url"]
            
            # Extract actions from the follow-up message
            actions = self._extract_actions(follow_up_message)
            
            return ChatResponse(
                message=follow_up.content,
                task_id=task_id,
                video_url=video_url,
                actions=actions,
                function_call=follow_up.function_call,
                function_response=function_response
            )
        
        # Extract actions from the message
        actions = self._extract_actions(message)
        
        return ChatResponse(
            message=assistant_message.content,
            actions=actions,
            function_call=None,
            function_response=None
        )
    
    async def handle_websocket_message(self, user_id: str, content: str, websocket: WebSocket):
        """
        Handle a message from a WebSocket connection.
        
        Args:
            user_id: ID of the user
            content: Content of the message
            websocket: WebSocket connection
        """
        # Process the message
        response = await self.process_message(user_id, content)
        
        # Send the initial response
        await websocket.send_json({
            "type": "agent_message",
            "content": response.message,
            "actions": response.actions
        })
        
        # If a task was created, start sending progress updates
        if response.task_id:
            # Start a background task to send progress updates
            asyncio.create_task(
                self._send_progress_updates(
                    websocket, 
                    user_id, 
                    response.task_id
                )
            )
    
    async def _send_progress_updates(self, websocket: WebSocket, user_id: str, task_id: str):
        """
        Send progress updates for a task via WebSocket.
        
        Args:
            websocket: WebSocket connection
            user_id: ID of the user
            task_id: ID of the task
        """
        while True:
            # Get task status from Redis
            status = await self.redis_client.get_json(f"task:{task_id}:progress")
            
            if not status:
                await asyncio.sleep(1)
                continue
            
            # Send progress update
            await websocket.send_json({
                "type": "progress_update",
                "task_id": task_id,
                "progress": status.get("progress", 0),
                "message": status.get("message", "Processing..."),
                "status": status.get("status", "processing")
            })
            
            # Check if task is complete
            if status.get("status") in ["completed", "error"]:
                # Get the result if available
                result = await self.redis_client.get_json(f"task:{task_id}:result")
                
                if result and "video_url" in result:
                    # Send video complete message
                    await websocket.send_json({
                        "type": "video_complete",
                        "task_id": task_id,
                        "video_url": result["video_url"]
                    })
                
                break
            
            await asyncio.sleep(2)
    
    async def _call_openai(self, messages: List[Dict[str, Any]]):
        """
        Call the OpenAI API with the given messages.
        
        Args:
            messages: List of messages to send to the API
            
        Returns:
            Response from the API
        """
        logger.debug("Calling OpenAI API")
        
        try:
            # Use the OpenAI service
            response = await self.openai_service.chat_completion(
                messages=messages,
                tools=self.tools
            )
            
            logger.debug(f"OpenAI API response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    async def _call_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a function with the given arguments.
        
        Args:
            function_name: Name of the function to call
            args: Arguments to pass to the function
            
        Returns:
            Result of the function call
        """
        logger.info(f"Calling function: {function_name} with args: {args}")
        
        # Map function names to actual functions
        function_map = {
            "generate_script": self._generate_script,
            "generate_character_images": self._generate_character_images,
            "generate_scene_image": self._generate_scene_image,
            "generate_voice_over": self._generate_voice_over,
            "generate_music": self._generate_music,
            "create_scene_video_with_motion": self._create_scene_video_with_motion,
            "create_project": self._create_project,
            "generate_video": self._generate_video
        }
        
        if function_name not in function_map:
            logger.error(f"Function {function_name} not found")
            return {"error": f"Function {function_name} not found"}
        
        # Call the function
        try:
            result = function_map[function_name](**args)
            
            # If the result is a coroutine, await it
            if asyncio.iscoroutine(result):
                logger.debug(f"Awaiting coroutine result for function: {function_name}")
                result = await result
            
            logger.info(f"Function result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling function {function_name}: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_script(self, prompt: str, character_consistency: bool = False, voice_character: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a script breakdown from a user prompt.
        
        Args:
            prompt: The user's prompt describing the desired video
            character_consistency: Whether to maintain consistent characters across scenes
            voice_character: Optional URL to a voice sample to clone
            
        Returns:
            A structured script breakdown
        """
        try:
            # Create a task ID
            task_id = f"script_{uuid.uuid4()}"
            
            # Generate the script
            script = await generate_script(
                prompt=prompt,
                character_consistency=character_consistency,
                voice_character=voice_character,
                user_id=None,
                openai_service=self.openai_service
            )
            
            # Set the task ID
            script.task_id = task_id
            
            # Store the script in Redis
            await self.redis_client.set_json(
                f"task:{task_id}:script",
                script.dict()
            )
            
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 100,
                    "message": "Script generation complete",
                    "status": "completed"
                }
            )
            
            logger.info(f"Generated script with {len(script.clips)} scenes")
            
            # Return the script data
            return {
                "task_id": task_id,
                "script": script.dict()
            }
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise
    
    async def _generate_character_images(self, character_profile: Dict[str, Any], views: List[str] = ["front"]) -> Dict[str, Any]:
        """
        Generate character images from a character profile.
        
        Args:
            character_profile: The character profile
            views: List of views to generate
            
        Returns:
            Dictionary with image URLs
        """
        try:
            # Convert the character profile to a CharacterProfile object
            from app.models import CharacterProfile
            profile = CharacterProfile(**character_profile)
            
            # Generate the character images
            image_urls = await generate_character_images(
                character_profile=profile,
                views=views,
                storage_service=self.storage_service,
                openai_service=self.openai_service
            )
            
            logger.info(f"Generated character images for {profile.name}")
            
            # Return the image URLs
            return {
                "character_name": profile.name,
                "image_urls": image_urls
            }
        except Exception as e:
            logger.error(f"Error generating character images: {str(e)}")
            raise
    
    async def _generate_scene_image(self, scene: Dict[str, Any], style: str = "cinematic") -> Dict[str, Any]:
        """
        Generate a scene image based on a scene description.
        
        Args:
            scene: The scene
            style: The style of the image
            
        Returns:
            Dictionary with the image URL
        """
        try:
            # Convert the scene to a Scene object
            from app.models import Scene
            scene_obj = Scene(**scene)
            
            # Generate the scene image
            image_url = await generate_scene_image(
                scene=scene_obj,
                style=style,
                storage_service=self.storage_service,
                openai_service=self.openai_service
            )
            
            logger.info(f"Generated scene image for scene {scene_obj.index}")
            
            # Return the image URL
            return {
                "scene_index": scene_obj.index,
                "scene_title": scene_obj.title,
                "image_url": image_url
            }
        except Exception as e:
            logger.error(f"Error generating scene image: {str(e)}")
            raise
    
    async def _generate_voice_over(self, script: str, voice_character: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a voice over from a script.
        
        Args:
            script: The script text
            voice_character: Optional URL to a voice sample to clone
            
        Returns:
            Dictionary with the audio URL and duration
        """
        try:
            # Generate the voice over
            audio_url, duration = await generate_voice_over(
                script=script,
                voice_character=voice_character,
                storage_service=self.storage_service,
                replicate_service=self.replicate_service
            )
            
            logger.info(f"Generated voice over with duration: {duration:.2f} seconds")
            
            # Return the audio URL and duration
            return {
                "audio_url": audio_url,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Error generating voice over: {str(e)}")
            raise
    
    async def _generate_music(self, prompt: str, duration: float) -> Dict[str, Any]:
        """
        Generate background music based on a prompt and duration.
        
        Args:
            prompt: Description of the desired music
            duration: Desired duration in seconds
            
        Returns:
            Dictionary with the music URL
        """
        try:
            # Generate the music
            music_url = await generate_music(
                prompt=prompt,
                duration=duration,
                storage_service=self.storage_service,
                replicate_service=self.replicate_service
            )
            
            logger.info(f"Generated music with prompt: {prompt}")
            
            # Return the music URL
            return {
                "music_url": music_url
            }
        except Exception as e:
            logger.error(f"Error generating music: {str(e)}")
            raise
    
    async def _create_scene_video_with_motion(
        self,
        scene_image_path: str,
        audio_path: str,
        output_path: str,
        motion_type: str = "pan"
    ) -> Dict[str, Any]:
        """
        Create a video with motion from a scene image and audio.
        
        Args:
            scene_image_path: Path to the scene image
            audio_path: Path to the audio file
            output_path: Path to save the output video
            motion_type: Type of motion to apply
            
        Returns:
            Dictionary with the video path
        """
        try:
            # Create the video with motion
            video_path = await create_scene_video_with_motion(
                scene_image_path=scene_image_path,
                audio_path=audio_path,
                output_path=output_path,
                motion_type=motion_type,
                fal_ai_service=self.fal_ai_service
            )
            
            logger.info(f"Created video with motion for scene image: {scene_image_path}")
            
            # Return the video path
            return {
                "video_path": video_path
            }
        except Exception as e:
            logger.error(f"Error creating video with motion: {str(e)}")
            raise
    
    async def _create_project(
        self,
        title: str,
        description: str,
        user_id: str,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new video project.
        
        Args:
            title: Title of the project
            description: Description of the project
            user_id: ID of the user
            style: Style of the video
            
        Returns:
            Dictionary with the project ID
        """
        try:
            # Create a project ID
            project_id = str(uuid.uuid4())
            
            # Create the project
            project = Project(
                id=project_id,
                title=title,
                description=description,
                user_id=user_id,
                style=style,
                status=ProjectStatus.CREATED,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store the project in Redis
            await self.redis_client.set_json(
                f"project:{project_id}",
                project.dict()
            )
            
            logger.info(f"Created project: {project_id}")
            
            # Return the project ID
            return {
                "project_id": project_id
            }
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    async def _generate_video(
        self,
        project_id: str,
        script_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate a complete video from a script.
        
        Args:
            project_id: ID of the project
            script_id: ID of the script
            user_id: ID of the user
            
        Returns:
            Dictionary with the task ID
        """
        try:
            # Create a task ID
            task_id = f"video_{uuid.uuid4()}"
            
            # Get the project
            project_data = await self.redis_client.get_json(f"project:{project_id}")
            if not project_data:
                raise ValueError(f"Project not found: {project_id}")
            
            project = Project(**project_data)
            
            # Set the script ID
            project.script_id = script_id
            
            # Update the project in Redis
            await self.redis_client.set_json(
                f"project:{project_id}",
                project.dict()
            )
            
            # Create a background task to generate the video
            asyncio.create_task(
                self._generate_video_task(
                    task_id=task_id,
                    project_id=project_id,
                    user_id=user_id
                )
            )
            
            logger.info(f"Started video generation task: {task_id}")
            
            # Return the task ID
            return {
                "task_id": task_id
            }
        except Exception as e:
            logger.error(f"Error starting video generation: {str(e)}")
            raise
    
    async def _generate_video_task(
        self,
        task_id: str,
        project_id: str,
        user_id: str
    ):
        """
        Background task to generate a video.
        
        Args:
            task_id: ID of the task
            project_id: ID of the project
            user_id: ID of the user
        """
        try:
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 0,
                    "message": "Starting video generation",
                    "status": "processing"
                }
            )
            
            # Get the project
            project_data = await self.redis_client.get_json(f"project:{project_id}")
            if not project_data:
                raise ValueError(f"Project not found: {project_id}")
            
            project = Project(**project_data)
            
            # Get the script
            script_data = await self.redis_client.get_json(f"task:{project.script_id}:script")
            if not script_data:
                raise ValueError(f"Script not found: {project.script_id}")
            
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 10,
                    "message": "Generating assets",
                    "status": "processing"
                }
            )
            
            # Create a video agent
            from app.ai.agents.video_agent import VideoAgent
            video_agent = VideoAgent(
                openai_service=self.openai_service,
                fal_ai_service=self.fal_ai_service,
                replicate_service=self.replicate_service,
                storage_service=self.storage_service,
                redis_client=self.redis_client
            )
            
            # Define a progress callback
            async def progress_callback(progress: int, message: Optional[str] = None):
                # Scale progress to 0-100%
                scaled_progress = 10 + (progress * 0.8)  # 10% to 90%
                
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": scaled_progress,
                        "message": message or "Processing...",
                        "status": "processing"
                    }
                )
            
            # Generate assets
            await video_agent.generate_assets(
                project=project,
                progress_callback=progress_callback
            )
            
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 90,
                    "message": "Creating video",
                    "status": "processing"
                }
            )
            
            # Create the video
            video_url = await video_agent.create_video(
                project=project,
                progress_callback=progress_callback
            )
            
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 100,
                    "message": "Video generation complete",
                    "status": "completed"
                }
            )
            
            # Store the result
            await self.redis_client.set_json(
                f"task:{task_id}:result",
                {
                    "video_url": video_url
                }
            )
            
            logger.info(f"Completed video generation task: {task_id}")
        except Exception as e:
            logger.error(f"Error in video generation task: {str(e)}")
            
            # Update the task progress
            await self.redis_client.set_json(
                f"task:{task_id}:progress",
                {
                    "progress": 100,
                    "message": f"Error: {str(e)}",
                    "status": "error"
                }
            )
    
    def _extract_actions(self, message) -> Optional[List[ChatAction]]:
        """
        Extract actions from a message.
        
        Args:
            message: The message
            
        Returns:
            List of actions, or None if no actions are found
        """
        # Check if the message has content
        if not message.content:
            return None
        
        actions = []
        
        # Look for action patterns in the message
        if "regenerate" in message.content.lower() and "scene" in message.content.lower():
            # Extract scene ID
            import re
            scene_match = re.search(r"scene\s+(\d+)", message.content.lower())
            if scene_match:
                scene_id = scene_match.group(1)
                actions.append(
                    ChatAction(
                        type="regenerate_image",
                        label=f"Regenerate scene {scene_id}",
                        scene_id=scene_id
                    )
                )
        
        if "change voice" in message.content.lower() or "different voice" in message.content.lower():
            actions.append(
                ChatAction(
                    type="change_voice",
                    label="Change voice"
                )
            )
        
        if "change music" in message.content.lower() or "different music" in message.content.lower():
            # Extract music style
            import re
            style_match = re.search(r"to\s+(\w+)\s+style", message.content.lower())
            style = style_match.group(1) if style_match else "different"
            
            actions.append(
                ChatAction(
                    type="change_music",
                    label=f"Change to {style} music",
                    style=style
                )
            )
        
        if "generate video" in message.content.lower() or "create video" in message.content.lower():
            # Extract prompt
            import re
            prompt_match = re.search(r"video\s+about\s+(.+?)[\.\?]", message.content.lower())
            prompt = prompt_match.group(1) if prompt_match else None
            
            actions.append(
                ChatAction(
                    type="generate_video",
                    label="Generate video",
                    prompt=prompt
                )
            )
        
        return actions if actions else None
