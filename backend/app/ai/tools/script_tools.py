"""
Script generation tools for the Pixora AI application.

This module provides tools for generating and refining scripts.
"""
import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union

from app.models import (
    ScriptBreakdown, Scene, Clip, MusicPrompt, CharacterProfile, TransitionType
)
from app.services.openai import OpenAIService

# Set up logging
logger = logging.getLogger(__name__)


async def generate_script(
    prompt: str,
    character_consistency: bool = False,
    voice_character: Optional[str] = None,
    user_id: str = None,
    openai_service: OpenAIService = None,
) -> ScriptBreakdown:
    """
    Generate a script from a prompt.

    Args:
        prompt: The prompt describing the video
        character_consistency: Whether to maintain consistent characters
        voice_character: Optional URL to a voice sample
        user_id: The ID of the user
        openai_service: The OpenAI service

    Returns:
        The generated script
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for script generation")
    
    try:
        logger.info(f"Generating script for prompt: {prompt}")
        
        # Create a system prompt for the script generation
        system_prompt = """
        You are a professional video script writer. Your task is to create a detailed script breakdown for a video based on the user's prompt.
        
        The script breakdown should include:
        1. A rewritten, enhanced version of the user's prompt
        2. A list of clips, each with:
           - A scene with an index, title, script (narration text), and video prompt (visual description)
           - A transition type for each scene
        3. Music prompts for different parts of the video
        4. Character profiles if character consistency is enabled
        
        Your response should be in JSON format with the following structure:
        {
            "rewritten_prompt": "Enhanced, detailed prompt",
            "clips": [
                {
                    "scene": {
                        "index": 1,
                        "title": "Scene title",
                        "script": "Narration text for the scene",
                        "video_prompt": "Detailed visual description for image generation",
                        "transition": "fade" // One of: fade, slide_left, slide_right, zoom_in, zoom_out, fade_to_black, crossfade
                    }
                },
                // More clips...
            ],
            "music": [
                {
                    "prompt": "Description of the music",
                    "scene_indexes": [1, 2] // Indexes of scenes that use this music
                },
                // More music prompts...
            ],
            "character_profiles": [
                {
                    "name": "Character name",
                    "image_prompt": "Detailed description for character image generation"
                },
                // More character profiles if character_consistency is true...
            ],
            "expected_duration": 60.0 // Estimated duration in seconds
        }
        
        Make sure each scene has a compelling title, engaging narration text, and a detailed visual description that can be used to generate an image.
        The transitions should be varied and appropriate for the content.
        The music prompts should match the mood and content of the scenes.
        If character consistency is enabled, create detailed character profiles that can be used to generate consistent character images.
        """
        
        # Create a user prompt with the video request
        user_prompt = f"""
        Create a script breakdown for a video with the following prompt:
        
        {prompt}
        
        Additional requirements:
        - Character consistency: {"Yes, maintain consistent characters throughout the video" if character_consistency else "No, not required"}
        - Voice character: {"Custom voice sample provided" if voice_character else "Default voice"}
        
        Please provide a detailed script breakdown following the specified JSON format.
        """
        
        # Generate the script using OpenAI
        response = await openai_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=4000
        )
        
        if not response:
            raise ValueError("Failed to generate script")
        
        # Parse the JSON response
        try:
            script_data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response if it's not pure JSON
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                script_data = json.loads(json_match.group(1))
            else:
                # Try to find JSON object in the response
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    script_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("Failed to parse script JSON")
        
        # Create the script breakdown
        clips = []
        for clip_data in script_data.get("clips", []):
            scene_data = clip_data.get("scene", {})
            
            # Create the scene
            scene = Scene(
                index=scene_data.get("index", 1),
                title=scene_data.get("title", "Untitled Scene"),
                script=scene_data.get("script", ""),
                video_prompt=scene_data.get("video_prompt", ""),
                transition=_parse_transition_type(scene_data.get("transition", "fade"))
            )
            
            # Create the clip
            clip = Clip(scene=scene)
            clips.append(clip)
        
        # Create the music prompts
        music_prompts = []
        for music_data in script_data.get("music", []):
            music_prompt = MusicPrompt(
                prompt=music_data.get("prompt", ""),
                scene_indexes=music_data.get("scene_indexes", [])
            )
            music_prompts.append(music_prompt)
        
        # Create the character profiles
        character_profiles = []
        if character_consistency:
            for character_data in script_data.get("character_profiles", []):
                character_profile = CharacterProfile(
                    name=character_data.get("name", ""),
                    image_prompt=character_data.get("image_prompt", "")
                )
                character_profiles.append(character_profile)
        
        # Create the script breakdown
        script_breakdown = ScriptBreakdown(
            user_prompt=prompt,
            rewritten_prompt=script_data.get("rewritten_prompt", prompt),
            voice_character=voice_character,
            character_consistency=character_consistency,
            music=music_prompts,
            character_profiles=character_profiles,
            clips=clips,
            expected_duration=script_data.get("expected_duration", 60.0),
            task_id=None,  # Will be set by the caller
            user_id=user_id
        )
        
        logger.info(f"Generated script with {len(clips)} scenes")
        
        return script_breakdown
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        raise


async def refine_script(
    script: ScriptBreakdown,
    feedback: str,
    openai_service: OpenAIService = None,
) -> ScriptBreakdown:
    """
    Refine a script based on user feedback.

    Args:
        script: The script to refine
        feedback: The user's feedback
        openai_service: The OpenAI service

    Returns:
        The refined script
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for script refinement")
    
    try:
        logger.info(f"Refining script based on feedback: {feedback}")
        
        # Create a system prompt for the script refinement
        system_prompt = """
        You are a professional video script editor. Your task is to refine an existing script breakdown based on the user's feedback.
        
        You will be provided with an existing script breakdown in JSON format and the user's feedback.
        Your job is to modify the script according to the feedback while maintaining its overall structure.
        
        Your response should be in JSON format with the same structure as the original script.
        """
        
        # Convert the script to JSON
        script_json = json.dumps(script.dict(), indent=2)
        
        # Create a user prompt with the script and feedback
        user_prompt = f"""
        Here is the existing script breakdown:
        
        ```json
        {script_json}
        ```
        
        Please refine this script based on the following feedback:
        
        {feedback}
        
        Return the refined script in the same JSON format.
        """
        
        # Generate the refined script using OpenAI
        response = await openai_service.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=4000
        )
        
        if not response:
            raise ValueError("Failed to refine script")
        
        # Parse the JSON response
        try:
            refined_script_data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response if it's not pure JSON
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                refined_script_data = json.loads(json_match.group(1))
            else:
                # Try to find JSON object in the response
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    refined_script_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("Failed to parse refined script JSON")
        
        # Create the refined script breakdown
        clips = []
        for clip_data in refined_script_data.get("clips", []):
            scene_data = clip_data.get("scene", {})
            
            # Create the scene
            scene = Scene(
                index=scene_data.get("index", 1),
                title=scene_data.get("title", "Untitled Scene"),
                script=scene_data.get("script", ""),
                video_prompt=scene_data.get("video_prompt", ""),
                transition=_parse_transition_type(scene_data.get("transition", "fade"))
            )
            
            # Create the clip
            clip = Clip(scene=scene)
            clips.append(clip)
        
        # Create the music prompts
        music_prompts = []
        for music_data in refined_script_data.get("music", []):
            music_prompt = MusicPrompt(
                prompt=music_data.get("prompt", ""),
                scene_indexes=music_data.get("scene_indexes", [])
            )
            music_prompts.append(music_prompt)
        
        # Create the character profiles
        character_profiles = []
        if script.character_consistency:
            for character_data in refined_script_data.get("character_profiles", []):
                character_profile = CharacterProfile(
                    name=character_data.get("name", ""),
                    image_prompt=character_data.get("image_prompt", "")
                )
                character_profiles.append(character_profile)
        
        # Create the refined script breakdown
        refined_script = ScriptBreakdown(
            user_prompt=f"{script.user_prompt} (with feedback: {feedback})",
            rewritten_prompt=refined_script_data.get("rewritten_prompt", script.rewritten_prompt),
            voice_character=script.voice_character,
            character_consistency=script.character_consistency,
            music=music_prompts,
            character_profiles=character_profiles,
            clips=clips,
            expected_duration=refined_script_data.get("expected_duration", script.expected_duration),
            task_id=None,  # Will be set by the caller
            user_id=script.user_id
        )
        
        logger.info(f"Refined script with {len(clips)} scenes")
        
        return refined_script
    except Exception as e:
        logger.error(f"Error refining script: {str(e)}")
        raise


def _parse_transition_type(transition_str: str) -> TransitionType:
    """
    Parse a transition type string into a TransitionType enum.

    Args:
        transition_str: The transition type string

    Returns:
        The TransitionType enum value
    """
    transition_map = {
        "fade": TransitionType.FADE,
        "slide_left": TransitionType.SLIDE_LEFT,
        "slide_right": TransitionType.SLIDE_RIGHT,
        "zoom_in": TransitionType.ZOOM_IN,
        "zoom_out": TransitionType.ZOOM_OUT,
        "fade_to_black": TransitionType.FADE_TO_BLACK,
        "crossfade": TransitionType.CROSSFADE
    }
    
    return transition_map.get(transition_str.lower(), TransitionType.FADE)
