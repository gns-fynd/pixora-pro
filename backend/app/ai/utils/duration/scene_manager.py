"""
Scene duration management utilities.

This module provides utilities for managing the duration of scenes in a video.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

from app.ai.utils.duration.audio_adjuster import AudioDurationAdjuster
from app.ai.utils.duration.video_adjuster import VideoDurationAdjuster


# Set up logging
logger = logging.getLogger(__name__)


class SceneDurationManager:
    """
    Utility for managing the duration of scenes in a video.
    
    This class provides methods for:
    - Calculating scene durations based on total video duration
    - Adjusting scene durations to match target durations
    - Redistributing durations when scenes are added or removed
    - Validating scene durations
    """
    
    @staticmethod
    def calculate_scene_durations(
        scenes: List[Dict[str, Any]],
        total_duration: float,
        min_scene_duration: float = 3.0
    ) -> List[float]:
        """
        Calculate scene durations based on total video duration.
        
        Args:
            scenes: List of scene data dictionaries
            total_duration: Total video duration in seconds
            min_scene_duration: Minimum duration for each scene in seconds
            
        Returns:
            List of scene durations in seconds
        """
        if not scenes:
            return []
        
        # Calculate minimum total duration based on minimum scene duration
        min_total_duration = len(scenes) * min_scene_duration
        
        # Ensure total duration is at least the minimum
        if total_duration < min_total_duration:
            logger.warning(
                f"Total duration {total_duration}s is less than minimum required "
                f"({min_total_duration}s for {len(scenes)} scenes). "
                f"Adjusting to minimum."
            )
            total_duration = min_total_duration
        
        # Get weights from scenes if available, otherwise use equal weights
        weights = []
        for scene in scenes:
            # Try to get weight from scene data
            weight = scene.get("weight", 1.0)
            if isinstance(weight, (int, float)) and weight > 0:
                weights.append(float(weight))
            else:
                weights.append(1.0)
        
        # Calculate durations based on weights
        total_weight = sum(weights)
        durations = [
            max(min_scene_duration, (weight / total_weight) * total_duration)
            for weight in weights
        ]
        
        # Adjust durations to match total duration
        actual_total = sum(durations)
        if abs(actual_total - total_duration) > 0.1:
            # Scale durations to match total
            scale_factor = total_duration / actual_total
            durations = [duration * scale_factor for duration in durations]
            
            # Ensure minimum duration for each scene
            for i in range(len(durations)):
                if durations[i] < min_scene_duration:
                    durations[i] = min_scene_duration
            
            # Adjust again to match total
            actual_total = sum(durations)
            if abs(actual_total - total_duration) > 0.1:
                # Distribute excess or deficit among scenes
                diff = total_duration - actual_total
                per_scene_diff = diff / len(scenes)
                durations = [duration + per_scene_diff for duration in durations]
        
        return durations
    
    @staticmethod
    def redistribute_durations(
        current_durations: List[float],
        index: int,
        operation: str,
        new_duration: Optional[float] = None,
        min_scene_duration: float = 3.0
    ) -> List[float]:
        """
        Redistribute durations when a scene is added, removed, or modified.
        
        Args:
            current_durations: Current list of scene durations
            index: Index of the scene to add, remove, or modify
            operation: Operation to perform ('add', 'remove', or 'modify')
            new_duration: New duration for the scene (only for 'add' or 'modify')
            min_scene_duration: Minimum duration for each scene in seconds
            
        Returns:
            Updated list of scene durations
        """
        if not current_durations and operation != 'add':
            return []
        
        # Calculate total duration
        total_duration = sum(current_durations)
        
        # Create a copy of current durations
        durations = current_durations.copy()
        
        if operation == 'add':
            # Add a new scene
            if new_duration is None:
                # If no duration specified, use minimum
                new_duration = min_scene_duration
            
            # Insert the new duration
            if 0 <= index <= len(durations):
                durations.insert(index, new_duration)
            else:
                durations.append(new_duration)
            
            # Adjust other durations to maintain total
            if len(durations) > 1:
                # Calculate how much to reduce other durations
                excess = new_duration
                num_other_scenes = len(durations) - 1
                per_scene_reduction = excess / num_other_scenes
                
                # Reduce other durations
                for i in range(len(durations)):
                    if i != index:
                        durations[i] = max(min_scene_duration, durations[i] - per_scene_reduction)
        
        elif operation == 'remove':
            # Remove a scene
            if 0 <= index < len(durations):
                removed_duration = durations.pop(index)
                
                # Distribute the removed duration among remaining scenes
                if durations:
                    per_scene_addition = removed_duration / len(durations)
                    durations = [duration + per_scene_addition for duration in durations]
        
        elif operation == 'modify':
            # Modify a scene's duration
            if 0 <= index < len(durations) and new_duration is not None:
                # Calculate the difference
                diff = new_duration - durations[index]
                
                # Update the duration
                durations[index] = new_duration
                
                # Adjust other durations to maintain total
                if len(durations) > 1 and abs(diff) > 0.1:
                    # Calculate how much to adjust other durations
                    num_other_scenes = len(durations) - 1
                    per_scene_adjustment = -diff / num_other_scenes
                    
                    # Adjust other durations
                    for i in range(len(durations)):
                        if i != index:
                            durations[i] = max(min_scene_duration, durations[i] + per_scene_adjustment)
        
        # Ensure all durations are at least the minimum
        for i in range(len(durations)):
            if durations[i] < min_scene_duration:
                durations[i] = min_scene_duration
        
        return durations
    
    @staticmethod
    def adjust_scene_durations(
        scenes: List[Dict[str, Any]],
        target_durations: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Adjust scene durations to match target durations.
        
        Args:
            scenes: List of scene data dictionaries
            target_durations: List of target durations in seconds
            
        Returns:
            Updated list of scene data dictionaries
        """
        if len(scenes) != len(target_durations):
            raise ValueError(
                f"Number of scenes ({len(scenes)}) does not match "
                f"number of target durations ({len(target_durations)})"
            )
        
        # Create a copy of scenes
        updated_scenes = []
        
        for i, scene in enumerate(scenes):
            # Create a copy of the scene
            updated_scene = scene.copy()
            
            # Update the duration
            updated_scene["duration"] = target_durations[i]
            
            # Add to updated scenes
            updated_scenes.append(updated_scene)
        
        return updated_scenes
    
    @staticmethod
    def validate_scene_durations(
        durations: List[float],
        total_duration: float,
        tolerance: float = 0.1
    ) -> bool:
        """
        Validate that scene durations add up to the total duration.
        
        Args:
            durations: List of scene durations
            total_duration: Expected total duration
            tolerance: Tolerance for floating-point comparison
            
        Returns:
            True if valid, False otherwise
        """
        if not durations:
            return True
        
        # Calculate actual total
        actual_total = sum(durations)
        
        # Check if within tolerance
        return abs(actual_total - total_duration) <= tolerance
    
    @staticmethod
    async def adjust_scene_media_durations(
        scenes: List[Dict[str, Any]],
        target_durations: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Adjust the durations of media files in scenes to match target durations.
        
        Args:
            scenes: List of scene data dictionaries with media file paths
            target_durations: List of target durations in seconds
            
        Returns:
            Updated list of scene data dictionaries with adjusted media file paths
        """
        if len(scenes) != len(target_durations):
            raise ValueError(
                f"Number of scenes ({len(scenes)}) does not match "
                f"number of target durations ({len(target_durations)})"
            )
        
        # Create a copy of scenes
        updated_scenes = []
        
        for i, scene in enumerate(scenes):
            # Create a copy of the scene
            updated_scene = scene.copy()
            target_duration = target_durations[i]
            
            # Adjust audio files if present
            if "audio_path" in scene and scene["audio_path"]:
                try:
                    adjusted_audio_path = await AudioDurationAdjuster.adjust_duration(
                        audio_path=scene["audio_path"],
                        target_duration=target_duration,
                        fade_out=True,
                        fade_in=False,
                        preserve_pitch=True
                    )
                    updated_scene["audio_path"] = adjusted_audio_path
                except Exception as e:
                    logger.error(f"Error adjusting audio duration for scene {i}: {e}")
            
            # Adjust video files if present
            if "video_path" in scene and scene["video_path"]:
                try:
                    adjusted_video_path = await VideoDurationAdjuster.adjust_duration(
                        video_path=scene["video_path"],
                        target_duration=target_duration,
                        fade_out=True,
                        fade_in=False,
                        preserve_audio_pitch=True
                    )
                    updated_scene["video_path"] = adjusted_video_path
                except Exception as e:
                    logger.error(f"Error adjusting video duration for scene {i}: {e}")
            
            # Update the duration
            updated_scene["duration"] = target_duration
            
            # Add to updated scenes
            updated_scenes.append(updated_scene)
        
        return updated_scenes
    
    @staticmethod
    def get_transition_durations(
        scenes: List[Dict[str, Any]],
        default_transition_duration: float = 1.0
    ) -> List[float]:
        """
        Get transition durations between scenes.
        
        Args:
            scenes: List of scene data dictionaries
            default_transition_duration: Default transition duration in seconds
            
        Returns:
            List of transition durations in seconds (length is len(scenes) - 1)
        """
        if len(scenes) <= 1:
            return []
        
        transition_durations = []
        
        for i in range(len(scenes) - 1):
            # Try to get transition duration from current scene
            current_scene = scenes[i]
            next_scene = scenes[i + 1]
            
            # Check for transition information in various formats
            transition_duration = None
            
            # Check for transition in current scene
            if "transition" in current_scene:
                transition = current_scene["transition"]
                if isinstance(transition, dict) and "duration" in transition:
                    transition_duration = transition["duration"]
                elif isinstance(transition, str) and transition != "none":
                    transition_duration = default_transition_duration
            
            # Check for transitions list
            if "transitions" in current_scene:
                transitions = current_scene["transitions"]
                if isinstance(transitions, list):
                    for t in transitions:
                        if isinstance(t, dict) and t.get("from") == i + 1 and t.get("to") == i + 2:
                            transition_duration = t.get("duration", default_transition_duration)
                            break
            
            # Use default if no transition found
            if transition_duration is None:
                transition_duration = default_transition_duration
            
            transition_durations.append(float(transition_duration))
        
        return transition_durations
    
    @staticmethod
    def adjust_for_transitions(
        scene_durations: List[float],
        transition_durations: List[float],
        min_scene_duration: float = 3.0
    ) -> List[float]:
        """
        Adjust scene durations to account for transitions.
        
        Args:
            scene_durations: List of scene durations
            transition_durations: List of transition durations
            min_scene_duration: Minimum duration for each scene in seconds
            
        Returns:
            Adjusted list of scene durations
        """
        if len(scene_durations) <= 1:
            return scene_durations
        
        if len(transition_durations) != len(scene_durations) - 1:
            # Pad or truncate transition durations if needed
            if len(transition_durations) < len(scene_durations) - 1:
                # Pad with default transition duration
                transition_durations = transition_durations + [1.0] * (
                    len(scene_durations) - 1 - len(transition_durations)
                )
            else:
                # Truncate
                transition_durations = transition_durations[:len(scene_durations) - 1]
        
        # Calculate total transition duration
        total_transition_duration = sum(transition_durations)
        
        # Calculate total scene duration
        total_scene_duration = sum(scene_durations)
        
        # Calculate adjusted scene durations
        adjusted_durations = []
        for i, duration in enumerate(scene_durations):
            # Calculate transition overlap for this scene
            overlap = 0.0
            if i > 0:
                # Overlap with previous scene
                overlap += transition_durations[i - 1] / 2
            if i < len(scene_durations) - 1:
                # Overlap with next scene
                overlap += transition_durations[i] / 2
            
            # Adjust duration
            adjusted_duration = max(min_scene_duration, duration - overlap)
            adjusted_durations.append(adjusted_duration)
        
        return adjusted_durations
