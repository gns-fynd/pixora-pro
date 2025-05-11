"""
Video generator for the Pixora AI platform.

This module provides a service for generating videos from prompts.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
import os
import uuid

from fastapi import Depends, HTTPException, status, BackgroundTasks

from app.core.config import Settings, get_settings
from app.services import (
    TextToImageService,
    ImageToVideoService,
    TextToSpeechService,
    TextToMusicService,
    CreditService,
    StorageManager,
)
from app.ai.agent import AgentOrchestrator
from app.ai.prompt_analyzer import PromptAnalyzer


# Set up logging
logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Video generator for the Pixora AI platform.
    """
    
    # Class variables for progress tracking
    # These are shared across all instances of the class
    progress = {}
    background_tasks = {}
    
    def __init__(
        self, 
        agent_orchestrator: AgentOrchestrator = Depends(),
        prompt_analyzer: PromptAnalyzer = Depends(),
        credit_service: CreditService = Depends(),
        storage_manager: StorageManager = Depends(),
        settings: Settings = Depends(get_settings)
    ):
        """
        Initialize the video generator.
        
        Args:
            agent_orchestrator: The agent orchestrator
            prompt_analyzer: The prompt analyzer
            credit_service: The credit service
            storage_manager: The storage manager
            settings: Application settings
        """
        self.agent_orchestrator = agent_orchestrator
        self.prompt_analyzer = prompt_analyzer
        self.credit_service = credit_service
        self.storage_manager = storage_manager
        self.settings = settings
    
    async def generate_video(
        self, 
        prompt: str,
        user_id: str,
        aspect_ratio: str = "16:9",
        duration: int = 30,
        style: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        Generate a video from a prompt.
        
        Args:
            prompt: The prompt to generate the video from
            user_id: The user ID
            aspect_ratio: The aspect ratio of the video
            duration: The duration of the video in seconds
            style: Optional style for the video
            background_tasks: Optional background tasks
            
        Returns:
            The video generation result with task ID
        """
        try:
            # Generate a task ID
            task_id = f"video_{uuid.uuid4()}"
            
            # Initialize progress
            self._update_progress(0, "Starting video generation", task_id, user_id)
            
            # Calculate total cost
            total_cost = await self._calculate_total_cost(prompt, duration, aspect_ratio)
            
            # Check if the user has enough credits
            user_credits = await self.credit_service.get_credit_balance(user_id)
            if user_credits < total_cost:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. Required: {total_cost}, Available: {user_credits}"
                )
            
            # Create a callback function for progress updates
            def progress_callback(progress: float, message: Optional[str] = None):
                self._update_progress(progress, message, task_id, user_id)
            
            # Start the video generation in the background
            if background_tasks:
                background_tasks.add_task(
                    self._generate_video_task,
                    task_id=task_id,
                    prompt=prompt,
                    user_id=user_id,
                    aspect_ratio=aspect_ratio,
                    duration=duration,
                    style=style,
                    total_cost=total_cost,
                    callback=progress_callback
                )
            else:
                # Create a background task manually
                asyncio.create_task(
                    self._generate_video_task(
                        task_id=task_id,
                        prompt=prompt,
                        user_id=user_id,
                        aspect_ratio=aspect_ratio,
                        duration=duration,
                        style=style,
                        total_cost=total_cost,
                        callback=progress_callback
                    )
                )
            
            # Return the task ID
            return {
                "task_id": task_id,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "style": style,
                "status": "processing",
                "cost": total_cost,
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video generation failed: {str(e)}"
            )
    
    async def get_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a video generation task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task status
        """
        # Get the progress
        progress = self.progress.get(task_id)
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Get the result if available
        result = self.background_tasks.get(task_id)
        
        # Create the response
        response = {
            "task_id": task_id,
            "status": "completed" if progress["progress"] == 100 else "processing",
            "progress": progress["progress"],
            "message": progress["message"],
        }
        
        # Add the result if available
        if result:
            response["result"] = result
            # Add the actual duration if available
            if "duration" in result:
                response["actual_duration"] = result["duration"]
        
        return response
    
    async def _generate_video_task(
        self,
        task_id: str,
        prompt: str,
        user_id: str,
        aspect_ratio: str,
        duration: int,
        style: Optional[str],
        total_cost: int,
        callback: Callable[[float, Optional[str]], None]
    ):
        """
        Generate a video in the background.
        
        Args:
            task_id: The task ID
            prompt: The prompt
            user_id: The user ID
            aspect_ratio: The aspect ratio
            duration: The duration in seconds
            style: Optional style
            total_cost: The total cost in credits
            callback: The callback function for progress updates
        """
        try:
            # Deduct credits
            await self.credit_service.deduct_credits(
                user_id=user_id,
                amount=total_cost,
                reason=f"Video generation: {prompt[:30]}"
            )
            
            # Generate the video with the updated workflow
            # Note: The duration parameter is now used as a maximum duration guideline
            # The actual duration will be determined by the voiceover audio length
            result = await self.agent_orchestrator.create_video(
                prompt=prompt,
                user_id=user_id,
                aspect_ratio=aspect_ratio,
                duration=duration,  # This is now used as a maximum duration guideline
                style=style,
                callback=lambda task_id, progress, message: callback(progress, message)
            )
            
            # Store the result
            self.background_tasks[task_id] = result
            
            # Update the progress
            self._update_progress(100, "Video generation complete", task_id, user_id)
            
        except Exception as e:
            logger.error(f"Error in video generation task: {str(e)}")
            
            # Refund credits
            try:
                await self.credit_service.add_credits(
                    user_id=user_id,
                    amount=total_cost,
                    reason=f"Refund for failed video generation: {prompt[:30]}"
                )
            except Exception as refund_error:
                logger.error(f"Error refunding credits: {str(refund_error)}")
            
            # Update the progress
            self._update_progress(0, f"Video generation failed: {str(e)}", task_id, user_id)
    
    async def _calculate_total_cost(self, prompt: str, duration: int, aspect_ratio: str) -> int:
        """
        Calculate the total cost of generating a video.
        
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
    
    def _update_progress(self, progress: float, message: Optional[str] = None, task_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Update the progress of a task.
        
        Args:
            progress: The progress (0-100)
            message: Optional message
            task_id: Optional task ID (used when called directly, not via callback)
            user_id: Optional user ID to associate with the task
        """
        if task_id:
            # Store the progress in the dictionary
            self.progress[task_id] = {
                "progress": progress,
                "message": message or f"Processing: {progress:.0f}%",
                "user_id": user_id,
            }
            logger.info(f"Updated progress for task {task_id}: {progress}% - {message}")
