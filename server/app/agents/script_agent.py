"""
Script generation agent for Pixora AI Video Creation Platform
"""
import logging
import json
from typing import Dict, Any, Optional, List, Union

# Import base agent
from .base_agent import BaseAgent

# Import tools
from ..tools.openai_tools import (
    generate_script,
    call_openai_with_json_mode
)

# Import telemetry
from ..utils.telemetry import traced, log_event

# Configure logging
logger = logging.getLogger(__name__)

class ScriptAgent(BaseAgent):
    """
    Agent for generating and refining video scripts.
    """
    
    def __init__(self):
        """Initialize the script agent."""
        instructions = """You are a professional video script generator that creates detailed breakdowns for video production.
        
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
        """
        
        # Define the tools
        tools = [
            generate_script,
            call_openai_with_json_mode
        ]
        
        # Initialize the base agent
        super().__init__(name="ScriptAgent", instructions=instructions, tools=tools)
        
        logger.info("Script agent initialized")
    
    @traced("create_script")
    async def create_script(
        self,
        prompt: str,
        character_consistency: bool = False,
        duration: Optional[float] = None,
        aspect_ratio: Optional[str] = None,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a script breakdown from a user prompt.
        
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
            # Generate the script
            script_data = await generate_script(
                prompt=prompt,
                character_consistency=character_consistency,
                duration=duration,
                aspect_ratio=aspect_ratio,
                style=style
            )
            
            # Log the script generation
            log_event(
                event_type="script_created",
                message=f"Script created for prompt: {prompt[:50]}...",
                data={
                    "task_id": script_data.get("task_id"),
                    "expected_duration": script_data.get("expected_duration"),
                    "scene_count": len(script_data.get("clips", [])),
                    "character_count": len(script_data.get("character_profiles", [])),
                    "music_count": len(script_data.get("music", []))
                }
            )
            
            return script_data
        except Exception as e:
            logger.error(f"Error creating script: {str(e)}")
            raise
    
    @traced("refine_script")
    async def refine_script(
        self,
        script_data: Dict[str, Any],
        feedback: str
    ) -> Dict[str, Any]:
        """
        Refine a script based on user feedback.
        
        Args:
            script_data: The original script data
            feedback: User feedback for refinement
            
        Returns:
            Dict[str, Any]: The refined script data
        """
        try:
            # Create a system prompt for refinement
            system_prompt = """You are a professional video script editor. Your task is to refine a video script based on user feedback.
            
            The original script is provided in JSON format. You must make changes according to the user's feedback while maintaining the structure.
            
            CRITICAL: The video_prompt for each scene MUST include motion descriptions for video generation. All scenes will be created as motion videos, not static images.
            
            CRITICAL: The video generation API can only generate videos of 5 or 10 seconds. This is a hard constraint that must be respected. Each scene must be either 5 or 10 seconds long.
            
            Your output must be a valid JSON object with the same structure as the original script.
            """
            
            # Create a user prompt with the original script and feedback
            user_prompt = f"""Original script:
            {json.dumps(script_data, indent=2)}
            
            User feedback:
            {feedback}
            
            Please refine the script according to the feedback while maintaining the JSON structure.
            """
            
            # Call OpenAI with JSON mode
            response = await call_openai_with_json_mode(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                temperature=0.7
            )
            
            # Get the refined script
            refined_script = response["result"]
            
            # Ensure the task_id is preserved
            refined_script["task_id"] = script_data.get("task_id")
            
            # Log the script refinement
            log_event(
                event_type="script_refined",
                message=f"Script refined based on feedback: {feedback[:50]}...",
                data={
                    "task_id": refined_script.get("task_id"),
                    "expected_duration": refined_script.get("expected_duration"),
                    "scene_count": len(refined_script.get("clips", [])),
                    "character_count": len(refined_script.get("character_profiles", [])),
                    "music_count": len(refined_script.get("music", []))
                }
            )
            
            return refined_script
        except Exception as e:
            logger.error(f"Error refining script: {str(e)}")
            raise
    
    @traced("analyze_prompt")
    async def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze a user prompt to extract key elements and suggest improvements.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Create a system prompt for analysis
            system_prompt = """You are a professional video prompt analyzer. Your task is to analyze a user's video prompt and extract key elements.
            
            For each prompt, identify:
            1. Main subject/topic
            2. Style/tone
            3. Key visual elements
            4. Potential scenes
            5. Suggested improvements to make the prompt more detailed and effective
            
            Your output should be a structured JSON object with these elements.
            """
            
            # Create a user prompt
            user_prompt = f"""Analyze the following video prompt:
            
            {prompt}
            
            Extract the key elements and suggest improvements to make it more effective for video generation.
            """
            
            # Define the schema
            schema = {
                "type": "object",
                "properties": {
                    "main_subject": {"type": "string"},
                    "style_tone": {"type": "string"},
                    "visual_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "potential_scenes": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "suggested_improvements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "enhanced_prompt": {"type": "string"}
                },
                "required": ["main_subject", "style_tone", "visual_elements", "potential_scenes", "suggested_improvements", "enhanced_prompt"]
            }
            
            # Call OpenAI with JSON mode and schema
            response = await call_openai_with_json_mode(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                schema=schema,
                temperature=0.7
            )
            
            # Get the analysis results
            analysis = response["result"]
            
            # Log the prompt analysis
            log_event(
                event_type="prompt_analyzed",
                message=f"Prompt analyzed: {prompt[:50]}...",
                data={
                    "main_subject": analysis.get("main_subject"),
                    "style_tone": analysis.get("style_tone"),
                    "visual_element_count": len(analysis.get("visual_elements", [])),
                    "potential_scene_count": len(analysis.get("potential_scenes", [])),
                    "improvement_count": len(analysis.get("suggested_improvements", []))
                }
            )
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing prompt: {str(e)}")
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
            # Analyze the input to determine the intent
            if "create script" in input_text.lower() or "generate script" in input_text.lower():
                # Extract parameters from the input
                character_consistency = "character consistency" in input_text.lower() or "consistent characters" in input_text.lower()
                
                # Extract duration if mentioned
                duration = None
                import re
                duration_match = re.search(r'(\d+)\s*seconds', input_text)
                if duration_match:
                    duration = float(duration_match.group(1))
                
                # Extract aspect ratio if mentioned
                aspect_ratio = None
                if "16:9" in input_text:
                    aspect_ratio = "16:9"
                elif "9:16" in input_text:
                    aspect_ratio = "9:16"
                elif "1:1" in input_text:
                    aspect_ratio = "1:1"
                
                # Extract style if mentioned
                style = None
                if "cinematic" in input_text.lower():
                    style = "cinematic"
                elif "cartoon" in input_text.lower():
                    style = "cartoon"
                elif "realistic" in input_text.lower():
                    style = "realistic"
                
                # Create the script
                script_data = await self.create_script(
                    prompt=input_text,
                    character_consistency=character_consistency,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    style=style
                )
                
                return {
                    "status": "success",
                    "output": f"Script created successfully with {len(script_data.get('clips', []))} scenes.",
                    "data": script_data
                }
            elif "refine script" in input_text.lower() or "improve script" in input_text.lower():
                # Check if we have a script in the context
                if "script" not in context:
                    return {
                        "status": "error",
                        "error": "No script found in context. Please create a script first."
                    }
                
                # Refine the script
                refined_script = await self.refine_script(
                    script_data=context["script"],
                    feedback=input_text
                )
                
                return {
                    "status": "success",
                    "output": f"Script refined successfully with {len(refined_script.get('clips', []))} scenes.",
                    "data": refined_script
                }
            elif "analyze prompt" in input_text.lower() or "analyze my prompt" in input_text.lower():
                # Analyze the prompt
                analysis = await self.analyze_prompt(prompt=input_text)
                
                return {
                    "status": "success",
                    "output": "Prompt analyzed successfully.",
                    "data": analysis
                }
            else:
                # Default to script creation
                script_data = await self.create_script(prompt=input_text)
                
                return {
                    "status": "success",
                    "output": f"Script created successfully with {len(script_data.get('clips', []))} scenes.",
                    "data": script_data
                }
        except Exception as e:
            logger.error(f"Error running script agent: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

# Create a global instance of the script agent
script_agent = ScriptAgent()
