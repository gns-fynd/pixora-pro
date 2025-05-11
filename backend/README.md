# Pixora AI Backend

This is the backend for the Pixora AI platform, a video generation platform that uses AI to create videos from text prompts.

## Architecture

The Pixora AI backend is built with FastAPI and follows a modular architecture:

```
backend/
├── app/                    # Main application package
│   ├── ai/                 # AI services
│   │   ├── agent.py        # Agent orchestrator
│   │   ├── prompt_analyzer.py # Prompt analysis with OpenAI
│   │   └── video_generator.py # Video generation service
│   ├── auth/               # Authentication services
│   │   ├── jwt.py          # JWT token handling
│   │   └── supabase.py     # Supabase auth integration
│   ├── core/               # Core application components
│   │   └── config.py       # Application configuration
│   ├── models/             # Database models
│   ├── routers/            # API routes
│   │   ├── auth.py         # Authentication routes
│   │   ├── generation.py   # Content generation routes
│   │   ├── scenes.py       # Scene breakdown routes
│   │   ├── users.py        # User management routes
│   │   └── videos.py       # Video management routes
│   ├── schemas/            # Pydantic schemas
│   │   ├── user.py         # User schemas
│   │   └── video.py        # Video schemas
│   ├── services/           # Business logic services
│   │   ├── credits.py      # Credit management
│   │   ├── fal_ai/         # Fal.ai integration
│   │   ├── storage/        # Storage services
│   │   └── supabase.py     # Supabase service
│   └── main.py             # FastAPI application entry point
├── db/                     # Database scripts
├── docs/                   # Documentation
├── tests/                  # Tests
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
└── run.py                  # Server startup script
```

## Features

- **Authentication**: JWT-based authentication with Supabase
- **User Management**: User profiles, credits, and permissions
- **Content Generation**:
  - Text-to-Image: Generate images from text prompts
  - Image-to-Video: Generate videos from images
  - Text-to-Speech: Generate speech from text
  - Text-to-Music: Generate music from text
- **Video Generation**:
  - Script Generation: Generate a script from a prompt using OpenAI
  - Voice Generation: Generate voiceover audio from the script
  - Scene Breakdown: Break down the script into scenes based on audio timing
  - Background Music: Generate background music matching the audio duration
  - Image Generation: Generate images for each scene
  - Video Creation: Create videos from the generated assets
- **Storage**: File storage with Supabase Storage
- **Credits System**: Track and manage user credits

## Setup

### Prerequisites

- Python 3.9+
- Supabase account
- Fal.ai API key
- OpenAI API key

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```
5. Run the server:
   ```bash
   python run.py
   ```

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

The following environment variables are required:

```
# API settings
API_V1_STR=/api/v1
PROJECT_NAME=Pixora AI

# Security
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Storage
STORAGE_VIDEOS_BUCKET=videos
STORAGE_IMAGES_BUCKET=images
STORAGE_AUDIO_BUCKET=audio
STORAGE_PUBLIC_URL=  # Leave empty to use Supabase URL

# AI Services
FAL_API_KEY=your-fal-ai-api-key
OPENAI_API_KEY=your-openai-api-key

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=True  # Set to False in production
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

This project follows PEP 8 style guidelines. Use `black` and `isort` for formatting:

```bash
black .
isort .
```

## License

This project is proprietary and confidential.
