# Pixora AI Codebase Documentation

This document provides a detailed analysis of the Pixora AI Video Generation System codebase, documenting each module, function, class, their parameters, purposes, and return values.

## Backend

### Core Components

#### backend/app/main.py

**File Purpose**: Main FastAPI application entry point that initializes the application, sets up middleware, and configures routes.

**Classes**:
- `RequestLoggingMiddleware`: Custom middleware for logging requests and responses
  - `__init__(self, app)`: Initializes the middleware with the FastAPI app
  - `dispatch(self, request, call_next)`: Processes requests, logs timing information, and adds headers
    - Parameters: `request` (Request), `call_next` (Callable)
    - Returns: `Response` object with timing headers

**Functions**:
- `lifespan(app)`: Context manager for application startup and shutdown events
  - Parameters: `app` (FastAPI)
  - Purpose: Initializes services and cleans up resources on shutdown
  - Returns: None
- `global_exception_handler(request, exc)`: Centralized error handling for all unhandled exceptions
  - Parameters: `request` (Request), `exc` (Exception)
  - Purpose: Logs exceptions and returns appropriate error responses
  - Returns: `JSONResponse` with error details
- `health_check()`: Simple health check endpoint
  - Parameters: None
  - Purpose: Verifies the API is running
  - Returns: `dict` with status message

**Dependencies**:
- FastAPI for web framework
- Starlette middleware for HTTP middleware
- App routers for API endpoints
- WebSocket manager for real-time communication

**Usage Patterns**:
- Initializes FastAPI application with middleware and exception handlers
- Configures CORS for cross-origin requests
- Includes routers for various API endpoints
- Sets up WebSocket connections for real-time updates

#### backend/app/core/config.py

**File Purpose**: Defines application settings and configuration using Pydantic models, loading values from environment variables.

**Classes**:
- `Settings`: Pydantic model for application configuration
  - Inherits from `BaseSettings` to load values from environment variables
  - Fields include:
    - API settings (API_V1_STR, PROJECT_NAME)
    - Security settings (SUPABASE_URL, SUPABASE_KEY, etc.)
    - Storage settings (bucket names, public URL)
    - AI service API keys (FAL_API_KEY, OPENAI_API_KEY, etc.)
    - Fal.ai model endpoints
    - Server configuration (HOST, PORT, RELOAD, etc.)
  - `model_config`: Configuration for environment variable loading

**Functions**:
- `get_settings()`: Cached function to retrieve settings
  - Parameters: None
  - Purpose: Loads settings from environment variables with caching
  - Returns: `Settings` instance
  - Decorated with `@lru_cache` to avoid loading .env file multiple times

**Dependencies**:
- Pydantic for data validation and settings management
- pydantic_settings for loading settings from environment variables
- functools.lru_cache for caching settings

**Usage Patterns**:
- Used as a dependency in FastAPI endpoints and services
- Provides centralized configuration for the entire application
- Loads values from .env file and environment variables
- Validates configuration values using Pydantic

#### backend/run.py

**File Purpose**: Script to start the FastAPI server for the Pixora AI backend.

**Functions**:
- Main script execution block (`if __name__ == "__main__"`)
  - Purpose: Starts the uvicorn server with the FastAPI application
  - Loads environment variables using dotenv
  - Configures server settings (host, port, reload mode)
  - Runs the uvicorn server with the FastAPI app

**Variables**:
- `host`: Server host address (default: "0.0.0.0")
- `port`: Server port number (default: 8000)
- `reload`: Whether to enable auto-reload for development (default: True)

**Dependencies**:
- uvicorn for ASGI server
- dotenv for loading environment variables
- os and sys standard libraries

**Usage Patterns**:
- Used as the main entry point for running the backend server
- Configures server settings from environment variables
- Provides informative console output about server status

#### backend/run_server.py

**File Purpose**: Script to run the Pixora AI server with WebSocket implementation.

**Functions**:
- Main script execution block (`if __name__ == "__main__"`)
  - Purpose: Starts the uvicorn server with the FastAPI application
  - Loads environment variables using dotenv
  - Configures server port from environment variables
  - Runs the uvicorn server with the FastAPI app

**Variables**:
- `port`: Server port number (default: 8000)

**Dependencies**:
- uvicorn for ASGI server
- dotenv for loading environment variables
- os standard library

**Usage Patterns**:
- Alternative entry point for running the backend server
- Specifically mentions WebSocket implementation
- Simpler than run.py with fewer configurable options
- Always uses "0.0.0.0" as host and enables reload mode

#### backend/test_websocket.py

**File Purpose**: Test script for the WebSocket implementation, connecting to the server and sending messages.

**Functions**:
- `test_websocket(token, server_url, prompt)`: Tests WebSocket by connecting and sending a chat message
  - Parameters: `token` (str), `server_url` (str), `prompt` (str)
  - Purpose: Connects to WebSocket server, authenticates, sends a message, and processes responses
  - Returns: None
  - Async function that handles various message types from the server

- `test_command(token, server_url, command, params)`: Tests a command via WebSocket
  - Parameters: `token` (str), `server_url` (str), `command` (str), `params` (dict)
  - Purpose: Connects to WebSocket server, authenticates, sends a command, and processes responses
  - Returns: None
  - Async function that handles command results and errors

- `get_token(server_url, supabase_token)`: Gets a JWT token from the server
  - Parameters: `server_url` (str), `supabase_token` (str)
  - Purpose: Exchanges a Supabase token for a JWT token
  - Returns: JWT token (str)
  - Uses aiohttp to make a POST request to the auth endpoint

- `main()`: Main entry point for the script
  - Parameters: None
  - Purpose: Parses command-line arguments and runs the appropriate test
  - Returns: None
  - Handles token acquisition and command/chat message testing

**Dependencies**:
- asyncio for asynchronous operations
- websockets for WebSocket client
- json for message serialization/deserialization
- uuid for generating unique task IDs
- argparse for command-line argument parsing
- aiohttp for HTTP requests
- dotenv for loading environment variables

**Usage Patterns**:
- Used as a testing tool for the WebSocket implementation
- Supports both chat messages and commands
- Handles various message types from the server (tokens, tool calls, progress updates, etc.)
- Provides flexible authentication options (direct token, Supabase token, environment variable)

### AI Module Components

#### backend/app/ai/agent.py

**File Purpose**: Provides the main agent orchestrator for the Pixora AI platform, coordinating various AI services to create videos from prompts.

**Classes**:
- `AgentOrchestrator`: Main orchestrator class for AI agents
  - `__init__(self, text_to_image_service, image_to_video_service, text_to_speech_service, text_to_music_service, credit_service, storage_manager, prompt_analyzer, settings)`: Initializes the orchestrator with various services
    - Parameters: Various service dependencies and settings
  - `create_video(self, prompt, user_id, aspect_ratio, duration, style, callback)`: Creates a video from a prompt
    - Parameters: `prompt` (str), `user_id` (str), `aspect_ratio` (str), `duration` (int), `style` (Optional[str]), `callback` (Optional[Callable])
    - Returns: Dict with video creation result
  - `_calculate_total_cost(self, prompt, duration, aspect_ratio)`: Calculates the cost of creating a video
    - Parameters: `prompt` (str), `duration` (int), `aspect_ratio` (str)
    - Returns: Total cost in credits (int)
  - `_analyze_prompt(self, prompt, style)`: Analyzes the prompt and generates a script
    - Parameters: `prompt` (str), `style` (Optional[str])
    - Returns: Script (Dict[str, Any])
  - `_break_down_script(self, script, duration)`: Breaks down the script into scenes
    - Parameters: `script` (Dict[str, Any]), `duration` (int)
    - Returns: List of scenes (List[Dict[str, Any]])
  - `_generate_scene_images(self, scenes, user_id)`: Generates images for each scene
    - Parameters: `scenes` (List[Dict[str, Any]]), `user_id` (str)
    - Returns: Dict mapping scene IDs to image URLs
  - `_generate_scene_videos(self, scenes, scene_images, user_id, aspect_ratio)`: Generates videos for each scene
    - Parameters: `scenes` (List[Dict[str, Any]]), `scene_images` (Dict[str, str]), `user_id` (str), `aspect_ratio` (str)
    - Returns: Dict mapping scene IDs to video URLs
  - `_generate_voiceover(self, script, user_id)`: Generates voiceover for the script
    - Parameters: `script` (Dict[str, Any]), `user_id` (str)
    - Returns: Dict with voiceover URL and duration
  - `_generate_background_music(self, script, duration, user_id)`: Generates background music
    - Parameters: `script` (Dict[str, Any]), `duration` (int), `user_id` (str)
    - Returns: Music URL (str)
  - `_update_progress(self, task_id, progress, message, callback)`: Updates task progress
    - Parameters: `task_id` (str), `progress` (float), `message` (Optional[str]), `callback` (Optional[Callable])
  - `get_scene_breakdown_intro(self, prompt)`: Generates an introduction message for scene breakdown
    - Parameters: `prompt` (str)
    - Returns: Introduction message (str)
  - `get_generation_started_message(self)`: Generates a message when generation starts
    - Returns: Message (str)
  - `get_generation_completed_message(self)`: Generates a message when generation completes
    - Returns: Message (str)
  - `process_chat_message(self, message, video_id, user_id)`: Processes a chat message
    - Parameters: `message` (str), `video_id` (str), `user_id` (str)
    - Returns: AI response with actions or updates (Dict[str, Any])
  - `_handle_scene_edit(self, intent, video, scenes, user_id)`: Handles scene edit requests
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `scenes` (List[Dict[str, Any]]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_handle_voice_change(self, intent, video, user_id)`: Handles voice change requests
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_handle_music_change(self, intent, video, user_id)`: Handles music change requests
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_generate_suggestion_actions(self, intent, video, scenes)`: Generates suggestion actions
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `scenes` (List[Dict[str, Any]])
    - Returns: List of suggested actions (List[Dict[str, Any]])
  - `_get_video(self, video_id)`: Gets a video by ID
    - Parameters: `video_id` (str)
    - Returns: Video data (Dict[str, Any])
  - `_get_scenes(self, video_id)`: Gets scenes for a video
    - Parameters: `video_id` (str)
    - Returns: Scenes data (List[Dict[str, Any]])
  - `_update_scene(self, scene_id, updates)`: Updates a scene in the database
    - Parameters: `scene_id` (str), `updates` (Dict[str, Any])
  - `get_progress(self, task_id)`: Gets the progress of a task
    - Parameters: `task_id` (str)
    - Returns: Progress data (Dict[str, Any])

**Dependencies**:
- TextToImageService for generating images from text
- ImageToVideoService for generating videos from images
- TextToSpeechService for generating voiceovers
- TextToMusicService for generating background music
- CreditService for managing user credits
- StorageManager for file storage
- PromptAnalyzer for OpenAI integration
- Settings for application configuration

**Usage Patterns**:
- Coordinates the entire video generation process
- Breaks down the process into discrete steps (script generation, scene breakdown, asset generation, etc.)
- Handles user credits and refunds for failed operations
- Provides progress tracking and callbacks
- Supports interactive chat for video editing and customization
- Implements fallback mechanisms for error handling

#### backend/app/ai/orchestrator.py

**File Purpose**: Provides the main agent orchestrator for video generation, integrating the new video agent implementation.

**Classes**:
- `VideoOrchestrator`: Main orchestrator class for video generation
  - `__init__(self, credit_service, redis_client, settings, openai_service, fal_ai_service, replicate_service, storage_service)`: Initializes the orchestrator with various services
    - Parameters: Various service dependencies and settings
  - `create_video(self, request, user_id)`: Creates a video from a request
    - Parameters: `request` (VideoRequest), `user_id` (str)
    - Returns: TaskResponse with task ID and status
  - `get_task_status(self, task_id, user_id)`: Gets the status of a task
    - Parameters: `task_id` (str), `user_id` (str)
    - Returns: TaskStatusModel with task status information
  - `cancel_task(self, task_id, user_id)`: Cancels a task
    - Parameters: `task_id` (str), `user_id` (str)
    - Returns: Boolean indicating success
  - `process_unified_request(self, request, task_id, user_id)`: Processes a unified generation request for video
    - Parameters: `request` (Dict[str, Any]), `task_id` (str), `user_id` (str)
    - Returns: Dict with result information

**Dependencies**:
- CreditService for managing user credits
- RedisClient for task progress tracking
- TaskManager for managing asynchronous tasks
- VideoAgent for video generation
- OpenAIService, FalAiService, ReplicateService for AI model access
- StorageAdapter for file storage
- Various models for request/response handling

**Usage Patterns**:
- Serves as the entry point for video generation requests
- Creates and manages tasks for asynchronous processing
- Tracks task progress and status using Redis
- Handles error cases and provides appropriate responses
- Supports unified request format for integration with other systems
- Enforces user permissions for task access

#### backend/app/ai/prompt_analyzer.py

**File Purpose**: Provides a service for analyzing prompts and generating video scripts using OpenAI's GPT models.

**Classes**:
- `PromptAnalyzer`: Service for analyzing prompts and generating video scripts
  - `__init__(self, settings)`: Initializes the prompt analyzer with settings
    - Parameters: `settings` (Settings)
  - `analyze_prompt(self, prompt, style)`: Analyzes a prompt and generates a video script
    - Parameters: `prompt` (str), `style` (Optional[str])
    - Returns: Script (Dict[str, Any])
  - `generate_scene_breakdown(self, script, duration)`: Generates a scene breakdown from a script
    - Parameters: `script` (Dict[str, Any]), `duration` (int)
    - Returns: List of scenes (List[Dict[str, Any]])
  - `analyze_chat_message(self, message, video, scenes)`: Analyzes a chat message to determine intent
    - Parameters: `message` (str), `video` (Dict[str, Any]), `scenes` (List[Dict[str, Any]])
    - Returns: Analyzed intent with action details (Dict[str, Any])
  - `generate_contextual_response(self, context_type, context_data)`: Generates a contextual response
    - Parameters: `context_type` (str), `context_data` (Optional[Dict[str, Any]])
    - Returns: Contextual response (str)
  - `select_voice(self, video_content)`: Selects an appropriate voice based on video content
    - Parameters: `video_content` (Dict[str, Any])
    - Returns: Voice selection details (Dict[str, Any])
  - `generate_image_prompts(self, scenes)`: Generates image prompts for each scene
    - Parameters: `scenes` (List[Dict[str, Any]])
    - Returns: Dict mapping scene IDs to image prompts
  - `_call_openai(self, system_message, user_message)`: Calls the OpenAI API
    - Parameters: `system_message` (str), `user_message` (str)
    - Returns: Response from the API (str)
  - `_parse_response(self, response, prompt, style)`: Parses the response from the OpenAI API
    - Parameters: `response` (str), `prompt` (str), `style` (Optional[str])
    - Returns: Parsed script (Dict[str, Any])
  - `_parse_scenes(self, response, duration)`: Parses the scene breakdown from the OpenAI API
    - Parameters: `response` (str), `duration` (int)
    - Returns: Parsed scenes (List[Dict[str, Any]])
  - `_parse_image_prompts(self, response, scenes)`: Parses the image prompts from the OpenAI API
    - Parameters: `response` (str), `scenes` (List[Dict[str, Any]])
    - Returns: Parsed image prompts (Dict[str, str])

**Dependencies**:
- OpenAI client for GPT model access
- Settings for application configuration
- JSON for parsing and formatting responses
- Logging for error tracking

**Usage Patterns**:
- Provides natural language processing for video generation
- Structures prompts for optimal results from GPT models
- Handles parsing and validation of model responses
- Implements fallback mechanisms for error handling
- Supports various video-related tasks (script generation, scene breakdown, chat analysis, etc.)
- Uses system and user messages to guide the model's responses

#### backend/app/ai/video_generator.py

**File Purpose**: Provides a service for generating videos from prompts, handling the video generation process in the background.

**Classes**:
- `VideoGenerator`: Service for generating videos from prompts
  - Class variables:
    - `progress`: Dictionary for tracking progress of all tasks
    - `background_tasks`: Dictionary for storing results of completed tasks
  - `__init__(self, agent_orchestrator, prompt_analyzer, credit_service, storage_manager, settings)`: Initializes the video generator with various services
    - Parameters: Various service dependencies and settings
  - `generate_video(self, prompt, user_id, aspect_ratio, duration, style, background_tasks)`: Generates a video from a prompt
    - Parameters: `prompt` (str), `user_id` (str), `aspect_ratio` (str), `duration` (int), `style` (Optional[str]), `background_tasks` (Optional[BackgroundTasks])
    - Returns: Dict with task ID and initial status
  - `get_video_status(self, task_id)`: Gets the status of a video generation task
    - Parameters: `task_id` (str)
    - Returns: Dict with task status and progress information
  - `_generate_video_task(self, task_id, prompt, user_id, aspect_ratio, duration, style, total_cost, callback)`: Generates a video in the background
    - Parameters: `task_id` (str), `prompt` (str), `user_id` (str), `aspect_ratio` (str), `duration` (int), `style` (Optional[str]), `total_cost` (int), `callback` (Callable)
    - Async function that handles the actual video generation process
  - `_calculate_total_cost(self, prompt, duration, aspect_ratio)`: Calculates the cost of generating a video
    - Parameters: `prompt` (str), `duration` (int), `aspect_ratio` (str)
    - Returns: Total cost in credits (int)
  - `_update_progress(self, progress, message, task_id, user_id)`: Updates the progress of a task
    - Parameters: `progress` (float), `message` (Optional[str]), `task_id` (Optional[str]), `user_id` (Optional[str])

**Dependencies**:
- AgentOrchestrator for coordinating the video generation process
- PromptAnalyzer for analyzing prompts and generating scripts
- CreditService for managing user credits
- StorageManager for file storage
- BackgroundTasks for asynchronous processing
- UUID for generating unique task IDs

**Usage Patterns**:
- Provides a high-level API for video generation
- Handles asynchronous processing using background tasks
- Tracks progress and status of video generation tasks
- Manages user credits for video generation
- Implements error handling and credit refunds for failed operations
- Uses callbacks for progress updates

#### backend/app/ai/websocket_manager.py

**File Purpose**: Provides a connection manager for WebSocket connections, enabling real-time communication with clients.

**Classes**:
- `ConnectionManager`: Manages WebSocket connections for real-time communication
  - `__init__(self)`: Initializes an empty connection manager
    - Initializes dictionaries for tracking connections, user tasks, and activity
  - `connect(self, task_id, websocket, user_id)`: Registers a new WebSocket connection
    - Parameters: `task_id` (str), `websocket` (WebSocket), `user_id` (Optional[str])
  - `disconnect(self, task_id, websocket, user_id)`: Removes a WebSocket connection
    - Parameters: `task_id` (str), `websocket` (WebSocket), `user_id` (Optional[str])
  - `send_message(self, task_id, message)`: Sends a message to all connections for a task
    - Parameters: `task_id` (str), `message` (Any)
  - `broadcast_to_user(self, user_id, message)`: Sends a message to all connections for a user
    - Parameters: `user_id` (str), `message` (Any)
  - `send_progress_update(self, task_id, progress, stage, message, substage, eta)`: Sends a progress update
    - Parameters: `task_id` (str), `progress` (int), `stage` (str), `message` (str), `substage` (Optional[str]), `eta` (Optional[float])
  - `send_detailed_progress(self, task_id, progress, stage, substage, message, eta, completed_steps, current_step, pending_steps)`: Sends detailed progress
    - Parameters: Various progress details including steps information
  - `send_tool_execution(self, task_id, tool_name, parameters, result)`: Sends tool execution update
    - Parameters: `task_id` (str), `tool_name` (str), `parameters` (Dict[str, Any]), `result` (Union[str, Dict[str, Any]])
  - `send_chat_message(self, task_id, role, content, metadata)`: Sends a chat message
    - Parameters: `task_id` (str), `role` (str), `content` (str), `metadata` (Optional[Dict[str, Any]])
  - `send_completion(self, task_id, result)`: Sends a completion message
    - Parameters: `task_id` (str), `result` (Dict[str, Any])
  - `send_error(self, task_id, error, error_type, recovery_options)`: Sends an error message
    - Parameters: `task_id` (str), `error` (str), `error_type` (Optional[str]), `recovery_options` (Optional[List[Dict[str, Any]]])
  - `send_task_control(self, task_id, action, params)`: Sends a task control message
    - Parameters: `task_id` (str), `action` (str), `params` (Optional[Dict[str, Any]])
  - `send_feedback_request(self, task_id, item_type, item_id, options, preview_url, message, timeout)`: Sends a feedback request
    - Parameters: Various feedback request details
  - `get_connection_count(self, task_id)`: Gets the number of active connections for a task
    - Parameters: `task_id` (str)
    - Returns: Number of connections (int)
  - `get_user_task_count(self, user_id)`: Gets the number of active tasks for a user
    - Parameters: `user_id` (str)
    - Returns: Number of tasks (int)
  - `get_connection_statistics(self)`: Gets statistics about active connections
    - Returns: Dictionary of statistics (Dict[str, Any])
  - `get_idle_connections(self, idle_threshold_seconds)`: Gets connections idle longer than threshold
    - Parameters: `idle_threshold_seconds` (int)
    - Returns: Dictionary of idle connections (Dict[str, List[WebSocket]])
  - `schedule_periodic_cleanup(self, interval_seconds, idle_threshold_seconds)`: Schedules periodic cleanup
    - Parameters: `interval_seconds` (int), `idle_threshold_seconds` (int)
  - `cleanup_idle_connections(self, idle_threshold_seconds)`: Disconnects idle connections
    - Parameters: `idle_threshold_seconds` (int)
    - Returns: Number of connections closed (int)

**Dependencies**:
- FastAPI WebSocket for WebSocket connections
- Starlette WebSocketState for connection state tracking
- Logging for error tracking
- Time module for tracking activity times
- Asyncio for asynchronous operations

**Usage Patterns**:
- Manages real-time communication with clients via WebSockets
- Tracks active connections by task ID and user ID
- Provides methods for sending various types of messages (progress updates, chat messages, etc.)
- Handles disconnections and cleanup of idle connections
- Collects statistics about active connections
- Supports broadcasting messages to all connections for a task or user

#### backend/app/ai/models/request.py

**File Purpose**: Defines request and response models for the video generation API using Pydantic.

**Enums**:
- `VideoStyle`: Defines available video styles
  - Values: REALISTIC, CARTOON, ANIME, CINEMATIC, ARTISTIC, VINTAGE, FUTURISTIC
  - Used to control the visual style of generated videos

**Classes**:
- `VideoRequest`: Request model for video creation
  - Fields:
    - `prompt` (str): The prompt describing the video to create
    - `duration` (int): Duration of the video in seconds (5-120)
    - `style` (VideoStyle): Style of the video (default: REALISTIC)
    - `voice_sample_url` (Optional[str]): URL to a voice sample for TTS
  - Includes example JSON schema

- `TaskResponse`: Response model for task creation
  - Fields:
    - `task_id` (str): Unique identifier for the task
    - `status` (str): Current status of the task
  - Includes example JSON schema

- `TaskStatus`: Response model for task status
  - Fields:
    - `task_id` (str): Unique identifier for the task
    - `status` (str): Current status of the task
    - `progress` (int): Progress percentage (0-100)
    - `video_url` (Optional[str]): URL of the generated video if completed
    - `error` (Optional[str]): Error message if task failed
    - `stage` (Optional[str]): Current stage of the task
    - `updated_at` (Optional[datetime]): Last update time
  - Includes example JSON schema

- `SceneData`: Model for scene data
  - Fields:
    - `description` (str): Description of the scene
    - `narration` (str): Narration script for the scene
    - `duration` (float): Duration of the scene in seconds
    - `style_params` (Dict[str, Any]): Style parameters for the scene
    - `characters` (List[str]): Characters in the scene
    - `transition` (Optional[str]): Transition to the next scene

- `StandardVideoMetadata`: Model for standard video metadata
  - Fields:
    - `scenes` (List[SceneData]): List of scenes in the video
    - `needs_character_consistency` (bool): Whether character consistency is needed
    - `characters` (List[Dict[str, Any]]): Character profiles
    - `style` (Dict[str, Any]): Global style parameters
    - `transitions` (List[Dict[str, Any]]): Transition specifications
    - `duration` (int): Total duration in seconds
    - `mood` (str): Overall mood of the video (default: "neutral")

- `VideoGenerationPreferences`: Model for video generation preferences
  - Fields:
    - `style` (VideoStyle): Style of the video (default: REALISTIC)
    - `duration` (int): Duration of the video in seconds (5-120)
    - `voice_sample_url` (Optional[str]): URL to a voice sample for TTS
    - `character_consistency` (bool): Whether character consistency is needed
    - `quality` (str): Quality of the generated video (default: "standard")
    - `aspect_ratio` (str): Aspect ratio of the video (default: "16:9")
  - Includes example JSON schema

- `UnifiedVideoRequest`: Unified request model for video generation
  - Fields:
    - `prompt` (str): The prompt describing the video to create
    - `preferences` (VideoGenerationPreferences): Preferences for video generation
    - `reference_files` (Optional[List[str]]): URLs of reference files
  - Includes example JSON schema

**Dependencies**:
- Pydantic for data validation and model definitions
- Python typing for type annotations
- Enum for enumeration types
- Datetime for timestamp handling

**Usage Patterns**:
- Used for input validation and type conversion in API endpoints
- Provides standardized request and response structures
- Enforces validation constraints (e.g., duration limits)
- Includes example schemas for documentation and testing
- Supports both basic and advanced video generation requests
- Facilitates standardized communication between frontend and backend

### Agent System Components

#### backend/app/ai/agent/controller.py

**File Purpose**: Defines the main entry point for the Pixora AI Agent, managing tasks, tools, and conversation memory.

**Classes**:
- `AgentController`: Main controller for the Pixora AI Agent
  - `__init__(self, user_id, redis_client, settings)`: Initializes the agent controller
    - Parameters: `user_id` (str), `redis_client` (RedisClient), `settings` (Settings)
    - Initializes components and registers tools
  - `_register_tools(self)`: Registers all available tools with the tool registry
    - Registers various tools for script generation, image generation, audio generation, video tools, and utility tools
  - `process_message_async(self, message, task_id, context, progress_callback)`: Processes a user message asynchronously
    - Parameters: `message` (str), `task_id` (Optional[str]), `context` (Optional[Dict[str, Any]]), `progress_callback` (Optional[Callable])
    - Returns: Task object
  - `_execute_task(self, task)`: Executes a task asynchronously
    - Parameters: `task` (Task)
    - Handles task execution and memory updates
  - `get_task(self, task_id)`: Gets a task by ID
    - Parameters: `task_id` (str)
    - Returns: Task object if found, None otherwise
  - `get_task_status(self, task_id)`: Gets the status of a task
    - Parameters: `task_id` (str)
    - Returns: Dictionary with task status
  - `list_user_tasks(self)`: Lists all task IDs for the current user
    - Returns: List of task IDs
  - `clear_memory(self)`: Clears the conversation memory
    - Resets the agent's memory

**Dependencies**:
- RedisClient for persistence
- Settings for application configuration
- ToolRegistry for managing available tools
- TaskManager for managing tasks
- ConversationMemory for storing conversation history
- Various tool implementations for different functionalities

**Usage Patterns**:
- Serves as the main entry point for the AI agent system
- Manages user-specific tasks and conversation memory
- Registers and provides access to various tools
- Handles asynchronous task execution
- Provides methods for task management and status tracking
- Maintains conversation context across interactions

#### backend/app/ai/agent/memory.py

**File Purpose**: Provides conversation memory functionality for the Pixora AI Agent, allowing it to maintain context across multiple interactions.

**Classes**:
- `ConversationMemory`: Manages conversation history for the Pixora AI Agent
  - `__init__(self, user_id, redis_client, max_history)`: Initializes conversation memory
    - Parameters: `user_id` (str), `redis_client` (RedisClient), `max_history` (int, default=10)
    - Sets up memory storage with user-specific key
  - `add_interaction(self, prompt, response, actions)`: Adds a new interaction to the conversation history
    - Parameters: `prompt` (str), `response` (str), `actions` (List[Dict[str, Any]])
    - Stores the interaction with timestamp and trims history if needed
  - `get_memory(self)`: Gets the conversation memory
    - Returns: List of conversation turns (List[Dict[str, Any]])
  - `get_context(self, max_turns)`: Gets recent conversation context for the system prompt
    - Parameters: `max_turns` (int, default=5)
    - Returns: String containing formatted conversation context
  - `clear(self)`: Clears the conversation history
    - Deletes the memory from Redis

**Dependencies**:
- RedisClient for persistent storage of conversation history
- Datetime for timestamping interactions

**Usage Patterns**:
- Stores conversation history in Redis with user-specific keys
- Provides formatted conversation context for AI prompts
- Limits history size to prevent excessive token usage
- Maintains chronological order of interactions
- Supports clearing conversation history when needed

#### backend/app/ai/agent/orchestrator.py

**File Purpose**: Provides the main agent orchestrator for the Pixora AI platform, integrating various AI services for video generation with parallel processing capabilities.

**Classes**:
- `AgentOrchestrator`: AI agent orchestrator for the Pixora AI platform
  - `__init__(self, text_to_image_service, image_to_video_service, voice_cloning_tts_service, text_to_music_service, credit_service, storage_manager, prompt_analyzer, redis_client, settings)`: Initializes the orchestrator with various services
    - Parameters: Various service dependencies and settings
  - `agent_llm(self, messages, temperature, response_format)`: Calls the OpenAI API with the given messages
    - Parameters: `messages` (List[Dict[str, str]]), `temperature` (float), `response_format` (Optional[Dict[str, str]])
    - Returns: Response from the API (str)
  - `_update_progress_json(self, task_id, progress, message)`: Updates the progress of a task in Redis
    - Parameters: `task_id` (str), `progress` (float), `message` (str)
  - `create_video(self, prompt, user_id, aspect_ratio, duration, style, callback)`: Creates a video from a prompt with parallel processing
    - Parameters: `prompt` (str), `user_id` (str), `aspect_ratio` (str), `duration` (int), `style` (Optional[str]), `callback` (Optional[Callable])
    - Returns: Dict with video creation result
  - `_calculate_total_cost(self, prompt, duration, aspect_ratio)`: Calculates the cost of creating a video
    - Parameters: `prompt` (str), `duration` (int), `aspect_ratio` (str)
    - Returns: Total cost in credits (int)
  - `_analyze_prompt(self, prompt, style)`: Analyzes the prompt and generates a script using OpenAI
    - Parameters: `prompt` (str), `style` (Optional[str])
    - Returns: Script (Dict[str, Any])
  - `_break_down_script(self, script, duration)`: Breaks down the script into scenes using OpenAI
    - Parameters: `script` (Dict[str, Any]), `duration` (int)
    - Returns: List of scenes (List[Dict[str, Any]])
  - `_generate_scene_images(self, scenes, user_id)`: Generates images for each scene in parallel
    - Parameters: `scenes` (List[Dict[str, Any]]), `user_id` (str)
    - Returns: Dict mapping scene IDs to image URLs
  - `_generate_scene_videos(self, scenes, scene_images, user_id, aspect_ratio)`: Generates videos for each scene in parallel
    - Parameters: `scenes` (List[Dict[str, Any]]), `scene_images` (Dict[str, str]), `user_id` (str), `aspect_ratio` (str)
    - Returns: Dict mapping scene IDs to video URLs
  - `_generate_scene_voiceovers(self, scenes, user_id)`: Generates voiceovers for all scenes in parallel
    - Parameters: `scenes` (List[Dict[str, Any]]), `user_id` (str)
    - Returns: Dict mapping scene IDs to voiceover data
  - `_generate_voiceover(self, script, user_id)`: Generates voiceover for the script
    - Parameters: `script` (Dict[str, Any]), `user_id` (str)
    - Returns: Dict with voiceover URL and duration
  - `_generate_background_music(self, script, duration, user_id)`: Generates background music for the video
    - Parameters: `script` (Dict[str, Any]), `duration` (int), `user_id` (str)
    - Returns: Music URL (str)
  - `_update_progress(self, task_id, progress, message, callback)`: Updates task progress
    - Parameters: `task_id` (str), `progress` (float), `message` (Optional[str]), `callback` (Optional[Callable])
  - `get_scene_breakdown_intro(self, prompt)`: Generates an introduction message for scene breakdown
    - Parameters: `prompt` (str)
    - Returns: Introduction message (str)
  - `get_generation_started_message(self)`: Generates a message when generation starts
    - Returns: Message (str)
  - `get_generation_completed_message(self)`: Generates a message when generation completes
    - Returns: Message (str)
  - `process_chat_message(self, message, video_id, user_id)`: Processes a chat message from the user
    - Parameters: `message` (str), `video_id` (str), `user_id` (str)
    - Returns: AI response with actions or updates (Dict[str, Any])
  - `_handle_scene_edit(self, intent, video, scenes, user_id)`: Handles a scene edit request
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `scenes` (List[Dict[str, Any]]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_handle_voice_change(self, intent, video, user_id)`: Handles a voice change request
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_handle_music_change(self, intent, video, user_id)`: Handles a music change request
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `user_id` (str)
    - Returns: Response with updates (Dict[str, Any])
  - `_generate_suggestion_actions(self, intent, video, scenes)`: Generates suggestion actions based on the intent
    - Parameters: `intent` (Dict[str, Any]), `video` (Dict[str, Any]), `scenes` (List[Dict[str, Any]])
    - Returns: List of suggested actions (List[Dict[str, Any]])
  - `_get_video(self, video_id)`: Gets a video by ID
    - Parameters: `video_id` (str)
    - Returns: Video data (Dict[str, Any])
  - `_get_scenes(self, video_id)`: Gets scenes for a video
    - Parameters: `video_id` (str)
    - Returns: Scenes data (List[Dict[str, Any]])
  - `_update_scene(self, scene_id, updates)`: Updates a scene in the database
    - Parameters: `scene_id` (str), `updates` (Dict[str, Any])
  - `get_progress(self, task_id)`: Gets the progress of a task
    - Parameters: `task_id` (str)
    - Returns: Progress data (Dict[str, Any])
  - `analyze_intent(self, prompt, video_id, scene_id, reference_files, preferences, client_context)`: Analyzes the user's prompt to determine the intent
    - Parameters: Various context parameters
    - Returns: Dict with intent analysis
  - `process_by_intent(self, intent, prompt, task_id, user_id, video_id, scene_id, reference_files, preferences, client_context)`: Processes the user's request based on the determined intent
    - Parameters: Various request parameters
    - Returns: Result dictionary with data appropriate for the intent
  - Various intent handler methods (`_handle_generate_script`, `_handle_generate_video`, etc.)
    - Handle specific intents with appropriate processing logic

**Dependencies**:
- TextToImageService for generating images from text
- ImageToVideoService for generating videos from images
- VoiceCloneTTSService for generating voiceovers
- TextToMusicService for generating background music
- CreditService for managing user credits
- StorageManager for file storage
- PromptAnalyzer for OpenAI integration
- RedisClient for task progress tracking
- Settings for application configuration
- AsyncOpenAI for LLM access

**Usage Patterns**:
- Coordinates the entire video generation process with parallel processing
- Provides a unified interface for various AI generation intents
- Handles asynchronous task execution and progress tracking
- Manages user credits and refunds for failed operations
- Implements retry logic and fallback mechanisms for error handling
- Supports interactive chat for video editing and customization
- Uses Redis for persistent progress tracking

#### backend/app/ai/agent/task.py

**File Purpose**: Defines the Task class for managing individual tasks in the Pixora AI Agent system.

**Classes**:
- `Task`: Represents a single task to be executed by the agent
  - `__init__(self, task_id, prompt, user_id, tool_registry, redis_client, model_name, conversation_context, context)`: Initializes a task
    - Parameters: `task_id` (str), `prompt` (str), `user_id` (str), `tool_registry` (ToolRegistry), `redis_client` (RedisClient), `model_name` (str), `conversation_context` (str), `context` (Optional[Dict[str, Any]])
    - Sets up task state and configuration
  - `set_progress_callback(self, callback)`: Sets a callback function for progress updates
    - Parameters: `callback` (Callable[[float, str], None])
  - `update_progress(self, progress, status)`: Updates the task progress
    - Parameters: `progress` (float), `status` (str)
    - Updates progress, calls callback, and persists to Redis
  - `add_message(self, role, content, tool_calls)`: Adds a message to the task history
    - Parameters: `role` (str), `content` (str), `tool_calls` (Optional[List[Dict[str, Any]]])
    - Adds message to history and updates Redis
  - `add_action(self, action)`: Adds an action to the task history
    - Parameters: `action` (Dict[str, Any])
    - Adds action to history and updates Redis
  - `clear_updates(self)`: Clears the updates flag and current actions
  - `set_error(self, error)`: Sets an error for the task
    - Parameters: `error` (str)
    - Updates task state and persists to Redis
  - `set_result(self, result, message)`: Sets the result for the task
    - Parameters: `result` (Dict[str, Any]), `message` (str)
    - Updates task state and persists to Redis
  - `_update_task_in_redis(self)`: Updates the task state in Redis
    - Async method that persists task state
  - `execute(self)`: Executes the task and returns the result
    - Returns: Dict with final response and actions taken
    - Main method that orchestrates task execution
  - `_get_agent_response(self)`: Gets the agent's response to the current state
    - Returns: OpenAI API response
    - Calls OpenAI API with prepared messages
  - `_process_response(self, response)`: Processes the agent's response and executes tools
    - Parameters: `response` (Any)
    - Returns: Dict with final response and actions
    - Handles tool calls and recursive execution
  - `_execute_tool(self, tool_call)`: Executes a tool and returns the result
    - Parameters: `tool_call` (Any)
    - Returns: Tool result as string
    - Calls the appropriate tool from the registry
  - `_prepare_messages(self)`: Prepares the messages for the API call
    - Returns: List of messages for OpenAI API
    - Formats messages with system prompt and history
  - `_get_system_prompt(self)`: Gets the system prompt for the agent
    - Returns: System prompt as string
    - Builds prompt with base instructions and context

**Dependencies**:
- ToolRegistry for accessing available tools
- RedisClient for persistence
- AsyncOpenAI for LLM access
- JSON for parsing tool arguments
- Asyncio for asynchronous operations

**Usage Patterns**:
- Represents a single user request as a task
- Manages the conversation flow with the LLM
- Handles tool execution based on LLM decisions
- Tracks progress and provides updates
- Persists state to Redis for recovery and monitoring
- Implements a recursive execution pattern for multi-step tasks
- Provides a clean interface for task execution and monitoring

#### backend/app/ai/agent/task_manager.py

**File Purpose**: Defines the TaskManager class for managing tasks with Redis-based persistence and queuing.

**Classes**:
- `TaskManager`: Manages tasks for the agent with Redis-based persistence
  - `__init__(self, tool_registry, redis_client)`: Initializes the task manager
    - Parameters: `tool_registry` (ToolRegistry), `redis_client` (RedisClient)
    - Sets up task registry and Redis client
  - `create_task(self, prompt, user_id, conversation_context, context, model_name)`: Creates a new task from a user prompt
    - Parameters: `prompt` (str), `user_id` (str), `conversation_context` (str), `context` (Optional[Dict[str, Any]]), `model_name` (str)
    - Returns: Task object
    - Generates unique task ID and stores task in memory and Redis
  - `get_task(self, task_id)`: Gets a task by ID
    - Parameters: `task_id` (str)
    - Returns: Task object if found, None otherwise
    - Checks memory first, then Redis
  - `list_user_tasks(self, user_id)`: Lists all task IDs for a user
    - Parameters: `user_id` (str)
    - Returns: List of task IDs
    - Retrieves task IDs from Redis
  - `get_task_status(self, task_id)`: Gets the status of a task
    - Parameters: `task_id` (str)
    - Returns: Dictionary with task status information
    - Retrieves task status from Redis

**Dependencies**:
- ToolRegistry for accessing available tools
- RedisClient for persistence and queuing
- Task class for task representation
- UUID and time modules for generating unique IDs

**Usage Patterns**:
- Manages the lifecycle of tasks from creation to completion
- Provides persistence for tasks using Redis
- Enables task retrieval by ID or user ID
- Supports task status monitoring
- Acts as a factory for Task objects
- Maintains an in-memory cache of active tasks

#### backend/app/ai/agents/video_agent.py

**File Purpose**: Provides the main video agent for orchestrating the video generation process with an improved workflow.

**Classes**:
- `VideoAgent`: Main video agent for orchestrating the video generation process
  - `__init__(self, openai_service, fal_ai_service, replicate_service, storage_service)`: Initializes the video agent
    - Parameters: Various service dependencies (all optional)
    - Initializes services and tools to None
  - `setup(self)`: Sets up the video agent with all required services and tools
    - Initializes services if they are None
    - Initializes tools if they are None
  - `create_video(self, task, progress_callback)`: Creates a video based on task parameters
    - Parameters: `task` (Task), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the generated video (str)
    - Orchestrates the entire video generation process
  - `_generate_scene_assets(self, clips, style, character_profiles, voice_character_url, progress_callback)`: Generates assets for all scenes in parallel
    - Parameters: `clips` (List[ClipData]), `style` (str), `character_profiles` (Dict[str, Dict[str, Any]]), `voice_character_url` (Optional[str]), `progress_callback` (Optional[ProgressCallback])
    - Returns: Dictionary mapping scene indexes to their assets
  - `_compose_video(self, scene_assets, music_urls, transitions, task_id, progress_callback)`: Composes the final video from scene assets and music
    - Parameters: `scene_assets` (Dict[int, Dict[str, Any]]), `music_urls` (Dict[int, str]), `transitions` (List[Dict[str, Any]]), `task_id` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the generated video (str)
  - `edit_scene(self, task, scene_index, new_prompt, progress_callback)`: Edits a scene in an existing video
    - Parameters: `task` (Task), `scene_index` (int), `new_prompt` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the updated video (str)

**Functions**:
- `get_video_agent(openai_service, fal_ai_service, replicate_service, storage_service)`: Factory function to create a properly initialized VideoAgent
  - Parameters: Various service dependencies (all optional)
  - Returns: Initialized VideoAgent instance
  - Ensures all tools are properly initialized
- `process_video_request(task, progress_callback, openai_service, fal_ai_service, replicate_service, storage_service)`: Processes a video generation request
  - Parameters: `task` (Task), `progress_callback` (Optional[ProgressCallback]), various service dependencies
  - Returns: URL of the generated video (str)
  - Creates a video agent and delegates to it
- `process_scene_edit_request(task, scene_index, new_prompt, progress_callback, openai_service, fal_ai_service, replicate_service, storage_service)`: Processes a scene edit request
  - Parameters: `task` (Task), `scene_index` (int), `new_prompt` (str), `progress_callback` (Optional[ProgressCallback]), various service dependencies
  - Returns: URL of the updated video (str)
  - Creates a video agent and delegates to it

**Dependencies**:
- OpenAIService for text generation and analysis
- FalAiService for image and video generation
- ReplicateService for audio generation
- StorageAdapter for file storage
- Various tools for specific tasks (scene generation, character generation, etc.)
- DependencyGraph for managing task dependencies
- ParallelExecutor for parallel execution of tasks

**Usage Patterns**:
- Orchestrates the entire video generation process
- Uses a dependency graph to manage task dependencies
- Executes tasks in parallel where possible
- Provides progress tracking and callbacks
- Supports scene editing for existing videos
- Implements lazy initialization of services and tools
- Uses factory functions for proper initialization

#### backend/app/ai/agents/tools/character_generator.py

**File Purpose**: Provides a tool for generating consistent character profiles with 4-angle views for video generation.

**Classes**:
- `CharacterGeneratorTool`: Tool for generating consistent character profiles with 4-angle views
  - `__init__(self, openai_service, storage_service)`: Initializes the character generator tool
    - Parameters: `openai_service` (Optional[OpenAIService]), `storage_service` (Optional[StorageAdapter])
    - Initializes services with defaults if not provided
  - `generate_character_profiles(self, character_profiles, style, progress_callback)`: Generates consistent character profiles with 4-angle reference images
    - Parameters: `character_profiles` (List[CharacterProfile]), `style` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: Dictionary mapping character names to their profiles with image URLs
    - Processes each character profile and generates images
  - `_generate_character_data(self, profile, style, progress_callback)`: Generates data for a single character
    - Parameters: `profile` (CharacterProfile), `style` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: Character data with images (Dict[str, Any])
    - Creates enhanced prompts based on style and generates images
  - `regenerate_character_image(self, profile, style, progress_callback)`: Regenerates a character image with a different prompt or style
    - Parameters: `profile` (CharacterProfile), `style` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: Updated character data with new images (Dict[str, Any])
    - Allows for regenerating specific character images

**Dependencies**:
- OpenAIService for image generation
- StorageAdapter for file storage
- CharacterProfile model for character data
- ProgressCallback type for progress updates
- JSON utilities for saving responses

**Usage Patterns**:
- Enhances character prompts based on video style
- Generates high-quality character images using OpenAI's image generation
- Stores images using the storage adapter
- Provides progress tracking during generation
- Handles errors gracefully with fallback images
- Supports regeneration of specific character images
- Saves character data to JSON files for persistence

#### backend/app/ai/agents/tools/music_generator.py

**File Purpose**: Provides a tool for generating background music for groups of scenes in video generation.

**Classes**:
- `MusicGeneratorTool`: Tool for generating music for groups of scenes
  - `__init__(self, replicate_service, storage_service)`: Initializes the music generator tool
    - Parameters: `replicate_service` (Optional[ReplicateService]), `storage_service` (Optional[StorageService])
    - Initializes services with defaults if not provided
  - `generate_music_for_scene_groups(self, music_definitions, scene_assets, style, progress_callback)`: Generates music for groups of scenes
    - Parameters: `music_definitions` (List[MusicDefinition]), `scene_assets` (Dict[int, Dict[str, Any]]), `style` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: Dictionary mapping scene indexes to music URLs
    - Processes each music definition and generates appropriate music
  - `_calculate_group_duration(self, scene_indexes, scene_assets)`: Calculates the total duration for a group of scenes
    - Parameters: `scene_indexes` (List[int]), `scene_assets` (Dict[int, Dict[str, Any]])
    - Returns: Total duration in seconds (int)
    - Sums up the durations of all scenes in the group
  - `_generate_music(self, prompt, duration, style)`: Generates music for a group of scenes
    - Parameters: `prompt` (str), `duration` (int), `style` (str)
    - Returns: URL of the generated music (str)
    - Enhances the prompt with style information and generates music
  - `regenerate_music(self, prompt, duration, style, progress_callback)`: Regenerates music with a different prompt or style
    - Parameters: `prompt` (str), `duration` (int), `style` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the regenerated music (str)
    - Allows for regenerating specific music tracks

**Dependencies**:
- ReplicateService for music generation
- StorageAdapter for file storage
- MusicDefinition model for music data
- ProgressCallback type for progress updates

**Usage Patterns**:
- Calculates appropriate music durations based on scene lengths
- Enhances music prompts with style information
- Generates background music using Replicate's music generation models
- Stores music files using the storage adapter
- Provides progress tracking during generation
- Handles errors gracefully with fallback audio
- Supports regeneration of specific music tracks
- Groups scenes together for consistent musical themes

#### backend/app/ai/agents/tools/scene_asset_generator.py

**File Purpose**: Provides a tool for generating assets (images, audio, videos) for scenes with TTS-based duration.

**Classes**:
- `SceneAssetGeneratorTool`: Tool for generating assets for a scene with TTS-based duration
  - `__init__(self, openai_service, fal_ai_service, replicate_service, storage_service)`: Initializes the scene asset generator tool
    - Parameters: `openai_service` (Optional[OpenAIService]), `fal_ai_service` (Optional[FalAiService]), `replicate_service` (Optional[ReplicateService]), `storage_service` (Optional[StorageAdapter])
    - Initializes services with defaults if not provided
  - `generate_scene_assets(self, scene, style, character_profiles, voice_character_url, progress_callback)`: Generates all assets for a scene in the correct order
    - Parameters: `scene` (SceneClip), `style` (str), `character_profiles` (Optional[Dict[str, Dict[str, Any]]]), `voice_character_url` (Optional[str]), `progress_callback` (Optional[ProgressCallback])
    - Returns: Dictionary with asset URLs and metadata
    - Orchestrates the generation of narration audio, scene image, and scene video
  - `_generate_scene_image(self, scene, style, character_profiles)`: Generates an image for a scene
    - Parameters: `scene` (SceneClip), `style` (str), `character_profiles` (Optional[Dict[str, Dict[str, Any]]])
    - Returns: URL of the generated image (str)
    - Creates image prompts and handles character consistency
  - `_generate_narration_audio(self, script, voice_character_url)`: Generates narration audio for a scene
    - Parameters: `script` (str), `voice_character_url` (Optional[str])
    - Returns: URL of the generated audio (str)
    - Uses Replicate's TTS model for voice generation
  - `_get_audio_duration(self, audio_url)`: Gets the duration of an audio file
    - Parameters: `audio_url` (str)
    - Returns: Duration of the audio in seconds (float)
    - Uses ffprobe to determine audio duration
  - `_generate_scene_video(self, image_url, scene, style, duration)`: Generates a video for a scene from an image
    - Parameters: `image_url` (str), `scene` (SceneClip), `style` (str), `duration` (float)
    - Returns: URL of the generated video (str)
    - Uses Fal.ai's image-to-video service
  - `_create_image_prompt(self, scene, style, character_profiles)`: Creates a prompt for generating a scene image
    - Parameters: `scene` (SceneClip), `style` (str), `character_profiles` (Optional[Dict[str, Dict[str, Any]]])
    - Returns: Image generation prompt (str)
    - Enhances prompts with style and character information
  - `regenerate_scene_image(self, scene, style, character_profiles, progress_callback)`: Regenerates an image for a scene
    - Parameters: `scene` (SceneClip), `style` (str), `character_profiles` (Optional[Dict[str, Dict[str, Any]]]), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the regenerated image (str)
    - Allows for regenerating specific scene images

**Dependencies**:
- OpenAIService for image generation
- FalAiService for image-to-video conversion
- ReplicateService for text-to-speech
- StorageAdapter for file storage
- SceneClip model for scene data
- ProgressCallback type for progress updates
- Subprocess for running ffprobe to get audio duration
- JSON utilities for parsing ffprobe output

**Usage Patterns**:
- Orchestrates the generation of all assets for a scene
- Generates assets in the correct order (audio first to determine video duration)
- Handles character consistency in image generation
- Enhances prompts based on style and character information
- Provides progress tracking during generation
- Handles errors gracefully with fallback assets
- Supports regeneration of specific scene images
- Uses ffprobe to determine audio durations
- Downloads remote images when needed for video generation

#### backend/app/ai/agents/tools/scene_generator.py

**File Purpose**: Provides a tool for generating scene breakdowns for videos with detailed structure, including scenes, characters, and music.

**Classes**:
- `SceneGeneratorTool`: Tool for generating scene breakdowns for videos with detailed structure
  - `__init__(self, openai_service)`: Initializes the scene generator tool
    - Parameters: `openai_service` (Optional[OpenAIService])
    - Initializes OpenAI service with default if not provided
  - `generate_scene_breakdown(self, prompt, duration, style, voice_sample_url, progress_callback)`: Generates a scene breakdown for a video
    - Parameters: `prompt` (str), `duration` (int), `style` (str), `voice_sample_url` (Optional[str]), `progress_callback` (Optional[ProgressCallback])
    - Returns: Tuple containing (VideoMetadata, StandardVideoMetadata)
    - Generates detailed scene breakdown with characters, music, and clips
  - `_create_system_prompt(self, duration, style)`: Creates the system prompt for the LLM
    - Parameters: `duration` (int), `style` (str)
    - Returns: System prompt (str)
    - Provides detailed instructions for the LLM
  - `_create_user_prompt(self, prompt, duration, style, voice_sample_url)`: Creates the user prompt for the LLM
    - Parameters: `prompt` (str), `duration` (int), `style` (str), `voice_sample_url` (Optional[str])
    - Returns: User prompt (str)
    - Formats the user's request with examples and requirements
  - `_fix_advanced_output_format(self, raw_output, prompt, voice_sample_url)`: Fixes the advanced output format if needed
    - Parameters: `raw_output` (Dict[str, Any]), `prompt` (str), `voice_sample_url` (Optional[str])
    - Returns: Fixed output (Dict[str, Any])
    - Ensures all required fields are present and properly formatted
  - `_validate_standard_metadata(self, metadata, expected_duration)`: Validates the standard metadata
    - Parameters: `metadata` (StandardVideoMetadata), `expected_duration` (int)
    - Adjusts scene durations and ensures transitions are properly formatted

**Dependencies**:
- OpenAIService for LLM access
- VideoMetadata and StandardVideoMetadata models for data structures
- ProgressCallback type for progress updates
- JSON utilities for saving responses
- Model converters for transforming between metadata formats

**Usage Patterns**:
- Generates detailed scene breakdowns with characters, music, and clips
- Uses OpenAI's structured output generation for consistent JSON responses
- Handles error cases by fixing and validating output formats
- Provides progress tracking during generation
- Saves scene breakdowns to JSON files for persistence
- Adjusts scene durations to match expected total duration
- Ensures character consistency when needed
- Validates and fixes transitions between scenes

#### backend/app/ai/agents/tools/video_composer.py

**File Purpose**: Provides a tool for composing the final video from scene assets, including video clips, audio, and background music.

**Classes**:
- `VideoComposerTool`: Tool for composing the final video from scene assets
  - `__init__(self, storage_service)`: Initializes the video composer tool
    - Parameters: `storage_service` (Optional[StorageService])
    - Initializes storage adapter
  - `compose_video(self, scene_assets, music_urls, transitions, task_id, progress_callback)`: Composes the final video from scene assets
    - Parameters: `scene_assets` (List[Dict[str, Any]]), `music_urls` (List[str]), `transitions` (List[Dict[str, Any]]), `task_id` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the final video (str)
    - Processes scene videos, adds audio, applies transitions, and adds background music
  - `edit_scene(self, scene_index, scene_assets, new_scene_assets, music_urls, transitions, task_id, progress_callback)`: Edits a scene in an existing video
    - Parameters: `scene_index` (int), `scene_assets` (List[Dict[str, Any]]), `new_scene_assets` (Dict[str, Any]), `music_urls` (List[str]), `transitions` (List[Dict[str, Any]]), `task_id` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the updated video (str)
    - Updates a specific scene and recomposes the video
  - `extract_scene(self, scene_index, scene_assets, task_id, progress_callback)`: Extracts a single scene as a standalone video
    - Parameters: `scene_index` (int), `scene_assets` (List[Dict[str, Any]]), `task_id` (str), `progress_callback` (Optional[ProgressCallback])
    - Returns: URL of the extracted scene video (str)
    - Returns the URL of a specific scene video

**Dependencies**:
- MoviePy for video editing and composition
- StorageAdapter for file storage and retrieval
- ProgressCallback type for progress updates
- Tempfile for creating temporary directories
- OS module for file path operations
- Aiohttp for downloading remote files

**Usage Patterns**:
- Composes final videos from individual scene assets
- Handles both local and remote video/audio files
- Applies transitions between scenes
- Adds background music with appropriate volume levels
- Loops or trims music to match video duration
- Provides progress tracking during composition
- Handles errors gracefully with fallback videos
- Supports editing specific scenes in existing videos
- Creates temporary directories for processing
- Cleans up temporary files after processing

#### backend/app/ai/agents/tools/audio_generator.py

**File Purpose**: Provides tools for generating narration audio and background music for video scenes.

**Classes**:
- `AudioGeneratorTool`: Tool for generating audio for scenes
  - `__init__(self, tts_service, replicate_service, storage_adapter)`: Initializes the audio generator tool
    - Parameters: `tts_service` (VoiceCloneTTSService), `replicate_service` (ReplicateService), `storage_adapter` (HierarchicalStorageAdapter)
    - Initializes services with dependency injection
  - `generate_narration(self, task_id, scene_index, script, voice_sample_url, user_id, progress_callback)`: Generates narration audio for a scene
    - Parameters: `task_id` (str), `scene_index` (int), `script` (str), `voice_sample_url` (Optional[str]), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with audio information (Dict[str, Any])
    - Generates narration using TTS service and stores it
  - `regenerate_narration(self, task_id, scene_index, new_script, voice_sample_url, user_id, progress_callback)`: Regenerates narration audio for a scene
    - Parameters: `task_id` (str), `scene_index` (int), `new_script` (str), `voice_sample_url` (Optional[str]), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with audio information (Dict[str, Any])
    - Regenerates narration with new script
  - `generate_music(self, task_id, mood, duration, genre, user_id, progress_callback)`: Generates background music
    - Parameters: `task_id` (str), `mood` (str), `duration` (int), `genre` (str), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with music information (Dict[str, Any])
    - Generates music using Replicate service
  - `_download_audio(self, url)`: Downloads audio from a URL
    - Parameters: `url` (str)
    - Returns: The audio data as bytes
    - Uses httpx for async HTTP requests

**Functions**:
- `generate_narration_tool(ctx, scene_index, script, voice_type)`: Function tool for OpenAI Assistants API to generate narration
  - Parameters: `ctx` (Context), `scene_index` (int), `script` (str), `voice_type` (str)
  - Returns: Dictionary with audio information (Dict[str, Any])
  - Handles context and progress tracking
- `regenerate_scene_audio_tool(ctx, scene_index, new_script, voice_character_url)`: Function tool for OpenAI Assistants API to regenerate scene audio
  - Parameters: `ctx` (Context), `scene_index` (int), `new_script` (str), `voice_character_url` (Optional[str])
  - Returns: Dictionary with audio information (Dict[str, Any])
  - Updates context with new audio information
- `generate_music_tool(ctx, mood, duration, genre)`: Function tool for OpenAI Assistants API to generate background music
  - Parameters: `ctx` (Context), `mood` (str), `duration` (int), `genre` (str)
  - Returns: Dictionary with music information (Dict[str, Any])
  - Stores music information in context

**Dependencies**:
- VoiceCloneTTSService for voice cloning and TTS
- ReplicateService for music generation
- HierarchicalStorageAdapter for file storage
- FastAPI Depends for dependency injection
- httpx for async HTTP requests
- Logging for error tracking

**Usage Patterns**:
- Generates narration audio using text-to-speech with voice cloning
- Creates background music based on mood and genre
- Provides progress tracking during generation
- Handles errors gracefully with status reporting
- Stores generated audio in hierarchical storage
- Supports regeneration of narration with different scripts
- Uses OpenAI Assistants API function tools for integration
- Updates context with generated audio information
- Limits music generation duration to Replicate's constraints

#### backend/app/ai/agents/tools/image_generator.py

**File Purpose**: Provides tools for generating and regenerating images for scenes in videos.

**Classes**:
- `ImageGeneratorTool`: Tool for generating images for scenes
  - `__init__(self, openai_service, storage_adapter)`: Initializes the image generator tool
    - Parameters: `openai_service` (OpenAIService), `storage_adapter` (HierarchicalStorageAdapter)
    - Initializes services with dependency injection
  - `generate_scene_image(self, task_id, scene_index, prompt, style, aspect_ratio, user_id, progress_callback)`: Generates an image for a scene
    - Parameters: `task_id` (str), `scene_index` (int), `prompt` (str), `style` (str), `aspect_ratio` (str), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with image information (Dict[str, Any])
    - Generates image using OpenAI DALL-E and stores it
  - `regenerate_scene_image(self, task_id, scene_index, new_prompt, style_adjustments, aspect_ratio, user_id, progress_callback)`: Regenerates an image for a scene with adjustments
    - Parameters: `task_id` (str), `scene_index` (int), `new_prompt` (str), `style_adjustments` (Optional[str]), `aspect_ratio` (str), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with image information (Dict[str, Any])
    - Regenerates image with new prompt and style adjustments
  - `_enhance_prompt(self, prompt, style)`: Enhances a prompt with style information
    - Parameters: `prompt` (str), `style` (str)
    - Returns: Enhanced prompt (str)
    - Combines base prompt with style description
  - `_get_dimensions_from_aspect_ratio(self, aspect_ratio)`: Gets image dimensions from an aspect ratio
    - Parameters: `aspect_ratio` (str)
    - Returns: Tuple of (width, height)
    - Converts aspect ratios to DALL-E compatible dimensions
  - `_download_image(self, url)`: Downloads an image from a URL
    - Parameters: `url` (str)
    - Returns: The image data as bytes
    - Uses httpx for async HTTP requests

**Functions**:
- `generate_scene_image_tool(ctx, scene_index, prompt, style, aspect_ratio)`: Function tool for OpenAI Assistants API to generate a scene image
  - Parameters: `ctx` (Context), `scene_index` (int), `prompt` (str), `style` (str), `aspect_ratio` (str)
  - Returns: Dictionary with image information (Dict[str, Any])
  - Updates context with image information
- `regenerate_scene_image_tool(ctx, scene_index, new_prompt, style_adjustments)`: Function tool for OpenAI Assistants API to regenerate a scene image
  - Parameters: `ctx` (Context), `scene_index` (int), `new_prompt` (str), `style_adjustments` (Optional[str])
  - Returns: Dictionary with image information (Dict[str, Any])
  - Updates context with new image information

**Dependencies**:
- OpenAIService for image generation (DALL-E)
- HierarchicalStorageAdapter for file storage
- FastAPI Depends for dependency injection
- httpx for async HTTP requests
- Logging for error tracking
- Time for versioning regenerated images

**Usage Patterns**:
- Generates high-quality images using OpenAI's DALL-E
- Enhances prompts with style information
- Handles different aspect ratios with appropriate dimensions
- Provides progress tracking during generation
- Stores images in hierarchical storage
- Supports regeneration with style adjustments
- Uses OpenAI Assistants API function tools for integration
- Updates context with image information
- Handles errors gracefully with status reporting
- Creates versioned filenames for regenerated images

#### backend/app/ai/agents/tools/video_generator.py

**File Purpose**: Provides tools for converting images to videos and combining videos with audio.

**Classes**:
- `VideoGeneratorTool`: Tool for generating videos from images and combining videos with audio
  - `__init__(self, fal_ai_service, storage_adapter)`: Initializes the video generator tool
    - Parameters: `fal_ai_service` (FalAIService), `storage_adapter` (HierarchicalStorageAdapter)
    - Initializes services with dependency injection
  - `image_to_video(self, task_id, scene_index, image_url, duration, motion_type, user_id, progress_callback)`: Converts a static image to a video with motion
    - Parameters: `task_id` (str), `scene_index` (int), `image_url` (str), `duration` (float), `motion_type` (str), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with video information (Dict[str, Any])
    - Converts image to video using Fal.ai service
  - `combine_video_audio(self, task_id, scene_index, video_url, audio_url, user_id, progress_callback)`: Combines video and audio for a scene
    - Parameters: `task_id` (str), `scene_index` (int), `video_url` (str), `audio_url` (str), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with combined video information (Dict[str, Any])
    - Uses FFmpeg to combine video and audio
  - `compose_final_video(self, task_id, scene_videos, background_music_url, transitions, user_id, progress_callback)`: Composes the final video from all components
    - Parameters: `task_id` (str), `scene_videos` (List[str]), `background_music_url` (Optional[str]), `transitions` (Optional[List[Dict[str, Any]]]), `user_id` (Optional[str]), `progress_callback` (Optional[callable])
    - Returns: Dictionary with final video information (Dict[str, Any])
    - Concatenates videos and adds background music
  - `_download_video(self, url)`: Downloads a video from a URL
    - Parameters: `url` (str)
    - Returns: The video data as bytes
    - Uses httpx for async HTTP requests
  - `_download_audio(self, url)`: Downloads audio from a URL
    - Parameters: `url` (str)
    - Returns: The audio data as bytes
    - Uses httpx for async HTTP requests

**Functions**:
- `image_to_video_tool(ctx, scene_index, image_url, duration, motion_type)`: Function tool for OpenAI Assistants API to convert an image to video
  - Parameters: `ctx` (Context), `scene_index` (int), `image_url` (str), `duration` (float), `motion_type` (str)
  - Returns: Dictionary with video information (Dict[str, Any])
  - Updates context with video information
- `combine_video_audio_tool(ctx, scene_index, video_url, audio_url)`: Function tool for OpenAI Assistants API to combine video and audio
  - Parameters: `ctx` (Context), `scene_index` (int), `video_url` (str), `audio_url` (str)
  - Returns: Dictionary with combined video information (Dict[str, Any])
  - Updates context with combined video information
- `compose_final_video_tool(ctx, scene_videos, background_music_url, transitions)`: Function tool for OpenAI Assistants API to compose the final video
  - Parameters: `ctx` (Context), `scene_videos` (List[str]), `background_music_url` (Optional[str]), `transitions` (Optional[List[Dict[str, Any]]])
  - Returns: Dictionary with final video information (Dict[str, Any])
  - Updates context with final video information

**Dependencies**:
- FalAIService for image-to-video conversion
- HierarchicalStorageAdapter for file storage
- FastAPI Depends for dependency injection
- httpx for async HTTP requests
- subprocess for running FFmpeg commands
- os module for file path operations
- Logging for error tracking

**Usage Patterns**:
- Converts static images to dynamic videos with motion effects
- Combines video and audio using FFmpeg
- Creates temporary directories for processing video files
- Composes final videos by concatenating scene videos
- Adds background music to videos
- Provides progress tracking during video generation
- Handles errors gracefully with status reporting
- Uses FFmpeg for video processing operations
- Uses OpenAI Assistants API function tools for integration
- Updates context with video information

#### backend/app/ai/agents/utils/dependency_graph.py

**File Purpose**: Provides a utility for managing task dependencies and parallel execution in a directed acyclic graph (DAG) structure.

**Classes**:
- `DependencyGraph`: A directed acyclic graph for managing task dependencies
  - `__init__(self)`: Initializes the dependency graph
    - Sets up dictionaries for tasks, dependencies, results, and in-progress tracking
  - `add_task(self, task_id, task_func, dependencies)`: Adds a task to the graph
    - Parameters: `task_id` (T), `task_func` (Callable[..., Awaitable[R]]), `dependencies` (Optional[List[T]])
    - Adds the task and its dependencies to the graph
  - `get_ready_tasks(self)`: Gets a list of tasks that are ready to execute
    - Returns: List of task IDs that are ready to execute (List[T])
    - A task is ready if all its dependencies have been completed
  - `is_complete(self)`: Checks if all tasks have been completed
    - Returns: True if all tasks have been completed, False otherwise (bool)
  - `execute_task(self, task_id)`: Executes a single task
    - Parameters: `task_id` (T)
    - Returns: Result of the task (R)
    - Executes the task with the results of its dependencies
  - `execute_all(self, max_concurrency, progress_callback)`: Executes all tasks in the graph in dependency order
    - Parameters: `max_concurrency` (int), `progress_callback` (Optional[Callable[[int, str], None]])
    - Returns: Dictionary mapping task IDs to their results (Dict[T, R])
    - Executes tasks in parallel while respecting dependencies

**Dependencies**:
- asyncio for asynchronous execution
- typing for type annotations
- logging for error tracking
- Generic types for flexible task IDs and result types

**Usage Patterns**:
- Manages dependencies between tasks using a directed acyclic graph
- Executes tasks in parallel while respecting dependencies
- Provides progress tracking through callbacks
- Limits concurrency to avoid overwhelming system resources
- Detects dependency cycles to prevent deadlocks
- Passes results of dependencies to dependent tasks
- Handles errors during task execution
- Uses semaphores to control parallel execution
- Supports generic typing for flexibility
- Tracks in-progress tasks to prevent redundant execution

#### backend/app/ai/agents/utils/parallel.py

**File Purpose**: Provides utilities for parallel execution of tasks with progress tracking and retry logic.

**Classes**:
- `ParallelExecutor`: Utility for executing tasks in parallel
  - `__init__(self, max_concurrency)`: Initializes the parallel executor
    - Parameters: `max_concurrency` (int)
    - Sets up a semaphore to limit concurrency
  - `execute(self, tasks)`: Executes a list of tasks in parallel
    - Parameters: `tasks` (List[Awaitable[T]])
    - Returns: List of results from the tasks (List[T])
    - Uses semaphores to limit concurrency
  - `execute_with_progress(self, tasks, progress_callback, retry_count, retry_delay)`: Executes tasks with progress reporting and retry logic
    - Parameters: `tasks` (List[Awaitable[T]]), `progress_callback` (Optional[Callable[[int, Optional[str]], None]]), `retry_count` (int), `retry_delay` (float)
    - Returns: List of results from the tasks (List[T])
    - Implements retry logic with exponential backoff
  - `map(func, items, max_concurrency, progress_callback, retry_count)`: (Static method) Applies a function to each item in a list in parallel
    - Parameters: `func` (Callable[[Any], Awaitable[T]]), `items` (List[Any]), `max_concurrency` (int), `progress_callback` (Optional[Callable[[int, Optional[str]], None]]), `retry_count` (int)
    - Returns: List of results from applying the function to each item (List[T])
    - Convenience wrapper for common parallelization pattern

**Dependencies**:
- asyncio for asynchronous execution
- typing for type annotations
- logging for error tracking
- time module for timing operations

**Usage Patterns**:
- Limits concurrent task execution to avoid resource exhaustion
- Provides detailed progress tracking for long-running operations
- Implements retry logic with exponential backoff
- Handles errors gracefully with comprehensive logging
- Offers convenient map-like interface for parallel operations
- Uses semaphores to control access to limited resources
- Supports both simple parallel execution and advanced features
- Provides task status tracking during execution
- Allows for custom retry strategies with configurable delays
- Aggregates results while preserving order of input tasks

#### backend/app/ai/models/task.py

**File Purpose**: Defines task models for managing video generation tasks, including status tracking and progress updates.

**Enums**:
- `TaskStatus`: Defines possible states for a task
  - Values: PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED
  - Used to track the current status of video generation tasks

- `TaskStage`: Defines the stages of video generation
  - Values: INITIALIZING, SCENE_BREAKDOWN, CHARACTER_GENERATION, ASSET_GENERATION, MUSIC_GENERATION, VIDEO_COMPOSITION, FINALIZING
  - Represents the specific stage of the video generation pipeline

**Classes**:
- `Task`: Model for a video generation task
  - Fields:
    - `id` (str): Unique identifier for the task (auto-generated UUID)
    - `status` (TaskStatus): Current status of the task (default: PENDING)
    - `stage` (TaskStage): Current stage of the task (default: INITIALIZING)
    - `progress` (int): Progress percentage (0-100)
    - `created_at` (float): Unix timestamp of creation time
    - `updated_at` (float): Unix timestamp of last update
    - `completed_at` (Optional[float]): Unix timestamp of completion time
    - `prompt` (str): The user's prompt for the video
    - `duration` (int): Duration of the video in seconds
    - `style` (str): Style of the video
    - `video_url` (Optional[str]): URL of the generated video if completed
    - `error` (Optional[str]): Error message if task failed
    - `metadata` (Dict[str, Any]): Additional metadata about the task
    - `scenes` (List[Dict[str, Any]]): Scene data for the video
    - `assets` (Dict[str, Any]): Asset URLs for the video
    - `user_id` (Optional[str]): ID of the user who created the task
  - Methods:
    - `update_progress(progress, stage)`: Updates the progress of the task
      - Parameters: `progress` (int), `stage` (Optional[TaskStage])
      - Updates progress percentage, stage if provided, and updated_at timestamp
    - `complete(video_url)`: Marks the task as completed
      - Parameters: `video_url` (str)
      - Sets status to COMPLETED, progress to 100, stage to FINALIZING, and stores video URL
    - `fail(error)`: Marks the task as failed
      - Parameters: `error` (str)
      - Sets status to FAILED and stores error message
    - `cancel()`: Marks the task as cancelled
      - Sets status to CANCELLED and updates timestamp
    - `to_dict()`: Converts the task to a dictionary for storage
      - Returns: Dictionary representation of the task
    - `from_dict(data)`: (Class method) Creates a task from a dictionary
      - Parameters: `data` (Dict[str, Any])
      - Returns: Task instance
      - Handles conversion of string enums to proper enum types

**Type Definitions**:
- `ProgressCallback`: Type for progress callback functions
  - Callable that takes progress percentage and optional message

**Dependencies**:
- Pydantic for data validation and model definitions
- UUID for generating unique task IDs
- Enum for enumeration types
- Time module for timestamps
- Python typing for type annotations

**Usage Patterns**:
- Used to track the status and progress of video generation tasks
- Provides standardized lifecycle management (creation, updating, completion, failure)
- Maintains timestamps for performance monitoring
- Facilitates conversion between Python objects and dictionary/JSON for storage
- Enables progress reporting across the video generation pipeline
- Organizes generated assets and metadata in a consistent structure
- Supports user ownership tracking for multi-user systems
- Serves as the central data model for task management in the application

#### backend/app/ai/tasks/task_manager.py

**File Purpose**: Provides a manager for handling asynchronous video generation tasks with Redis-based persistence.

**Classes**:
- `TaskManager`: Manager for asynchronous video generation tasks
  - `__init__(self, redis_client)`: Initializes the task manager
    - Parameters: `redis_client` (Optional[RedisClient])
    - Sets up in-memory task storage, semaphore for concurrency control, and Redis client
  - `create_task(self, prompt, duration, style, user_id)`: Creates a new task
    - Parameters: `prompt` (str), `duration` (int), `style` (str), `user_id` (Optional[str])
    - Returns: Task object
    - Creates a new task and stores it in memory and Redis
  - `_store_task_in_redis(self, task)`: Stores a task in Redis
    - Parameters: `task` (Task)
    - Async method that persists task data and initial progress to Redis
  - `get_task_from_redis(self, task_id)`: Gets a task from Redis
    - Parameters: `task_id` (str)
    - Returns: Task object if found, None otherwise
    - Retrieves task data from Redis and creates a Task object
  - `get_task(self, task_id)`: Gets a task by ID
    - Parameters: `task_id` (str)
    - Returns: Task object if found, None otherwise
    - Checks in-memory cache first, then tries Redis if available
  - `_get_task_from_redis_and_cache(self, task_id)`: Gets a task from Redis and caches it
    - Parameters: `task_id` (str)
    - Async method that retrieves a task from Redis and adds it to in-memory cache
  - `get_all_tasks(self)`: Gets all tasks
    - Returns: List of all tasks
    - Returns all tasks from in-memory cache
  - `get_active_tasks(self)`: Gets all active tasks
    - Returns: List of active tasks (pending or processing)
    - Filters tasks by status
  - `start_task(self, task_id, process_func, timeout_seconds)`: Starts processing a task asynchronously
    - Parameters: `task_id` (str), `process_func` (Callable), `timeout_seconds` (int, default=3600)
    - Async method that updates task status, creates progress callback, and runs the task with semaphore
  - `cancel_task(self, task_id)`: Cancels a running task
    - Parameters: `task_id` (str)
    - Returns: True if cancelled, False otherwise
    - Cancels the running task and updates status
  - `cleanup_old_tasks(self, max_age_seconds)`: Removes old completed or failed tasks
    - Parameters: `max_age_seconds` (int, default=86400)
    - Returns: Number of tasks removed
    - Removes old tasks from memory and Redis

**Dependencies**:
- RedisClient for task persistence
- Task model for task representation
- asyncio for asynchronous operations
- logging for error tracking
- time module for timestamps
- datetime for ISO format timestamps
- Settings for application configuration

**Usage Patterns**:
- Manages the lifecycle of video generation tasks
- Provides in-memory caching with Redis-based persistence
- Limits concurrent task execution with semaphores
- Implements timeout handling for long-running tasks
- Tracks task progress and status updates
- Provides callbacks for progress reporting
- Handles task cancellation and cleanup of old tasks
- Stores task results and errors in Redis
- Uses asyncio for non-blocking task execution
- Implements comprehensive error handling and logging

#### backend/app/ai/models/request.py

**File Purpose**: Defines request and response models for the video generation API using Pydantic.

**Enums**:
- `VideoStyle`: Defines available video styles
  - Values: REALISTIC, CARTOON, ANIME, CINEMATIC, ARTISTIC, VINTAGE, FUTURISTIC
  - Used to control the visual style of generated videos

**Classes**:
- `VideoRequest`: Request model for video creation
  - Fields:
    - `prompt` (str): The prompt describing the video to create
    - `duration` (int): Duration of the video in seconds (5-120, default: 30)
    - `style` (VideoStyle): Style of the video (default: REALISTIC)
    - `voice_sample_url` (Optional[str]): URL to a voice sample for TTS
  - Includes example JSON schema for documentation

- `TaskResponse`: Response model for task creation
  - Fields:
    - `task_id` (str): Unique identifier for the task
    - `status` (str): Current status of the task
  - Includes example JSON schema for documentation

- `TaskStatus`: Response model for task status
  - Fields:
    - `task_id` (str): Unique identifier for the task
    - `status` (str): Current status of the task
    - `progress` (int): Progress percentage (0-100)
    - `video_url` (Optional[str]): URL of the generated video if completed
    - `error` (Optional[str]): Error message if task failed
    - `stage` (Optional[str]): Current stage of the task
    - `updated_at` (Optional[datetime]): Last update time
  - Includes example JSON schema for documentation

- `SceneData`: Model for scene data
  - Fields:
    - `description` (str): Description of the scene
    - `narration` (str): Narration script for the scene
    - `duration` (float): Duration of the scene in seconds
    - `style_params` (Dict[str, Any]): Style parameters for the scene
    - `characters` (List[str]): Characters in the scene
    - `transition` (Optional[str]): Transition to the next scene

- `StandardVideoMetadata`: Model for standard video metadata
  - Fields:
    - `scenes` (List[SceneData]): List of scenes in the video
    - `needs_character_consistency` (bool): Whether character consistency is needed
    - `characters` (List[Dict[str, Any]]): Character profiles
    - `style` (Dict[str, Any]): Global style parameters
    - `transitions` (List[Dict[str, Any]]): Transition specifications
    - `duration` (int): Total duration in seconds
    - `mood` (str): Overall mood of the video (default: "neutral")

- `VideoGenerationPreferences`: Model for video generation preferences
  - Fields:
    - `style` (VideoStyle): Style of the video (default: REALISTIC)
    - `duration` (int): Duration of the video in seconds (5-120, default: 30)
    - `voice_sample_url` (Optional[str]): URL to a voice sample for TTS
    - `character_consistency` (bool): Whether character consistency is needed
    - `quality` (str): Quality of the generated video (default: "standard")
    - `aspect_ratio` (str): Aspect ratio of the video (default: "16:9")
  - Includes example JSON schema for documentation

- `UnifiedVideoRequest`: Unified request model for video generation
  - Fields:
    - `prompt` (str): The prompt describing the video to create
    - `preferences` (VideoGenerationPreferences): Preferences for video generation
    - `reference_files` (Optional[List[str]]): URLs of reference files
  - Includes example JSON schema for documentation

**Dependencies**:
- Pydantic for data validation and model definitions
- Python typing for type annotations
- Enum for enumeration types
- Datetime for timestamp handling

**Usage Patterns**:
- Used for input validation and type conversion in API endpoints
- Provides standardized request and response structures
- Enforces validation constraints (e.g., duration limits)
- Includes example schemas for documentation and testing
- Supports both basic and advanced video generation requests
- Facilitates standardized communication between frontend and backend
- Enables consistent error handling and response formatting
- Supports various video styles through enumeration
- Allows for flexible preferences configuration
- Provides structured metadata for video generation

#### backend/app/ai/models/video_metadata.py

**File Purpose**: Defines advanced request and response models for the video agent API with detailed structure for characters, music, and scenes.

**Classes**:
- `CharacterProfile`: Model for character profile with image prompt
  - Fields:
    - `name` (str): Name of the character
    - `image_prompt` (str): Prompt for generating character images with 4 angles
    - `image_urls` (Dict[str, str]): URLs of generated character images
  - Represents characters that need visual consistency across scenes

- `MusicDefinition`: Model for music definition with scene grouping
  - Fields:
    - `prompt` (str): Prompt for generating music
    - `scene_indexes` (List[int]): Indexes of scenes this music applies to
    - `music_url` (Optional[str]): URL of the generated music
  - Enables grouping scenes with consistent musical themes

- `SceneClip`: Model for scene clip with title, script, and video prompt
  - Fields:
    - `index` (int): Index of the scene
    - `title` (str): Title of the scene
    - `script` (str): Narration script for the scene
    - `video_prompt` (str): Prompt for generating the scene video
    - `duration` (Optional[float]): Duration of the scene in seconds
    - `transition` (Optional[str]): Transition to the next scene
  - Represents individual scenes with their detailed content

- `ClipData`: Model for clip data containing scene information and asset URLs
  - Fields:
    - `scene` (SceneClip): Scene information for the clip
    - `audio_url` (Optional[str]): URL of the generated audio
    - `image_url` (Optional[str]): URL of the generated image
    - `video_url` (Optional[str]): URL of the generated video
  - Combines scene information with generated assets

- `VideoMetadata`: Advanced model for video metadata with detailed structure
  - Fields:
    - `user_prompt` (str): Original user prompt
    - `rewritten_prompt` (str): Rewritten prompt for better clarity
    - `voice_character` (Optional[str]): URL to a voice sample for TTS
    - `character_consistency` (bool): Whether character consistency is needed
    - `music` (List[MusicDefinition]): Music definitions with scene groupings
    - `character_profiles` (List[CharacterProfile]): Character profiles with image prompts
    - `clips` (List[ClipData]): List of clips with scene information
    - `expected_duration` (int): Expected total duration of the video in seconds
    - `task_id` (Optional[str]): ID of the associated task
    - `user_id` (Optional[str]): ID of the user who created this video
    - `final_video_url` (Optional[str]): URL of the final composed video
  - Methods:
    - `to_dict()`: Convert the video metadata to a dictionary for storage
    - `from_dict(data)`: Create video metadata from a dictionary
  - Serves as the comprehensive structure for entire video projects

**Dependencies**:
- Pydantic for data validation and model definitions
- Python typing for type annotations

**Usage Patterns**:
- Defines the structured data model for video generation
- Provides validation and serialization for complex nested structures
- Supports character consistency across multiple scenes
- Groups scenes with consistent musical themes
- Organizes video metadata in a hierarchical structure
- Includes example JSON schema for documentation and testing
- Enables conversion between Python objects and JSON/dictionary formats
- Serves as the central data model connecting various components
- Supports tracking of generated assets throughout the pipeline
- Maintains relationships between characters, scenes, and music

#### backend/app/ai/utils/json_utils.py

**File Purpose**: Provides utility functions for working with JSON data, including parsing, formatting, and file operations.

**Functions**:
- `parse_json(json_str)`: Parses a JSON string into a Python dictionary
  - Parameters: `json_str` (str)
  - Returns: Parsed JSON as dictionary (Dict[str, Any])
  - Handles errors gracefully with logging

- `format_json(data, indent)`: Formats a Python dictionary as a JSON string
  - Parameters: `data` (Dict[str, Any]), `indent` (int, default=2)
  - Returns: Formatted JSON string (str)
  - Handles errors gracefully with logging

- `get_logs_dir(base_dir)`: Gets the logs directory, creating it if needed
  - Parameters: `base_dir` (Optional[str])
  - Returns: Path to logs directory (str)
  - Uses default logs directory if none provided

- `get_category_dir(category, base_dir)`: Gets a category directory within the logs directory
  - Parameters: `category` (str), `base_dir` (Optional[str])
  - Returns: Path to category directory (str)
  - Creates the directory if it doesn't exist

- `save_json_response(data, category, name, base_dir)`: Saves a JSON response to a file
  - Parameters: `data` (Dict[str, Any]), `category` (str), `name` (str), `base_dir` (Optional[str])
  - Returns: Path to the saved file (str)
  - Creates timestamped filenames for versioning

- `load_json_file(filepath)`: Loads a JSON file
  - Parameters: `filepath` (str)
  - Returns: Loaded data as dictionary (Dict[str, Any])
  - Handles errors gracefully with logging

- `load_latest_json(category, name_prefix, base_dir)`: Loads the latest JSON file in a category
  - Parameters: `category` (str), `name_prefix` (str), `base_dir` (Optional[str])
  - Returns: Loaded data as dictionary (Dict[str, Any])
  - Finds the most recently modified file matching the prefix

**Variables**:
- `DEFAULT_LOGS_DIR`: Default directory for logs, relative to the module location

**Dependencies**:
- os module for file and directory operations
- json module for JSON parsing and formatting
- logging for error tracking
- datetime for timestamping files
- Python typing for type annotations

**Usage Patterns**:
- Provides error-safe JSON parsing and formatting
- Organizes logs in a hierarchical directory structure
- Creates timestamped files for versioning
- Supports loading the latest version of a file
- Handles errors gracefully with comprehensive logging
- Creates directories as needed for file operations
- Provides flexible base directory configuration
- Enables categorization of JSON responses by type
- Supports debugging and analysis of AI responses
- Maintains a history of generated content

#### backend/app/ai/utils/model_converters.py

**File Purpose**: Provides utility functions for converting between different model formats used in the video generation system.

**Functions**:
- `advanced_to_standard_metadata(advanced)`: Converts advanced VideoMetadata to standard VideoMetadata
  - Parameters: `advanced` (VideoMetadata)
  - Returns: StandardVideoMetadata
  - Handles scene duration adjustments to match expected total duration
  - Converts clips to scenes, character profiles, and transitions

- `standard_to_advanced_metadata(metadata, user_prompt, voice_character)`: Converts standard VideoMetadata to advanced VideoMetadata
  - Parameters: `metadata` (StandardVideoMetadata), `user_prompt` (str), `voice_character` (Optional[str])
  - Returns: VideoMetadata
  - Creates character profiles, clips, and music definitions from standard metadata

- `extract_character_profiles(advanced)`: Extracts character profiles from advanced VideoMetadata
  - Parameters: `advanced` (VideoMetadata)
  - Returns: List of character profiles as dictionaries
  - Formats character data for use in other components

- `extract_music_definitions(advanced)`: Extracts music definitions from advanced VideoMetadata
  - Parameters: `advanced` (VideoMetadata)
  - Returns: List of tuples containing (prompt, scene_indexes)
  - Formats music data for use in other components

- `unified_request_to_video_request(request)`: Converts a UnifiedGenerationRequest to a format suitable for the video agent
  - Parameters: `request` (Dict[str, Any] or UnifiedGenerationRequest)
  - Returns: Dictionary with parameters for the video agent
  - Extracts preferences and formats them for the video agent

- `video_result_to_unified_response(result, task_id, message)`: Converts a video generation result to a UnifiedGenerationResponse
  - Parameters: `result` (Dict[str, Any]), `task_id` (str), `message` (str, default="Video generation complete")
  - Returns: UnifiedGenerationResponse
  - Formats the response to match frontend expectations

**Dependencies**:
- StandardVideoMetadata and SceneData models from app.ai.models.request
- VideoMetadata, CharacterProfile, MusicDefinition, ClipData, SceneClip models from app.ai.models.video_metadata
- UnifiedGenerationRequest, UnifiedGenerationResponse, ResponseType from app.schemas.ai_generation
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Facilitates conversion between different metadata formats used in the system
- Adjusts scene durations to match expected total duration
- Handles character consistency across different model formats
- Extracts specific components (characters, music) for specialized processing
- Provides unified request/response handling for the API
- Ensures backward compatibility with frontend expectations
- Formats data consistently across the system
- Supports both object-based and dictionary-based conversions
- Handles missing or optional fields gracefully
- Maintains relationships between scenes, characters, and music across formats

#### backend/app/ai/utils/storage_adapter.py

**File Purpose**: Provides a storage adapter for the video agent that uses Supabase storage, with methods for saving and retrieving various types of files.

**Classes**:
- `StorageAdapter`: Storage adapter for the video agent that uses Supabase storage
  - `__init__(self, storage_manager)`: Initializes the storage adapter
    - Parameters: `storage_manager` (StorageManager)
    - Sets up the storage manager dependency
  - `create_task_directory_structure(self, task_id)`: Creates a hierarchical directory structure for a task
    - Parameters: `task_id` (str)
    - Returns: Dictionary with paths for different asset types
    - Creates a timestamp-based directory with subdirectories for scenes, music, and final output
  - `create_scene_directory(self, task_dir, scene_index)`: Creates a directory structure for a scene
    - Parameters: `task_dir` (Dict[str, Any]), `scene_index` (int)
    - Returns: Dictionary with paths for different scene asset types
    - Creates subdirectories for script, image, audio, and video assets
  - `save_video(self, file_data, filename, user_id)`: Saves a video file to storage
    - Parameters: `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the saved file
    - Generates a unique filename if not provided
  - `save_image(self, file_data, filename, user_id)`: Saves an image file to storage
    - Parameters: `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the saved file
    - Generates a unique filename if not provided
  - `save_audio(self, file_data, filename, user_id)`: Saves an audio file to storage
    - Parameters: `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the saved file
    - Generates a unique filename if not provided
  - `download_and_store_file_from_url(self, url, bucket, filename, user_id)`: Downloads a file from a URL and stores it
    - Parameters: `url` (str), `bucket` (str), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the stored file
    - Uses the storage manager to handle the download and upload
  - `download_and_store_video(self, url, filename, user_id)`: Downloads a video from a URL and stores it
    - Parameters: `url` (str), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the stored video
    - Uses the videos bucket for storage
  - `download_and_store_image(self, url, filename, user_id)`: Downloads an image from a URL and stores it
    - Parameters: `url` (str), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the stored image
    - Uses the images bucket for storage
  - `download_and_store_audio(self, url, filename, user_id)`: Downloads an audio file from a URL and stores it
    - Parameters: `url` (str), `filename` (Optional[str]), `user_id` (Optional[str])
    - Returns: URL of the stored audio
    - Uses the audio bucket for storage
  - `get_public_url(self, path_or_url, bucket)`: Gets the public URL for a file (async version)
    - Parameters: `path_or_url` (str), `bucket` (Optional[str])
    - Returns: Public URL of the file
    - Handles both paths and URLs
  - `get_public_url_sync(self, path_or_url, bucket)`: Gets the public URL for a file (synchronous version)
    - Parameters: `path_or_url` (str), `bucket` (Optional[str])
    - Returns: Path or URL as is
    - Simplified version for JSON serialization
  - `create_temp_directory(self)`: Creates a temporary directory
    - Returns: Path to the temporary directory
    - Uses the system's temp directory
  - `cleanup_temp_directory(self, dir_path)`: Cleans up a temporary directory
    - Parameters: `dir_path` (str)
    - Removes the directory and its contents
  - `get_local_path(self, url)`: Gets the local file path from a URL
    - Parameters: `url` (str)
    - Returns: Local file path or None if it's a remote URL
    - Distinguishes between local paths and remote URLs
  - `get_placeholder_image_url(self)`: Gets a placeholder image URL
    - Returns: URL of a placeholder image
    - Used when an image is not available
  - `get_placeholder_audio_url(self)`: Gets a placeholder audio URL
    - Returns: URL of a placeholder audio file
    - Used when audio is not available
  - `get_placeholder_video_url(self)`: Gets a placeholder video URL
    - Returns: URL of a placeholder video
    - Used when a video is not available
  - `save_scene_asset(self, task_dir, scene_index, asset_type, file_data, filename, user_id, metadata)`: Saves a scene asset
    - Parameters: `task_dir` (Dict[str, Any]), `scene_index` (int), `asset_type` (str), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str]), `metadata` (Optional[Dict[str, Any]])
    - Returns: Dictionary with information about the saved asset
    - Saves the asset to the appropriate location in the hierarchical structure
  - `save_music_asset(self, task_dir, file_data, filename, user_id, metadata)`: Saves a music asset
    - Parameters: `task_dir` (Dict[str, Any]), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str]), `metadata` (Optional[Dict[str, Any]])
    - Returns: Dictionary with information about the saved asset
    - Saves the asset to the music directory
  - `save_final_video(self, task_dir, file_data, filename, user_id, metadata)`: Saves the final video
    - Parameters: `task_dir` (Dict[str, Any]), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `user_id` (Optional[str]), `metadata` (Optional[Dict[str, Any]])
    - Returns: Dictionary with information about the saved asset
    - Saves the video to the final directory
  - `save_task_metadata(self, task_dir, metadata)`: Saves metadata for the entire task
    - Parameters: `task_dir` (Dict[str, Any]), `metadata` (Dict[str, Any])
    - Returns: Path to the saved metadata file
    - Saves the metadata to the base directory

**Dependencies**:
- StorageManager for file storage operations
- FastAPI Depends for dependency injection
- os module for file path operations
- uuid module for generating unique identifiers
- logging for error tracking
- Python typing for type annotations
- pathlib.Path for path manipulation
- tempfile module for temporary directory creation
- shutil module for directory removal
- json module for metadata serialization

**Usage Patterns**:
- Provides a unified interface for file storage operations
- Creates hierarchical directory structures for organizing assets
- Handles both local and remote file storage
- Supports various file types (video, image, audio)
- Generates unique filenames for assets
- Downloads files from URLs and stores them locally
- Provides placeholder URLs for missing assets
- Manages temporary directories for processing
- Saves metadata alongside assets
- Supports both synchronous and asynchronous URL retrieval
- Handles both file-like objects and bytes for file data

#### backend/app/ai/utils/hierarchical_storage_adapter.py

**File Purpose**: Provides an enhanced storage adapter that uses a hierarchical folder structure for organizing files related to video generation.

**Classes**:
- `HierarchicalStorageAdapter`: Enhanced storage adapter that extends StorageAdapter with hierarchical organization
  - `__init__(self, storage_manager)`: Initializes the hierarchical storage adapter
    - Parameters: `storage_manager` (StorageManager)
    - Inherits from StorageAdapter and initializes metadata dictionary
  - `initialize_task_storage(self, task_id, user_id)`: Initializes storage for a new task
    - Parameters: `task_id` (str), `user_id` (Optional[str])
    - Returns: Dictionary with storage information
    - Creates a timestamp-based folder structure and initializes metadata
  - `_save_metadata(self, task_id)`: Saves metadata to storage
    - Parameters: `task_id` (str)
    - Saves task metadata to a JSON file in storage
  - `save_scene_script(self, task_id, scene_index, script_data)`: Saves a scene script to storage
    - Parameters: `task_id` (str), `scene_index` (int), `script_data` (Dict[str, Any])
    - Returns: URL of the saved script
    - Saves script data as JSON in the appropriate scene folder
  - `save_scene_image(self, task_id, scene_index, file_data, filename)`: Saves a scene image to storage
    - Parameters: `task_id` (str), `scene_index` (int), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str])
    - Returns: URL of the saved image
    - Saves image in the scene's image folder and updates metadata
  - `save_scene_audio(self, task_id, scene_index, file_data, filename, audio_type)`: Saves scene audio to storage
    - Parameters: `task_id` (str), `scene_index` (int), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str]), `audio_type` (str, default="narration")
    - Returns: URL of the saved audio
    - Saves audio in the scene's audio folder and updates metadata
  - `save_scene_video(self, task_id, scene_index, file_data, filename)`: Saves a scene video to storage
    - Parameters: `task_id` (str), `scene_index` (int), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str])
    - Returns: URL of the saved video
    - Saves video in the scene's video folder and updates metadata
  - `save_background_music(self, task_id, file_data, filename)`: Saves background music to storage
    - Parameters: `task_id` (str), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str])
    - Returns: URL of the saved audio
    - Saves music in the task's music folder and updates metadata
  - `save_final_video(self, task_id, file_data, filename)`: Saves the final video to storage
    - Parameters: `task_id` (str), `file_data` (Union[bytes, BinaryIO]), `filename` (Optional[str])
    - Returns: URL of the saved video
    - Saves video in the task's base folder and updates metadata
  - `get_task_metadata(self, task_id)`: Gets metadata for a task
    - Parameters: `task_id` (str)
    - Returns: The task metadata
    - Retrieves metadata from memory or loads from storage
  - `cleanup_task_storage(self, task_id)`: Cleans up storage for a task
    - Parameters: `task_id` (str)
    - Returns: True if successful, False otherwise
    - Deletes all files associated with the task from storage

**Dependencies**:
- StorageAdapter as the base class
- StorageManager for file storage operations
- FastAPI Depends for dependency injection
- os module for file path operations
- uuid module for generating unique identifiers
- json module for metadata serialization
- time module for timestamps
- datetime for formatted timestamps
- logging for error tracking
- Python typing for type annotations
- tempfile module for temporary file creation
- httpx for downloading files from URLs

**Usage Patterns**:
- Extends the base StorageAdapter with enhanced organization
- Maintains a consistent hierarchical folder structure for all task assets
- Tracks metadata for all stored assets
- Provides specialized methods for each asset type (scripts, images, audio, video)
- Persists metadata to storage for recovery
- Supports task-level operations (initialization, cleanup)
- Organizes assets by scene and type
- Handles both in-memory and persistent metadata
- Provides clean URLs for accessing stored assets
- Supports cleanup of all task-related files

#### backend/app/ai/utils/duration_adjuster.py

**File Purpose**: Provides duration adjustment utilities for media files, serving as a backward compatibility layer that imports from the modular duration utility structure.

**Functions**:
- Re-exports the following classes and functions from the modular duration utilities:
  - `AudioDurationAdjuster`: Class for adjusting audio durations
  - `VideoDurationAdjuster`: Class for adjusting video durations
  - `SceneDurationManager`: Class for managing scene durations
  - `get_duration`: Function to get the duration of a media file
  - `copy_file`: Function to copy a file
  - `get_media_info`: Function to get information about a media file
  - `get_media_type`: Function to determine the type of a media file
  - `extract_audio`: Function to extract audio from a video file
  - `extract_frame`: Function to extract a frame from a video file
  - `combine_audio_video`: Function to combine audio and video files
  - `convert_image_to_video`: Function to convert an image to a video

**Dependencies**:
- Imports from app.ai.utils.duration module
- Imports from app.ai.utils.duration.media_utils module
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Serves as a backward compatibility layer
- Provides a single import point for duration adjustment utilities
- Maintains the same interface while using a more modular implementation
- Simplifies migration from older code to the new modular structure
- Centralizes duration-related functionality for easier maintenance

#### backend/app/ai/utils/duration/audio_adjuster.py

**File Purpose**: Provides utilities for adjusting the duration of audio files, including speeding up, slowing down, trimming, looping, and adding fade effects.

**Classes**:
- `AudioDurationAdjuster`: Utility for adjusting the duration of audio files
  - `adjust_duration(audio_path, target_duration, output_path, fade_out, fade_in, preserve_pitch)`: (Static method) Adjusts the duration of an audio file
    - Parameters: `audio_path` (str), `target_duration` (float), `output_path` (Optional[str]), `fade_out` (bool, default=True), `fade_in` (bool, default=False), `preserve_pitch` (bool, default=True)
    - Returns: Path to the adjusted audio file (str)
    - Determines the best method to adjust duration (trim, speed, or loop)
  - `trim_audio(input_path, output_path, target_duration, fade_out, fade_in)`: (Static method) Trims an audio file to a specific duration
    - Parameters: `input_path` (str), `output_path` (str), `target_duration` (float), `fade_out` (bool, default=True), `fade_in` (bool, default=False)
    - Uses ffmpeg to trim the audio and apply fade effects
  - `adjust_speed(input_path, output_path, speed_factor, preserve_pitch, fade_out, fade_in)`: (Static method) Adjusts the speed of an audio file
    - Parameters: `input_path` (str), `output_path` (str), `speed_factor` (float), `preserve_pitch` (bool, default=True), `fade_out` (bool, default=True), `fade_in` (bool, default=False)
    - Uses ffmpeg with atempo filter for speed adjustment with pitch preservation
    - Chains multiple atempo filters for extreme speed adjustments
  - `loop_audio(input_path, output_path, target_duration, fade_out, fade_in, crossfade_duration)`: (Static method) Loops an audio file to reach a specific duration
    - Parameters: `input_path` (str), `output_path` (str), `target_duration` (float), `fade_out` (bool, default=True), `fade_in` (bool, default=False), `crossfade_duration` (float, default=1.0)
    - Uses ffmpeg's stream_loop option to repeat the audio
    - Applies fade effects to the looped audio
  - `apply_fades(input_path, output_path, fade_in, fade_out, fade_in_duration, fade_out_duration)`: (Static method) Applies fade-in and fade-out effects to an audio file
    - Parameters: `input_path` (str), `output_path` (str), `fade_in` (bool, default=False), `fade_out` (bool, default=True), `fade_in_duration` (float, default=1.0), `fade_out_duration` (float, default=1.0)
    - Uses ffmpeg's afade filter to apply fade effects

**Dependencies**:
- os module for file path operations
- tempfile module for creating temporary files
- logging for error tracking
- asyncio for asynchronous operations
- Python typing for type annotations
- common.py for utility functions (get_duration, copy_file, execute_ffmpeg_command, calculate_fade_durations)

**Usage Patterns**:
- Provides a comprehensive set of tools for audio duration adjustment
- Uses ffmpeg for high-quality audio processing
- Handles temporary file creation and cleanup
- Implements intelligent duration adjustment based on the target duration
- Preserves audio quality during speed adjustments
- Supports fade effects for smoother transitions
- Uses asynchronous operations for better performance
- Handles error cases gracefully with cleanup
- Creates appropriate output paths when not provided

#### backend/app/ai/utils/duration/common.py

**File Purpose**: Provides shared utilities used by multiple duration adjusters, including functions for getting media duration, copying files, and executing ffmpeg commands.

**Functions**:
- `get_duration(file_path)`: Gets the duration of a media file
  - Parameters: `file_path` (str)
  - Returns: Duration in seconds (float) or None if it could not be determined
  - Uses ffprobe to get the duration of the media file
  - Handles errors gracefully with logging

- `copy_file(input_path, output_path)`: Copies a file using ffmpeg
  - Parameters: `input_path` (str), `output_path` (str)
  - Uses ffmpeg to copy the file, ensuring compatibility
  - Raises RuntimeError if the copy operation fails

- `execute_ffmpeg_command(command)`: Executes an ffmpeg command and returns stdout and stderr
  - Parameters: `command` (list) - The ffmpeg command as a list of strings
  - Returns: Tuple of (stdout, stderr) as bytes
  - Uses asyncio.create_subprocess_exec for asynchronous execution
  - Raises RuntimeError if the command fails

- `calculate_fade_durations(total_duration, fade_in, fade_out)`: Calculates appropriate fade durations based on total media duration
  - Parameters: `total_duration` (float), `fade_in` (bool, default=False), `fade_out` (bool, default=True)
  - Returns: Tuple of (fade_in_duration, fade_out_duration) in seconds
  - Calculates fade durations as max 1 second or 1/4 of total duration
  - Returns 0.0 for fade_in_duration or fade_out_duration if the corresponding flag is False

**Dependencies**:
- os module for file path operations
- logging for error tracking
- asyncio for asynchronous operations
- subprocess for executing external commands
- Python typing for type annotations

**Usage Patterns**:
- Provides core utilities used by multiple duration adjustment modules
- Uses ffprobe to get media information
- Uses ffmpeg for media file operations
- Implements asynchronous execution for better performance
- Handles errors gracefully with comprehensive logging
- Calculates appropriate fade durations based on media length
- Ensures consistent behavior across different duration adjusters

#### backend/app/ai/utils/duration/media_utils.py

**File Purpose**: Provides utilities for working with media files, including getting information, extracting audio/frames, and converting between formats.

**Functions**:
- `get_media_info(file_path)`: Gets detailed information about a media file
  - Parameters: `file_path` (str)
  - Returns: Dictionary of media information (Dict[str, Any]) or None if it could not be determined
  - Uses ffprobe to get detailed information in JSON format
  - Handles errors gracefully with logging

- `get_media_type(file_path)`: Determines the type of media file based on extension
  - Parameters: `file_path` (str)
  - Returns: Media type as string ('audio', 'video', 'image', or 'unknown')
  - Uses file extension to categorize media types
  - Supports common audio, video, and image formats

- `extract_audio(video_path, output_path, start_time, duration)`: Extracts audio from a video file
  - Parameters: `video_path` (str), `output_path` (Optional[str]), `start_time` (Optional[float]), `duration` (Optional[float])
  - Returns: Path to the extracted audio file (str)
  - Uses ffmpeg to extract audio with optional time range
  - Creates temporary output file if not provided

- `extract_frame(video_path, output_path, time_position)`: Extracts a frame from a video file
  - Parameters: `video_path` (str), `output_path` (Optional[str]), `time_position` (float, default=0.0)
  - Returns: Path to the extracted frame (str)
  - Uses ffmpeg to extract a single frame at the specified time position
  - Creates temporary output file if not provided

- `combine_audio_video(video_path, audio_path, output_path, audio_volume)`: Combines a video file with an audio file
  - Parameters: `video_path` (str), `audio_path` (str), `output_path` (Optional[str]), `audio_volume` (float, default=1.0)
  - Returns: Path to the combined video file (str)
  - Uses ffmpeg to combine video and audio with volume adjustment
  - Creates temporary output file if not provided

- `convert_image_to_video(image_path, output_path, duration, motion_type)`: Converts an image to a video
  - Parameters: `image_path` (str), `output_path` (Optional[str]), `duration` (float, default=5.0), `motion_type` (str, default="none")
  - Returns: Path to the video file (str)
  - Uses ffmpeg to create a video from an image with optional motion effects
  - Supports various motion types: 'none', 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'
  - Creates temporary output file if not provided

**Dependencies**:
- os module for file path operations
- logging for error tracking
- asyncio for asynchronous operations
- subprocess for executing external commands
- tempfile for creating temporary files
- json for parsing ffprobe output
- Python typing for type annotations

**Usage Patterns**:
- Provides comprehensive utilities for media file operations
- Uses ffmpeg and ffprobe for high-quality media processing
- Implements asynchronous execution for better performance
- Handles temporary file creation and cleanup
- Supports various media transformations (extraction, combination, conversion)
- Implements motion effects for image-to-video conversion
- Handles errors gracefully with comprehensive logging
- Creates appropriate output paths when not provided
- Supports time-based operations (extraction from specific positions)
- Provides volume adjustment for audio in combined videos

#### backend/app/ai/utils/duration/scene_manager.py

**File Purpose**: Provides utilities for managing the duration of scenes in a video, including calculating, redistributing, and adjusting scene durations.

**Classes**:
- `SceneDurationManager`: Utility for managing the duration of scenes in a video
  - `calculate_scene_durations(scenes, total_duration, min_scene_duration)`: (Static method) Calculates scene durations based on total video duration
    - Parameters: `scenes` (List[Dict[str, Any]]), `total_duration` (float), `min_scene_duration` (float, default=3.0)
    - Returns: List of scene durations in seconds (List[float])
    - Distributes duration based on scene weights while ensuring minimum duration
  - `redistribute_durations(current_durations, index, operation, new_duration, min_scene_duration)`: (Static method) Redistributes durations when a scene is added, removed, or modified
    - Parameters: `current_durations` (List[float]), `index` (int), `operation` (str), `new_duration` (Optional[float]), `min_scene_duration` (float, default=3.0)
    - Returns: Updated list of scene durations (List[float])
    - Handles 'add', 'remove', and 'modify' operations while maintaining total duration
  - `adjust_scene_durations(scenes, target_durations)`: (Static method) Adjusts scene durations to match target durations
    - Parameters: `scenes` (List[Dict[str, Any]]), `target_durations` (List[float])
    - Returns: Updated list of scene data dictionaries (List[Dict[str, Any]])
    - Updates duration field in each scene dictionary
  - `validate_scene_durations(durations, total_duration, tolerance)`: (Static method) Validates that scene durations add up to the total duration
    - Parameters: `durations` (List[float]), `total_duration` (float), `tolerance` (float, default=0.1)
    - Returns: True if valid, False otherwise (bool)
    - Checks if sum of durations is within tolerance of total duration
  - `adjust_scene_media_durations(scenes, target_durations)`: (Static method) Adjusts the durations of media files in scenes to match target durations
    - Parameters: `scenes` (List[Dict[str, Any]]), `target_durations` (List[float])
    - Returns: Updated list of scene data dictionaries (List[Dict[str, Any]])
    - Adjusts audio and video files using AudioDurationAdjuster and VideoDurationAdjuster
  - `get_transition_durations(scenes, default_transition_duration)`: (Static method) Gets transition durations between scenes
    - Parameters: `scenes` (List[Dict[str, Any]]), `default_transition_duration` (float, default=1.0)
    - Returns: List of transition durations in seconds (List[float])
    - Extracts transition information from scene data or uses default
  - `adjust_for_transitions(scene_durations, transition_durations, min_scene_duration)`: (Static method) Adjusts scene durations to account for transitions
    - Parameters: `scene_durations` (List[float]), `transition_durations` (List[float]), `min_scene_duration` (float, default=3.0)
    - Returns: Adjusted list of scene durations (List[float])
    - Accounts for transition overlaps while ensuring minimum scene duration

**Dependencies**:
- AudioDurationAdjuster for adjusting audio durations
- VideoDurationAdjuster for adjusting video durations
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Manages scene durations in a video composition workflow
- Ensures scenes have appropriate durations based on total video length
- Handles transitions between scenes with proper timing
- Maintains minimum scene durations for readability
- Supports weighted distribution of durations based on scene importance
- Provides validation to ensure durations add up correctly
- Adjusts actual media files to match target durations
- Handles scene addition, removal, and modification with duration redistribution
- Supports various transition types and durations
- Accounts for transition overlaps in duration calculations

#### backend/app/ai/utils/duration/video_adjuster.py

**File Purpose**: Provides utilities for adjusting the duration of video files, including speeding up, slowing down, trimming, looping, and adding fade effects.

**Classes**:
- `VideoDurationAdjuster`: Utility for adjusting the duration of video files
  - `adjust_duration(video_path, target_duration, output_path, fade_out, fade_in, preserve_audio_pitch)`: (Static method) Adjusts the duration of a video file
    - Parameters: `video_path` (str), `target_duration` (float), `output_path` (Optional[str]), `fade_out` (bool, default=True), `fade_in` (bool, default=False), `preserve_audio_pitch` (bool, default=True)
    - Returns: Path to the adjusted video file (str)
    - Determines the best method to adjust duration (trim, speed, or loop)
  - `trim_video(input_path, output_path, target_duration, fade_out, fade_in)`: (Static method) Trims a video file to a specific duration
    - Parameters: `input_path` (str), `output_path` (str), `target_duration` (float), `fade_out` (bool, default=True), `fade_in` (bool, default=False)
    - Uses ffmpeg to trim the video and apply fade effects
  - `adjust_speed(input_path, output_path, speed_factor, preserve_audio_pitch, fade_out, fade_in)`: (Static method) Adjusts the speed of a video file
    - Parameters: `input_path` (str), `output_path` (str), `speed_factor` (float), `preserve_audio_pitch` (bool, default=True), `fade_out` (bool, default=True), `fade_in` (bool, default=False)
    - Uses ffmpeg with setpts filter for video and atempo filter for audio
    - Chains multiple atempo filters for extreme speed adjustments
  - `loop_video(input_path, output_path, target_duration, fade_out, fade_in, crossfade_duration)`: (Static method) Loops a video file to reach a specific duration
    - Parameters: `input_path` (str), `output_path` (str), `target_duration` (float), `fade_out` (bool, default=True), `fade_in` (bool, default=False), `crossfade_duration` (float, default=1.0)
    - Uses ffmpeg's stream_loop option to repeat the video
    - Applies fade effects to the looped video
  - `apply_fades(input_path, output_path, fade_in, fade_out, fade_in_duration, fade_out_duration)`: (Static method) Applies fade-in and fade-out effects to a video file
    - Parameters: `input_path` (str), `output_path` (str), `fade_in` (bool, default=False), `fade_out` (bool, default=True), `fade_in_duration` (float, default=1.0), `fade_out_duration` (float, default=1.0)
    - Uses ffmpeg's fade filter to apply fade effects

**Dependencies**:
- os module for file path operations
- tempfile module for creating temporary files
- logging for error tracking
- asyncio for asynchronous operations
- Python typing for type annotations
- common.py for utility functions (get_duration, copy_file, execute_ffmpeg_command, calculate_fade_durations)

**Usage Patterns**:
- Provides a comprehensive set of tools for video duration adjustment
- Uses ffmpeg for high-quality video processing
- Handles temporary file creation and cleanup
- Implements intelligent duration adjustment based on the target duration
- Preserves audio quality during speed adjustments
- Supports fade effects for smoother transitions
- Uses asynchronous operations for better performance
- Handles error cases gracefully with cleanup
- Creates appropriate output paths when not provided
- Applies different strategies based on the duration difference

#### backend/app/ai/sdk/agent.py

**File Purpose**: Defines the agents used by Pixora AI for video generation using the OpenAI Agents SDK, providing a structured approach to video creation with specialized agents for different stages.

**Variables**:
- `_services`: Dictionary for storing service singletons (redis_client, openai_service, replicate_service, fal_ai_service, storage_manager)
- `VIDEO_AGENT_INSTRUCTIONS`: System instructions for the main video agent, detailing the video creation process

**Functions**:
- `get_services()`: Gets or initializes service singletons
  - Returns: Dictionary of service instances
  - Lazy-loads services on first call
- `get_agent_for_stage(stage)`: Gets the appropriate agent for a given task stage
  - Parameters: `stage` (str)
  - Returns: The appropriate Agent[TaskContext] for the stage
- `simulate_video_generation(task_id, user_id)`: Simulates the video generation process
  - Parameters: `task_id` (str), `user_id` (str)
  - Asynchronous function that updates progress and simulates generation stages

**Classes**:
- `SceneBreakdownRequest`: Pydantic model for scene breakdown requests
  - Fields: `prompt` (str), `style` (str), `duration` (int), `aspect_ratio` (str)
- `SceneData`: Pydantic model for scene data
  - Fields: `index` (int), `title` (str), `script` (str), `video_prompt` (str), `duration` (Optional[float]), `transition` (Optional[str])
- `SceneBreakdownResponse`: Pydantic model for scene breakdown responses
  - Fields: `scenes` (List[SceneData]), `style` (str), `mood` (str), `transitions` (List[Dict[str, Any]]), `estimated_duration` (float)

**Agent Definitions**:
- `video_agent`: Main agent for video creation
  - Model: gpt-4o
  - Tools: All available tools
- `scene_breakdown_agent`: Specialized agent for scene breakdown
  - Model: gpt-4o
  - Tools: generate_scene_breakdown_tool, update_scene_tool
- `character_generator_agent`: Specialized agent for character generation
  - Model: gpt-4o
  - Tools: (To be implemented in Phase 2)
- `asset_generator_agent`: Specialized agent for asset generation
  - Model: gpt-4o
  - Tools: regenerate_scene_image_tool, (more to be implemented)
- `video_composer_agent`: Specialized agent for video composition
  - Model: gpt-4o
  - Tools: check_generation_status_tool, (more to be implemented)
- `editor_agent`: Specialized agent for video editing
  - Model: gpt-4o
  - Tools: update_scene_tool, regenerate_scene_image_tool

**Function Tools**:
- `generate_scene_breakdown_tool(ctx, prompt, style, duration, aspect_ratio, mood)`: Generates a scene breakdown
  - Parameters: `ctx` (RunContextWrapper[TaskContext]), `prompt` (str), `style` (str), `duration` (int), `aspect_ratio` (str, default="16:9"), `mood` (Optional[str])
  - Returns: Scene breakdown (Dict[str, Any])
  - Calls OpenAI to generate a structured scene breakdown
- `update_scene_tool(ctx, scene_index, new_content, update_type)`: Updates a specific scene
  - Parameters: `ctx` (RunContextWrapper[TaskContext]), `scene_index` (int), `new_content` (str), `update_type` (str, default="both")
  - Returns: Updated scene breakdown (Dict[str, Any])
  - Updates script, visual prompt, or both
- `generate_video_tool(ctx)`: Starts the video generation process
  - Parameters: `ctx` (RunContextWrapper[TaskContext])
  - Returns: Status information (Dict[str, Any])
  - Initiates an asynchronous video generation task
- `check_generation_status_tool(ctx)`: Checks the status of video generation
  - Parameters: `ctx` (RunContextWrapper[TaskContext])
  - Returns: Current status (Dict[str, Any])
  - Retrieves status from Redis
- `regenerate_scene_image_tool(ctx, scene_index, new_prompt, style_adjustments)`: Regenerates an image for a scene
  - Parameters: `ctx` (RunContextWrapper[TaskContext]), `scene_index` (int), `new_prompt` (str), `style_adjustments` (Optional[str])
  - Returns: Information about the regenerated image (Dict[str, Any])
  - Simulates image regeneration (to be implemented with OpenAI)

**Dependencies**:
- OpenAI Agents SDK (Agent, function_tool, RunContextWrapper)
- Pydantic for data validation and model definitions
- TaskContext for maintaining task state
- RedisClient for persistence
- OpenAIService for LLM and image generation
- ReplicateService for audio generation
- FalAiService for video generation
- StorageManager for file storage
- Python standard libraries (os, json, time, logging, asyncio)

**Usage Patterns**:
- Implements a multi-agent system for video generation
- Uses specialized agents for different stages of the process
- Provides function tools for specific tasks
- Maintains task state in Redis for persistence
- Simulates video generation for demonstration
- Supports interactive workflow with user approval
- Implements progress tracking and status updates
- Uses OpenAI's GPT-4o model for all agents
- Provides detailed instructions for each agent
- Supports scene editing and regeneration

#### backend/app/ai/sdk/context.py

**File Purpose**: Provides an enhanced task context for the OpenAI Assistants SDK with improved progress tracking, message history management, and asset URL management.

**Classes**:
- `ProgressUpdate`: Pydantic model for a progress update
  - Fields: `progress` (float), `stage` (str), `substage` (Optional[str]), `message` (str), `timestamp` (float), `eta` (Optional[float])
  - Represents a single progress update with percentage, stage, and message

- `Message`: Pydantic model for a message in the task context
  - Fields: `role` (str), `content` (str), `timestamp` (float), `metadata` (Dict[str, Any])
  - Represents a single message in the conversation history

- `Asset`: Pydantic model for an asset in the task context
  - Fields: `url` (str), `type` (str), `metadata` (Dict[str, Any]), `created_at` (float), `scene_index` (Optional[int])
  - Represents a single asset (image, audio, video) with its URL and metadata

- `TaskContext`: Generic class for maintaining task state
  - `__init__(self, task_id, user_id, redis_client)`: Initializes the task context
    - Parameters: `task_id` (str), `user_id` (Optional[str]), `redis_client` (Optional[RedisClient])
    - Sets up data structures and initializes with a system message
  
  - Basic data storage methods:
    - `get(self, key, default)`: Gets a value from the context
    - `set(self, key, value)`: Sets a value in the context
    - `delete(self, key)`: Deletes a key from the context
    - `has(self, key)`: Checks if a key exists in the context
    - `clear(self)`: Clears all data from the context
  
  - Progress tracking methods:
    - `set_progress(self, progress, stage, message, substage, eta)`: Sets the current progress
    - `get_current_progress(self)`: Gets the current progress
    - `get_progress_history(self, limit)`: Gets the progress history
    - `calculate_eta(self, current_progress)`: Calculates the estimated time of completion
  
  - Message history methods:
    - `add_message(self, role, content, metadata)`: Adds a message to the history
    - `get_messages(self, limit, roles)`: Gets messages from the history
    - `get_chat_history(self, limit)`: Gets the chat history in OpenAI API format
    - `clear_messages(self)`: Clears all messages from the history
  
  - Asset management methods:
    - `add_asset(self, asset_id, url, asset_type, metadata, scene_index)`: Adds an asset to the context
    - `get_asset(self, asset_id)`: Gets an asset by ID
    - `get_assets_by_type(self, asset_type)`: Gets all assets of a specific type
    - `get_scene_assets(self, scene_index)`: Gets all assets for a specific scene
    - `delete_asset(self, asset_id)`: Deletes an asset by ID
  
  - Scene data methods:
    - `set_scene_data(self, scene_index, key, value)`: Sets data for a specific scene
    - `get_scene_data(self, scene_index, key, default)`: Gets data for a specific scene
    - `get_all_scene_data(self, scene_index)`: Gets all data for a specific scene
    - `get_all_scenes(self)`: Gets data for all scenes
    - `delete_scene_data(self, scene_index, key)`: Deletes data for a specific scene
  
  - Redis persistence methods:
    - `load_from_redis(self)`: Loads data from Redis
    - Various private methods for persisting different types of data to Redis

**Dependencies**:
- Pydantic for data validation and model definitions
- RedisClient for persistence
- Python typing for type annotations (including Generic and TypeVar)
- JSON for serialization
- Time module for timestamps
- Logging for error tracking
- Asyncio for asynchronous Redis operations

**Usage Patterns**:
- Provides a comprehensive state management system for AI tasks
- Maintains progress tracking with detailed stages and substages
- Manages conversation history with role-based messages
- Organizes assets by type and scene
- Supports scene-specific data storage
- Persists all data to Redis for recovery and monitoring
- Uses Pydantic models for data validation and serialization
- Implements asynchronous Redis operations to avoid blocking
- Provides ETA calculation based on progress history
- Supports filtering and limiting of message and progress history
- Organizes assets by scene for easy retrieval

#### backend/app/ai/tools/base.py

**File Purpose**: Defines the base Tool class and ToolRegistry for managing tools used by the Pixora AI Agent.

**Classes**:
- `Tool`: Abstract base class for all tools used by the Pixora AI Agent
  - `__init__(self, name, description, parameters_schema)`: Initializes a tool
    - Parameters: `name` (str), `description` (str), `parameters_schema` (Dict[str, Any])
    - Sets up the tool's basic properties
  - `execute(self, **kwargs)`: (Abstract method) Executes the tool with the given parameters
    - Parameters: Tool-specific parameters as keyword arguments
    - Returns: A string containing the tool's output, typically JSON
    - Must be implemented by subclasses
  - `get_definition(self)`: Gets the tool definition for the OpenAI API
    - Returns: A dictionary containing the tool definition in OpenAI format
    - Used to register the tool with the OpenAI API

- `ToolRegistry`: Registry for managing available tools
  - `__init__(self)`: Initializes an empty tool registry
    - Sets up an empty dictionary for storing tools
  - `register_tool(self, tool)`: Registers a tool with the registry
    - Parameters: `tool` (Tool)
    - Adds the tool to the registry using its name as the key
  - `get_tool(self, name)`: Gets a tool by name
    - Parameters: `name` (str)
    - Returns: The tool if found, None otherwise
    - Provides lookup by tool name
  - `get_tool_definitions(self)`: Gets the tool definitions for the OpenAI API
    - Returns: A list of tool definitions in OpenAI format
    - Used to register all tools with the OpenAI API
  - `list_tools(self)`: Lists all registered tool names
    - Returns: A list of tool names
    - Provides a way to enumerate available tools

**Dependencies**:
- ABC and abstractmethod from abc module for abstract class definition
- JSON for serialization
- Python typing for type annotations

**Usage Patterns**:
- Provides a standardized interface for all tools
- Enables dynamic tool registration and discovery
- Supports OpenAI API integration with proper tool definitions
- Enforces consistent tool implementation through abstract methods
- Centralizes tool management in the ToolRegistry
- Allows for easy addition of new tools
- Provides a clean way to get tool definitions for API calls
- Supports tool lookup by name
- Enables listing of available tools
- Standardizes parameter schema definition

#### backend/app/ai/tools/audio_tools.py

**File Purpose**: Provides tools for audio generation, including text-to-speech and music generation for the Pixora AI Agent.

**Classes**:
- `TextToSpeechTool`: Tool for generating speech from text using OpenAI's TTS models
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for text, voice, model, and speed
  - `execute(self, text, voice, model, speed)`: Executes the text-to-speech generation
    - Parameters: `text` (str), `voice` (str, default="nova"), `model` (str, default="tts-1"), `speed` (float, default=1.0)
    - Returns: JSON string containing the generated speech information
    - Uses OpenAI's API to generate speech and saves it to a temporary file
    - Calculates estimated duration based on word count and speed

- `MusicGenerationTool`: Tool for generating background music
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for prompt, duration, genre, and mood
  - `execute(self, prompt, duration, genre, mood)`: Executes the music generation
    - Parameters: `prompt` (str), `duration` (float, default=30.0), `genre` (str, default="cinematic"), `mood` (str, default="inspirational")
    - Returns: JSON string containing the generated music information
    - Simulates music generation with a mock URL (would call a music generation API in production)

- `AudioMixingTool`: Tool for mixing audio tracks
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for tracks and output format
  - `execute(self, tracks, output_format)`: Executes the audio mixing
    - Parameters: `tracks` (List[Dict[str, Any]]), `output_format` (str, default="mp3")
    - Returns: JSON string containing the mixed audio information
    - Simulates audio mixing with a mock URL (would download and mix tracks in production)
    - Calculates total duration based on track start times and durations

**Dependencies**:
- Tool base class for tool implementation
- AsyncOpenAI for OpenAI API access
- aiohttp for HTTP requests
- tempfile for temporary file creation
- os for file operations
- json for serialization/deserialization
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Provides specialized tools for audio-related tasks
- Implements the Tool interface for consistent integration
- Uses OpenAI's TTS API for high-quality speech generation
- Simulates music generation and audio mixing (would use real APIs in production)
- Handles temporary file creation and cleanup
- Provides detailed error handling and logging
- Returns structured JSON responses with relevant information
- Calculates estimated durations for generated audio
- Supports various voices, models, and speeds for TTS
- Supports various genres and moods for music generation
- Supports mixing multiple audio tracks with volume and timing control

#### backend/app/ai/tools/image_tools.py

**File Purpose**: Provides tools for image generation, editing, and variation creation using OpenAI's GPT-Image-1 model.

**Classes**:
- `OpenAIImageGenerationTool`: Tool for generating images using OpenAI's GPT-Image-1 model
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for prompt, size, quality, and style
  - `execute(self, prompt, size, quality, style)`: Executes the image generation
    - Parameters: `prompt` (str), `size` (str, default="1024x1024"), `quality` (str, default="standard"), `style` (str, default="vivid")
    - Returns: JSON string containing the generated image information
    - Uses OpenAI's API to generate images based on text prompts
    - Handles different image sizes, qualities, and styles

- `OpenAIImageEditTool`: Tool for editing images using OpenAI's GPT-Image-1 model
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for image URLs, prompt, and size
  - `execute(self, image_urls, prompt, size)`: Executes the image editing
    - Parameters: `image_urls` (List[str]), `prompt` (str), `size` (str, default="1024x1024")
    - Returns: JSON string containing the edited image information
    - Downloads images from URLs and processes them with OpenAI's API
    - Supports editing or combining up to 4 images
    - Handles temporary file creation and cleanup

- `OpenAIImageVariationTool`: Tool for creating variations of images using OpenAI's GPT-Image-1 model
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for image URL, size, and number of variations
  - `execute(self, image_url, size, num_variations)`: Executes the image variation creation
    - Parameters: `image_url` (str), `size` (str, default="1024x1024"), `num_variations` (int, default=1)
    - Returns: JSON string containing the variation image information
    - Downloads the image from URL and processes it with OpenAI's API
    - Supports generating multiple variations of the same image
    - Handles temporary file creation and cleanup

**Dependencies**:
- Tool base class for tool implementation
- AsyncOpenAI for OpenAI API access
- aiohttp for HTTP requests
- tempfile for temporary file creation
- os for file operations
- base64 for encoding/decoding image data
- json for serialization/deserialization
- logging for error tracking
- Python typing for type annotations
- urllib.parse for URL parsing

**Usage Patterns**:
- Provides specialized tools for image-related tasks
- Implements the Tool interface for consistent integration
- Uses OpenAI's GPT-Image-1 model for high-quality image generation
- Handles downloading and processing of remote images
- Supports various image sizes, qualities, and styles
- Provides detailed error handling and logging
- Returns structured JSON responses with relevant information
- Supports base64 encoding for direct image data access
- Handles temporary file creation and cleanup
- Supports multiple variations of the same image
- Enables editing and combining of multiple images

#### backend/app/ai/tools/script_tools.py

**File Purpose**: Provides tools for script generation and scene breakdown for video creation.

**Classes**:
- `ScriptGenerationTool`: Tool for generating a script from a prompt
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for prompt, style, and duration
  - `execute(self, prompt, style, duration)`: Executes the script generation
    - Parameters: `prompt` (str), `style` (str, default="standard"), `duration` (int, default=30)
    - Returns: JSON string containing the generated script
    - Uses OpenAI's API to generate a detailed script based on the prompt
    - Handles different video styles and durations
    - Includes fallback script generation in case of errors

- `SceneBreakdownTool`: Tool for breaking down a script into scenes
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for script, duration, and number of scenes
  - `execute(self, script, duration, num_scenes)`: Executes the scene breakdown
    - Parameters: `script` (Dict[str, Any]), `duration` (int, default=30), `num_scenes` (Optional[int])
    - Returns: JSON string containing the scene breakdown
    - Uses OpenAI's API to break down a script into logical scenes
    - Automatically determines the appropriate number of scenes based on duration if not specified
    - Ensures scenes have appropriate durations that add up to the total video length
    - Includes fallback scene breakdown generation in case of errors

**Dependencies**:
- Tool base class for tool implementation
- AsyncOpenAI for OpenAI API access
- json for serialization/deserialization
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Provides specialized tools for script-related tasks in video creation
- Implements the Tool interface for consistent integration
- Uses OpenAI's GPT-4o model for high-quality script generation
- Handles different video styles (cinematic, documentary, commercial, etc.)
- Supports various video durations with appropriate scene breakdowns
- Provides detailed error handling and logging
- Returns structured JSON responses with relevant information
- Includes fallback mechanisms for error cases
- Automatically determines appropriate number of scenes based on video duration
- Ensures scene durations add up to the total video duration
- Generates detailed visual descriptions for each scene

#### backend/app/ai/tools/utility_tools.py

**File Purpose**: Provides utility tools for task management, progress tracking, user preferences, and error handling.

**Classes**:
- `ProgressTrackingTool`: Tool for tracking progress of a task
  - `__init__(self, redis_client)`: Initializes the tool with a Redis client
    - Parameters: `redis_client` (RedisClient)
    - Sets up the tool with parameters for task ID, progress, status, and step
  - `execute(self, task_id, progress, status, step)`: Executes the progress tracking
    - Parameters: `task_id` (str), `progress` (float), `status` (str, default=""), `step` (Optional[str])
    - Returns: JSON string containing the updated progress information
    - Updates task progress in Redis and returns the updated information
    - Handles errors gracefully with logging

- `TaskManagementTool`: Tool for managing tasks
  - `__init__(self, task_manager)`: Initializes the tool with a task manager
    - Parameters: `task_manager` (TaskManager)
    - Sets up the tool with parameters for action, task ID, and user ID
  - `execute(self, action, task_id, user_id)`: Executes the task management action
    - Parameters: `action` (str), `task_id` (Optional[str]), `user_id` (Optional[str])
    - Returns: JSON string containing the action result
    - Supports actions: get_status, list_tasks, get_task
    - Handles errors gracefully with logging

- `UserPreferenceTool`: Tool for managing user preferences
  - `__init__(self, user_id, redis_client)`: Initializes the tool with user ID and Redis client
    - Parameters: `user_id` (str), `redis_client` (RedisClient)
    - Sets up the tool with parameters for action, key, and value
  - `execute(self, action, key, value)`: Executes the preference management action
    - Parameters: `action` (str), `key` (str), `value` (Optional[Any])
    - Returns: JSON string containing the action result
    - Supports actions: get, set, delete
    - Uses Redis for preference storage with user-specific keys
    - Handles errors gracefully with logging

- `ErrorHandlingTool`: Tool for handling errors
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for error message, error type, context, and recovery strategy
  - `execute(self, error_message, error_type, context, recovery_strategy)`: Executes the error handling
    - Parameters: `error_message` (str), `error_type` (str, default="unknown_error"), `context` (Optional[Dict[str, Any]]), `recovery_strategy` (str, default="fallback")
    - Returns: JSON string containing the error handling result
    - Supports recovery strategies: retry, fallback, abort, user_intervention
    - Provides appropriate user messages based on the recovery strategy
    - Logs errors for tracking and debugging
    - Handles errors in error handling gracefully

**Dependencies**:
- Tool base class for tool implementation
- RedisClient for persistence
- TaskManager for task operations
- json for serialization/deserialization
- logging for error tracking
- Python typing for type annotations

**Usage Patterns**:
- Provides utility tools for common operations in the agent system
- Implements the Tool interface for consistent integration
- Uses Redis for persistent storage of progress and preferences
- Supports task management operations with appropriate error handling
- Provides user preference management with user-specific keys
- Implements comprehensive error handling with different recovery strategies
- Returns structured JSON responses with relevant information
- Logs errors for tracking and debugging
- Provides appropriate user messages based on the context
- Handles errors in utility operations gracefully

#### backend/app/ai/tools/video_tools.py

**File Purpose**: Provides tools for video assembly, editing, image-to-video conversion, and video analysis.

**Classes**:
- `VideoAssemblyTool`: Tool for assembling a video from components
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for scenes, background music, title, aspect ratio, and resolution
  - `execute(self, scenes, title, background_music_url, aspect_ratio, resolution)`: Executes the video assembly
    - Parameters: `scenes` (List[Dict[str, Any]]), `title` (str), `background_music_url` (Optional[str]), `aspect_ratio` (str, default="16:9"), `resolution` (str, default="1080p")
    - Returns: JSON string containing the assembled video information
    - Simulates video assembly with a mock URL (would use a video rendering library in production)
    - Calculates total duration based on scene durations

- `VideoEditTool`: Tool for editing a video
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for video URL and edits to apply
  - `execute(self, video_url, edits)`: Executes the video editing
    - Parameters: `video_url` (str), `edits` (List[Dict[str, Any]])
    - Returns: JSON string containing the edited video information
    - Simulates video editing with a mock URL (would apply edits to the video in production)
    - Supports various edit types (replace_scene, add_scene, remove_scene, add_effect, add_text, crop, trim)

- `ImageToVideoTool`: Tool for converting an image to a video with motion effects
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for image URL, duration, motion type, and audio URL
  - `execute(self, image_url, duration, motion_type, audio_url)`: Executes the image-to-video conversion
    - Parameters: `image_url` (str), `duration` (float, default=5.0), `motion_type` (str, default="ken_burns"), `audio_url` (Optional[str])
    - Returns: JSON string containing the generated video information
    - Simulates image-to-video conversion with a mock URL (would apply motion effects in production)
    - Supports various motion types (pan, zoom, ken_burns, parallax, none)

- `VideoAnalysisTool`: Tool for analyzing a video
  - `__init__(self)`: Initializes the tool with name, description, and parameters schema
    - Sets up the tool with parameters for video URL and analysis type
  - `execute(self, video_url, analysis_type)`: Executes the video analysis
    - Parameters: `video_url` (str), `analysis_type` (str, default="comprehensive")
    - Returns: JSON string containing the analysis results
    - Simulates video analysis with mock data (would perform actual analysis in production)
    - Supports various analysis types (scene_detection, content_analysis, quality_assessment, comprehensive)
    - Returns detailed information about the video (duration, resolution, fps, scenes, quality score, content summary)

**Dependencies**:
- Tool base class for tool implementation
- aiohttp for HTTP requests
- json for serialization/deserialization
- logging for error tracking
- Python typing for type annotations
- os and tempfile modules for file operations

**Usage Patterns**:
- Provides specialized tools for video-related tasks
- Implements the Tool interface for consistent integration
- Simulates video operations with mock responses (would use actual video processing in production)
- Handles errors gracefully with comprehensive logging
- Returns structured JSON responses with relevant information
- Supports various video formats, resolutions, and aspect ratios
- Enables complex video operations (assembly, editing, conversion, analysis)
- Provides detailed information about videos and operations
- Supports motion effects for image-to-video conversion
- Enables scene-level operations for video assembly and editing

#### backend/app/auth/jwt.py

**File Purpose**: Provides JWT authentication utilities for validating Supabase tokens and managing user authentication.

**Classes**:
- `TokenData`: TypedDict for token data structure
  - Fields: `sub` (str), `email` (Optional[str]), `name` (Optional[str]), `exp` (int), `aud` (str)
  - Represents the structure of the decoded JWT token data

- `TokenPayload`: Pydantic model for token payload validation
  - Fields: `sub` (str), `email` (Optional[str]), `name` (Optional[str]), `exp` (int), `aud` (str, default="authenticated")
  - Used for validating the structure of the decoded JWT token

**Functions**:
- `get_jwt_secret()`: Gets the JWT secret from environment variables
  - Returns: JWT secret (str)
  - Raises ValueError if JWT secret is not set in environment variables

- `create_access_token(data, expires_delta)`: Creates a new JWT access token
  - Parameters: `data` (Dict[str, Any]), `expires_delta` (Optional[timedelta])
  - Returns: Encoded JWT token (str)
  - Sets expiration time (default 24 hours) and encodes the token with HS256 algorithm

- `validate_token(credentials)`: Validates a JWT token from the Authorization header
  - Parameters: `credentials` (HTTPAuthorizationCredentials)
  - Returns: TokenData with user ID and claims
  - Decodes and validates the token, raising HTTPException if invalid

- `get_current_user_id(token_data)`: Extracts the user ID from the token data
  - Parameters: `token_data` (TokenData)
  - Returns: User ID (str)
  - Simple utility to extract the subject (user ID) from token data

- `get_current_user(token_data, supabase_service)`: Gets the current user from the token data
  - Parameters: `token_data` (TokenData), `supabase_service` (SupabaseService)
  - Returns: User object with user details
  - Fetches user data from Supabase or creates a default profile if not found

- `get_current_user_ws(token, settings)`: Authenticates a WebSocket connection
  - Parameters: `token` (str), `settings` (Settings)
  - Returns: User object with user details
  - Validates token and fetches user data for WebSocket authentication

**Variables**:
- `security`: HTTPBearer instance for Swagger UI security scheme
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for HTTP handling and dependency injection
- FastAPI security for HTTP Bearer authentication
- Jose JWT for token encoding/decoding
- Pydantic for data validation
- Datetime for token expiration handling
- Typing for type annotations
- Logging for error tracking
- User schema for response models
- SupabaseService for user data access
- Settings for application configuration

**Usage Patterns**:
- Provides JWT-based authentication for API endpoints
- Validates tokens from Authorization headers
- Creates new tokens with configurable expiration
- Extracts user information from tokens
- Fetches user data from Supabase
- Creates default user profiles if not found
- Supports WebSocket authentication
- Handles error cases with appropriate HTTP exceptions
- Uses dependency injection for integration with FastAPI
- Implements proper security practices for JWT handling

#### backend/app/auth/supabase.py

**File Purpose**: Provides utilities for verifying and validating Supabase JWT tokens and retrieving user information.

**Functions**:
- `verify_supabase_token(token)`: Verifies a Supabase JWT token and extracts user information
  - Parameters: `token` (str)
  - Returns: Dictionary with user ID, email, and name if token is valid, None otherwise
  - Decodes and validates the token using the Supabase JWT secret
  - Extracts user information from various locations in the token payload
  - Handles missing email by generating a default one

- `validate_supabase_token(request)`: Validates a Supabase JWT token from the Authorization header
  - Parameters: `request` (Request)
  - Returns: Dictionary with user ID, email, name, and expiration time
  - Extracts the token from the Authorization header
  - Decodes and validates the token using the Supabase JWT secret
  - Raises HTTPException if token is invalid or missing
  - Extracts user information from various locations in the token payload

- `get_current_user_from_supabase(token_data, supabase_service)`: Gets the current user from a Supabase token
  - Parameters: `token_data` (Dict[str, Any]), `supabase_service` (SupabaseService)
  - Returns: User data from Supabase
  - Fetches user data from Supabase using the user ID from the token
  - Creates a default profile if the user doesn't exist in the database
  - Raises HTTPException if user not found and could not be created

**Variables**:
- `settings`: Application settings from get_settings()
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for HTTP handling and dependency injection
- Jose JWT for token decoding and validation
- Logging for error tracking
- Python typing for type annotations
- Settings for application configuration
- SupabaseService for user data access

**Usage Patterns**:
- Provides utilities for working with Supabase JWT tokens
- Extracts user information from token payloads
- Handles different token payload structures
- Provides both verification (returns None on failure) and validation (raises exception on failure)
- Creates default user profiles for users with valid tokens but no database entry
- Supports FastAPI dependency injection for easy integration
- Implements proper error handling and logging
- Extracts user information from various locations in the token payload
- Handles missing email and name with default values
- Provides debug logging for token payload structure

#### backend/app/routers/admin.py

**File Purpose**: Provides API endpoints for admin operations in the Pixora AI platform.

**Models**:
- `UserListResponse`: Response model for user list
  - Fields: `id` (str), `email` (str), `name` (Optional[str]), `avatar_url` (Optional[str]), `credits` (int), `created_at` (str)
  - Represents a user in the admin user list

- `CreditAdjustmentRequest`: Request model for credit adjustment
  - Fields: `user_id` (str), `amount` (int), `reason` (str)
  - Used to adjust a user's credit balance

- `VoiceModel`: Model for a voice
  - Fields: `id` (str), `name` (str), `gender` (str), `tone` (str), `preview_url` (str), `is_default` (bool)
  - Represents a voice model in the system

- `VoiceCreateRequest`: Request model for voice creation
  - Fields: `name` (str), `gender` (str), `tone` (str), `audio_url` (str), `is_default` (bool)
  - Used to create a new voice model

**Endpoints**:
- `GET /admin/users`: Lists all users
  - Parameters: None
  - Returns: List of UserListResponse objects
  - Requires admin authentication
  - Fetches user profiles and auth data from Supabase

- `GET /admin/users/{user_id}`: Gets a user by ID
  - Parameters: `user_id` (str)
  - Returns: UserListResponse object
  - Requires admin authentication
  - Fetches user profile and auth data from Supabase

- `POST /admin/credits`: Adjusts a user's credits
  - Parameters: CreditAdjustmentRequest object
  - Returns: Dictionary with user ID, credits, adjustment, and reason
  - Requires admin authentication
  - Uses CreditService to add or deduct credits

- `GET /admin/voices`: Lists all voice models
  - Parameters: None
  - Returns: List of VoiceModel objects
  - Requires admin authentication
  - Fetches voice models from Supabase

- `POST /admin/voices`: Creates a new voice model
  - Parameters: VoiceCreateRequest object
  - Returns: VoiceModel object
  - Requires admin authentication
  - Uses TextToSpeechService to clone a voice and create a preview

- `DELETE /admin/voices/{voice_id}`: Deletes a voice model
  - Parameters: `voice_id` (str)
  - Returns: Dictionary with ID and deletion status
  - Requires admin authentication
  - Deletes the voice model from Supabase

**Variables**:
- `router`: APIRouter instance for admin endpoints
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- Settings for application configuration
- JWT authentication for admin user verification
- CreditService for managing user credits
- SupabaseClient for database operations
- TextToSpeechService for voice cloning
- StorageManager for file storage
- Logging for error tracking

**Usage Patterns**:
- Provides administrative functionality for the Pixora AI platform
- Implements user management operations
- Supports credit adjustment for users
- Manages voice models for text-to-speech
- Enforces admin-only access to endpoints
- Uses dependency injection for service access
- Implements proper error handling and logging
- Returns structured responses with appropriate status codes
- Handles background tasks for resource-intensive operations

#### backend/app/routers/agent_chat.py

**File Purpose**: Provides WebSocket endpoints for agent chat in the Pixora AI platform.

**Endpoints**:
- `WebSocket /agent/ws/{user_id}`: WebSocket endpoint for agent chat
  - Parameters: `user_id` (str)
  - Establishes a WebSocket connection for real-time chat with the AI agent
  - Authenticates the user with a JWT token
  - Processes messages asynchronously using the AgentController
  - Sends progress updates, acknowledgments, and results back to the client
  - Handles disconnections and errors gracefully

- `GET /agent/tasks`: Gets all tasks for the current user
  - Parameters: None
  - Returns: List of task IDs
  - Requires authentication
  - Uses AgentController to retrieve tasks

- `GET /agent/tasks/{task_id}`: Gets the status of a task
  - Parameters: `task_id` (str)
  - Returns: Task status information
  - Requires authentication
  - Verifies that the task belongs to the user
  - Uses AgentController to retrieve task status

- `DELETE /agent/memory`: Clears the conversation memory for the current user
  - Parameters: None
  - Returns: Success message
  - Requires authentication
  - Uses AgentController to clear memory

**Variables**:
- `router`: APIRouter instance for agent chat endpoints
- `logger`: Logger instance for error tracking
- `active_connections`: Dictionary tracking active WebSocket connections by user ID

**Functions**:
- `agent_websocket(websocket, user_id, redis_client, settings)`: Handles WebSocket connections for agent chat
  - Parameters: `websocket` (WebSocket), `user_id` (str), `redis_client` (RedisClient), `settings` (Settings)
  - Accepts the WebSocket connection and authenticates the user
  - Initializes the AgentController and processes messages
  - Sends updates and results back to the client
  - Handles disconnections and errors

- `progress_callback(task_id, progress, status)`: Callback function for progress updates
  - Parameters: `task_id` (str), `progress` (float), `status` (str)
  - Sends progress updates to the client via WebSocket
  - Defined as a nested function within agent_websocket

**Dependencies**:
- FastAPI for API routing and WebSocket handling
- Starlette for WebSocket state management
- AsyncIO for asynchronous operations
- JWT authentication for user verification
- RedisClient for persistence
- AgentController for processing messages
- Settings for application configuration
- Logging for error tracking

**Usage Patterns**:
- Provides real-time communication with the AI agent via WebSockets
- Implements asynchronous message processing with progress updates
- Tracks active connections for each user
- Enforces authentication and authorization
- Handles WebSocket lifecycle (connection, messages, disconnection)
- Provides REST endpoints for task management
- Supports clearing conversation memory
- Implements proper error handling and logging
- Uses dependency injection for service access
- Ensures proper cleanup of resources on disconnection

#### backend/app/routers/ai_chat.py

**File Purpose**: Provides API endpoints for chatting with the AI agent about videos and getting contextual responses.

**Models**:
- `ChatRequest`: Request model for AI chat
  - Fields: `message` (str), `video_id` (str)
  - Represents a user's message to the AI about a specific video

- `ChatResponse`: Response model for AI chat
  - Fields: `message` (str), `actions` (Optional[List[Dict[str, Any]]]), `video_updates` (Optional[Dict[str, Any]])
  - Contains the AI's response message, suggested actions, and any updates to the video

- `ContextualResponseRequest`: Request model for contextual responses
  - Fields: `context_type` (str), `prompt` (Optional[str]), `scene_number` (Optional[int]), `voice_type` (Optional[str]), `music_style` (Optional[str])
  - Specifies the type of contextual response needed and relevant parameters

- `ContextualResponseResponse`: Response model for contextual responses
  - Fields: `message` (str)
  - Contains the AI's contextual response message

**Endpoints**:
- `POST /ai/chat`: Chat with the AI agent about a video
  - Parameters: ChatRequest object
  - Returns: ChatResponse object
  - Requires authentication
  - Processes the message with the AgentOrchestrator
  - Returns the AI's response with suggested actions and video updates

- `POST /ai/contextual-response`: Get a contextual response from the AI agent
  - Parameters: ContextualResponseRequest object
  - Returns: ContextualResponseResponse object
  - Requires authentication
  - Gets a contextual response based on the specified context type
  - Supports various context types (scene_breakdown_intro, generation_started, generation_completed, etc.)

- `GET /ai/voices`: Get available voice options
  - Parameters: None
  - Returns: List of voice options
  - Requires authentication
  - Returns mock voice data (would fetch from database in production)

**Variables**:
- `router`: APIRouter instance for AI chat endpoints
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- Settings for application configuration
- JWT authentication for user verification
- AgentOrchestrator for processing messages and generating responses
- BackgroundTasks for asynchronous processing
- Logging for error tracking

**Usage Patterns**:
- Provides REST API endpoints for chatting with the AI agent
- Implements structured request/response models with validation
- Supports video-specific chat interactions
- Provides contextual responses for different stages of video creation
- Returns suggested actions for the frontend to display
- Handles errors gracefully with appropriate HTTP exceptions
- Uses dependency injection for service access
- Supports mock voice options for text-to-speech selection

#### backend/app/routers/ai_generation.py

**File Purpose**: Provides a unified endpoint for all AI generation tasks, with a focus on video generation.

**Models** (imported from schemas):
- `UnifiedGenerationRequest`: Request model for unified AI generation
  - Fields: `prompt` (str), `video_id` (Optional[UUID]), `scene_id` (Optional[UUID]), `reference_files` (Optional[List[str]]), `preferences` (Optional[Dict[str, Any]]), `client_context` (Optional[Dict[str, Any]])
  - Represents a user's request for AI-generated content

- `UnifiedGenerationResponse`: Response model for unified AI generation
  - Fields: `response_type` (ResponseType), `message` (str), `data` (Dict[str, Any]), `task_id` (Optional[str]), `ui_action` (Optional[UIAction])
  - Contains the response with appropriate data and UI action

- `TaskStatus`: Response model for task status
  - Fields: `progress` (float), `message` (str), `status` (str), `task_id` (str), `user_id` (Optional[str]), `updated_at` (Optional[datetime]), `result` (Optional[Dict[str, Any]])
  - Represents the current status of a task

**Endpoints**:
- `POST /ai/generate`: Unified AI generation endpoint
  - Parameters: UnifiedGenerationRequest object
  - Returns: UnifiedGenerationResponse object
  - Requires authentication
  - Analyzes the user's intent and routes to appropriate generator
  - Handles credit checking and asynchronous processing
  - Returns task ID for long-running operations

- `GET /ai/generate/status/{task_id}`: Get task status
  - Parameters: `task_id` (str)
  - Returns: TaskStatus object
  - Requires authentication
  - Verifies that the task belongs to the user
  - Retrieves task status from Redis

- `POST /ai/generate/cancel/{task_id}`: Cancel a task
  - Parameters: `task_id` (str)
  - Returns: Dictionary with success status and message
  - Requires authentication
  - Verifies that the task belongs to the user
  - Cancels the task and updates status in Redis

**Functions**:
- `analyze_intent(prompt, video_id, scene_id, reference_files, preferences, client_context)`: Analyzes the user's prompt to determine intent
  - Parameters: Various request parameters
  - Returns: Dictionary with intent analysis
  - Currently simplified to always return video generation intent

- `process_video_generation_task(orchestrator, credit_service, redis_client, task_id, user_id, request, estimated_credits)`: Background task handler for video generation
  - Parameters: Various service dependencies and task parameters
  - Handles credit reservation, task processing, and error handling
  - Updates task progress in Redis
  - Refunds credits on failure

- `_map_intent_to_response_type(intent)`: Maps intent to response type
  - Parameters: `intent` (str)
  - Returns: ResponseType enum value
  - Provides mapping from intent strings to response types

- `_create_ui_action_for_intent(intent, result, client_context)`: Creates UI action based on intent and result
  - Parameters: `intent` (str), `result` (Dict[str, Any]), `client_context` (Optional[Dict[str, Any]])
  - Returns: UIAction object
  - Customizes UI action based on intent and current page

**Variables**:
- `router`: APIRouter instance for AI generation endpoints
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- Settings for application configuration
- JWT authentication for user verification
- VideoOrchestrator for video generation
- CreditService for managing user credits
- RedisClient for task persistence
- BackgroundTasks for asynchronous processing
- Logging utilities for structured logging
- UUID for generating unique task IDs
- Datetime for timestamp handling

**Usage Patterns**:
- Provides a unified entry point for all AI generation tasks
- Implements intent analysis to determine the appropriate generator
- Handles credit checking and reservation
- Processes video generation asynchronously with progress tracking
- Stores task state in Redis for persistence
- Implements task status monitoring and cancellation
- Uses structured logging with context for debugging
- Handles errors gracefully with credit refunds
- Creates appropriate UI actions based on intent and client context
- Uses dependency injection for service access

#### backend/app/routers/auth.py

**File Purpose**: Provides authentication-related API endpoints, specifically for token exchange between Supabase and the backend.

**Models**:
- `TokenResponse`: Response model for token exchange
  - Fields: `access_token` (str), `token_type` (str, default="bearer")
  - Represents the JWT token response after successful authentication

**Endpoints**:
- `POST /auth/token`: Exchange a Supabase token for a backend token
  - Parameters: `authorization` header containing Supabase token
  - Returns: TokenResponse object with backend access token
  - Verifies the Supabase token and creates a new backend JWT token
  - Ensures user profile exists in the database, creating a default one if needed

**Functions**:
- `exchange_token(authorization, supabase_service)`: Exchanges a Supabase token for a backend token
  - Parameters: `authorization` (Optional[str]), `supabase_service` (SupabaseService)
  - Returns: TokenResponse with access token
  - Extracts and validates the Supabase token from the authorization header
  - Verifies the token with the Supabase service
  - Creates or retrieves user profile
  - Generates a new JWT token for backend authentication

**Variables**:
- `router`: APIRouter instance for authentication endpoints

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- JWT authentication utilities for token creation
- Supabase authentication utilities for token verification
- SupabaseService for user profile management

**Usage Patterns**:
- Provides a bridge between Supabase authentication and backend authentication
- Implements token exchange for seamless authentication flow
- Ensures user profiles exist in the database
- Creates default user profiles with initial credits for new users
- Handles various error cases with appropriate HTTP exceptions
- Extracts user information from Supabase tokens
- Generates JWT tokens with user information for backend use
- Uses dependency injection for service access

#### backend/app/routers/generation.py

**File Purpose**: Provides API endpoints for generating various types of content using AI models, including images, videos, voice cloning, speech, music, and sound effects.

**Models** (imported from schemas):
- `GenerationRequest`: Request model for video generation
  - Fields: `prompt` (str), `video_id` (Optional[UUID]), various preferences
  - Represents a user's request for video generation

- `GenerationStatusResponse`: Response model for generation status
  - Fields: `task_id` (str), `video_id` (Optional[UUID]), `status` (GenerationStatus), `progress` (float), various status fields
  - Represents the current status of a generation task

- Various request/response models for specific generation types:
  - `TextToImageRequest/Response`: For image generation
  - `ImageToVideoRequest/Response`: For video generation from images
  - `VoiceCloneRequest/Response`: For voice cloning
  - `TextToSpeechRequest/Response`: For speech generation
  - `TextToMusicRequest/Response`: For music generation
  - `MusicGenerationRequest/Response`: For music generation with Meta's MusicGen

**Endpoints**:
- `POST /generation/image`: Generate an image from a text prompt
  - Parameters: TextToImageRequest object
  - Returns: TextToImageResponse object
  - Uses text-to-image service to generate images

- `POST /generation/video/from-image`: Generate a video from an image URL
  - Parameters: ImageToVideoRequest object
  - Returns: ImageToVideoResponse object
  - Uses image-to-video service to generate videos

- `POST /generation/video/from-file`: Generate a video from an uploaded image file
  - Parameters: Form data with prompt, image file, duration, aspect ratio
  - Returns: ImageToVideoResponse object
  - Handles file upload and video generation

- `POST /generation/voice/clone`: Clone a voice from an audio URL
  - Parameters: VoiceCloneRequest object
  - Returns: VoiceCloneResponse object
  - Uses text-to-speech service to clone voices

- `POST /generation/voice/clone-from-file`: Clone a voice from an uploaded audio file
  - Parameters: Form data with audio file and processing options
  - Returns: VoiceCloneResponse object
  - Handles file upload and voice cloning

- `POST /generation/speech`: Generate speech from text
  - Parameters: TextToSpeechRequest object
  - Returns: TextToSpeechResponse object
  - Uses text-to-speech service to generate speech

- `POST /generation/music`: Generate music from text
  - Parameters: TextToMusicRequest object
  - Returns: TextToMusicResponse object
  - Uses text-to-music service to generate music

- `POST /generation/sound-effect`: Generate a sound effect from a description
  - Parameters: description (str), duration (float)
  - Returns: TextToMusicResponse object
  - Uses text-to-music service to generate sound effects

- `POST /generation/music/meta`: Generate music with Meta's MusicGen model
  - Parameters: MusicGenerationRequest object
  - Returns: MusicGenerationResponse object
  - Uses music generation service with Meta's model

- `POST /generation/start`: Start a video generation task
  - Parameters: GenerationRequest object
  - Returns: GenerationStatusResponse object
  - Starts an asynchronous video generation task

- `GET /generation/status/{task_id}`: Get the status of a video generation task
  - Parameters: task_id (str)
  - Returns: GenerationStatusResponse object
  - Retrieves detailed status information for a task

- `GET /generation/progress/{task_id}`: Get the progress of a generation task
  - Parameters: task_id (str)
  - Returns: Dictionary with progress information
  - Provides a simpler progress tracking endpoint

**Functions**:
- `track_progress(task_id, progress, message)`: Tracks progress of a generation task
  - Parameters: `task_id` (str), `progress` (float), `message` (Optional[str])
  - Updates the global progress tracking dictionary

- `generate_video_in_background(task_id, request, user_id, video_generator)`: Background task for video generation
  - Parameters: `task_id` (str), `request` (GenerationRequest), `user_id` (str), `video_generator` (VideoGenerator)
  - Simulates the video generation process with step-by-step progress updates
  - Updates task status and progress information

**Variables**:
- `router`: APIRouter instance for generation endpoints
- `logger`: Logger instance for error tracking
- `generation_progress`: Dictionary for tracking progress of generation tasks
- `generation_tasks`: Dictionary for storing detailed task information

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- Settings for application configuration
- JWT authentication for user verification
- Various services for content generation:
  - TextToImageService
  - ImageToVideoService
  - TextToSpeechService
  - TextToMusicService
  - MusicGenerationService
  - CreditService
  - VideoGenerator
- BackgroundTasks for asynchronous processing
- UUID for generating unique task IDs
- Asyncio for simulating asynchronous work
- Time module for timestamps

**Usage Patterns**:
- Provides a comprehensive set of endpoints for AI-generated content
- Implements progress tracking for long-running operations
- Handles credit deduction and refunds for paid operations
- Processes generation tasks asynchronously with background tasks
- Provides detailed step-by-step progress information
- Handles file uploads for various content types
- Enforces authentication and authorization
- Implements proper error handling and logging
- Uses dependency injection for service access
- Simulates video generation with realistic progress updates

#### backend/app/routers/scenes.py

**File Purpose**: Provides API endpoints for scene breakdown and video generation in the Pixora AI platform.

**Models**:
- `ScriptRequest`: Request model for script generation
  - Fields: `prompt` (str), `style` (Optional[str])
  - Represents a user's request to generate a script from a prompt

- `ScriptResponse`: Response model for script generation
  - Fields: `title` (str), `description` (str), `style` (str), `narration` (str), `tone` (Optional[str]), `target_audience` (Optional[str]), `key_points` (Optional[List[str]])
  - Contains the generated script with metadata

- `SceneBreakdownRequest`: Request model for scene breakdown
  - Fields: `script` (Dict[str, Any]), `duration` (int, default=30, range 10-300)
  - Represents a request to break down a script into scenes

- `SceneResponse`: Response model for a scene
  - Fields: `id` (str), `title` (str), `description` (str), `duration` (int), `narration` (str)
  - Represents a single scene in the breakdown

- `SceneBreakdownResponse`: Response model for scene breakdown
  - Fields: `scenes` (List[SceneResponse]), `total_duration` (int)
  - Contains the list of scenes and total duration

- `VideoGenerationRequest`: Request model for video generation
  - Fields: `prompt` (str), `aspect_ratio` (str, default="16:9"), `duration` (int, default=30, range 10-300), `style` (Optional[str])
  - Represents a request to generate a video from a prompt

- `VideoGenerationResponse`: Response model for video generation
  - Fields: `task_id` (str), `prompt` (str), `aspect_ratio` (str), `duration` (int), `style` (Optional[str]), `status` (str), `cost` (int), `actual_duration` (Optional[int])
  - Contains information about the video generation task

- `VideoStatusResponse`: Response model for video status
  - Fields: `task_id` (str), `status` (str), `progress` (float), `message` (str), `result` (Optional[Dict[str, Any]])
  - Represents the current status of a video generation task

**Endpoints**:
- `POST /scenes/script`: Generate a script from a prompt
  - Parameters: ScriptRequest object
  - Returns: ScriptResponse object
  - Uses PromptAnalyzer to generate a script

- `POST /scenes/breakdown`: Generate a scene breakdown from a script
  - Parameters: SceneBreakdownRequest object
  - Returns: SceneBreakdownResponse object
  - Uses PromptAnalyzer to break down a script into scenes

- `POST /scenes/video`: Generate a video from a prompt
  - Parameters: VideoGenerationRequest object
  - Returns: VideoGenerationResponse object
  - Uses VideoGenerator to generate a video
  - Implements rate limiting and checks for active tasks

- `GET /scenes/debug/progress`: Debug endpoint to get the progress dictionary
  - Parameters: None
  - Returns: Dictionary with progress and background tasks
  - Used for debugging video generation progress

- `GET /scenes/video/{task_id}`: Get the status of a video generation task
  - Parameters: task_id (str)
  - Returns: VideoStatusResponse object
  - Uses VideoGenerator to get the status of a task

**Variables**:
- `router`: APIRouter instance for scenes endpoints
- `logger`: Logger instance for error tracking
- `user_last_request`: Dictionary tracking the last request time for each user
- `MIN_REQUEST_INTERVAL`: Minimum time between requests in seconds (5)

**Functions**:
- `generate_script(request, current_user, prompt_analyzer)`: Generates a script from a prompt
  - Parameters: `request` (ScriptRequest), `current_user` (User), `prompt_analyzer` (PromptAnalyzer)
  - Returns: Generated script
  - Handles errors with appropriate HTTP exceptions

- `generate_scene_breakdown(request, current_user, prompt_analyzer)`: Generates a scene breakdown from a script
  - Parameters: `request` (SceneBreakdownRequest), `current_user` (User), `prompt_analyzer` (PromptAnalyzer)
  - Returns: Scene breakdown with total duration
  - Handles errors with appropriate HTTP exceptions

- `generate_video(request, background_tasks, current_user, video_generator)`: Generates a video from a prompt
  - Parameters: `request` (VideoGenerationRequest), `background_tasks` (BackgroundTasks), `current_user` (User), `video_generator` (VideoGenerator)
  - Returns: Video generation task information
  - Implements rate limiting and checks for active tasks
  - Handles errors with appropriate HTTP exceptions

- `get_progress_debug(video_generator)`: Gets the progress dictionary for debugging
  - Parameters: `video_generator` (VideoGenerator)
  - Returns: Dictionary with progress and background tasks
  - Used for debugging video generation progress

- `get_video_status(task_id, current_user, video_generator)`: Gets the status of a video generation task
  - Parameters: `task_id` (str), `current_user` (User), `video_generator` (VideoGenerator)
  - Returns: Video status information
  - Handles errors with appropriate HTTP exceptions

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- Settings for application configuration
- JWT authentication for user verification
- PromptAnalyzer for script generation and scene breakdown
- VideoGenerator for video generation
- BackgroundTasks for asynchronous processing
- Time module for rate limiting
- Logging for error tracking

**Usage Patterns**:
- Provides a complete workflow for video generation (script → scene breakdown → video)
- Implements rate limiting to prevent abuse
- Checks for active tasks to prevent multiple concurrent tasks
- Provides detailed error handling with appropriate HTTP exceptions
- Uses dependency injection for service access
- Supports debugging with a dedicated endpoint
- Tracks progress of video generation tasks
- Enforces authentication and authorization
- Validates request parameters with Pydantic models

#### backend/app/routers/tasks.py

**File Purpose**: Provides API endpoints for task management in the Pixora AI platform.

**Models**:
- `TaskStatusResponse`: Response model for task status
  - Fields: `task_id` (str), `user_id` (str), `status` (str), `progress` (float), `message` (Optional[str]), `result` (Optional[Dict[str, Any]]), `created_at` (float), `updated_at` (float)
  - Represents the detailed status of a task with all metadata

- `TaskSummaryResponse`: Response model for task summary
  - Fields: `task_id` (str), `status` (str), `progress` (float), `created_at` (float), `updated_at` (float)
  - Represents a simplified view of a task for listing purposes

**Endpoints**:
- `GET /tasks/{task_id}`: Get the status of a specific task
  - Parameters: `task_id` (str)
  - Returns: TaskStatusResponse object
  - Retrieves detailed task information from Redis
  - Verifies that the task belongs to the current user

- `GET /tasks/user`: Get all tasks for the current user
  - Parameters: None
  - Returns: List of TaskSummaryResponse objects
  - Retrieves all task IDs for the user from Redis
  - Gets summary information for each task
  - Sorts tasks by creation time (newest first)

**Functions**:
- `get_task_status(task_id, current_user)`: Gets the status of a specific task
  - Parameters: `task_id` (str), `current_user` (User)
  - Returns: TaskStatusResponse with detailed task information
  - Creates a Redis client and retrieves task data
  - Verifies that the task belongs to the current user
  - Raises HTTP exceptions for not found or forbidden access

- `get_user_tasks(current_user)`: Gets all tasks for the current user
  - Parameters: `current_user` (User)
  - Returns: List of TaskSummaryResponse objects
  - Creates a Redis client and retrieves task IDs for the user
  - Gets summary information for each task
  - Sorts tasks by creation time (newest first)

**Variables**:
- `router`: APIRouter instance for tasks endpoints
- `logger`: Logger instance for error tracking

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- JWT authentication for user verification
- RedisClient for task data storage and retrieval
- Settings for application configuration
- Logging for error tracking

**Usage Patterns**:
- Provides endpoints for monitoring task status and history
- Enforces authentication and authorization for task access
- Retrieves task data directly from Redis for efficiency
- Creates a Redis client on-demand rather than using dependency injection
- Formats task data into appropriate response models
- Sorts tasks by creation time for better user experience
- Handles errors with appropriate HTTP exceptions
- Provides both detailed and summary views of tasks

#### backend/app/routers/users.py

**File Purpose**: Provides API endpoints for user management, including profile retrieval, updates, and credit management.

**Models** (imported from schemas):
- `UserResponse`: Response model for user data
  - Fields: `id` (str), `email` (str), `name` (str), `avatar_url` (str), `role` (str), `credits` (int)
  - Represents a user profile with basic information and credit balance

- `UserUpdate`: Request model for user profile updates
  - Fields not explicitly shown in the file, but used for updating user profiles
  - Likely includes fields like name, avatar_url, etc.

**Endpoints**:
- `GET /users/me`: Get current user profile
  - Parameters: None (uses token for authentication)
  - Returns: UserResponse object with user profile data
  - Creates a default profile if the user doesn't exist in the database
  - Uses token data to populate default profile fields

- `PUT /users/{user_id}`: Update user profile
  - Parameters: `user_id` (str), UserUpdate object
  - Returns: UserResponse object with updated profile data
  - Verifies that the user is updating their own profile
  - Updates only the fields provided in the request

- `GET /users/me/credits`: Get current user's credit balance
  - Parameters: None (uses token for authentication)
  - Returns: Dictionary with credit balance
  - Uses CreditService to retrieve the balance

- `POST /users/me/credits`: Add credits to current user's account
  - Parameters: `amount` (int)
  - Returns: Dictionary with new credit balance
  - Uses CreditService to add credits
  - Noted as being for testing purposes only

**Functions**:
- `get_current_user(token_data, supabase_service)`: Gets the current user profile
  - Parameters: `token_data` (TokenData), `supabase_service` (SupabaseService)
  - Returns: UserResponse with user profile data
  - Retrieves user data from Supabase
  - Creates a default profile if the user doesn't exist
  - Uses token data to populate default profile fields

- `update_user(user_id, user_update, current_user_id, supabase_service)`: Updates a user profile
  - Parameters: `user_id` (str), `user_update` (UserUpdate), `current_user_id` (str), `supabase_service` (SupabaseService)
  - Returns: UserResponse with updated profile data
  - Verifies that the user is updating their own profile
  - Updates only the fields provided in the request
  - Raises HTTP exceptions for not found, not authorized, or update failure

- `get_credits(current_user, credit_service)`: Gets the current user's credit balance
  - Parameters: `current_user` (User), `credit_service` (CreditService)
  - Returns: Dictionary with credit balance
  - Uses CreditService to retrieve the balance

- `add_credits(amount, current_user, credit_service)`: Adds credits to the current user's account
  - Parameters: `amount` (int), `current_user` (User), `credit_service` (CreditService)
  - Returns: Dictionary with new credit balance
  - Uses CreditService to add credits
  - Noted as being for testing purposes only

**Variables**:
- `router`: APIRouter instance for user endpoints

**Dependencies**:
- FastAPI for API routing and dependency injection
- Pydantic for request/response model validation
- JWT authentication for user verification
- SupabaseService for user data storage and retrieval
- CreditService for credit management
- UUID for user ID validation

**Usage Patterns**:
- Provides endpoints for user profile management
- Implements automatic profile creation for new users
- Enforces authentication and authorization for profile updates
- Uses dependency injection for service access
- Handles errors with appropriate HTTP exceptions
- Provides credit management functionality
- Ensures users can only update their own profiles
- Uses token data to populate default profile fields
- Supports partial updates with model_dump(exclude_unset=True)

#### backend/app/routers/videos.py

**File Purpose**: Provides API endpoints for video management, including listing and retrieving user videos.

**Endpoints**:
- `GET /videos`: Get user's videos
  - Parameters: None (uses token for authentication)
  - Returns: List of dictionaries containing video information
  - Currently returns placeholder data (would fetch from Supabase in production)
  - Includes basic video metadata (id, title, description, status, created_at, user_id)

- `GET /videos/{video_id}`: Get video by ID
  - Parameters: `video_id` (str)
  - Returns: Dictionary containing video information
  - Currently returns placeholder data for video ID "1" (would fetch from Supabase in production)
  - Raises HTTP 404 exception if video ID is not "1" (simulating video not found)
  - Includes basic video metadata (id, title, description, status, created_at, user_id)

**Functions**:
- `get_videos(current_user_id, supabase_service)`: Gets the current user's videos
  - Parameters: `current_user_id` (str), `supabase_service` (SupabaseService)
  - Returns: List of dictionaries containing video information
  - Currently returns placeholder data (would fetch from Supabase in production)
  - Includes basic video metadata (id, title, description, status, created_at, user_id)

- `get_video(video_id, current_user_id, supabase_service)`: Gets a specific video by ID
  - Parameters: `video_id` (str), `current_user_id` (str), `supabase_service` (SupabaseService)
  - Returns: Dictionary containing video information
  - Currently returns placeholder data for video ID "1" (would fetch from Supabase in production)
  - Raises HTTP 404 exception if video ID is not "1" (simulating video not found)
  - Includes basic video metadata (id, title, description, status, created_at, user_id)

**Variables**:
- `router`: APIRouter instance for video endpoints

**Dependencies**:
- FastAPI for API routing and dependency injection
- JWT authentication for user verification
- SupabaseService for database operations (currently unused but injected for future implementation)

**Usage Patterns**:
- Provides endpoints for video management
- Currently implements placeholder functionality
- Includes comments indicating how real implementation would work
- Enforces authentication for video access
- Handles errors with appropriate HTTP exceptions
- Uses dependency injection for service access
- Simulates basic error cases (video not found)
- Structured for easy extension to real database operations

#### backend/app/routers/voice_samples.py

**File Purpose**: Provides API endpoints for managing voice samples, including creation, retrieval, updating, and deletion.

**Models** (imported from schemas):
- `VoiceSample`: Response model for voice sample data
- `VoiceSampleCreate`: Request model for creating a voice sample
- `VoiceSampleUpdate`: Request model for updating a voice sample
- `VoiceSampleList`: Response model for a list of voice samples

**Endpoints**:
- `POST /voice-samples/`: Create a new voice sample
  - Parameters: Form data with name, description, gender, tone, is_default, is_public, and audio_file
  - Returns: VoiceSample object with created voice sample data
  - Validates audio file format (MP3, WAV, OGG)
  - Requires authentication
  - Uses VoiceSampleService to handle creation

- `GET /voice-samples/`: Get voice samples for the current user
  - Parameters: Query parameters for filtering (include_public, gender, tone, limit, offset)
  - Returns: VoiceSampleList object with voice samples
  - Includes user's own samples and optionally public samples
  - Requires authentication
  - Supports pagination and filtering

- `GET /voice-samples/public`: Get public voice samples
  - Parameters: Query parameters for filtering (gender, tone, limit, offset)
  - Returns: VoiceSampleList object with public voice samples
  - Does not require authentication
  - Supports pagination and filtering

- `GET /voice-samples/{voice_sample_id}`: Get a specific voice sample
  - Parameters: `voice_sample_id` (UUID)
  - Returns: VoiceSample object with voice sample data
  - Requires authentication
  - Checks if sample belongs to user or is public

- `PUT /voice-samples/{voice_sample_id}`: Update a voice sample
  - Parameters: `voice_sample_id` (UUID) and form data with optional fields to update
  - Returns: VoiceSample object with updated voice sample data
  - Validates audio file format if provided
  - Requires authentication
  - Checks if sample belongs to user

- `DELETE /voice-samples/{voice_sample_id}`: Delete a voice sample
  - Parameters: `voice_sample_id` (UUID)
  - Returns: Success response
  - Requires authentication
  - Checks if sample belongs to user

**Functions**:
- `create_voice_sample(name, description, gender, tone, is_default, is_public, audio_file, current_user, service)`: Creates a new voice sample
