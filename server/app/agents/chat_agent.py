"""
Chat Agent for Pixora AI Video Creation Platform
"""
import os
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import openai
from datetime import datetime

# Import agents
from .script_agent import script_agent
from .asset_agent import asset_agent
from .video_agent import video_agent

# Import telemetry
from ..utils.telemetry import traced, log_event

# Import services
from ..services.supabase import supabase_service
from ..utils.file_utils import get_task_storage_path_from_id, save_script

# Configure logging
logger = logging.getLogger(__name__)

class Message(BaseModel):
    """
    Message model for the chat agent.
    """
    role: str
    content: str
    function_call: Optional[Dict[str, Any]] = None
    name: Optional[str] = None

class ChatAgent:
    """
    A unified agent that handles the entire video generation process through chat.
    """
    
    def __init__(self):
        """Initialize the chat agent."""
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tools = self._get_tools()
        self.context_store = {}  # For temporary context during a session
        
        logger.info("Chat agent initialized")
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """
        Define the tools available to the agent.
        
        Returns:
            List[Dict[str, Any]]: List of tool definitions
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
                            "duration": {
                                "type": "number",
                                "description": "Desired duration of the video in seconds"
                            },
                            "aspect_ratio": {
                                "type": "string",
                                "description": "Aspect ratio of the video (e.g., '16:9', '9:16', '1:1')"
                            },
                            "style": {
                                "type": "string",
                                "description": "Style of the video (e.g., 'cinematic', 'cartoon', 'realistic')"
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
                            "image_prompt": {
                                "type": "string",
                                "description": "Detailed description for generating character images"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "character_id": {
                                "type": "string",
                                "description": "ID of the character"
                            }
                        },
                        "required": ["image_prompt", "task_id", "character_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_scene_images",
                    "description": "Generate a scene image based on the video prompt and character references",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "video_prompt": {
                                "type": "string",
                                "description": "Detailed description for generating the scene image"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "scene_index": {
                                "type": "integer",
                                "description": "Index of the scene"
                            },
                            "character_references": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Optional list of URLs to character images to include in the scene"
                            }
                        },
                        "required": ["video_prompt", "task_id", "scene_index"]
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
                            "text": {
                                "type": "string",
                                "description": "The script text to convert to speech"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "scene_index": {
                                "type": "integer",
                                "description": "Index of the scene"
                            },
                            "voice_sample": {
                                "type": "string",
                                "description": "Optional URL to a voice sample to clone"
                            }
                        },
                        "required": ["text", "task_id", "scene_index"]
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
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "duration": {
                                "type": "number",
                                "description": "Desired duration in seconds (1-30)"
                            },
                            "scene_indexes": {
                                "type": "array",
                                "items": {
                                    "type": "integer"
                                },
                                "description": "List of scene indexes that use this music"
                            }
                        },
                        "required": ["prompt", "task_id", "duration", "scene_indexes"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_scene_video_with_motion",
                    "description": "Create an engaging video with motion and animation from a scene image. This creates more visually interesting videos than the static image method.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "scene_index": {
                                "type": "integer",
                                "description": "Index of the scene"
                            },
                            "scene_image": {
                                "type": "string",
                                "description": "URL to the scene image (must be a hosted URL)"
                            },
                            "audio_url": {
                                "type": "string",
                                "description": "URL to the audio file"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Text description of desired camera movements and animations (e.g., 'slow pan from left to right with subtle leaf movement')"
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration of the video in seconds"
                            }
                        },
                        "required": ["task_id", "scene_index", "scene_image", "audio_url", "prompt", "duration"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "stitch_video",
                    "description": "Stitch multiple scene videos with audio and transitions into a final video",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task"
                            },
                            "scene_videos": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "List of URLs to scene videos"
                            },
                            "transitions": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "List of transition types"
                            },
                            "music_url": {
                                "type": "string",
                                "description": "Optional URL to background music"
                            }
                        },
                        "required": ["task_id", "scene_videos", "transitions"]
                    }
                }
            }
        ]
    
    async def get_conversation(self, user_id: str, video_id: Optional[str] = None) -> List[Message]:
        """
        Get the conversation history for a user.
        
        Args:
            user_id: ID of the user
            video_id: Optional ID of the associated video
            
        Returns:
            List[Message]: List of messages in the conversation
        """
        # Check if we have a conversation ID in the context store
        conversation_id = None
        if user_id in self.context_store and "conversation_id" in self.context_store[user_id]:
            conversation_id = self.context_store[user_id]["conversation_id"]
        
        # If we have a conversation ID, get the messages from Supabase
        if conversation_id:
            # Get the messages from Supabase
            db_messages = supabase_service.get_conversation_messages(conversation_id)
            
            # Convert to Message objects
            messages = []
            for msg in db_messages:
                function_call = None
                if msg.get("function_call"):
                    try:
                        function_call = json.loads(msg["function_call"])
                    except:
                        pass
                
                messages.append(Message(
                    role=msg["role"],
                    content=msg["content"],
                    function_call=function_call,
                    name=msg.get("name")
                ))
            
            # If we have messages, return them
            if messages:
                return messages
        
        # If we don't have a conversation ID or messages, create a new conversation
        # Initialize with system message
        system_message = Message(
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
            
            CRITICAL: The video generation API can only generate videos of 5 or 10 seconds. This is a hard constraint that must be respected in the script generation phase. Each scene must be either 5 or 10 seconds long.
            
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
            
            IMPORTANT: Always maintain context of the conversation. When the user refers to previously generated content or scenes, use that context in your response. If the user asks to modify a specific scene, refer to the scene details you've previously generated and incorporate their changes.
            
            Be conversational, helpful, and provide updates on the progress of video generation.
            """
        )
        
        # Create a new conversation in Supabase
        metadata = {}
        if video_id:
            metadata["video_id"] = video_id
        
        conversation_id = supabase_service.create_conversation(user_id, video_id, metadata)
        
        # Store the conversation ID in the context store
        if user_id not in self.context_store:
            self.context_store[user_id] = {"conversation_id": conversation_id}
        else:
            self.context_store[user_id]["conversation_id"] = conversation_id
        
        # Add the system message to the conversation
        await self.add_message(user_id, system_message, video_id)
        
        # Return the messages
        return [system_message]
    
    async def add_message(self, user_id: str, message: Message, video_id: Optional[str] = None):
        """
        Add a message to the conversation history.
        
        Args:
            user_id: ID of the user
            message: Message to add
            video_id: Optional ID of the associated video
        """
        # Get the conversation ID from the context store
        if user_id not in self.context_store or "conversation_id" not in self.context_store[user_id]:
            # Create a new conversation
            await self.get_conversation(user_id, video_id)
        
        conversation_id = self.context_store[user_id]["conversation_id"]
        
        # Add the message to the conversation
        supabase_service.add_message(
            conversation_id,
            message.role,
            message.content,
            message.name,
            message.function_call
        )
    
    async def process_message(self, user_id: str, content: str, task_id: Optional[str] = None, video_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a message from the user and generate a response.
        
        Args:
            user_id: ID of the user
            content: Content of the message
            task_id: Optional ID of the task
            video_id: Optional ID of the associated video
            
        Returns:
            Dict[str, Any]: Response from the agent
        """
        logger.info(f"Processing message from user {user_id}: {content[:50]}...")
        
        # Create a task ID if not provided
        if not task_id:
            task_id = str(uuid.uuid4())
            logger.info(f"Created new task ID: {task_id}")
        
        # Add user message to conversation
        await self.add_message(user_id, Message(role="user", content=content), video_id)
        
        # Get conversation history
        conversation = await self.get_conversation(user_id, video_id)
        
        # Convert to OpenAI format
        messages = []
        for msg in conversation:
            message_dict = {
                "role": msg.role,
                "content": msg.content or ""
            }
            if msg.function_call:
                message_dict["function_call"] = msg.function_call
            if msg.name:
                message_dict["name"] = msg.name
            messages.append(message_dict)
        
        logger.debug(f"Sending {len(messages)} messages to OpenAI")
        
        # Call OpenAI API
        response = await self._call_openai(messages)
        
        logger.debug(f"Received response from OpenAI")
        
        # Process the response
        message = response.choices[0].message
        
        assistant_message = Message(
            role="assistant",
            content=message.content or "",
            function_call=message.function_call.model_dump() if message.function_call else None,
        )
        
        # Add assistant message to conversation
        await self.add_message(user_id, assistant_message, video_id)
        
        # Initialize function_response to None
        function_response = None
        
        # Check if tool calls are present (new API format)
        if hasattr(message, 'tool_calls') and message.tool_calls:
            logger.info(f"Tool calls detected: {len(message.tool_calls)} tool calls")
            
            # Process all tool calls
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Processing tool call: function={function_name}")
                
                # Add task_id to function args if not present
                if "task_id" not in function_args and function_name != "generate_script":
                    function_args["task_id"] = task_id
                
                # Call the function
                function_response = await self._call_function(function_name, function_args)
                
                # Add function response to conversation
                function_message = Message(
                    role="function",
                    name=function_name,
                    content=json.dumps(function_response)
                )
                await self.add_message(user_id, function_message, video_id)
            
            # Get updated conversation history
            updated_conversation = await self.get_conversation(user_id, video_id)
            
            # Convert to OpenAI format
            updated_messages = []
            for msg in updated_conversation:
                message_dict = {
                    "role": msg.role,
                    "content": msg.content or ""
                }
                if msg.function_call:
                    message_dict["function_call"] = msg.function_call
                if msg.name:
                    message_dict["name"] = msg.name
                updated_messages.append(message_dict)
            
            # Generate a follow-up response
            follow_up_response = await self._call_openai(updated_messages)
            
            follow_up_message = follow_up_response.choices[0].message
            follow_up = Message(
                role="assistant",
                content=follow_up_message.content or "",
                function_call=follow_up_message.function_call.model_dump() if follow_up_message.function_call else None,
            )
            
            # Add follow-up message to conversation
            await self.add_message(user_id, follow_up, video_id)
            
            return {
                "type": "agent_message",
                "content": follow_up.content,
                "function_call": follow_up.function_call,
                "function_response": function_response,
                "task_id": task_id
            }
        # Check if function call is required (old API format)
        elif message.function_call:
            logger.info(f"Function call detected: {message.function_call.name}")
            
            # Extract function details
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments or "{}")
            
            # Add task_id to function args if not present
            if "task_id" not in function_args and function_name != "generate_script":
                function_args["task_id"] = task_id
            
            # Call the function
            function_response = await self._call_function(function_name, function_args)
            
            # Add function response to conversation
            function_message = Message(
                role="function",
                name=function_name,
                content=json.dumps(function_response)
            )
            await self.add_message(user_id, function_message, video_id)
            
            # Get updated conversation history
            updated_conversation = await self.get_conversation(user_id, video_id)
            
            # Convert to OpenAI format
            updated_messages = []
            for msg in updated_conversation:
                message_dict = {
                    "role": msg.role,
                    "content": msg.content or ""
                }
                if msg.function_call:
                    message_dict["function_call"] = msg.function_call
                if msg.name:
                    message_dict["name"] = msg.name
                updated_messages.append(message_dict)
            
            # Generate a follow-up response
            follow_up_response = await self._call_openai(updated_messages)
            
            follow_up_message = follow_up_response.choices[0].message
            follow_up = Message(
                role="assistant",
                content=follow_up_message.content or "",
                function_call=follow_up_message.function_call.model_dump() if follow_up_message.function_call else None,
            )
            
            # Add follow-up message to conversation
            await self.add_message(user_id, follow_up, video_id)
            
            return {
                "type": "agent_message",
                "content": follow_up.content,
                "function_call": follow_up.function_call,
                "function_response": function_response,
                "task_id": task_id
            }
        
        return {
            "type": "agent_message",
            "content": assistant_message.content,
            "function_call": None,
            "function_response": None,
            "task_id": task_id
        }
    
    async def _call_openai(self, messages: List[Dict[str, Any]]):
        """
        Call the OpenAI API with the given messages.
        
        Args:
            messages: List of messages to send to the API
            
        Returns:
            Response from the API
        """
        logger.debug("Creating AsyncOpenAI client")
        
        # Create an async client
        async_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.debug(f"Calling OpenAI API with model: gpt-4o, messages count: {len(messages)}")
        
        try:
            # Use the async client
            response = await async_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools
            )
            
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    @traced("call_function")
    async def _call_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a function with the given arguments.
        
        Args:
            function_name: Name of the function to call
            args: Arguments to pass to the function
            
        Returns:
            Result of the function call
        """
        logger.info(f"Calling function: {function_name}")
        
        # Create context for the agent
        context = {}
        
        # Add task_id to context
        if "task_id" in args:
            context["task_id"] = args["task_id"]
        
        # Map function names to agent methods
        try:
            if function_name == "generate_script":
                # Use the script agent
                result = await script_agent.create_script(
                    prompt=args["prompt"],
                    character_consistency=args.get("character_consistency", False),
                    duration=args.get("duration"),
                    aspect_ratio=args.get("aspect_ratio"),
                    style=args.get("style")
                )
                
                # Store the script in context for future use
                if "task_id" in result:
                    context["task_id"] = result["task_id"]
                context["script"] = result
                
                return result
            elif function_name == "generate_character_images":
                # Use the asset agent
                result = await asset_agent.generate_character_assets(
                    task_id=args["task_id"],
                    character_profiles=[{
                        "id": args["character_id"],
                        "name": args["character_id"],
                        "image_prompt": args["image_prompt"]
                    }]
                )
                
                # Store the character images in context for future use
                if "characters" in result and args["character_id"] in result["characters"]:
                    return result["characters"][args["character_id"]]
                
                return result
            elif function_name == "generate_scene_images":
                # Use the asset agent
                result = await asset_agent.generate_scene_assets(
                    task_id=args["task_id"],
                    scenes=[{
                        "index": args["scene_index"],
                        "video_prompt": args["video_prompt"],
                        "characters": args.get("character_references", [])
                    }]
                )
                
                # Store the scene images in context for future use
                if "scenes" in result and str(args["scene_index"]) in result["scenes"]:
                    return result["scenes"][str(args["scene_index"])]
                
                return result
            elif function_name == "generate_voice_over":
                # Use the asset agent
                result = await asset_agent.generate_audio_assets(
                    task_id=args["task_id"],
                    scenes=[{
                        "index": args["scene_index"],
                        "script": args["text"]
                    }],
                    voice_sample=args.get("voice_sample")
                )
                
                # Store the audio in context for future use
                if "audio" in result and str(args["scene_index"]) in result["audio"]:
                    return result["audio"][str(args["scene_index"])]
                
                return result
            elif function_name == "generate_music":
                # Use the asset agent
                result = await asset_agent.generate_music_assets(
                    task_id=args["task_id"],
                    music_specs=[{
                        "prompt": args["prompt"],
                        "scene_indexes": args["scene_indexes"],
                        "duration": args["duration"]
                    }]
                )
                
                # Store the music in context for future use
                if "music" in result and len(result["music"]) > 0:
                    return result["music"][0]
                
                return result
            elif function_name == "create_scene_video_with_motion":
                # Use the video agent
                result = await video_agent.create_scene_videos(
                    task_id=args["task_id"],
                    scenes=[{
                        "index": args["scene_index"],
                        "video_prompt": args["prompt"],
                        "duration": args["duration"]
                    }],
                    scene_images={
                        str(args["scene_index"]): {"url": args["scene_image"]}
                    },
                    scene_audio={
                        str(args["scene_index"]): {"url": args["audio_url"]}
                    }
                )
                
                # Store the videos in context for future use
                if "videos" in result and str(args["scene_index"]) in result["videos"]:
                    return result["videos"][str(args["scene_index"])]
                
                return result
            elif function_name == "stitch_video":
                # Use the video agent
                result = await video_agent.stitch_final_video(
                    task_id=args["task_id"],
                    scenes=[{"index": i} for i in range(len(args["scene_videos"]))],
                    scene_videos={
                        str(i): {"url": url} for i, url in enumerate(args["scene_videos"])
                    },
                    transitions=args.get("transitions", []),
                    music=[{"url": args["music_url"]}] if "music_url" in args else None
                )
                
                return result
            else:
                logger.warning(f"Function {function_name} not found")
                return {"error": f"Function {function_name} not found"}
        except Exception as e:
            logger.error(f"Error calling function {function_name}: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_script(self, prompt: str, character_consistency: bool = False, 
                              duration: Optional[float] = None, aspect_ratio: Optional[str] = None,
                              style: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a script breakdown from a user prompt.
        
        Args:
            prompt: The user's prompt describing the desired video
            character_consistency: Whether to maintain consistent characters across scenes
            duration: Optional desired duration of the video in seconds
            aspect_ratio: Optional aspect ratio of the video
            style: Optional style of the video
            
        Returns:
            Dict[str, Any]: A structured script breakdown
        """
        try:
            # Create an async client
            async_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Create the system message
            system_message = """You are a professional video script generator that creates detailed breakdowns for video production.
            
            Your task is to create a detailed video script breakdown with:
            1. A rewritten, enhanced version of the user's prompt
            2. A series of scenes with titles, scripts, and visual descriptions
            3. Appropriate transitions between scenes
            4. Music suggestions that match the mood of each scene
            5. Character profiles if character consistency is requested
            
            CRITICAL: The video_prompt for each scene MUST include motion descriptions for video generation. All scenes will be created as motion videos, not static images. For each scene, you must include:
            
            1. Visual elements to include in the scene
            2. Camera movements (pan, tilt, zoom, tracking)
            3. Dynamic elements that should have motion (e.g., leaves blowing, water flowing)
            
            CRITICAL: The video generation API can only generate videos of 5 or 10 seconds. This is a hard constraint that must be respected. Each scene must be either 5 or 10 seconds long.
            
            Examples of good motion prompts:
            - "A forest scene with leaves gently blowing in the wind, camera slowly panning from left to right"
            - "A cityscape at sunset with cars moving on streets below, camera gradually zooming out to reveal the skyline"
            - "A close-up of a character's face with subtle expressions changing, camera slowly pushing in"
            
            Your output must be a valid JSON object matching the following structure:
            {
              "user_prompt": "Original user prompt",
              "rewritten_prompt": "Enhanced, detailed prompt",
              "voice_character": null,
              "character_consistency": true/false,
              "music": [
                {
                  "prompt": "Description of music for specific scenes",
                  "scene_indexes": [list of scene indexes]
                }
              ],
              "character_profiles": [
                {
                  "name": "Character name",
                  "image_prompt": "Detailed description for generating character images"
                }
              ],
              "clips": [
                {
                  "scene": {
                    "index": 1,
                    "title": "Scene title",
                    "script": "Scene script/narration",
                    "video_prompt": "Visual description with camera movement and dynamic elements",
                    "transition": "fade/slide_left/zoom_out/etc.",
                    "duration": 5 or 10
                  }
                }
              ],
              "expected_duration": estimated duration in seconds
            }
            """
            
            # Create the user message
            user_message = f"Create a video script about: {prompt}."
            
            # Add optional parameters to the user message
            if character_consistency:
                user_message += f" Character consistency: {character_consistency}."
            if duration:
                user_message += f" Duration: {duration} seconds."
            if aspect_ratio:
                user_message += f" Aspect ratio: {aspect_ratio}."
            if style:
                user_message += f" Style: {style}."
            
            # Call OpenAI to generate the script
            response = await async_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            script_data = json.loads(response.choices[0].message.content)
            
            # Add task_id
            task_id = str(uuid.uuid4())
            script_data["task_id"] = task_id
            
            # Get the task storage path
            task_storage_path = get_task_storage_path_from_id(task_id)
            
            # Save the script to Supabase storage
            save_script(task_storage_path, script_data)
            
            # Create a task in the database if Supabase is configured
            try:
                if hasattr(supabase_service, 'client') and supabase_service.client:
                    supabase_service.create_task(user_id="user_1", task_id=task_id, prompt=prompt)
                    logger.info(f"Created task in database: {task_id}")
            except Exception as e:
                logger.warning(f"Failed to create task in database: {str(e)}")
                # Continue execution even if database operations fail
            
            return script_data
        except Exception as e:
            # Log the error
            logger.error(f"Error generating script: {str(e)}")
            
            # Raise the error
            raise

# Create a global instance of the chat agent
chat_agent = ChatAgent()
