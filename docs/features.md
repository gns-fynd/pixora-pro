# Pixora AI Video Generator - Features

## Core Video Generation Features

### AI Prompt Analysis
- Natural language prompt processing
- Scene-by-scene breakdown generation
- Visual and audio description for each scene
- Customizable video settings (aspect ratio, duration, style, tone)
- Editable scene breakdown before generation

### Video Generation Pipeline
- Text-to-image generation for visual content
- Image-to-video conversion for scene clips
- Text-to-audio (TTS) for narration and dialogue
- Text-to-music for background soundtrack
- Scene-based video assembly
- Progress tracking for each generation step

### Video Editing
- Timeline-based editor with existing functionality
- Scene-specific regeneration
- Element version history
- Audio synchronization
- Background music integration
- Multiple aspect ratio support (16:9, 9:16, 1:1)

### Download and Export
- MP4 video download
- Quality selection options
- Thumbnail generation
- Video metadata

## AI Assistant Features

### Prompt Analysis
- Natural language understanding
- Context-aware suggestions
- Scene breakdown generation
- Visual and audio recommendations

### In-Editor AI Assistant
- Context-aware of selected elements
- Element-specific regeneration
- Suggested prompts based on context
- Natural language editing instructions

### Regeneration Capabilities
- Scene-specific regeneration
- Visual-only or audio-only regeneration
- Style and tone adjustments
- Version history tracking

## User Interface

### Landing Page
- Prompt entry as primary focus
- Video settings customization
- Example showcase
- Authentication not required to start

### Scene Breakdown Review
- Overall video summary
- Scene-by-scene breakdown
- Visual and audio descriptions
- Editable scenes
- Regeneration options

### Generation Progress
- Overall progress tracking
- Scene-by-scene progress
- Preview of completed scenes
- Regeneration options for completed scenes
- Estimated time remaining

### Video Preview
- Full video playback
- Scene navigation
- Download options
- Edit in timeline option

### Editor Integration
- Three-column layout (AI Assistant, Preview, Assets)
- Timeline with video, audio, and music tracks
- AI regeneration dialog
- Element version history

### Dashboard and History
- Recent videos display
- Video history with filtering and sorting
- Video metadata and statistics
- Continue editing option

## User Management

### Authentication
- Email/password authentication
- User profiles
- Session management
- Protected routes

### Credit System
- Credit balance display
- Credit usage for video generation
- Credit usage for regeneration
- Credit transaction history
- Admin credit management (manual)

### User Profile
- Profile information management
- Avatar customization
- Usage statistics
- Settings management
- Appearance settings (dark/light mode)

## Technical Architecture

### Frontend
- React with TypeScript
- Vite as build tool
- Zustand for state management
- Tailwind CSS for styling
- Radix UI components
- Remotion for video editing

### Backend
- FastAPI for API endpoints
- Celery with Redis for task queue
- fal.ai models integration
- Video processing pipeline
- Async processing for long-running tasks

### Supabase Integration
- Authentication and user management
- PostgreSQL database
- Storage for video assets
- Row-level security

### Data Flow
- Frontend authentication with Supabase
- API requests to FastAPI with JWT
- Task queue for video generation
- Storage access for assets
- Real-time status updates


