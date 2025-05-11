"""
Script agent for the Pixora AI application.

This module provides the script agent for generating and refining scripts.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from fastapi import Depends

from app.models import ScriptBreakdown, PromptRequest
from app.services.openai import OpenAIService
from app.services.redis_client import RedisClient
from app.ai.tools.script_tools import generate_script, refine_script

# Set up logging
logger = logging.getLogger(__name__)


class ScriptAgent:
    """
    Agent for generating and refining scripts.
    """

    def __init__(
        self,
        openai_service: OpenAIService = Depends(),
        redis_client: RedisClient = Depends(),
    ):
        """
        Initialize the script agent.

        Args:
            openai_service: The OpenAI service
            redis_client: The Redis client
        """
        self.openai_service = openai_service
        self.redis_client = redis_client

    async def generate_script_from_prompt(
        self,
        prompt_request: PromptRequest,
        task_id: Optional[str] = None,
    ) -> ScriptBreakdown:
        """
        Generate a script from a prompt.

        Args:
            prompt_request: The prompt request
            task_id: Optional task ID

        Returns:
            The generated script
        """
        try:
            logger.info(f"Generating script for prompt: {prompt_request.prompt}")
            
            # Generate the script
            script = await generate_script(
                prompt=prompt_request.prompt,
                character_consistency=prompt_request.character_consistency,
                voice_character=prompt_request.voice_character,
                user_id=prompt_request.user_id,
                openai_service=self.openai_service
            )
            
            # Set the task ID
            script.task_id = task_id
            
            # Store the script in Redis if task_id is provided
            if task_id:
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
            
            return script
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            
            # Update the task progress if task_id is provided
            if task_id:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error generating script: {str(e)}",
                        "status": "error"
                    }
                )
            
            raise

    async def refine_script(
        self,
        script: ScriptBreakdown,
        feedback: str,
        task_id: Optional[str] = None,
    ) -> ScriptBreakdown:
        """
        Refine a script based on user feedback.

        Args:
            script: The script to refine
            feedback: The user's feedback
            task_id: Optional task ID

        Returns:
            The refined script
        """
        try:
            logger.info(f"Refining script based on feedback: {feedback}")
            
            # Refine the script
            refined_script = await refine_script(
                script=script,
                feedback=feedback,
                openai_service=self.openai_service
            )
            
            # Set the task ID
            refined_script.task_id = task_id
            
            # Store the refined script in Redis if task_id is provided
            if task_id:
                await self.redis_client.set_json(
                    f"task:{task_id}:script",
                    refined_script.dict()
                )
                
                # Update the task progress
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": "Script refinement complete",
                        "status": "completed"
                    }
                )
            
            logger.info(f"Refined script with {len(refined_script.clips)} scenes")
            
            return refined_script
        except Exception as e:
            logger.error(f"Error refining script: {str(e)}")
            
            # Update the task progress if task_id is provided
            if task_id:
                await self.redis_client.set_json(
                    f"task:{task_id}:progress",
                    {
                        "progress": 100,
                        "message": f"Error refining script: {str(e)}",
                        "status": "error"
                    }
                )
            
            raise

    async def get_script(self, task_id: str) -> Optional[ScriptBreakdown]:
        """
        Get a script from Redis.

        Args:
            task_id: The task ID

        Returns:
            The script, or None if not found
        """
        try:
            # Get the script from Redis
            script_data = await self.redis_client.get_json(f"task:{task_id}:script")
            
            if not script_data:
                return None
            
            # Create the script
            script = ScriptBreakdown(**script_data)
            
            return script
        except Exception as e:
            logger.error(f"Error getting script: {str(e)}")
            return None
