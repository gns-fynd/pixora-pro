# Pixora AI Codebase Analysis

This document provides a comprehensive analysis of the Pixora AI Video Generation System codebase, identifying function purposes, dependencies, and usage patterns to help optimize and clean up the codebase.

## Directory Structure

### Backend
- [ ] backend/
  - [ ] app/
    - [ ] ai/
      - [ ] agents/
        - [ ] tools/
          - [ ] character_generator.py
          - [ ] music_generator.py
          - [ ] scene_asset_generator.py
          - [ ] scene_generator.py
          - [ ] video_composer.py
        - [ ] video_agent.py
      - [ ] models/
        - [ ] request.py
        - [ ] video_metadata.py
      - [ ] sdk/
        - [ ] agent.py
      - [ ] tasks/
        - [ ] task_manager.py
      - [ ] utils/
        - [ ] json_utils.py
        - [ ] model_converters.py
        - [ ] storage_adapter.py
      - [ ] orchestrator.py
      - [ ] websocket_manager.py
    - [ ] auth/
      - [ ] jwt.py
      - [ ] supabase.py
    - [ ] core/
      - [ ] config.py
    - [ ] routers/
      - [ ] admin.py
      - [ ] agent_chat.py
      - [ ] ai_chat.py
      - [ ] ai_generation.py
      - [ ] auth.py
      - [ ] generation.py
      - [ ] scenes.py
      - [ ] tasks.py
      - [ ] users.py
      - [ ] videos.py
      - [ ] voice_samples.py
      - [ ] websocket_router.py
    - [ ] schemas/
      - [ ] ai_generation.py
      - [ ] generation.py
      - [ ] scene_image.py
      - [ ] user.py
      - [ ] voice_sample.py
    - [ ] services/
      - [ ] fal_ai/
        - [ ] base.py
      - [ ] openai/
        - [ ] service.py
      - [ ] replicate/
        - [ ] base.py
        - [ ] tts.py
      - [ ] storage/
        - [ ] base.py
        - [ ] manager.py
        - [ ] supabase.py
      - [ ] credit_service.py
      - [ ] credits.py
      - [ ] dependencies.py
      - [ ] redis_client.py
      - [ ] supabase.py
      - [ ] voice_sample.py
    - [ ] utils/
      - [ ] logging_config.py
      - [ ] logging_utils.py
    - [ ] main.py

### Frontend
- [ ] src/
  - [ ] components/
  - [ ] pages/
  - [ ] services/
  - [ ] store/
  - [ ] utils/
  - [ ] app.tsx
  - [ ] main.tsx

## Analysis

Let's begin with the backend core components to understand the system architecture.

### Core Components

#### 1. Main Application Entry Point (`backend/app/main.py`)
- [x] backend/app/main.py

**File Purpose**: Main FastAPI application entry point that initializes the application, sets up middleware, and configures routes.

**Key Components**:
- **RequestLoggingMiddleware**: Custom middleware for logging requests and responses with timing information
- **lifespan**: Context manager for application startup and shutdown events
- **global_exception_handler**: Centralized error handling for all unhandled exceptions
- **Routers**: Includes routers for users, videos, auth, ai_generation, and websocket endpoints

**Imports**:
- `fastapi`: Used extensively for the web framework (USED)
- `starlette.middleware`: Used for the BaseHTTPMiddleware (USED)
- `dotenv`: Used to load environment variables (USED)
- `app.utils.logging_config`: Used for setting up logging (USED)
- `app.utils.logging_utils`: Used for request ID generation and logging utilities (USED)
- `app.core.config`: Used to get application settings (USED)
- `app.routers`: Imports various routers (USED)
- `app.ai.websocket_manager`: Used for WebSocket connection management (USED)

**Functions/Classes**:
- `RequestLoggingMiddleware.dispatch(request, call_next)`: Logs request/response details and adds timing headers (USED)
- `lifespan(app)`: Manages application startup/shutdown, initializes WebSocket cleanup (USED)
- `global_exception_handler(request, exc)`: Handles unhandled exceptions with proper logging (USED)
- `health_check()`: Simple health check endpoint (USED)

**Dependencies**:
- Depends on `app.ai.websocket_manager.ConnectionManager` for WebSocket management
- Depends on various routers for API endpoints

#### 2. Application Configuration (`backend/app/core/config.py`)
- [x] backend/app/core/config.py

**File Purpose**: Defines application settings and configuration using Pydantic models, loading values from environment variables.

**Key Components**:
- **Settings**: Pydantic model for application configuration
- **get_settings**: Cached function to retrieve settings

**Imports**:
- `functools.lru_cache`: Used for caching settings (USED)
- `pydantic`: Used for data validation and settings management (USED)
- `pydantic_settings`: Used for loading settings from environment (USED)

**Classes**:
- `Settings`: Defines all application configuration parameters (USED)
  - API settings
  - Security settings (Supabase credentials)
  - Storage configuration
  - AI service API keys
  - Server configuration

**Functions**:
- `get_settings()`: Returns cached Settings instance (USED)

**Dependencies**:
- Depends on environment variables (.env file)

#### 3. AI Orchestrator (`backend/app/ai/orchestrator.py`)
- [x] backend/app/ai/orchestrator.py

**File Purpose**: Coordinates the video generation process, managing tasks, services, and handling the overall workflow.

**Key Components**:
- **VideoOrchestrator**: Main class that orchestrates the video generation process

**Imports**:
- `logging`, `json`, `asyncio`, `datetime`, `uuid`: Standard libraries (USED)
- `fastapi`: For dependency injection and HTTP exceptions (USED)
- `app.core.config`: For application settings (USED)
- `app.services.*`: Various services for AI, storage, and credits (USED)
- `app.ai.models.*`: Data models for tasks and requests (USED)
- `app.ai.tasks.task_manager`: For task management (USED)
- `app.ai.agents.video_agent`: For video generation (USED)
- `app.ai.utils.*`: Utility functions for storage and model conversion (USED)

**Classes**:
- `VideoOrchestrator`: Main orchestrator class (USED)
  - `__init__`: Initializes services and task manager
  - `create_video`: Creates a video generation task
  - `get_task_status`: Retrieves task status
  - `cancel_task`: Cancels a running task
  - `process_unified_request`: Processes a unified generation request

**Dependencies**:
- Depends on `CreditService` for user credit management
- Depends on `RedisClient` for task progress tracking
- Depends on `TaskManager` for task management
- Depends on various AI services (OpenAI, Fal.ai, Replicate)
- Depends on `StorageAdapter` for file storage

**Usage Patterns**:
- Creates tasks via TaskManager
- Processes video requests via the VideoAgent
- Tracks progress in Redis
- Handles errors and updates task status accordingly

### AI Components

#### 4. Video Agent (`backend/app/ai/agents/video_agent.py`)
- [x] backend/app/ai/agents/video_agent.py

**File Purpose**: Main agent responsible for orchestrating the video generation process, coordinating various tools to create a complete video.

**Key Components**:
- **VideoAgent**: Main class that manages the video generation workflow
- **DependencyGraph**: Used to manage task dependencies and parallel execution
- **Helper Functions**: Factory functions to create and use the agent

**Imports**:
- `asyncio`, `logging`: Standard libraries (USED)
- `app.ai.models.*`: Data models for tasks and video metadata (USED)
- `app.ai.agents.utils.*`: Utilities for parallel execution and dependency management (USED)
- `app.services.*`: Various AI services (USED)
- `app.ai.utils.storage_adapter`: Storage adapter for file operations (USED)

**Classes**:
- `VideoAgent`: Main agent class (USED)
  - `__init__`: Initializes services and tools
  - `setup`: Ensures all services and tools are initialized
  - `create_video`: Main method to create a video from a task
  - `_generate_scene_assets`: Helper method to generate assets for all scenes
  - `_compose_video`: Helper method to compose the final video
  - `edit_scene`: Method to edit a specific scene in an existing video

**Functions**:
- `get_video_agent`: Factory function to create a properly initialized VideoAgent (USED)
- `process_video_request`: Function to process a video generation request (USED)
- `process_scene_edit_request`: Function to edit a scene in an existing video (USED)

**Dependencies**:
- Depends on various tools (SceneGeneratorTool, CharacterGeneratorTool, etc.)
- Depends on AI services (OpenAI, Fal.ai, Replicate)
- Depends on StorageAdapter for file operations

**Usage Patterns**:
- Uses a dependency graph to manage task dependencies and parallel execution
- Breaks down the video generation process into discrete steps
- Provides progress updates via callbacks
- Handles errors and updates task status accordingly

#### 5. Character Generator Tool (`backend/app/ai/agents/tools/character_generator.py`)
- [x] backend/app/ai/agents/tools/character_generator.py

**File Purpose**: Tool for generating consistent character profiles with images using AI.

**Key Components**:
- **CharacterGeneratorTool**: Main class for generating character profiles

**Imports**:
- `json`, `logging`, `os`: Standard libraries (USED)
- `app.ai.models.task`: For progress callback type (USED)
- `app.services.openai`: For image generation (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)
- `app.ai.utils.json_utils`: For saving JSON responses (USED)
- `app.ai.models.video_metadata`: For CharacterProfile model (USED)

**Classes**:
- `CharacterGeneratorTool`: Main tool class (USED)
  - `__init__`: Initializes OpenAI service and storage adapter
  - `generate_character_profiles`: Generates profiles for multiple characters
  - `_generate_character_data`: Helper method to generate data for a single character
  - `regenerate_character_image`: Method to regenerate a character image

**Dependencies**:
- Depends on OpenAIService for image generation
- Depends on StorageAdapter for file storage
- Depends on save_json_response for logging responses

**Usage Patterns**:
- Enhances prompts based on the video style
- Generates images using OpenAI's image generation API
- Stores images using the storage adapter
- Provides progress updates via callbacks
- Handles errors gracefully

**Note**: The code mentions "4-angle views" in comments and class description, but the implementation currently generates a single image. This suggests a potential feature that was planned but not fully implemented.

#### 6. Scene Generator Tool (`backend/app/ai/agents/tools/scene_generator.py`)
- [x] backend/app/ai/agents/tools/scene_generator.py

**File Purpose**: Tool for generating scene breakdowns for videos, converting user prompts into structured scene data.

**Key Components**:
- **SceneGeneratorTool**: Main class for generating scene breakdowns

**Imports**:
- `json`, `logging`: Standard libraries (USED)
- `app.ai.models.request`: For StandardVideoMetadata model (USED)
- `app.ai.models.video_metadata`: For VideoMetadata model (USED)
- `app.ai.models.task`: For progress callback type (USED)
- `app.services.openai`: For LLM-based scene generation (USED)
- `app.ai.utils.json_utils`: For saving JSON responses (USED)
- `app.ai.utils.model_converters`: For converting between metadata formats (USED)

**Classes**:
- `SceneGeneratorTool`: Main tool class (USED)
  - `__init__`: Initializes OpenAI service
  - `generate_scene_breakdown`: Generates a scene breakdown from a prompt
  - `_create_system_prompt`: Creates the system prompt for the LLM
  - `_create_user_prompt`: Creates the user prompt for the LLM
  - `_fix_advanced_output_format`: Fixes the output format if needed
  - `_validate_standard_metadata`: Validates the standard metadata

**Dependencies**:
- Depends on OpenAIService for LLM-based scene generation
- Depends on advanced_to_standard_metadata for converting between metadata formats
- Depends on save_json_response for logging responses

**Usage Patterns**:
- Uses OpenAI's structured output generation to create a scene breakdown
- Provides detailed prompts with examples to guide the LLM
- Handles errors and fixes output format issues
- Validates and adjusts scene durations to match the expected total duration
- Provides progress updates via callbacks

#### 7. Scene Asset Generator Tool (`backend/app/ai/agents/tools/scene_asset_generator.py`)
- [x] backend/app/ai/agents/tools/scene_asset_generator.py

**File Purpose**: Tool for generating assets (images, audio, video) for each scene in the video.

**Key Components**:
- **SceneAssetGeneratorTool**: Main class for generating scene assets

**Imports**:
- `json`, `logging`, `os`, `subprocess`: Standard libraries (USED)
- `app.ai.models.video_metadata`: For SceneClip model (USED)
- `app.ai.models.task`: For progress callback type (USED)
- `app.services.openai`: For image generation (USED)
- `app.services.fal_ai`: For image-to-video conversion (USED)
- `app.services.replicate`: For text-to-speech (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)
- `app.ai.utils.json_utils`: For saving JSON responses (USED)

**Classes**:
- `SceneAssetGeneratorTool`: Main tool class (USED)
  - `__init__`: Initializes services
  - `generate_scene_assets`: Generates all assets for a scene
  - `_generate_scene_image`: Generates an image for a scene
  - `_generate_narration_audio`: Generates narration audio for a scene
  - `_get_audio_duration`: Gets the duration of an audio file
  - `_generate_scene_video`: Generates a video for a scene from an image
  - `_create_image_prompt`: Creates a prompt for generating a scene image
  - `regenerate_scene_image`: Regenerates an image for a scene

**Dependencies**:
- Depends on OpenAIService for image generation
- Depends on FalAiService for image-to-video conversion
- Depends on ReplicateService for text-to-speech
- Depends on StorageAdapter for file storage
- Depends on ffprobe (external) for getting audio duration

**Usage Patterns**:
- Generates assets in a specific order: audio → image → video
- Uses the audio duration to determine the video duration
- Handles character consistency by using reference images when available
- Provides fallback mechanisms for failed asset generation
- Handles remote URLs by downloading them to temporary files
- Provides progress updates via callbacks

**Note**: The code includes special handling for character consistency, downloading remote images, and determining audio duration, showing attention to edge cases and robustness.

#### 8. Music Generator Tool (`backend/app/ai/agents/tools/music_generator.py`)
- [x] backend/app/ai/agents/tools/music_generator.py

**File Purpose**: Tool for generating background music for groups of scenes in the video.

**Key Components**:
- **MusicGeneratorTool**: Main class for generating music for scene groups

**Imports**:
- `logging`: Standard library (USED)
- `app.ai.models.video_metadata`: For MusicDefinition model (USED)
- `app.ai.models.task`: For progress callback type (USED)
- `app.services.replicate`: For music generation (USED)
- `app.services.storage.base`: For StorageService type (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)

**Classes**:
- `MusicGeneratorTool`: Main tool class (USED)
  - `__init__`: Initializes Replicate service and storage adapter
  - `generate_music_for_scene_groups`: Generates music for groups of scenes
  - `_calculate_group_duration`: Calculates the total duration for a group of scenes
  - `_generate_music`: Generates music for a group of scenes
  - `regenerate_music`: Regenerates music with a different prompt or style

**Dependencies**:
- Depends on ReplicateService for music generation
- Depends on StorageAdapter for file storage

**Usage Patterns**:
- Calculates the total duration for each group of scenes
- Generates music using Replicate's MusicGen model
- Enhances prompts with style information
- Ensures minimum duration requirements are met
- Provides progress updates via callbacks
- Handles errors gracefully with placeholder audio

#### 9. Video Composer Tool (`backend/app/ai/agents/tools/video_composer.py`)
- [x] backend/app/ai/agents/tools/video_composer.py

**File Purpose**: Tool for composing the final video by combining scene videos, narration audio, and background music.

**Key Components**:
- **VideoComposerTool**: Main class for composing the final video

**Imports**:
- `json`, `logging`, `os`, `tempfile`: Standard libraries (USED)
- `moviepy.editor`: For video editing and composition (USED)
- `app.ai.models.request`: For SceneData model (USED)
- `app.ai.models.task`: For progress callback type (USED)
- `app.services.storage.base`: For StorageService type (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)

**Classes**:
- `VideoComposerTool`: Main tool class (USED)
  - `__init__`: Initializes storage adapter
  - `compose_video`: Composes the final video from scene assets
  - `edit_scene`: Edits a scene in an existing video
  - `extract_scene`: Extracts a single scene as a standalone video

**Dependencies**:
- Depends on MoviePy for video editing and composition
- Depends on StorageAdapter for file storage
- Depends on aiohttp for downloading remote assets

**Usage Patterns**:
- Creates a temporary directory for processing
- Downloads remote assets if needed
- Applies transitions between scenes
- Handles multiple music clips with proper timing
- Mixes narration audio with background music
- Provides progress updates via callbacks
- Handles errors gracefully with placeholder videos
- Cleans up temporary files after processing

**Note**: The code includes robust error handling for various edge cases, such as missing assets, remote URLs, and failed downloads. It also handles complex audio mixing scenarios with multiple music clips.

### Supporting Utilities

#### 10. Storage Adapter (`backend/app/ai/utils/storage_adapter.py`)
- [x] backend/app/ai/utils/storage_adapter.py

**File Purpose**: Provides a unified interface for file storage operations, abstracting the underlying storage system (Supabase).

**Key Components**:
- **StorageAdapter**: Main class for handling file storage operations

**Imports**:
- `os`, `uuid`, `logging`, `pathlib`: Standard libraries (USED)
- `fastapi`: For dependency injection (USED)
- `app.services.storage`: For StorageManager (USED)

**Classes**:
- `StorageAdapter`: Main adapter class (USED)
  - `__init__`: Initializes the storage manager
  - `create_task_directory_structure`: Creates a hierarchical directory structure for a task
  - `create_scene_directory`: Creates a directory structure for a scene
  - `save_video`, `save_image`, `save_audio`: Methods for saving different file types
  - `download_and_store_*`: Methods for downloading and storing files from URLs
  - `get_public_url`, `get_public_url_sync`: Methods for getting public URLs for files
  - `create_temp_directory`, `cleanup_temp_directory`: Methods for temporary directory management
  - `get_local_path`: Gets the local file path from a URL
  - `get_placeholder_*`: Methods for getting placeholder URLs for different file types
  - `save_scene_asset`, `save_music_asset`, `save_final_video`: Methods for saving assets in the hierarchical structure
  - `save_task_metadata`: Saves metadata for the entire task

**Dependencies**:
- Depends on StorageManager for actual storage operations

**Usage Patterns**:
- Provides a unified interface for file storage operations
- Handles both local and remote files
- Creates hierarchical directory structures for tasks and scenes
- Provides placeholder URLs for failed asset generation
- Manages temporary directories for processing
- Handles metadata storage alongside assets

**Note**: The class provides both synchronous and asynchronous versions of some methods, with the synchronous versions being simplified for use in contexts where async/await can't be used.

#### 11. Model Converters (`backend/app/ai/utils/model_converters.py`)
- [x] backend/app/ai/utils/model_converters.py

**File Purpose**: Provides utility functions for converting between different metadata formats used in the system.

**Key Components**:
- **Converter Functions**: Functions for converting between different metadata formats

**Imports**:
- `logging`: Standard library (USED)
- `app.ai.models.request`: For StandardVideoMetadata and SceneData models (USED)
- `app.ai.models.video_metadata`: For VideoMetadata and related models (USED)
- `app.schemas.ai_generation`: For UnifiedGenerationRequest and UnifiedGenerationResponse models (USED)

**Functions**:
- `advanced_to_standard_metadata`: Converts advanced VideoMetadata to standard format (USED)
- `standard_to_advanced_metadata`: Converts standard metadata to advanced format (USED)
- `extract_character_profiles`: Extracts character profiles from advanced metadata (USED)
- `extract_music_definitions`: Extracts music definitions from advanced metadata (USED)
- `unified_request_to_video_request`: Converts a unified request to a video request (USED)
- `video_result_to_unified_response`: Converts a video result to a unified response (USED)

**Usage Patterns**:
- Handles conversion between different metadata formats
- Adjusts scene durations to match expected total duration
- Extracts specific components from metadata
- Ensures backward compatibility with frontend expectations

**Note**: The code includes special handling for scene durations, ensuring they match the expected total duration by scaling them proportionally.

### External Services

#### 12. OpenAI Service (`backend/app/services/openai/service.py`)
- [x] backend/app/services/openai/service.py

**File Purpose**: Provides a service for interacting with OpenAI APIs, including text generation, structured output generation, and image generation.

**Key Components**:
- **OpenAIService**: Main class for interacting with OpenAI APIs
- **ImageGenerationRequest/Response**: Models for image generation requests and responses

**Imports**:
- `logging`, `os`, `asyncio`, `base64`, `tempfile`, `json`: Standard libraries (USED)
- `fastapi`: For dependency injection and HTTP exceptions (USED)
- `pydantic`: For data validation and request/response models (USED)
- `app.core.config`: For application settings (USED)
- `app.services.storage`: For storing generated images (USED)
- `app.ai.models.task`: For progress callback type (USED)

**Classes**:
- `ImageSize`, `ImageQuality`, `ImageStyle`: Enums for image generation parameters (USED)
- `ImageGenerationRequest`: Request model for image generation (USED)
- `ImageGenerationResponse`: Response model for image generation (USED)
- `OpenAIService`: Main service class (USED)
  - `__init__`: Initializes the service with settings and storage manager
  - `setup`: Sets up the OpenAI client and default settings
  - `generate_text`: Generates text using the OpenAI API
  - `generate_structured_output`: Generates structured JSON output
  - `generate_structured_output_from_pydantic`: Generates output as a Pydantic model
  - `generate_image`: Generates images from text prompts
  - `generate_image_with_reference`: Generates images with a reference image
  - `generate_image_variation`: Generates variations of an image
  - `_call_openai_*`: Helper methods for calling OpenAI APIs

**Dependencies**:
- Depends on OpenAI Python client for API calls
- Depends on StorageManager for storing generated images
- Depends on Settings for API keys and configuration

**Usage Patterns**:
- Uses asyncio to run blocking OpenAI API calls in a thread pool
- Handles errors with proper HTTP exceptions
- Provides progress updates via callbacks
- Uploads generated images to storage
- Supports various image generation parameters

#### 13. Fal.ai Service (`backend/app/services/fal_ai/base.py`)
- [x] backend/app/services/fal_ai/base.py

**File Purpose**: Provides a service for interacting with Fal.ai models, particularly for image-to-video conversion.

**Key Components**:
- **FalAiService**: Main class for interacting with Fal.ai models

**Imports**:
- `os`, `logging`, `asyncio`, `time`, `json`: Standard libraries (USED)
- `fal_client`: For interacting with Fal.ai APIs (USED)
- `fastapi`: For dependency injection and HTTP exceptions (USED)
- `app.core.config`: For application settings (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)

**Classes**:
- `FalAiService`: Main service class (USED)
  - `__init__`: Initializes the service with settings
  - `setup`: Sets up the Fal.ai client and API key
  - `_enforce_rate_limit`: Enforces rate limiting to avoid API limits
  - `call_model`: Calls a Fal.ai model with retry logic
  - `upload_file`, `upload_bytes`: Uploads files to storage
  - `image_to_video`: Generates a video from an image

**Dependencies**:
- Depends on fal_client for API calls
- Depends on StorageAdapter for file storage
- Depends on Settings for API keys and configuration

**Usage Patterns**:
- Implements retry logic with exponential backoff
- Enforces rate limiting to avoid API limits
- Handles errors with proper HTTP exceptions
- Provides progress updates via callbacks
- Downloads and stores generated videos

**Note**: The service includes robust error handling and retry logic to deal with API failures, as well as rate limiting to avoid hitting API limits.

#### 14. Replicate Service (`backend/app/services/replicate/base.py`)
- [x] backend/app/services/replicate/base.py

**File Purpose**: Provides a service for interacting with Replicate models, particularly for text-to-speech and music generation.

**Key Components**:
- **ReplicateService**: Main class for interacting with Replicate models

**Imports**:
- `logging`, `os`, `asyncio`: Standard libraries (USED)
- `replicate`: For interacting with Replicate APIs (USED)
- `fastapi`: For dependency injection and HTTP exceptions (USED)
- `app.core.config`: For application settings (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)

**Classes**:
- `ReplicateService`: Main service class (USED)
  - `__init__`: Initializes the service with settings
  - `setup`: Sets up the Replicate client and API token
  - `run_model`: Runs a Replicate model
  - `download_output`: Downloads the output from a model run
  - `handle_binary_response`: Handles binary responses from models
  - `text_to_speech`: Generates speech using LLASA
  - `generate_music`: Generates music using MusicGen

**Dependencies**:
- Depends on replicate Python client for API calls
- Depends on StorageAdapter for file storage
- Depends on Settings for API keys and configuration

**Usage Patterns**:
- Uses asyncio to run blocking Replicate API calls in a thread pool
- Handles binary responses by saving them to storage
- Provides progress updates via callbacks
- Handles errors with proper HTTP exceptions
- Supports various model parameters

**Note**: The service includes special handling for binary responses, which can be audio, image, or video files. It also includes specific implementations for text-to-speech and music generation.

#### 15. Text-to-Speech Service (`backend/app/services/replicate/tts.py`)
- [x] backend/app/services/replicate/tts.py

**File Purpose**: Provides a specialized service for text-to-speech generation using Replicate's LLASA model.

**Key Components**:
- **VoiceCloneTTSService**: Main class for text-to-speech generation
- **TTSRequest/Response**: Models for TTS requests and responses

**Imports**:
- `logging`: Standard library (USED)
- `fastapi`: For dependency injection and HTTP exceptions (USED)
- `pydantic`: For data validation and request/response models (USED)
- `app.core.config`: For application settings (USED)
- `app.services.replicate.base`: For ReplicateService (USED)
- `app.ai.utils.storage_adapter`: For file storage (USED)

**Classes**:
- `TTSRequest`: Request model for text-to-speech (USED)
- `TTSResponse`: Response model for text-to-speech (USED)
- `VoiceCloneTTSService`: Main service class (USED)
  - `__init__`: Initializes the service with ReplicateService
  - `generate_speech`: Generates speech from text
  - `_generate_speech_chunked`: Handles long text by breaking it into chunks
  - `_combine_audio_files`: Combines multiple audio files into one

**Dependencies**:
- Depends on ReplicateService for model execution
- Depends on StorageAdapter for file storage
- Depends on ffmpeg (external) for combining audio files

**Usage Patterns**:
- Handles long text by breaking it into chunks
- Combines audio chunks using ffmpeg
- Provides progress updates via callbacks
- Handles errors with proper HTTP exceptions
- Estimates audio duration based on text length

**Note**: The service includes special handling for long text, breaking it into chunks and then combining the resulting audio files. It also includes fallback mechanisms for error handling.

### Storage Services

#### 16. Storage Service Base (`backend/app/services/storage/base.py`)
- [x] backend/app/services/storage/base.py

**File Purpose**: Defines the abstract base class for storage services, providing a common interface for all storage implementations.

**Key Components**:
- **StorageService**: Abstract base class for storage services

**Imports**:
- `abc`: For abstract base class definition (USED)
- `typing`: For type hints (USED)

**Classes**:
- `StorageService`: Abstract base class (USED)
  - `upload_file`: Upload a file to storage
  - `download_file`: Download a file from storage
  - `get_file_url`: Get the URL for a file
  - `delete_file`: Delete a file from storage
  - `list_files`: List files in a bucket
  - `create_bucket`: Create a new bucket
  - `delete_bucket`: Delete a bucket

**Usage Patterns**:
- Defines a common interface for all storage implementations
- Uses abstract methods to enforce implementation of required methods
- Provides clear method signatures with type hints

**Note**: This is a pure interface class with no implementation details, following the Interface Segregation Principle from SOLID design principles.

#### 17. Storage Manager (`backend/app/services/storage/manager.py`)
- [x] backend/app/services/storage/manager.py

**File Purpose**: Provides a unified interface for storage operations, abstracting away the underlying storage implementation.

**Key Components**:
- **StorageManager**: Main class for handling file operations

**Imports**:
- `os`, `uuid`, `time`, `datetime`, `logging`: Standard libraries (USED)
- `fastapi`: For dependency injection (USED)
- `app.core.config`: For application settings (USED)
- `app.services.storage.base`: For StorageService interface (USED)
- `app.services.storage.supabase`: For SupabaseStorageService implementation (USED)

**Classes**:
- `StorageManager`: Main manager class (USED)
  - `__init__`: Initializes the storage manager with a storage service
  - `upload_video`, `upload_image`, `upload_audio`: Methods for uploading different file types
  - `upload_file_from_url`: Downloads a file from a URL and uploads it to storage
  - `delete_file`: Deletes a file from storage
  - `get_file_url`: Gets the URL for a file
  - `list_files`: Lists files in a bucket
  - `_construct_path`: Helper method to construct a path for a file
  - `_get_extension_from_content_type`: Helper method to get a file extension from a MIME type

**Dependencies**:
- Depends on StorageService for actual storage operations
- Depends on Settings for bucket names and other configuration

**Usage Patterns**:
- Provides a simplified interface for common storage operations
- Handles file naming and path construction
- Supports uploading from URLs
- Organizes files by date and user ID

**Note**: The class follows the Facade pattern, providing a simplified interface to the more complex storage service implementations.

#### 18. Supabase Storage Service (`backend/app/services/storage/supabase.py`)
- [x] backend/app/services/storage/supabase.py

**File Purpose**: Provides a concrete implementation of the StorageService interface using Supabase Storage.

**Key Components**:
- **SupabaseStorageService**: Implementation of StorageService using Supabase

**Imports**:
- `io`, `os`, `mimetypes`, `logging`: Standard libraries (USED)
- `httpx`: For HTTP requests (USED)
- `fastapi`: For dependency injection (USED)
- `supabase`: For Supabase client (USED)
- `app.core.config`: For application settings (USED)
- `app.services.storage.base`: For StorageService interface (USED)

**Classes**:
- `SupabaseStorageService`: Supabase implementation of StorageService (USED)
  - `__init__`: Initializes the Supabase client and settings
  - `upload_file`: Uploads a file to Supabase storage
  - `download_file`: Downloads a file from Supabase storage
  - `get_file_url`: Gets the URL for a file in Supabase storage
  - `delete_file`: Deletes a file from Supabase storage
  - `list_files`: Lists files in a Supabase storage bucket
  - `create_bucket`: Creates a new bucket in Supabase storage
  - `delete_bucket`: Deletes a bucket from Supabase storage

**Dependencies**:
- Depends on Supabase Python client for API calls
- Depends on Settings for Supabase credentials and configuration

**Usage Patterns**:
- Implements all methods required by the StorageService interface
- Handles bucket creation and management
- Supports public and private buckets
- Provides robust error handling

**Note**: The implementation includes special handling for bucket creation and public access policies, ensuring that buckets are properly configured for the application's needs.

### Conclusion

This comprehensive analysis of the Pixora AI Video Generation System codebase has identified the key components, their purposes, dependencies, and usage patterns. The system follows a modular architecture with clear separation of concerns, making it maintainable and extensible.

The core components include:
1. The Orchestrator, which coordinates the entire video generation process
2. The Video Agent, which manages the video generation workflow
3. Various tools for specific tasks (character generation, scene generation, etc.)
4. External services for AI capabilities (OpenAI, Fal.ai, Replicate)
5. Storage services for managing generated assets

The system uses a combination of AI models to generate scripts, scenes, character profiles, images, audio, and finally compose them into a complete video. The modular design allows for easy replacement or enhancement of individual components without affecting the rest of the system.

The identified issues, such as duplicate TTS implementations and method name mismatches, can be addressed to improve the system's robustness and maintainability.
