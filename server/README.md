# Pixora AI Video Creation Platform - Server

This is the backend server for the Pixora AI Video Creation Platform. It provides a WebSocket-based chat interface for interacting with an AI agent that can generate videos from text prompts. The platform uses cloud storage (Supabase) for all assets, making it production-ready and scalable.

## Features

- WebSocket-based chat interface for real-time interaction with the AI agent
- Script generation with scene breakdown
- Character image generation with consistency across scenes
- Scene image generation
- Voice-over generation using Fal.ai ElevenLabs TTS
- Music generation using Meta MusicGen
- Video generation with motion using Kling 1.6
- Video stitching with transitions and background music
- Supabase integration for authentication, database, and storage

## Requirements

- Python 3.9+
- FFmpeg
- OpenAI API key
- Replicate API token
- Fal.ai API key
- Supabase account (optional)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/pixora-ai.git
cd pixora-ai/server
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on the `.env.example` file:

```bash
cp .env.example .env
```

5. Edit the `.env` file and add your API keys:

```
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Replicate API Token
REPLICATE_API_TOKEN=your_replicate_api_token_here

# FAL.ai API Key
FAL_CLIENT_API_KEY=your_fal_api_key_here

# Supabase Configuration (optional)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
SUPABASE_JWT_SECRET=your_supabase_jwt_secret_here

# JWT Configuration
JWT_SECRET=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

## Running the Server

```bash
python main.py
```

The server will start on http://localhost:8000.

## API Documentation

Once the server is running, you can access the API documentation at http://localhost:8000/docs.

## WebSocket API

The WebSocket API is available at `ws://localhost:8000/api/chat/ws?token=<token>`.

To get a token, you need to call the `/api/auth/token` endpoint with a Supabase JWT token. If you're not using Supabase, you can use the development token in the `.env` file.

### WebSocket Message Format

#### Client to Server

```json
{
  "message": "Create a 30-second video about space exploration",
  "task_id": "optional_task_id"
}
```

#### Server to Client

```json
{
  "type": "agent_message",
  "content": "I'll create a video about space exploration. Let me analyze your prompt and break it down into scenes.",
  "task_id": "task_12345",
  "function_call": null,
  "function_response": null
}
```

## Development

### Project Structure

- `main.py`: Entry point for the application
- `app/`: Main application package
  - `api/`: API endpoints
  - `agents/`: AI agents
  - `tools/`: Tools for the AI agents
  - `utils/`: Utility functions
  - `services/`: Services for external APIs
  - `models/`: Database models
  - `schemas/`: Pydantic schemas

### Cloud Storage Architecture

The platform uses Supabase Storage for all assets, making it production-ready and scalable. The storage is organized into the following buckets:

- `pixora`: Main bucket for all assets
  - `tasks/<task_id>/`: Task-specific assets
    - `script.json`: Script breakdown
    - `characters/`: Character images
    - `scenes/`: Scene images and videos
    - `audio/`: Voice-over audio files
    - `music/`: Background music files
    - `final.mp4`: Final stitched video

All assets are stored with appropriate metadata and can be accessed via URLs, making them CDN-ready. The platform can run in multiple instances without file system conflicts, making it suitable for containerized deployments.

### Error Handling and Logging

The platform includes comprehensive error handling and logging:

- Structured JSON logs (optional)
- Log levels configurable via environment variables
- Detailed error messages with stack traces
- Graceful fallbacks for failed operations
- Automatic cleanup of temporary files

### WebSocket Manager

The WebSocket manager handles real-time communication with clients:

- Connection tracking by user ID
- Task status updates
- Message broadcasting to specific users or tasks
- Automatic reconnection handling
- Error recovery

### Adding a New Tool

To add a new tool to the AI agent, follow these steps:

1. Add the tool definition to the `_get_tools` method in `app/agents/chat_agent.py`
2. Implement the tool function in `app/tools/`
3. Add the tool function to the `function_map` in the `_call_function` method in `app/agents/chat_agent.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
