"""
Agent definitions for Pixora AI using OpenAI Agents SDK.

This module defines the agents used by Pixora AI for video generation
using the OpenAI Agents SDK.
"""
import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union

from agents import Agent, function_tool, RunContextWrapper
from pydantic import BaseModel, Field

from app.ai.sdk.context import TaskContext
from app.services.redis_client import RedisClient
from app.services.openai.service import OpenAIService
from app.services.replicate.base import ReplicateService
from app.services.fal_ai.base import FalAiService
from app.services.storage.manager import StorageManager

# Set up logging
logger = logging.getLogger(__name__)

# Service singleton container
_services = {
    "redis_client": None,
    "openai_service": None,
    "replicate_service": None,
    "fal_ai_service": None,
    "storage_manager": None
}

def get_services():
    """
    Get or initialize services.
    
    Returns:
        Dictionary of service instances
    """
    if _services["redis_client"] is None:
        from app.core.config import get_settings
        
        # Get settings
        settings = get_settings()
        
        # Initialize services with settings
        _services["redis_client"] = RedisClient(settings)
        _services["openai_service"] = OpenAIService(settings)
        _services["replicate_service"] = ReplicateService(settings)
        _services["fal_ai_service"] = FalAiService(settings)
        _services["storage_manager"] = StorageManager(settings)
    
    return _services


# System instructions for the video agent
VIDEO_AGENT_INSTRUCTIONS = """
You are an AI video generation assistant for Pixora AI. Your job is to help users create professional videos from text prompts.

When a user provides a prompt, you should:
1. Analyze the prompt to understand what kind of video the user wants
2. Break down the video creation process into steps
3. Use the appropriate tools to generate each component of the video
4. Provide clear explanations of what you're doing at each step
5. Track progress and provide updates to the user

The video creation process follows these stages:
1. Scene Breakdown: Analyze the prompt and create a detailed breakdown of scenes
   - Identify key themes, style preferences, and duration requirements
   - Create a logical scene sequence with narrative flow
   - Assign approximate durations to each scene
   - Specify transitions between scenes

2. Character Generation (if needed):
   - Create consistent character profiles with visual characteristics
   - Define personality traits and roles in the story
   - Ensure consistency across all scenes

3. Asset Generation:
   - Generate scene images based on prompts using DALL-E 3
   - Create narration audio from scripts using LLASA
   - Convert static images to video segments with motion effects
   - Generate background music matching the mood using MusicGen

4. Video Composition:
   - Combine scene videos in sequence
   - Add transitions between scenes
   - Layer narration audio with scene videos
   - Add background music with appropriate volume
   - Apply final adjustments (color grading, etc.)

Always think step by step and use the most appropriate tools for each part of the process.
Be creative but practical, and focus on creating high-quality, professional videos.

IMPORTANT: This is an interactive process. After generating the scene breakdown, 
wait for the user to approve or request changes before proceeding to the next steps.
Provide real-time updates on the progress of each stage.
"""


# Create the main video agent
video_agent = Agent[TaskContext](
    name="VideoCreationAgent",
    instructions=VIDEO_AGENT_INSTRUCTIONS,
    model="gpt-4o",
)


# Create the scene breakdown agent
scene_breakdown_agent = Agent[TaskContext](
    name="SceneBreakdownAgent",
    instructions="""
    You are a scene breakdown specialist for video creation. Your job is to analyze a prompt
    and create a detailed breakdown of scenes for a video.
    
    For each scene, provide:
    1. A title that captures the essence of the scene
    2. A script for narration that flows naturally and engages the viewer
    3. A detailed visual description for image generation with specific details about:
       - Setting and environment
       - Characters and their positions
       - Lighting and atmosphere
       - Camera angle and framing
       - Color palette and visual style
    4. Approximate duration based on the script length and visual complexity
    5. Appropriate transition to the next scene
    
    Be creative but practical, and ensure the scenes flow logically from one to the next.
    Consider the overall style and tone requested by the user.
    
    The scene breakdown should tell a cohesive story with a clear beginning, middle, and end.
    Pay attention to pacing, ensuring that important moments have adequate time and that
    the overall video maintains viewer interest throughout.
    
    For visual descriptions, be specific enough that an image generation model can create
    a compelling image, but avoid overly complex or impossible-to-visualize scenes.
    """,
    model="gpt-4o",
)


# Create the character generator agent
character_generator_agent = Agent[TaskContext](
    name="CharacterGeneratorAgent",
    instructions="""
    You are a character design specialist for video creation. Your job is to create
    consistent character profiles based on the scene breakdown.
    
    For each character, provide:
    1. A name that fits the character's personality and role
    2. A detailed visual description including:
       - Physical appearance (age, height, build, etc.)
       - Facial features and expressions
       - Clothing and accessories
       - Distinctive visual traits
       - Color palette
    3. Personality traits that define the character's behavior and motivations
    4. Role in the story and relationship to other characters
    5. Voice characteristics for narration and dialogue
    
    Ensure characters are consistent across all scenes and match the overall style of the video.
    
    Character designs should be:
    - Visually distinctive and memorable
    - Appropriate for the video's style and tone
    - Consistent with their role in the narrative
    - Detailed enough for image generation models to create consistent visuals
    
    Pay special attention to maintaining consistency across multiple scenes, ensuring
    that characters are immediately recognizable throughout the video.
    """,
    model="gpt-4o",
)


# Create the editor agent for handling edits to the video
editor_agent = Agent[TaskContext](
    name="EditorAgent",
    instructions="""
    You are a video editor assistant. Your job is to help users make specific edits
    to their videos, such as:
    1. Changing scene content (script, visual description, duration)
    2. Adjusting audio (narration, background music, sound effects)
    3. Modifying images (style, composition, colors)
    4. Changing the music (genre, mood, tempo)
    5. Adjusting transitions between scenes
    6. Reordering or removing scenes
    
    Use the appropriate tools to make the requested edits and provide clear explanations
    of what you're doing at each step.
    
    When making edits, consider:
    - The overall narrative flow and pacing
    - Visual and audio consistency across scenes
    - The user's specific requirements and preferences
    - Technical constraints and possibilities
    
    Provide options when appropriate, explaining the pros and cons of different approaches.
    Always maintain the quality and coherence of the video while implementing the requested changes.
    """,
    model="gpt-4o",
)


# Create the asset generator agent
asset_generator_agent = Agent[TaskContext](
    name="AssetGeneratorAgent",
    instructions="""
    You are an asset generation specialist for video creation. Your job is to create
    high-quality assets for videos, including:
    1. Images for scenes using DALL-E 3
    2. Narration audio using LLASA
    3. Background music using MusicGen
    4. Video segments from static images
    
    For each asset type, consider:
    
    Images:
    - Visual style and consistency across scenes
    - Composition and framing
    - Color palette and lighting
    - Level of detail appropriate for the scene
    
    Audio:
    - Voice characteristics matching the narration style
    - Pacing and emphasis
    - Emotional tone
    - Audio quality and clarity
    
    Music:
    - Genre and style matching the video's mood
    - Tempo and energy level
    - Instrumentation
    - Duration and looping potential
    
    Video:
    - Motion effects (panning, zooming, etc.)
    - Transition compatibility
    - Duration matching the script
    - Visual quality and stability
    
    Use the appropriate tools for each asset type and ensure all assets work together
    cohesively in the final video.
    """,
    model="gpt-4o",
)


# Create the video composer agent
video_composer_agent = Agent[TaskContext](
    name="VideoComposerAgent",
    instructions="""
    You are a video composition specialist. Your job is to combine all generated assets
    into a cohesive final video, including:
    1. Sequencing scene videos in the correct order
    2. Adding transitions between scenes
    3. Layering narration audio with scene videos
    4. Adding background music with appropriate volume
    5. Applying final adjustments (color grading, etc.)
    
    When composing the video, consider:
    - Timing and synchronization between visual and audio elements
    - Smooth transitions between scenes
    - Audio mixing and balance
    - Overall pacing and flow
    - Final video quality and format
    
    Use the appropriate tools for each composition task and ensure the final video
    meets the user's requirements and expectations.
    
    Pay special attention to:
    - Audio-visual synchronization
    - Consistent style and quality throughout
    - Appropriate pacing and rhythm
    - Smooth transitions
    - Overall narrative coherence
    """,
    model="gpt-4o",
)


# Function to get the appropriate agent based on the task stage
def get_agent_for_stage(stage: str) -> Agent[TaskContext]:
    """
    Get the appropriate agent for a given task stage.
    
    Args:
        stage: The current stage of the task
        
    Returns:
        The appropriate agent for the stage
    """
    stage_to_agent = {
        "scene_breakdown": scene_breakdown_agent,
        "character_generation": character_generator_agent,
        "asset_generation": asset_generator_agent,
        "video_composition": video_composer_agent,
        "editing": editor_agent,
    }
    
    return stage_to_agent.get(stage, video_agent)


# Define tool schemas
class SceneBreakdownRequest(BaseModel):
    """Request model for scene breakdown."""
    prompt: str = Field(..., description="The user's prompt for the video")
    style: str = Field(..., description="The style of the video (e.g., cinematic, cartoon)")
    duration: int = Field(..., description="The approximate duration of the video in seconds")
    aspect_ratio: str = Field("16:9", description="The aspect ratio of the video")


class SceneData(BaseModel):
    """Data model for a scene."""
    index: int = Field(..., description="The scene index (starting from 1)")
    title: str = Field(..., description="The scene title")
    script: str = Field(..., description="The narration script for the scene")
    video_prompt: str = Field(..., description="The visual description for image generation")
    duration: Optional[float] = Field(None, description="The approximate duration in seconds")
    transition: Optional[str] = Field(None, description="Transition to the next scene")


class SceneBreakdownResponse(BaseModel):
    """Response model for scene breakdown."""
    scenes: List[SceneData] = Field(..., description="List of scenes")
    style: str = Field(..., description="The style of the video")
    mood: str = Field(..., description="The overall mood of the video")
    transitions: List[Dict[str, Any]] = Field(..., description="List of transitions between scenes")
    estimated_duration: float = Field(..., description="Estimated total duration in seconds")


# Define tools
@function_tool
async def generate_scene_breakdown_tool(
    ctx: RunContextWrapper[TaskContext],
    prompt: str,
    style: str,
    duration: int,
    aspect_ratio: str = "16:9",
    mood: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a scene breakdown from the user's prompt.
    
    Args:
        prompt: The user's prompt for the video
        style: The style of the video (e.g., cinematic, cartoon)
        duration: The approximate duration of the video in seconds
        aspect_ratio: The aspect ratio of the video (default: 16:9)
        mood: The mood of the video (e.g., upbeat, dramatic)
        
    Returns:
        A detailed scene breakdown
    """
    try:
        # Update progress
        await ctx.context.set_progress(10, "scene_breakdown", "Analyzing prompt and generating scene breakdown")
        
        # Store in task state
        ctx.context.set("prompt", prompt)
        ctx.context.set("style", style)
        ctx.context.set("duration", duration)
        ctx.context.set("aspect_ratio", aspect_ratio)
        if mood:
            ctx.context.set("mood", mood)
        
        # Use OpenAI to generate a scene breakdown
        logger.info(f"Generating scene breakdown for prompt: {prompt}")
        
        # Create a system message for the scene breakdown
        system_message = f"""
        You are a professional video scriptwriter and director. Your task is to create a detailed scene breakdown for a {style} video about "{prompt}" with a duration of approximately {duration} seconds.
        
        For each scene, provide:
        1. A title
        2. A script for narration
        3. A detailed visual description for image generation
        4. Approximate duration in seconds
        5. Transition to the next scene
        
        The total duration should be approximately {duration} seconds.
        The aspect ratio is {aspect_ratio}.
        """
        
        if mood:
            system_message += f"\nThe mood of the video should be {mood}."
        
        # Get services
        services = get_services()
        openai_service = services["openai_service"]
        redis_client = services["redis_client"]
        
        # Call OpenAI to generate the scene breakdown
        response = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Create a scene breakdown for a {style} video about {prompt}."}
            ],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        content = response.choices[0].message.content
        scene_breakdown = json.loads(content)
        
        # Ensure the scene breakdown has the required fields
        if "scenes" not in scene_breakdown:
            scene_breakdown["scenes"] = []
        
        if "style" not in scene_breakdown:
            scene_breakdown["style"] = style
        
        if "mood" not in scene_breakdown:
            scene_breakdown["mood"] = mood or "neutral"
        
        if "transitions" not in scene_breakdown:
            scene_breakdown["transitions"] = []
            
            # Generate transitions if not provided
            for i in range(len(scene_breakdown["scenes"]) - 1):
                scene_breakdown["transitions"].append({
                    "from": i + 1,
                    "to": i + 2,
                    "type": "fade",
                    "duration": 1.0
                })
        
        if "estimated_duration" not in scene_breakdown:
            # Calculate estimated duration from scenes
            total_duration = sum(scene.get("duration", 0) for scene in scene_breakdown["scenes"])
            scene_breakdown["estimated_duration"] = total_duration or duration
        
        # Update progress
        await ctx.context.set_progress(20, "scene_breakdown", "Scene breakdown generated")
        
        # Store in task state
        ctx.context.set("scene_breakdown", scene_breakdown)
        
        # Store in Redis for persistence
        await redis_client.set_json(
            f"task:{ctx.context.task_id}:scene_breakdown", 
            scene_breakdown
        )
        
        # Add a message to the task history
        await ctx.context.add_message(
            "system", 
            f"Generated scene breakdown with {len(scene_breakdown['scenes'])} scenes"
        )
        
        return scene_breakdown
    
    except Exception as e:
        logger.error(f"Error generating scene breakdown: {str(e)}")
        
        # Create a fallback scene breakdown
        scene_breakdown = {
            "scenes": [
                {
                    "index": 1,
                    "title": "Introduction",
                    "script": "Our journey begins with a glimpse into the world of AI-powered video creation.",
                    "video_prompt": "A futuristic laboratory with holographic displays showing video creation in progress.",
                    "duration": duration * 0.2,
                    "transition": "fade"
                },
                {
                    "index": 2,
                    "title": "The Process",
                    "script": "The AI analyzes the prompt and breaks it down into scenes, characters, and assets.",
                    "video_prompt": "Split screen showing text analysis on one side and visual storyboards emerging on the other.",
                    "duration": duration * 0.3,
                    "transition": "slide"
                },
                {
                    "index": 3,
                    "title": "The Result",
                    "script": "The final video comes together, combining all elements into a cohesive story.",
                    "video_prompt": "A completed video playing on a large screen with an audience watching in amazement.",
                    "duration": duration * 0.5,
                    "transition": "none"
                }
            ],
            "style": style,
            "mood": mood or "inspirational",
            "transitions": [
                {"from": 1, "to": 2, "type": "fade", "duration": 1.0},
                {"from": 2, "to": 3, "type": "slide", "duration": 1.0}
            ],
            "estimated_duration": duration
        }
        
        # Store in task state
        ctx.context.set("scene_breakdown", scene_breakdown)
        
        # Store in Redis for persistence
        await redis_client.set_json(
            f"task:{ctx.context.task_id}:scene_breakdown", 
            scene_breakdown
        )
        
        return {
            "error": f"Error generating scene breakdown: {str(e)}",
            "scene_breakdown": scene_breakdown
        }


@function_tool
async def update_scene_tool(
    ctx: RunContextWrapper[TaskContext],
    scene_index: int,
    new_content: str,
    update_type: str = "both"
) -> Dict[str, Any]:
    """Update a specific scene in the video breakdown.
    
    Args:
        scene_index: The index of the scene to update (starting from 1)
        new_content: The new content for the scene
        update_type: What to update - "script", "visual", or "both"
        
    Returns:
        The updated scene breakdown
    """
    try:
        # Update progress
        await ctx.context.set_progress(25, "scene_breakdown", f"Updating scene {scene_index}")
        
        # Get scene breakdown from context
        scene_breakdown = ctx.context.get("scene_breakdown")
        if not scene_breakdown:
            return {"error": "No scene breakdown found. Generate one first."}
        
        # Adjust for 0-based indexing
        idx = scene_index - 1
        if idx < 0 or idx >= len(scene_breakdown["scenes"]):
            return {"error": f"Scene index {scene_index} is out of range"}
        
        # Update the scene based on update_type
        if update_type in ["script", "both"]:
            scene_breakdown["scenes"][idx]["script"] = new_content
            logger.info(f"Updated script for scene {scene_index}")
        
        if update_type in ["visual", "both"]:
            scene_breakdown["scenes"][idx]["video_prompt"] = new_content
            logger.info(f"Updated visual prompt for scene {scene_index}")
        
        # Update context
        ctx.context.set("scene_breakdown", scene_breakdown)
        
        # Get services
        services = get_services()
        redis_client = services["redis_client"]
        
        # Update Redis
        await redis_client.set_json(
            f"task:{ctx.context.task_id}:scene_breakdown", 
            scene_breakdown
        )
        
        # Add a message to the task history
        await ctx.context.add_message(
            "system", 
            f"Updated scene {scene_index} ({update_type})"
        )
        
        # Update progress
        await ctx.context.set_progress(30, "scene_breakdown", f"Scene {scene_index} updated successfully")
        
        return scene_breakdown
    
    except Exception as e:
        logger.error(f"Error updating scene: {str(e)}")
        return {"error": f"Error updating scene: {str(e)}"}


@function_tool
async def generate_video_tool(
    ctx: RunContextWrapper[TaskContext]
) -> Dict[str, Any]:
    """Start the video generation process using the approved scene breakdown.
    
    Returns:
        Status information about the video generation process
    """
    try:
        # Get scene breakdown from context
        scene_breakdown = ctx.context.get("scene_breakdown")
        if not scene_breakdown:
            return {"error": "No scene breakdown found. Generate one first."}
        
        # Update progress
        await ctx.context.set_progress(35, "video_generation", "Starting video generation process")
        
        # Store in task state
        ctx.context.set("generation_started", True)
        ctx.context.set("generation_stage", "video_generation")
        
        # Get services
        services = get_services()
        redis_client = services["redis_client"]
        
        # Store in Redis
        await redis_client.set_json(
            f"task:{ctx.context.task_id}:generation_status",
            {
                "status": "started",
                "progress": 35,
                "stage": "video_generation",
                "message": "Video generation started",
                "timestamp": time.time()
            }
        )
        
        # Add a message to the task history
        await ctx.context.add_message(
            "system", 
            "Video generation process has started. This will take several minutes."
        )
        
        # In a real implementation, this would start an async task to generate the video
        # For now, we'll simulate the process with a background task
        asyncio.create_task(
            simulate_video_generation(ctx.context.task_id, ctx.context.user_id)
        )
        
        return {
            "status": "started",
            "estimated_time": "3-5 minutes",
            "message": "Video generation has started. You will receive updates as the process progresses."
        }
    
    except Exception as e:
        logger.error(f"Error starting video generation: {str(e)}")
        return {"error": f"Error starting video generation: {str(e)}"}


async def simulate_video_generation(task_id: str, user_id: str):
    """
    Simulate the video generation process.
    
    Args:
        task_id: The task ID
        user_id: The user ID
    """
    # Get services
    services = get_services()
    redis_client = services["redis_client"]
    try:
        # Create a context for the task
        context = TaskContext(task_id=task_id, user_id=user_id)
        
        # Load the state
        await context.load_state()
        
        # Simulate progress updates
        stages = [
            {"progress": 40, "stage": "asset_generation", "message": "Generating scene images"},
            {"progress": 50, "stage": "asset_generation", "message": "Generating narration audio"},
            {"progress": 60, "stage": "asset_generation", "message": "Converting images to videos"},
            {"progress": 70, "stage": "asset_generation", "message": "Generating background music"},
            {"progress": 80, "stage": "video_composition", "message": "Composing scene videos"},
            {"progress": 90, "stage": "video_composition", "message": "Adding transitions and music"},
            {"progress": 100, "stage": "completed", "message": "Video generation complete"}
        ]
        
        for stage in stages:
            # Wait a bit to simulate processing time
            await asyncio.sleep(3)
            
            # Update progress
            await context.set_progress(
                progress=stage["progress"],
                stage=stage["stage"],
                message=stage["message"]
            )
            
            # Add a message to the task history
            await context.add_message("system", stage["message"])
        
        # Store the final result
        await context.store_result({
            "video_url": f"https://example.com/videos/{task_id}.mp4",
            "thumbnail_url": f"https://example.com/thumbnails/{task_id}.jpg",
            "created_at": time.time()
        })
        
        logger.info(f"Video generation simulation completed for task {task_id}")
    
    except Exception as e:
        logger.error(f"Error in video generation simulation: {str(e)}")


@function_tool
async def check_generation_status_tool(
    ctx: RunContextWrapper[TaskContext]
) -> Dict[str, Any]:
    """Check the status of the video generation process.
    
    Returns:
        Current status of the video generation process
    """
    try:
        # Get services
        services = get_services()
        redis_client = services["redis_client"]
        
        # Get status from Redis
        status = await redis_client.get_json(f"task:{ctx.context.task_id}:generation_status")
        if not status:
            return {
                "status": "unknown",
                "progress": 0,
                "message": "No generation status found"
            }
        
        # Get result if status is completed
        if status.get("status") == "completed" or status.get("progress") == 100:
            result = await redis_client.get_json(f"task:{ctx.context.task_id}:result")
            if result:
                status["result"] = result
        
        # Add a message to the task history
        await ctx.context.add_message(
            "system", 
            f"Current status: {status.get('message', 'Unknown')} ({status.get('progress', 0)}%)"
        )
        
        return status
    
    except Exception as e:
        logger.error(f"Error checking generation status: {str(e)}")
        return {
            "status": "error",
            "progress": 0,
            "message": f"Error checking status: {str(e)}"
        }


@function_tool
async def regenerate_scene_image_tool(
    ctx: RunContextWrapper[TaskContext],
    scene_index: int,
    new_prompt: str,
    style_adjustments: Optional[str] = None
) -> Dict[str, Any]:
    """Regenerate the image for a specific scene.
    
    Args:
        scene_index: The index of the scene to update (starting from 1)
        new_prompt: The new prompt for image generation
        style_adjustments: Optional style adjustments
        
    Returns:
        Information about the regenerated image
    """
    try:
        # Get scene breakdown from context
        scene_breakdown = ctx.context.get("scene_breakdown")
        if not scene_breakdown:
            return {"error": "No scene breakdown found. Generate one first."}
        
        # Adjust for 0-based indexing
        idx = scene_index - 1
        if idx < 0 or idx >= len(scene_breakdown["scenes"]):
            return {"error": f"Scene index {scene_index} is out of range"}
        
        # Update progress
        await ctx.context.set_progress(
            40, 
            "asset_generation", 
            f"Regenerating image for scene {scene_index}"
        )
        
        # Get the style from the scene breakdown
        style = scene_breakdown.get("style", "cinematic")
        
        # Apply style adjustments if provided
        if style_adjustments:
            style = f"{style}, {style_adjustments}"
        
        # Log the request
        logger.info(f"Regenerating image for scene {scene_index} with prompt: {new_prompt}")
        
        # In a real implementation, this would call OpenAI to generate the image
        # For now, we'll simulate the process
        
        # Add a message to the task history
        await ctx.context.add_message(
            "system", 
            f"Regenerating image for scene {scene_index} with prompt: {new_prompt}"
        )
        
        # Simulate a delay
        await asyncio.sleep(1)
        
        # Create a mock image URL
        image_url = f"https://example.com/images/scene_{scene_index}_regenerated.jpg"
        
        # Update the scene's image URL in the context
        scene_assets = ctx.context.get("scene_assets", {})
        if not scene_assets:
            scene_assets = {}
        
        if str(scene_index) not in scene_assets:
            scene_assets[str(scene_index)] = {}
        
        scene_assets[str(scene_index)]["image_url"] = image_url
        ctx.context.set("scene_assets", scene_assets)
        
        # Save to Redis
        await ctx.context.save_state()
        
        # Update progress
        await ctx.context.set_progress(
            45, 
            "asset_generation", 
            f"Image for scene {scene_index} regenerated successfully"
        )
        
        return {
            "scene_index": scene_index,
            "new_image_url": image_url,
            "message": f"Image for scene {scene_index} has been regenerated"
        }
    
    except Exception as e:
        logger.error(f"Error regenerating scene image: {str(e)}")
        return {
            "error": f"Error regenerating scene image: {str(e)}",
            "scene_index": scene_index
        }


# Add tools to agents
video_agent.tools = [
    generate_scene_breakdown_tool,
    update_scene_tool,
    generate_video_tool,
    check_generation_status_tool,
    regenerate_scene_image_tool,
]

scene_breakdown_agent.tools = [
    generate_scene_breakdown_tool,
    update_scene_tool,
]

character_generator_agent.tools = [
    # Will be implemented in Phase 2
]

asset_generator_agent.tools = [
    regenerate_scene_image_tool,
    # More tools will be implemented in Phase 2
]

video_composer_agent.tools = [
    check_generation_status_tool,
    # More tools will be implemented in Phase 2
]

editor_agent.tools = [
    update_scene_tool,
    regenerate_scene_image_tool,
]
