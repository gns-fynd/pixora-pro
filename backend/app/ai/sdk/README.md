# Pixora AI WebSocket-Centric Architecture

This directory contains the implementation of the WebSocket-centric architecture for Pixora AI using the OpenAI Agents SDK.

## Overview

The WebSocket-centric architecture provides a real-time, interactive experience for video generation. It uses the OpenAI Agents SDK to create a natural, conversational interface for users to generate videos.

Key components:
- WebSocket connection manager for real-time communication
- OpenAI Agents SDK integration for natural language interaction
- Task context for dependency injection and state management
- Specialized agents for different stages of video generation

## Architecture

```
app/ai/sdk/
├── __init__.py        # Package exports
├── agent.py           # Agent definitions and tools
├── context.py         # Task context for dependency injection
└── README.md          # This file

app/ai/
├── websocket_manager.py  # WebSocket connection manager
└── utils/
    └── duration_adjuster.py  # Media duration adjustment utilities

app/routers/
└── websocket_router.py  # WebSocket endpoints
```

## Agents

The system uses multiple specialized agents:

1. **VideoCreationAgent**: Main agent for video generation
2. **SceneBreakdownAgent**: Specialized agent for scene breakdown
3. **CharacterGeneratorAgent**: Specialized agent for character generation
4. **EditorAgent**: Specialized agent for video editing

Each agent has access to specific tools relevant to its task.

## WebSocket Protocol

The WebSocket protocol is designed to be simple and flexible:

### Connection

1. Connect to `/api/v1/ws/{task_id}`
2. Send JWT token for authentication
3. Receive connection confirmation

### Message Types

#### Client to Server

1. **Chat Message**:
   ```json
   {
     "type": "chat_message",
     "message": "Create a video about space exploration"
   }
   ```

2. **Command**:
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

#### Server to Client

1. **Token** (streaming response):
   ```json
   {
     "type": "token",
     "content": "I'll"
   }
   ```

2. **Tool Call**:
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

3. **Tool Result**:
   ```json
   {
     "type": "tool_result",
     "data": {
       "tool": "generate_scene_breakdown_tool",
       "result": "..."
     }
   }
   ```

4. **Message**:
   ```json
   {
     "type": "message",
     "data": {
       "role": "assistant",
       "content": "I've created a scene breakdown for your space exploration video."
     }
   }
   ```

5. **Progress Update**:
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

6. **Completion**:
   ```json
   {
     "type": "completion",
     "data": {
       "video_url": "https://example.com/videos/123.mp4",
       "thumbnail_url": "https://example.com/thumbnails/123.jpg",
       "message": "Video generation complete"
     }
   }
   ```

7. **Error**:
   ```json
   {
     "type": "error",
     "message": "Failed to generate scene breakdown"
   }
   ```

## Commands

The system supports the following commands:

1. **generate_scene_breakdown**: Generate a scene breakdown from a prompt
   - Parameters:
     - `prompt`: The prompt for the video
     - `style`: The style of the video (e.g., cinematic, cartoon)
     - `duration`: The approximate duration in seconds
     - `aspect_ratio`: The aspect ratio (default: 16:9)

2. **update_scene**: Update a specific scene in the breakdown
   - Parameters:
     - `scene_index`: The index of the scene to update (starting from 1)
     - `new_content`: The new content for the scene
     - `update_type`: What to update - "script", "visual", or "both"

3. **generate_video**: Start the video generation process
   - Parameters: None (uses the approved scene breakdown)

4. **check_generation_status**: Check the status of video generation
   - Parameters: None

## Storage Structure

The system uses the following folder structure for storage:

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

## Testing

You can test the WebSocket implementation using the `test_websocket.py` script:

```bash
python backend/test_websocket.py --token YOUR_JWT_TOKEN --prompt "Create a video about space exploration"
```

Or test a specific command:

```bash
python backend/test_websocket.py --token YOUR_JWT_TOKEN --command generate_scene_breakdown --params '{"prompt": "Space exploration", "style": "cinematic", "duration": 60}'
```

## Implementation Notes

1. The WebSocket implementation uses FastAPI's WebSocket support
2. The OpenAI Agents SDK is used for natural language interaction
3. Redis is used for task persistence and state management
4. The system supports streaming responses for a more interactive experience
5. The architecture is designed to be modular and extensible
