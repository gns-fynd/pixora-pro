# Pixora AI Video Generator - Coding Standards

This document outlines the coding standards and architectural guidelines for the Pixora AI Video Generator application. Following these standards will ensure consistency throughout the development process and make the codebase more maintainable as it grows.

## Project Structure

### Frontend Structure

```
src/
├── assets/              # Static assets like images, fonts
├── components/          # Reusable UI components
│   ├── ui/              # Basic UI components (buttons, inputs, etc.)
│   ├── shared/          # Shared components used across features
│   └── [feature]/       # Feature-specific components
├── hooks/               # Custom React hooks
├── interfaces/          # TypeScript interfaces and types
├── lib/                 # Utility functions and libraries
├── pages/               # Page components
│   ├── auth/            # Authentication pages
│   ├── dashboard/       # Dashboard pages
│   ├── editor/          # Editor pages
│   └── landing/         # Landing page
├── services/            # API and external service integrations
│   ├── api.ts           # FastAPI client
│   ├── supabase.ts      # Supabase client
│   └── ai-service.ts    # AI service integration
├── store/               # State management
│   ├── use-auth-store.ts    # Authentication state
│   ├── use-video-store.ts   # Video state
│   └── use-editor-store.ts  # Editor state
├── styles/              # Global styles
├── utils/               # Utility functions
├── app.tsx              # Main app component
└── main.tsx             # Entry point
```

### Backend Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app initialization
├── config.py            # Configuration settings
├── dependencies.py      # Dependency injection
├── auth/                # Authentication logic
├── models/              # Data models
├── ai/                  # AI integration
│   ├── prompt_analyzer.py
│   ├── video_generator.py
│   ├── audio_generator.py
│   └── music_generator.py
├── routers/             # API routes
│   ├── auth.py
│   ├── videos.py
│   └── users.py
├── services/            # External service integrations
│   ├── supabase.py
│   ├── fal_ai.py
│   └── credits.py
├── tasks/               # Celery tasks
│   ├── video_tasks.py
│   └── notification_tasks.py
└── utils/               # Utility functions
```

## Naming Conventions

### General

- Use descriptive names that clearly communicate purpose
- Avoid abbreviations unless they are widely understood
- Be consistent with naming patterns across similar entities

### Frontend

- **Components**: PascalCase (e.g., `VideoPlayer.tsx`)
- **Hooks**: camelCase with 'use' prefix (e.g., `useVideoState.ts`)
- **Interfaces**: PascalCase with 'I' prefix (e.g., `IVideoProps`)
- **Types**: PascalCase (e.g., `VideoStatus`)
- **Files**: kebab-case for most files (e.g., `video-player.css`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_VIDEO_DURATION`)

### Backend

- **Modules**: snake_case (e.g., `video_generator.py`)
- **Classes**: PascalCase (e.g., `VideoGenerator`)
- **Functions**: snake_case (e.g., `generate_video`)
- **Variables**: snake_case (e.g., `video_duration`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_VIDEO_DURATION`)

## Code Organization

### React Components

- One component per file (except for small, related components)
- Follow this structure for components:
  1. Imports
  2. Types/Interfaces
  3. Constants
  4. Component definition
  5. Helper functions
  6. Exports

```tsx
// Example component structure
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useVideoState } from '@/hooks/use-video-state';

interface VideoPlayerProps {
  videoUrl: string;
  autoPlay?: boolean;
}

const VIDEO_CONTROLS = ['play', 'pause', 'volume'];

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ 
  videoUrl, 
  autoPlay = false 
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const { currentTime, setCurrentTime } = useVideoState();
  
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };
  
  return (
    <div className="video-player">
      {/* Component JSX */}
    </div>
  );
};

export default VideoPlayer;
```

### Python Code

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Structure modules with:
  1. Imports (standard library, third-party, local)
  2. Constants
  3. Classes
  4. Functions
  5. Main execution (if applicable)

```python
# Example module structure
import os
from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel

from app.models.video import Video
from app.utils.helpers import generate_id

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Models
class SceneDescription(BaseModel):
    visual: str
    audio: str
    duration: int

# Functions
async def analyze_prompt(prompt: str) -> List[SceneDescription]:
    """
    Analyze a prompt and generate scene descriptions.
    
    Args:
        prompt: The user's video prompt
        
    Returns:
        A list of scene descriptions
    """
    # Function implementation
    pass
```

## State Management

### Zustand Store Guidelines

- Create separate stores for different domains (auth, videos, editor)
- Keep stores focused on a specific concern
- Use TypeScript interfaces to define store state and actions
- Follow this pattern for stores:

```tsx
// Example store pattern
import { create } from 'zustand';

interface VideoState {
  // State properties
  videos: Video[];
  currentVideo: Video | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchVideos: () => Promise<void>;
  createVideo: (prompt: string) => Promise<void>;
  updateVideo: (id: string, data: Partial<Video>) => Promise<void>;
  deleteVideo: (id: string) => Promise<void>;
}

const useVideoStore = create<VideoState>((set, get) => ({
  // Initial state
  videos: [],
  currentVideo: null,
  isLoading: false,
  error: null,
  
  // Actions
  fetchVideos: async () => {
    set({ isLoading: true, error: null });
    try {
      // Implementation
      set({ videos: fetchedVideos, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },
  
  // Other actions...
}));

export default useVideoStore;
```

## API Integration

### Frontend API Service Pattern

- Use a consistent pattern for API services
- Implement error handling and loading states
- Use TypeScript for request and response types

```tsx
// Example API service pattern
import axios from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL;

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  const session = await supabase.auth.getSession();
  if (session.data.session) {
    config.headers.Authorization = `Bearer ${session.data.session.access_token}`;
  }
  return config;
});

// API service
export const videoService = {
  getVideos: async () => {
    return api.get('/videos');
  },
  
  createVideo: async (prompt: string, settings: VideoSettings) => {
    return api.post('/videos', { prompt, settings });
  },
  
  // Other methods...
};
```

### Backend API Route Pattern

- Use consistent route organization
- Implement proper dependency injection
- Use Pydantic models for request/response validation

```python
# Example API route pattern
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.video import VideoCreate, VideoResponse
from app.services.video_service import VideoService
from app.auth.jwt import get_current_user

router = APIRouter()

@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    video_data: VideoCreate,
    current_user = Depends(get_current_user),
    video_service: VideoService = Depends()
):
    """
    Create a new video from a prompt
    """
    try:
        return await video_service.create_video(video_data, current_user["id"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

## Styling Guidelines

### CSS/Tailwind Approach

- Use Tailwind CSS for most styling needs
- Create custom components for repeated patterns
- Use CSS modules for complex component-specific styles
- Follow this pattern for custom components:

```tsx
// Example custom component with Tailwind
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'default',
  size = 'md',
  ...props
}) => {
  return (
    <button
      className={cn(
        // Base styles
        'rounded font-medium transition-colors',
        // Variant styles
        variant === 'primary' && 'bg-primary text-white hover:bg-primary/90',
        variant === 'secondary' && 'bg-secondary text-white hover:bg-secondary/90',
        variant === 'ghost' && 'bg-transparent hover:bg-gray-100',
        // Size styles
        size === 'sm' && 'px-3 py-1 text-sm',
        size === 'md' && 'px-4 py-2',
        size === 'lg' && 'px-6 py-3 text-lg',
        // Additional classes
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};
```

## Error Handling

### Frontend Error Handling

- Use try/catch blocks for async operations
- Store error states in component state or global store
- Display user-friendly error messages
- Log detailed errors for debugging

```tsx
// Example error handling
const handleSubmit = async () => {
  setLoading(true);
  setError(null);
  
  try {
    await videoService.createVideo(prompt, settings);
    navigate('/videos');
  } catch (error) {
    // User-friendly error message
    setError('Failed to create video. Please try again.');
    // Detailed logging
    console.error('Video creation error:', error);
  } finally {
    setLoading(false);
  }
};
```

### Backend Error Handling

- Use proper HTTP status codes
- Return structured error responses
- Implement global exception handlers
- Log detailed errors

```python
# Example exception handler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

class VideoGenerationError(Exception):
    def __init__(self, message: str):
        self.message = message

@app.exception_handler(VideoGenerationError)
async def video_generation_exception_handler(request: Request, exc: VideoGenerationError):
    logger.error(f"Video generation failed: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message}
    )
```

## Testing Guidelines

### Frontend Testing

- Use Vitest for unit and component testing
- Test components, hooks, and utilities
- Mock API calls and external dependencies
- Follow this pattern for component tests:

```tsx
// Example component test
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoPlayer } from './VideoPlayer';

describe('VideoPlayer', () => {
  it('renders video element with correct source', () => {
    render(<VideoPlayer videoUrl="https://example.com/video.mp4" />);
    const videoElement = screen.getByTestId('video-player');
    expect(videoElement).toBeInTheDocument();
    expect(videoElement.src).toContain('https://example.com/video.mp4');
  });
  
  it('toggles play/pause when button is clicked', () => {
    render(<VideoPlayer videoUrl="https://example.com/video.mp4" />);
    const playButton = screen.getByRole('button', { name: /play/i });
    fireEvent.click(playButton);
    expect(playButton).toHaveTextContent('Pause');
    fireEvent.click(playButton);
    expect(playButton).toHaveTextContent('Play');
  });
});
```

### Backend Testing

- Use pytest for API and unit testing
- Use test database for integration tests
- Mock external services
- Follow this pattern for API tests:

```python
# Example API test
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_video():
    # Setup test data
    test_prompt = "Create a video about nature"
    test_settings = {"duration": 30, "aspect_ratio": "16:9"}
    
    # Mock authentication
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Make request
    response = client.post(
        "/videos",
        json={"prompt": test_prompt, "settings": test_settings},
        headers=headers
    )
    
    # Assert response
    assert response.status_code == 201
    data = response.json()
    assert data["prompt"] == test_prompt
    assert data["status"] == "pending"
    assert "id" in data
```

## Documentation Guidelines

### Code Documentation

- Use JSDoc for JavaScript/TypeScript
- Use docstrings for Python
- Document complex functions, components, and classes
- Include parameter descriptions and return values
- Explain non-obvious logic

```tsx
// Example JSDoc
/**
 * Generates a video from a prompt and settings
 * 
 * @param prompt - The user's video description
 * @param settings - Video generation settings
 * @param settings.duration - Desired video duration in seconds
 * @param settings.aspectRatio - Video aspect ratio (16:9, 9:16, 1:1)
 * @returns Promise resolving to the generated video data
 * @throws Will throw an error if generation fails
 */
async function generateVideo(
  prompt: string, 
  settings: VideoSettings
): Promise<VideoData> {
  // Implementation
}
```

```python
# Example Python docstring
def generate_video(prompt: str, settings: dict) -> dict:
    """
    Generate a video from a prompt and settings.
    
    Args:
        prompt: The user's video description
        settings: A dictionary containing video settings
            - duration: Desired video duration in seconds
            - aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            
    Returns:
        A dictionary containing the generated video data
        
    Raises:
        VideoGenerationError: If video generation fails
    """
    # Implementation
```

### API Documentation

- Use OpenAPI/Swagger for API documentation
- Include example requests and responses
- Document error responses
- Keep documentation in sync with implementation

## Performance Considerations

### Frontend Performance

- Use React.memo for expensive components
- Implement virtualization for long lists
- Optimize bundle size with code splitting
- Use proper loading states and skeleton screens

### Backend Performance

- Use async processing for long-running tasks
- Implement database query optimization
- Use caching where appropriate
- Monitor and optimize API response times

## Security Guidelines

### Frontend Security

- Sanitize user inputs
- Use HTTPS for all API calls
- Implement proper authentication flows
- Store sensitive data securely (JWT tokens, etc.)

### Backend Security

- Validate all inputs with Pydantic models
- Implement proper authentication and authorization
- Use parameterized queries to prevent SQL injection
- Set up proper CORS configuration
- Implement rate limiting

## Version Control Guidelines

- Use descriptive branch names (feature/video-generation, fix/auth-error)
- Write meaningful commit messages
- Create pull requests with clear descriptions
- Review code before merging

## Conclusion

Following these coding standards will ensure consistency throughout the development process and make the codebase more maintainable as it grows. These standards should be reviewed and updated as needed throughout the development lifecycle.
