# Pixora AI WebSocket-Centric Architecture Reference Document

This comprehensive document outlines the architecture, implementation details, and design decisions for the Pixora AI WebSocket-centric approach using the OpenAI Agents SDK.

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │◄────┤  WebSocket API  │◄────┤  OpenAI Agents  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ▲                      ▲                       ▲
         │                      │                       │
         │                      │                       │
         ▼                      ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  State Manager  │     │  Task Manager   │     │  Tool Registry  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               ▲
                               │
                               ▼
                        ┌─────────────────┐
                        │                 │
                        │  Redis Storage  │
                        │                 │
                        └─────────────────┘
```

### 1.2 Key Components

- [x] **WebSocket Layer**
  - Real-time bidirectional communication
  - Connection management
  - Message broadcasting
  - Progress tracking

- [x] **Agent System**
  - Main video agent for orchestration
  - Specialized agents for specific tasks
  - Context-aware agent selection
  - Tool execution framework

- [x] **Task Management**
  - Task creation and tracking
  - State persistence
  - Progress reporting
  - Error handling

- [ ] **Storage System** (Phase 2)
  - Hierarchical folder structure
  - Consistent naming conventions
  - Metadata tracking
  - Cleanup mechanisms

## 2. WebSocket Implementation

### 2.1 Connection Manager

- [x] **Connection Tracking**
  - Map task_id to list of active connections
  - Map user_id to set of task_ids
  - Connection lifecycle management

- [x] **Message Types**
  - Progress updates
  - Tool executions
  - Chat messages
  - Completion notifications
  - Error messages

- [x] **Broadcasting Methods**
  - Send to specific task
  - Broadcast to user
  - Send progress updates
  - Send tool execution updates

### 2.2 WebSocket Protocol

- [x] **Client to Server Messages**
  ```json
  {
    "type": "chat_message",
    "message": "Create a video about space exploration"
  }
  ```
  ```json
  {
    "type": "command",
    "command": "generate_scene_breakdown",
    "params": {
      "prompt": "Space exploration",
      "style": "cinematic",
      "duration": 60
    }
  }
  ```

- [x] **Server to Client Messages**
  ```json
  {
    "type": "token",
    "content": "I'll"
  }
  ```
  ```json
  {
    "type": "tool_call",
    "data": {
      "tool": "generate_scene_breakdown_tool",
      "parameters": {
        "prompt": "Space exploration",
        "style": "cinematic",
        "duration": 60
      }
    }
  }
  ```
  ```json
  {
    "type": "progress_update",
    "data": {
      "progress": 50,
      "stage": "video_generation",
      "message": "Generating scene videos"
    }
  }
  ```

### 2.3 Authentication

- [x] **Token-Based Authentication**
  - JWT validation for WebSocket connections
  - User identification and authorization
  - Session management

## 3. OpenAI Agents SDK Integration

### 3.1 Agent Definitions

- [x] **Main Video Agent**
  - System instructions for video generation
  - Access to all tools
  - Overall orchestration

- [x] **Scene Breakdown Agent**
  - Specialized for scene breakdown
  - Access to scene-related tools
  - Detailed prompt analysis

- [x] **Character Generator Agent**
  - Character design and consistency
  - Personality and visual traits
  - Role definition

- [x] **Asset Generator Agent**
  - Image generation
  - Audio creation
  - Video segment production

- [x] **Video Composer Agent**
  - Final video assembly
  - Transition management
  - Audio-visual synchronization

- [x] **Editor Agent**
  - Video editing capabilities
  - Scene modification
  - Asset adjustment

### 3.2 Task Context

- [x] **Context Structure**
  - Task ID
  - User ID
  - State management
  - Persistence methods

- [x] **State Management**
  - Get/set methods
  - Serialization
  - Redis integration
  - Progress tracking
  - Message history

### 3.3 Tool Definitions

- [x] **Scene Tools**
  - Scene breakdown generation
  - Scene updating
  - Scene visualization

- [x] **Video Generation Tools**
  - Video generation
  - Status checking
  - Result retrieval

- [x] **Utility Tools**
  - Progress tracking
  - Error handling
  - User preference management

## 4. Storage System

### 4.1 Folder Structure

- [ ] **Hierarchical Organization**
  ```
  {timestamp}-{task_id}/
  ├── scene_1/
  │   ├── script.json
  │   ├── video/
  │   │   └── scene_1.mp4
  │   ├── audio/
  │   │   └── narration.mp3
  │   └── image/
  │       └── scene_image.png
  ├── scene_2/
  │   └── ...
  ├── music/
  │   └── background.mp3
  └── final_video.mp4
  ```

### 4.2 Storage Adapter

- [ ] **File Operations**
  - Save methods for different file types
  - URL generation
  - Metadata tracking

- [ ] **Cleanup Mechanisms**
  - Temporary file handling
  - Error recovery
  - Resource management

## 5. Media Processing

### 5.1 TTS Implementation

- [ ] **Fixes and Improvements**
  - Remove `return_timestamps=True` parameter
  - Standardize method naming
  - Implement chunking for long texts

### 5.2 Duration Adjustment

- [ ] **Audio Adjustment**
  - Target duration matching
  - Speed adjustment
  - Quality preservation

- [ ] **Video Adjustment**
  - Speed modification
  - Looping for extension
  - Trimming for reduction

- [ ] **Music Handling**
  - Looping for longer videos
  - Fade-out implementation
  - Volume normalization

## 6. Task Management

### 6.1 Task Creation and Tracking

- [ ] **Task Lifecycle**
  - Creation
  - Execution
  - Completion
  - Error handling

- [ ] **Progress Tracking**
  - Stage-based progress
  - Percentage calculation
  - Status messages

### 6.2 Redis Integration

- [ ] **Data Storage**
  - Task data
  - Scene breakdowns
  - Generation status
  - Results

- [ ] **Persistence Methods**
  - JSON serialization
  - Key naming conventions
  - Expiration policies

## 7. Implementation Phases

### 7.1 Phase 1: Core Infrastructure ✅

- [x] WebSocket Connection Manager
- [x] OpenAI Agents SDK Integration
- [x] Authentication for WebSockets

### 7.2 Phase 2: Tool Implementation

- [ ] Convert Existing Tools to SDK Format
- [ ] Fix TTS Implementation
- [ ] Implement Storage Adapter Tools

### 7.3 Phase 3: Task Management Integration

- [ ] Enhance Task Manager
- [ ] Implement Duration Adjustment Utility

### 7.4 Phase 4: WebSocket Router Implementation

- [ ] Create WebSocket Router
- [ ] Integrate with Main Application

### 7.5 Phase 5: Code Cleanup and Integration

- [ ] Remove Redundant Code
- [ ] Update Requirements
- [ ] Documentation

## 8. Technical Considerations

### 8.1 Error Handling

- [ ] **WebSocket Errors**
  - Connection issues
  - Authentication failures
  - Message parsing errors

- [ ] **Agent Errors**
  - Tool execution failures
  - Context management issues
  - Model limitations

- [ ] **Media Processing Errors**
  - File format issues
  - Duration adjustment failures
  - Storage problems

### 8.2 Performance Optimization

- [ ] **Connection Management**
  - Efficient broadcasting
  - Connection cleanup
  - Resource management

- [ ] **Agent Execution**
  - Appropriate model selection
  - Context size management
  - Tool result caching

- [ ] **Media Processing**
  - Parallel processing
  - Resource allocation
  - Caching strategies

### 8.3 Security Considerations

- [ ] **Authentication**
  - Token validation
  - User verification
  - Permission checking

- [ ] **Input Validation**
  - Message validation
  - Parameter checking
  - Error reporting

- [ ] **Resource Protection**
  - Rate limiting
  - User quotas
  - System monitoring

## 9. Integration Points

### 9.1 Frontend Integration

- [ ] **WebSocket Client**
  - Connection management
  - Message handling
  - UI updates

- [ ] **User Interface**
  - Progress display
  - Tool visualization
  - Result presentation

### 9.2 Backend Integration

- [ ] **Main Application**
  - Router inclusion
  - Dependency injection
  - Error handling

- [ ] **Authentication System**
  - Token validation
  - User management
  - Session handling

### 9.3 External Services

- [ ] **OpenAI API**
  - Model selection
  - Context management
  - Error handling

- [ ] **Storage Services**
  - File management
  - URL generation
  - Cleanup processes

## 10. Video Creation Pipeline

### 10.1 End-to-End Process Flow

- [ ] **User Prompt Analysis**
  - Parse user intent
  - Extract key themes, style preferences, and duration requirements
  - Determine if characters are needed

- [ ] **Scene Breakdown Generation**
  - Create logical scene sequence
  - Define narrative flow
  - Assign approximate durations
  - Specify transitions between scenes

- [ ] **Character Generation** (if needed)
  - Create consistent character profiles
  - Define visual characteristics
  - Establish personality traits
  - Ensure consistency across scenes

- [ ] **Asset Generation**
  - Generate scene images based on prompts
  - Create narration audio from scripts
  - Convert static images to video segments
  - Generate background music matching mood

- [ ] **Video Composition**
  - Combine scene videos in sequence
  - Add transitions between scenes
  - Layer narration audio with scene videos
  - Add background music with appropriate volume
  - Apply final adjustments (color grading, etc.)

### 10.2 Interactive Workflow

- [ ] **Scene Breakdown Approval**
  - Present scene breakdown to user
  - Allow modifications to individual scenes
  - Support regeneration of specific scenes
  - Confirm final breakdown before proceeding

- [ ] **Progress Tracking**
  - Real-time updates on generation stages
  - Percentage completion indicators
  - Detailed status messages
  - Error notifications with recovery options

- [ ] **Result Delivery**
  - Provide final video URL
  - Include thumbnail image
  - Offer scene-by-scene breakdown
  - Support downloading or sharing options

## 11. Comprehensive Tool List

### 11.1 Scene Generation Tools

- [x] **generate_scene_breakdown_tool**
  ```python
  @function_tool
  async def generate_scene_breakdown_tool(
      ctx: RunContextWrapper[TaskContext],
      prompt: str,
      style: str,
      duration: int,
      aspect_ratio: str = "16:9",
      mood: Optional[str] = None
  ) -> Dict[str, Any]:
      """Generate a scene breakdown from the user's prompt."""
      # Implementation completed in Phase 1
  ```

- [x] **update_scene_tool**
  ```python
  @function_tool
  async def update_scene_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      new_content: str,
      update_type: str = "both"  # "script", "visual", or "both"
  ) -> Dict[str, Any]:
      """Update a specific scene in the breakdown."""
      # Implementation completed in Phase 1
  ```

- [ ] **regenerate_scene_tool**
  ```python
  @function_tool
  async def regenerate_scene_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      additional_guidance: str = ""
  ) -> Dict[str, Any]:
      """Regenerate a specific scene with new guidance."""
      # Implementation details
  ```

### 11.2 Character Generation Tools

- [ ] **generate_character_tool**
  ```python
  @function_tool
  async def generate_character_tool(
      ctx: RunContextWrapper[TaskContext],
      name: str,
      role: str,
      description: str,
      personality: str = ""
  ) -> Dict[str, Any]:
      """Generate a character profile with consistent traits."""
      # Implementation details
  ```

- [ ] **update_character_tool**
  ```python
  @function_tool
  async def update_character_tool(
      ctx: RunContextWrapper[TaskContext],
      character_id: str,
      updates: Dict[str, str]
  ) -> Dict[str, Any]:
      """Update aspects of an existing character."""
      # Implementation details
  ```

### 11.3 Image Generation Tools

- [ ] **generate_scene_image_tool**
  ```python
  @function_tool
  async def generate_scene_image_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      prompt: str,
      style: str,
      aspect_ratio: str = "16:9"
  ) -> Dict[str, Any]:
      """Generate an image for a specific scene."""
      # Implementation details
  ```

- [x] **regenerate_scene_image_tool**
  ```python
  @function_tool
  async def regenerate_scene_image_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      new_prompt: str,
      style_adjustments: Optional[str] = None
  ) -> Dict[str, Any]:
      """Regenerate the image for a specific scene."""
      # Implementation completed in Phase 1
  ```

### 11.4 Audio Generation Tools

- [ ] **generate_narration_tool**
  ```python
  @function_tool
  async def generate_narration_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      script: str,
      voice_type: str = "neutral"
  ) -> Dict[str, Any]:
      """Generate narration audio for a scene."""
      # Implementation details
  ```

- [ ] **generate_music_tool**
  ```python
  @function_tool
  async def generate_music_tool(
      ctx: RunContextWrapper[TaskContext],
      mood: str,
      duration: int,
      genre: str = "ambient"
  ) -> Dict[str, Any]:
      """Generate background music matching the mood."""
      # Implementation details
  ```

- [ ] **adjust_audio_tool**
  ```python
  @function_tool
  async def adjust_audio_tool(
      ctx: RunContextWrapper[TaskContext],
      audio_id: str,
      target_duration: float,
      fade_out: bool = True
  ) -> Dict[str, Any]:
      """Adjust audio to match target duration."""
      # Implementation details
  ```

### 11.5 Video Generation Tools

- [ ] **image_to_video_tool**
  ```python
  @function_tool
  async def image_to_video_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      image_url: str,
      duration: float,
      motion_type: str = "gentle_pan"
  ) -> Dict[str, Any]:
      """Convert a static image to video with motion."""
      # Implementation details
  ```

- [ ] **combine_video_audio_tool**
  ```python
  @function_tool
  async def combine_video_audio_tool(
      ctx: RunContextWrapper[TaskContext],
      scene_index: int,
      video_url: str,
      audio_url: str
  ) -> Dict[str, Any]:
      """Combine video and audio for a scene."""
      # Implementation details
  ```

- [x] **generate_video_tool**
  ```python
  @function_tool
  async def generate_video_tool(
      ctx: RunContextWrapper[TaskContext]
  ) -> Dict[str, Any]:
      """Start the video generation process using the approved scene breakdown."""
      # Implementation completed in Phase 1
  ```

### 11.6 Status and Management Tools

- [x] **check_generation_status_tool**
  ```python
  @function_tool
  async def check_generation_status_tool(
      ctx: RunContextWrapper[TaskContext]
  ) -> Dict[str, Any]:
      """Check the status of the video generation process."""
      # Implementation completed in Phase 1
  ```

- [ ] **update_progress_tool**
  ```python
  @function_tool
  async def update_progress_tool(
      ctx: RunContextWrapper[TaskContext],
      progress: float,
      stage: str,
      message: str
  ) -> Dict[str, Any]:
      """Update the progress of the generation process."""
      # Implementation details
  ```

- [ ] **handle_error_tool**
  ```python
  @function_tool
  async def handle_error_tool(
      ctx: RunContextWrapper[TaskContext],
      error_message: str,
      recovery_action: str = "retry"
  ) -> Dict[str, Any]:
      """Handle errors during the generation process."""
      # Implementation details
  ```

## 12. Tool Integration with External Services

### 12.1 OpenAI Service Integration

- [ ] **Image Generation**
  - DALL-E 3 for high-quality scene images
  - Consistent style across scenes
  - Proper prompt engineering for best results

- [ ] **Text Processing**
  - GPT-4o for script refinement
  - Character dialogue generation
  - Style consistency checking

### 12.2 Replicate Service Integration

- [ ] **Text-to-Speech**
  - LLASA model for natural narration
  - Voice customization options
  - Proper chunking for long texts

- [ ] **Music Generation**
  - MusicGen for background music
  - Style and mood matching
  - Duration adjustment capabilities

### 12.3 Fal.ai Service Integration

- [ ] **Image-to-Video**
  - Convert static images to dynamic videos
  - Apply motion effects (pan, zoom, etc.)
  - Maintain image quality during conversion

## 13. Agent Decision-Making Process

### 13.1 Tool Selection Logic

- [ ] **Context-Aware Selection**
  - Choose tools based on current task stage
  - Consider previous tool results
  - Adapt to user feedback

- [ ] **Error Recovery**
  - Detect tool execution failures
  - Implement retry mechanisms
  - Fall back to alternative approaches

- [ ] **Optimization Strategies**
  - Parallel tool execution when possible
  - Caching of intermediate results
  - Resource-aware scheduling

### 13.2 Agent Collaboration

- [ ] **Main Agent Responsibilities**
  - Overall process orchestration
  - User interaction management
  - High-level decision making

- [ ] **Specialized Agent Roles**
  - Scene breakdown agent for narrative structure
  - Character agent for consistent personalities
  - Editor agent for refinement and adjustments

### 13.3 Feedback Integration

- [ ] **User Feedback Processing**
  - Parse user requests for changes
  - Identify specific elements to modify
  - Translate feedback into tool parameters

- [ ] **Iterative Improvement**
  - Track changes across iterations
  - Maintain consistency with previous versions
  - Apply learned preferences to future generations

## 14. Implementation Details

### 14.1 Tool Implementation Pattern

```python
@function_tool
async def example_tool(
    ctx: RunContextWrapper[TaskContext],
    param1: str,
    param2: int
) -> Dict[str, Any]:
    """Tool description for the agent."""
    
    # 1. Extract context information
    task_id = ctx.context.task_id
    user_id = ctx.context.user_id
    
    # 2. Get relevant state from context
    existing_data = ctx.context.get("some_key")
    
    # 3. Execute core functionality
    result = await some_service.do_something(param1, param2)
    
    # 4. Update context with results
    ctx.context.set("result_key", result)
    
    # 5. Store in Redis for persistence
    await redis_client.set_json(
        f"task:{task_id}:result_key", 
        result
    )
    
    # 6. Return structured result
    return {
        "status": "success",
        "data": result,
        "message": "Operation completed successfully"
    }
```

### 14.2 Error Handling Pattern

```python
try:
    # Attempt the operation
    result = await some_service.do_something()
    return result
except ServiceException as e:
    # Handle service-specific errors
    logger.error(f"Service error: {str(e)}")
    return {
        "status": "error",
        "error_type": "service_error",
        "message": str(e)
    }
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {str(e)}")
    return {
        "status": "error",
        "error_type": "unexpected_error",
        "message": "An unexpected error occurred"
    }
```

### 14.3 Progress Tracking Pattern

```python
# Update progress in Redis
await redis_client.set_json(
    f"task:{task_id}:generation_status",
    {
        "status": "processing",
        "progress": progress_value,
        "message": status_message,
        "timestamp": time.time()
    }
)

# Broadcast to all connections
await connection_manager.send_progress_update(
    task_id=task_id,
    progress=progress_value,
    stage=current_stage,
    message=status_message
)
