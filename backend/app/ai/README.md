# Pixora AI Video Generation Agent

This directory contains the implementation of the Pixora AI video generation agent, which is responsible for generating videos from user prompts.

## Architecture

The video generation agent is structured as follows:

### Models

- `models/task.py`: Defines the Task model for tracking video generation tasks.
- `models/video_metadata.py`: Defines the VideoMetadata model for storing video metadata.
- `models/request.py`: Defines request and response models for the video generation API.

### Tasks

- `tasks/task_manager.py`: Manages asynchronous video generation tasks, including task creation, execution, and progress tracking.

### Agents

- `agents/video_agent.py`: The main video agent that orchestrates the video generation process.
- `agents/tools/`: Contains specialized tools for different aspects of video generation:
  - `scene_generator.py`: Generates scene breakdowns from user prompts.
  - `character_generator.py`: Generates character profiles with consistent appearances.
  - `scene_asset_generator.py`: Generates assets for scenes (images, audio, video).
  - `music_generator.py`: Generates background music for scenes.
  - `video_composer.py`: Composes the final video from scene assets.
- `agents/utils/`: Contains utility functions for the agents:
  - `dependency_graph.py`: Manages task dependencies and parallel execution.
  - `parallel.py`: Provides utilities for parallel execution of tasks.

### Utils

- `utils/model_converters.py`: Converts between different model formats.
- `utils/json_utils.py`: Provides utilities for working with JSON data.

### Orchestrator

- `orchestrator.py`: The main orchestrator that integrates with the FastAPI application and manages the video generation process.

## Flow

1. The user submits a video generation request through the `/ai/generate` endpoint.
2. The request is processed by the `VideoOrchestrator` which creates a task and starts the video generation process.
3. The `VideoAgent` breaks down the process into steps:
   - Generate a scene breakdown from the user prompt
   - Generate character profiles if needed
   - Generate assets for each scene (images, audio)
   - Generate background music
   - Compose the final video
4. The progress is tracked and reported back to the user.
5. The final video URL is returned to the user.

## Integration

The video agent is integrated with the FastAPI application through the `ai_generation.py` router, which provides endpoints for video generation, task status checking, and task cancellation.

## Dependencies

The video agent depends on several external services:

- OpenAI API for generating scene breakdowns and character profiles
- Fal.ai API for generating images and videos
- Replicate API for generating audio and music
- Redis for task progress tracking
- Supabase for storage and database operations

## Configuration

The video agent is configured through the application settings in `core/config.py`.
