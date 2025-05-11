# Pixora AI: System Architecture Documentation

This document provides a comprehensive overview of the Pixora AI video generation platform's architecture, including both high-level design and low-level implementation details.

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Key Workflows](#key-workflows)
4. [System Components](#system-components)
5. [Data Model](#data-model)
6. [Frontend Architecture](#frontend-architecture)
7. [Backend Architecture](#backend-architecture)
8. [AI Integration](#ai-integration)
9. [Authentication Flow](#authentication-flow)
10. [Video Generation Pipeline](#video-generation-pipeline)
11. [Deployment Architecture](#deployment-architecture)
12. [Security Considerations](#security-considerations)
13. [Performance Considerations](#performance-considerations)
14. [Future Enhancements](#future-enhancements)

## System Overview

Pixora AI is an advanced AI-powered video generation platform that transforms text prompts into professional-quality videos. The system breaks down user prompts into scenes, generates visual and audio content for each scene, and assembles them into a cohesive video with minimal user intervention.

The platform offers:
- Natural language prompt processing
- Scene-by-scene breakdown generation
- AI-powered visual and audio content creation
- Video assembly with transitions
- Timeline-based video editing
- User management with credit system

## Core Architecture

The application follows a modern client-server architecture:

- **Frontend**: React/TypeScript SPA with Tailwind CSS for styling
- **Backend**: FastAPI Python server with async processing
- **Database**: PostgreSQL via Supabase for data persistence
- **Authentication**: JWT-based auth with Supabase integration
- **Storage**: Supabase Storage for media assets
- **AI Services**: Integration with fal.ai for AI generation capabilities
- **Task Queue**: Celery with Redis for background processing

![Architecture Diagram](images/architecture-diagram.png)

## Key Workflows

### Video Generation Flow

1. User enters a text prompt with video settings (aspect ratio, duration, style)
2. System analyzes prompt and breaks it down into scenes
3. User reviews and can edit scene breakdown
4. System generates visual and audio content for each scene
5. System assembles scenes into a complete video
6. User can download or further edit the video

### Authentication Flow

1. User signs up/in via email/password or OAuth providers (Google, Apple)
2. Frontend authenticates with Supabase
3. Supabase token is exchanged for a backend JWT
4. JWT is used for all subsequent API requests

### Credit System Flow

1. User receives initial credits upon registration
2. Credits are consumed for video generation and regeneration
3. System tracks credit usage and transaction history
4. Admin can manage user credits

## System Components

### Frontend Components

- **Landing Page**: Prompt entry and video settings
- **Scene Breakdown**: Review and edit scene descriptions
- **Generation Progress**: Track video generation progress
- **Video Preview**: View and download completed video
- **Editor**: Timeline-based video editor
- **Dashboard**: Manage video projects and history
- **User Profile**: Manage account and credits

### Backend Services

- **Prompt Analysis Service**: Break down prompts into scenes
- **Video Generation Service**: Generate visual and audio content
- **Assembly Service**: Combine scenes into a video
- **Authentication Service**: Handle user authentication
- **Credit Service**: Manage user credits
- **Storage Service**: Handle media asset storage

### AI Components

- **Text-to-Image**: Generate scene visuals from descriptions
- **Image-to-Video**: Convert still images to video clips
- **Text-to-Speech**: Generate narration and dialogue
- **Text-to-Music**: Generate background music
- **AI Agent**: Orchestrate AI operations with function calling

## Data Model

### Users/Profiles

- User authentication data
- Profile information (name, email, avatar)
- Credit balance
- Account settings

### Videos

- Video metadata (title, description)
- Generation settings (style, aspect ratio, duration)
- Status (pending, processing, completed, failed)
- Output URLs (video, thumbnail)

### Scenes

- Scene descriptions (visual, audio, script)
- Order and duration
- Generated asset URLs (image, video, audio)
- Status (pending, processing, completed, failed)

### Credits

- Credit transactions
- Transaction types (initial, consumption, purchase)
- Timestamps and amounts

### Generation Jobs

- Job status and progress
- Error messages
- Timestamps (started, completed)

## Frontend Architecture

### Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand
- **Styling**: Tailwind CSS with custom components
- **UI Components**: Custom components with Radix UI primitives
- **Routing**: React Router v6
- **HTTP Client**: Custom API client with Axios

### Directory Structure

```
src/
├── assets/            # Static assets
├── components/        # Reusable UI components
│   ├── ui/            # Base UI components
│   ├── shared/        # Shared components
│   └── color-picker/  # Color picker components
├── data/              # Static data and mock data
├── hooks/             # Custom React hooks
├── interfaces/        # TypeScript interfaces
├── lib/               # Utility libraries
├── pages/             # Page components
│   ├── auth/          # Authentication pages
│   ├── landing/       # Landing page
│   ├── scene-breakdown/ # Scene breakdown page
│   ├── generation/    # Generation progress page
│   ├── editor/        # Video editor
│   └── dashboard/     # User dashboard
├── services/          # API services
├── store/             # Zustand state stores
└── utils/             # Utility functions
```

### Key Components

**Authentication Components**:
- `Auth`: Main authentication page
- `SignUp`: User registration
- `ResetPassword`: Password reset flow
- `ProtectedRoute`: Route guard for authenticated routes

**Video Generation Components**:
- `Landing`: Prompt entry and video settings
- `SceneBreakdown`: Scene review and editing
- `Generation`: Generation progress tracking
- `Editor`: Timeline-based video editor

**UI Components**:
- `Button`: Custom button component
- `Dialog`: Modal dialog component
- `Input`: Form input component
- `Textarea`: Text area component
- `Navbar`: Navigation component

### State Management

**Authentication Store**:
```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<AuthResponse>;
  signUp: (email: string, password: string) => Promise<AuthResponse>;
  signOut: () => Promise<void>;
  checkSession: () => Promise<void>;
}
```

**Video Store**:
```typescript
interface VideoState {
  videos: Video[];
  currentVideo: Video | null;
  isLoading: boolean;
  fetchVideos: () => Promise<void>;
  createVideo: (data: VideoCreateData) => Promise<Video>;
  getVideo: (id: string) => Promise<Video>;
  updateVideo: (id: string, data: Partial<Video>) => Promise<Video>;
  deleteVideo: (id: string) => Promise<void>;
}
```

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI with Python 3.9+
- **Database**: PostgreSQL via Supabase
- **Authentication**: JWT with Supabase integration
- **Task Queue**: Celery with Redis
- **AI Integration**: fal.ai API client
- **Storage**: Supabase Storage

### Directory Structure

```
backend/
├── app/
│   ├── ai/            # AI-related modules
│   │   ├── agent.py   # AI agent implementation
│   │   ├── prompt_analyzer.py # Prompt analysis
│   │   └── video_generator.py # Video generation
│   ├── auth/          # Authentication
│   │   └── jwt.py     # JWT handling
│   ├── models/        # Database models
│   ├── routers/       # API routes
│   │   ├── auth.py    # Auth endpoints
│   │   ├── videos.py  # Video endpoints
│   │   ├── scenes.py  # Scene endpoints
│   │   └── users.py   # User endpoints
│   ├── schemas/       # Pydantic schemas
│   │   ├── user.py    # User schemas
│   │   └── video.py   # Video schemas
│   ├── services/      # Business logic
│   │   ├── fal_ai/    # fal.ai integration
│   │   ├── storage/   # Storage service
│   │   ├── credits.py # Credit management
│   │   └── supabase.py # Supabase client
│   ├── tasks/         # Celery tasks
│   │   └── worker.py  # Worker definition
│   └── main.py        # Application entry point
├── db/                # Database migrations
├── docs/              # Documentation
└── tests/             # Unit and integration tests
```

### API Endpoints

**Authentication Endpoints**:
- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login with email/password
- `POST /api/v1/auth/logout`: Logout current user
- `POST /api/v1/auth/reset-password`: Request password reset
- `POST /api/v1/auth/exchange-token`: Exchange Supabase token for JWT

**Video Endpoints**:
- `GET /api/v1/videos`: List user's videos
- `POST /api/v1/videos`: Create a new video
- `GET /api/v1/videos/{id}`: Get video details
- `PUT /api/v1/videos/{id}`: Update video
- `DELETE /api/v1/videos/{id}`: Delete video

**Scene Endpoints**:
- `GET /api/v1/scenes`: List scenes for a video
- `POST /api/v1/scenes`: Create a new scene
- `GET /api/v1/scenes/{id}`: Get scene details
- `PUT /api/v1/scenes/{id}`: Update scene
- `DELETE /api/v1/scenes/{id}`: Delete scene

**Generation Endpoints**:
- `POST /api/v1/generation/analyze`: Analyze prompt
- `POST /api/v1/generation/video/{id}`: Generate video
- `GET /api/v1/generation/status/{job_id}`: Check generation status

**User Endpoints**:
- `GET /api/v1/users/me`: Get current user
- `PUT /api/v1/users/{id}`: Update user
- `GET /api/v1/users/credits`: Get user credits
- `POST /api/v1/users/credits/add`: Add credits

### Database Schema

**profiles Table**:
```sql
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  credits INTEGER DEFAULT 10,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**videos Table**:
```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) NOT NULL,
  title TEXT,
  description TEXT,
  status TEXT DEFAULT 'pending',
  style TEXT,
  aspect_ratio TEXT,
  duration INTEGER,
  output_url TEXT,
  thumbnail_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**scenes Table**:
```sql
CREATE TABLE scenes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) NOT NULL,
  order_index INTEGER NOT NULL,
  visual_description TEXT,
  audio_description TEXT,
  script TEXT,
  duration INTEGER,
  status TEXT DEFAULT 'pending',
  image_url TEXT,
  video_url TEXT,
  audio_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## AI Integration

### fal.ai Services

**Text-to-Image**:
- Model: Flux Pro v1.1 Ultra
- Input: Visual description, style
- Output: Generated image URL

**Image-to-Video**:
- Model: Kling Video v1.6 Pro
- Input: Image URL, duration
- Output: Generated video URL

**Text-to-Speech**:
- Model: MiniMax TTS Voice Clone
- Input: Script text, voice selection
- Output: Generated audio URL

**Text-to-Music**:
- Model: CassetteAI Music Generator
- Input: Music description, duration
- Output: Generated music URL

### AI Agent

The AI Agent uses function calling to orchestrate the AI operations:

```python
class AIAgent:
    def __init__(self):
        self.functions = {}
        
    def register_function(self, name, function, description, parameters):
        self.functions[name] = {
            "function": function,
            "description": description,
            "parameters": parameters
        }
        
    async def run(self, prompt, context, function_names):
        # Call OpenAI with function calling
        # Execute the selected function
        # Return the result
```

## Authentication Flow

1. Frontend authenticates with Supabase
2. Supabase returns a session with access token
3. Frontend exchanges Supabase token for backend JWT
4. Backend verifies Supabase token and issues JWT
5. Frontend stores JWT and uses it for API requests
6. Backend validates JWT for protected endpoints

## Video Generation Pipeline

1. **Prompt Analysis**:
   - Parse user prompt
   - Generate scene breakdown
   - Store scene metadata

2. **Scene Generation**:
   - For each scene:
     - Generate image from visual description
     - Convert image to video clip
     - Generate audio from script
     - Generate background music
     - Store generated assets

3. **Video Assembly**:
   - Combine scene videos
   - Add audio tracks
   - Apply transitions
   - Generate final video
   - Create thumbnail

## Deployment Architecture

- **Frontend**: Static hosting (Vercel/Netlify)
- **Backend**: Docker containers on cloud VMs
- **Database**: Supabase managed PostgreSQL
- **Storage**: Supabase Storage
- **Task Queue**: Redis and Celery workers on cloud VMs
- **CI/CD**: GitHub Actions for automated deployment

## Security Considerations

- JWT-based authentication with short-lived tokens
- HTTPS for all communications
- CORS configuration for API security
- Input validation with Pydantic schemas
- Row-level security in Supabase
- Environment variables for sensitive configuration
- Rate limiting for API endpoints

## Performance Considerations

- Async processing for long-running tasks
- Task queue for background processing
- Caching for frequently accessed data
- Pagination for large data sets
- Optimized database queries
- CDN for static assets and media files

## Future Enhancements

- Advanced video editing capabilities
- AI-powered video enhancement
- Template library for quick video creation
- Collaboration features
- Export to social media platforms
- Mobile application
- Subscription-based pricing model
- Analytics dashboard

---

This architecture document provides both high-level design and low-level implementation details for the Pixora AI video generation platform. It serves as a roadmap for development and a reference for understanding the system's components and interactions.
