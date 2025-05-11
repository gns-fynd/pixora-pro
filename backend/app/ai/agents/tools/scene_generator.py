"""
Tool for generating scene breakdowns for videos with detailed structure.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.ai.models.request import StandardVideoMetadata
from app.ai.models.video_metadata import VideoMetadata
from app.ai.models.task import TaskStage, ProgressCallback
from app.services.openai import OpenAIService
from app.ai.utils.json_utils import save_json_response
from app.ai.utils.model_converters import advanced_to_standard_metadata

# Set up logging
logger = logging.getLogger(__name__)


class SceneGeneratorTool:
    """Tool for generating scene breakdowns for videos with detailed structure."""
    
    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize the scene generator tool.
        
        Args:
            openai_service: OpenAI service instance (creates a new one if None)
        """
        self.openai_service = openai_service or OpenAIService()
    
    async def generate_scene_breakdown(
        self,
        prompt: str,
        duration: int,
        style: str,
        voice_sample_url: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Tuple[VideoMetadata, StandardVideoMetadata]:
        """
        Generate a scene breakdown for a video.
        
        Args:
            prompt: The prompt describing the video to create
            duration: Duration of the video in seconds
            style: Style of the video
            voice_sample_url: Optional URL to a voice sample for TTS
            progress_callback: Optional callback for progress updates
            
        Returns:
            A tuple containing (VideoMetadata, StandardVideoMetadata)
        """
        if progress_callback:
            await progress_callback(10, f"Generating scene breakdown for '{prompt}'")
        
        # Create the prompt for the LLM
        system_prompt = self._create_system_prompt(duration, style)
        user_prompt = self._create_user_prompt(prompt, duration, style, voice_sample_url)
        
        # Generate the scene breakdown
        if progress_callback:
            await progress_callback(20, "Sending request to OpenAI")
        
        try:
            # Generate structured output using the VideoMetadata schema
            # Add JSON mention to the prompt to enable JSON mode
            json_prompt = f"{system_prompt}\n\n{user_prompt}\n\nPlease provide your response as a valid JSON object."
            advanced_result = await self.openai_service.generate_structured_output(
                prompt=json_prompt,
                output_schema=VideoMetadata.model_json_schema(),
                temperature=0.7,
                progress_callback=lambda p, m: progress_callback(20 + int(p * 0.7), m) if progress_callback else None,
            )
            
            # Convert to VideoMetadata
            advanced_result["expected_duration"] = duration
            advanced_metadata = VideoMetadata.model_validate(advanced_result)
            
        except Exception as e:
            # If validation fails, try to fix the format
            logger.warning(f"Error in advanced structured output generation: {e}")
            
            # Get the raw output without validation
            # Add JSON mention to the prompt to enable JSON mode
            json_prompt = f"{system_prompt}\n\n{user_prompt}\n\nPlease provide your response as a valid JSON object."
            raw_output = await self.openai_service.generate_structured_output(
                prompt=json_prompt,
                output_schema=VideoMetadata.model_json_schema(),
                temperature=0.7,
            )
            
            # Fix the format if needed
            fixed_output = self._fix_advanced_output_format(raw_output, prompt, voice_sample_url)
            
            # Set the expected duration
            fixed_output["expected_duration"] = duration
            
            # Try validation again
            advanced_metadata = VideoMetadata.model_validate(fixed_output)
        
        if progress_callback:
            await progress_callback(90, "Processing scene breakdown")
        
        # Log the advanced scene breakdown result
        logger.info(f"Scene breakdown result: {json.dumps(advanced_metadata.model_dump(), indent=2)}")
        
        # Save the advanced scene breakdown to a JSON file
        save_json_response(
            data=advanced_metadata.model_dump(),
            category="scene_breakdowns",
            name=f"scene_breakdown_{prompt[:20].replace(' ', '_')}"
        )
        
        # Convert to standard VideoMetadata
        standard_metadata = advanced_to_standard_metadata(advanced_metadata)
        
        # Validate and adjust the standard metadata
        self._validate_standard_metadata(standard_metadata, duration)
        
        if progress_callback:
            await progress_callback(100, "Scene breakdown complete")
        
        return advanced_metadata, standard_metadata
    
    def _create_system_prompt(self, duration: int, style: str) -> str:
        """
        Create the system prompt for the LLM.
        
        Args:
            duration: Duration of the video in seconds
            style: Style of the video
            
        Returns:
            The system prompt
        """
        return f"""You are a professional video director, screenwriter, and creative storyteller. Your task is to create a detailed video concept with scenes, characters, and music.

For a {duration}-second video in {style} style, you need to:
1. Rewrite the user's prompt to create a more compelling and detailed video concept
2. Determine if character consistency is needed across scenes
3. Create detailed character profiles with image prompts for 4-angle views
4. Divide the video into logical scenes with titles, scripts, and video prompts
5. Define music for groups of scenes

Guidelines:
- Create a cohesive narrative that tells a compelling story
- The total duration should be approximately {duration} seconds
- Consider the {style} style in your scene descriptions
- For character-driven narratives, create detailed character profiles
- For each character, provide a detailed image prompt that specifies 4 angles: front, side, back, and 3/4 view
- Group scenes logically for music to create a cohesive audio experience
- Provide detailed video prompts that describe the visual content of each scene
- Write concise, engaging narration scripts for each scene

Your output will be used to generate character images, scene videos, narration audio, and background music, which will then be combined into a final video."""
    
    def _create_user_prompt(
        self,
        prompt: str,
        duration: int,
        style: str,
        voice_sample_url: Optional[str] = None
    ) -> str:
        """
        Create the user prompt for the LLM.
        
        Args:
            prompt: The prompt describing the video to create
            duration: Duration of the video in seconds
            style: Style of the video
            voice_sample_url: Optional URL to a voice sample for TTS
            
        Returns:
            The user prompt
        """
        voice_instruction = ""
        if voice_sample_url:
            voice_instruction = f"\nUse the provided voice sample URL: {voice_sample_url}"
        
        return f"""Create a detailed video concept for a {duration}-second video with the following prompt:

"{prompt}"

The video should be in {style} style.{voice_instruction}

Provide your response as a structured JSON object with the following fields:
- user_prompt: The original prompt (exactly as provided)
- rewritten_prompt: A more detailed and compelling version of the prompt
- voice_character: URL to a voice sample for text-to-speech narration (use the provided URL if available)
- character_consistency: Boolean indicating if character consistency is needed across scenes
- music: List of music definitions, each with a prompt and list of scene indexes it applies to
- character_profiles: List of character profiles, each with a name and detailed image prompt for 4-angle views
- clips: List of clips, each containing a scene object with index, title, script, and video prompt

EXAMPLE FORMAT:
```json
{{
  "user_prompt": "Make a video on the story of Surya Putra Karna from Mahabharata",
  "rewritten_prompt": "Create a compelling video narrative of Karna's life, the son of Surya from the Mahabharata, emphasizing his virtues, struggles, and legacy.",
  "voice_character": "https://storage.googleapis.com/falserverless/model_tests/zonos/demo_voice_zonos.wav",
  "character_consistency": true,
  "music": [
    {{
      "prompt": "Gentle, mysterious flute music evolving into inspirational and powerful orchestral tones",
      "scene_indexes": [1, 2, 3]
    }},
    {{
      "prompt": "Melancholic and heroic strings",
      "scene_indexes": [4]
    }}
  ],
  "character_profiles": [
    {{
      "name": "Karna",
      "image_prompt": "Generate a character profile with 4 angles: front, side, back, and 3/4 view. A regal, muscular warrior with golden armor and earrings, medium-dark skin, long black hair tied back, intense brown eyes, dressed in royal dhoti and chestplate, holding a bow, standing under the sun."
    }},
    {{
      "name": "Kunti",
      "image_prompt": "Generate a character profile with 4 angles: front, side, back, and 3/4 view. A graceful, middle-aged Indian woman in a royal saree, expressive sad eyes, traditional gold jewelry, elegant posture, standing near palace interiors with natural light."
    }}
  ],
  "clips": [
    {{
      "scene": {{
        "index": 1,
        "title": "The Birth of Karna",
        "script": "Born to an unwed mother, Princess Kunti, and blessed by the Sun God Surya, Karna was set adrift in a basket on a river to avoid disgrace. Discovered and raised by a charioteer, his origins remained a mystery, shadowing his future.",
        "video_prompt": "Soft morning light over a tranquil river. A basket gently floats along the water, a baby inside, wrapped in royal cloth. Cut to a humble charioteer family discovering the baby."
      }}
    }},
    {{
      "scene": {{
        "index": 2,
        "title": "Karna's Quest for Knowledge",
        "script": "Undeterred by societal boundaries, Karna fervently pursued martial arts under Parashurama, the great sage who taught warriors of Brahmin lineage, deceiving the sage about his origins.",
        "video_prompt": "Visuals of a young Karna practicing archery with immense focus and skill in a lush forest setting. Transition to Karna respectfully approaching Parashurama, who is teaching other Brahmin students."
      }}
    }}
  ]
}}
```

IMPORTANT REQUIREMENTS:
1. Each scene must have a unique index starting from 1
2. Character profiles must include detailed image prompts for 4-angle views
3. Music definitions must specify which scene indexes they apply to
4. All scene indexes in the music definitions must correspond to actual scenes
5. The video prompt for each scene should be detailed and visual
6. The script for each scene should be concise and engaging
7. If character consistency is true, include all relevant characters in the character_profiles list"""
    
    def _fix_advanced_output_format(
        self,
        raw_output: Dict[str, Any],
        prompt: str,
        voice_sample_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fix the advanced output format if needed.
        
        Args:
            raw_output: Raw output from the LLM
            prompt: Original prompt
            voice_sample_url: Optional URL to a voice sample for TTS
            
        Returns:
            Fixed output
        """
        # Ensure required fields are present
        if "user_prompt" not in raw_output:
            raw_output["user_prompt"] = prompt
        
        if "rewritten_prompt" not in raw_output:
            raw_output["rewritten_prompt"] = prompt
        
        if "voice_character" not in raw_output and voice_sample_url:
            raw_output["voice_character"] = voice_sample_url
        
        if "character_consistency" not in raw_output:
            raw_output["character_consistency"] = False
        
        # Fix music format if needed
        if "music" not in raw_output:
            raw_output["music"] = []
        
        if not raw_output["music"] and "clips" in raw_output and raw_output["clips"]:
            # Create default music for all scenes
            scene_indexes = [clip["scene"]["index"] for clip in raw_output["clips"] if "scene" in clip and "index" in clip["scene"]]
            if scene_indexes:
                raw_output["music"] = [{
                    "prompt": "Background music appropriate for the video's mood and style",
                    "scene_indexes": scene_indexes
                }]
        
        # Fix character profiles if needed
        if "character_profiles" not in raw_output:
            raw_output["character_profiles"] = []
        
        if raw_output["character_consistency"] and not raw_output["character_profiles"] and "clips" in raw_output:
            # Extract character names from clips
            character_names = set()
            for clip in raw_output["clips"]:
                if "scene" in clip and "script" in clip["scene"]:
                    # Extract potential character names (capitalized words)
                    script = clip["scene"]["script"]
                    words = script.split()
                    for word in words:
                        if word and word[0].isupper() and len(word) > 3 and word.lower() not in ["this", "that", "these", "those", "there", "their", "they", "them"]:
                            character_names.add(word.rstrip(",.;:!?"))
            
            # Create character profiles
            for name in list(character_names)[:5]:  # Limit to 5 characters
                raw_output["character_profiles"].append({
                    "name": name,
                    "image_prompt": f"Generate a character profile with 4 angles: front, side, back, and 3/4 view. A detailed portrayal of {name} in appropriate attire and setting for the video's context."
                })
        
        # Fix clips format if needed
        if "clips" not in raw_output:
            raw_output["clips"] = []
        
        # Ensure each clip has the required fields
        for i, clip in enumerate(raw_output["clips"]):
            if "scene" not in clip:
                clip["scene"] = {}
            
            scene = clip["scene"]
            if "index" not in scene:
                scene["index"] = i + 1
            
            if "title" not in scene:
                scene["title"] = f"Scene {scene['index']}"
            
            if "script" not in scene and "narration" in scene:
                scene["script"] = scene["narration"]
            elif "script" not in scene:
                scene["script"] = f"Narration for scene {scene['index']}"
            
            if "video_prompt" not in scene and "description" in scene:
                scene["video_prompt"] = scene["description"]
            elif "video_prompt" not in scene:
                scene["video_prompt"] = f"Visual content for scene {scene['index']}"
        
        return raw_output
    
    def _validate_standard_metadata(self, metadata: StandardVideoMetadata, expected_duration: int):
        """
        Validate the standard metadata.
        
        Args:
            metadata: The standard metadata to validate
            expected_duration: The expected total duration in seconds
            
        Raises:
            ValueError: If the metadata is invalid
        """
        # Check if the total duration matches the expected duration
        total_duration = sum(scene.duration for scene in metadata.scenes)
        if abs(total_duration - expected_duration) > 1:  # Allow 1 second tolerance
            logger.warning(
                f"Total scene duration ({total_duration}s) doesn't match expected duration ({expected_duration}s)"
            )
            
            # Adjust scene durations proportionally
            adjustment_factor = expected_duration / total_duration
            for scene in metadata.scenes:
                scene.duration *= adjustment_factor
        
        # Check if character consistency is needed but no characters are defined
        if metadata.needs_character_consistency and not metadata.characters:
            logger.warning("Character consistency is needed but no characters are defined")
            metadata.characters = []
        
        # Ensure all scenes have transitions except the last one
        for i, scene in enumerate(metadata.scenes[:-1]):
            # Convert dictionary transitions to strings if needed
            if isinstance(scene.transition, dict) and "type" in scene.transition:
                scene.transition = scene.transition["type"]
                logger.warning(f"Converted dictionary transition to string: {scene.transition}")
            
            if not scene.transition:
                logger.warning(f"Scene {i} has no transition, defaulting to 'fade'")
                scene.transition = "fade"
        
        # Ensure transitions in the VideoMetadata are in the correct format
        if metadata.transitions and isinstance(metadata.transitions, list):
            for i, transition in enumerate(metadata.transitions):
                if isinstance(transition, str):
                    # Convert string transitions to dictionary format
                    metadata.transitions[i] = {"type": transition}
                    logger.warning(f"Converted string transition '{transition}' to dictionary format")
