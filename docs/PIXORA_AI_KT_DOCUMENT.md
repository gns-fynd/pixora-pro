# Pixora AI - Technical Knowledge Transfer Document

## 1. Project Overview

Pixora AI is a comprehensive video generation platform that leverages AI to create professional videos from text prompts. The platform follows a multi-step process:

1. Users enter a text prompt describing the video they want to create
2. AI analyzes the prompt and breaks it down into scenes
3. The system generates visuals, audio narration, and background music
4. All components are assembled into a final video
5. Users can edit the video in a timeline editor

The project consists of a React/TypeScript frontend and a FastAPI Python backend, with Supabase providing authentication, database, and storage services.

## 2. System Architecture

### 2.1 Frontend Architecture

- **Framework**: React 18 with TypeScript
- **State Management**: Zustand for global state
- **Styling**: TailwindCSS with custom components
- **Routing**: React Router v6
- **Form Handling**: React Hook Form with Zod validation
- **HTTP Client**: Axios with custom wrapper (ApiClient)
- **UI Components**: Mix of custom components and Radix UI primitives
- **Video Editing**: Remotion for video composition and rendering

### 2.2 Backend Architecture

- **Framework**: FastAPI (Python)
- **Authentication**: JWT with Supabase integration
- **Database**: PostgreSQL via Supabase
- **Storage**: Supabase Storage
- **AI Services**: Integration with various AI providers:
  - Text-to-Image: Fal.ai
  - Image-to-Video: Fal.ai
  - Text-to-Speech: Fal.ai
  - Text-to-Music: Fal.ai and Replicate (Meta MusicGen)
- **Credit System**: Tracks user credit usage for AI operations

### 2.3 Data Flow

```
User Input → Frontend → API Client → Backend API → AI Services → Storage → Frontend → Video Player/Editor
```

## 3. Frontend Components - Technical Details

### 3.1 Component Architecture

The frontend follows a hierarchical component structure:

```
App
├── ThemeProvider
├── ChatProvider
└── RouterProvider
    ├── Landing
    │   └── TypedPlaceholder (Animated text input)
    ├── Auth
    │   ├── SignIn
    │   ├── SignUp
    │   └── ResetPassword
    ├── SceneBreakdown
    │   └── SplitScreenLayout (Chat + Content)
    ├── Generation
    │   └── SplitScreenLayout (Chat + Content)
    └── Editor
        ├── Timeline
        ├── Player
        └── Controls
```

### 3.2 State Management Implementation

#### Zustand Store Pattern

The auth store (`src/store/use-auth-store.ts`) uses Zustand with immer middleware for immutable updates:

```typescript
const useAuthStore = create<AuthStore>()(
  immer((set) => ({
    // State
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    
    // Actions
    setUser: (user) => set((state) => {
      state.user = user;
      state.isAuthenticated = !!user;
      state.error = null;
    }),
    
    signIn: async (email, password) => {
      set((state) => { state.isLoading = true; });
      try {
        // Auth logic
        set((state) => { 
          state.user = user;
          state.isAuthenticated = true;
        });
      } catch (error) {
        set((state) => { state.error = error.message; });
      } finally {
        set((state) => { state.isLoading = false; });
      }
    },
    // Other actions...
  }))
);
```

#### Context API Usage

The ChatContext (`src/context/ChatContext.tsx`) uses React Context API with useReducer for complex state:

```typescript
// Reducer pattern for chat state management
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload]
      };
    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: []
      };
    // Other cases...
  }
}

// Provider component
export const ChatProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  
  // Memoized context value
  const value = useMemo(() => ({
    messages: state.messages,
    addMessage: (message: ChatMessage) => 
      dispatch({ type: 'ADD_MESSAGE', payload: message }),
    clearMessages: () => 
      dispatch({ type: 'CLEAR_MESSAGES' }),
  }), [state.messages]);
  
  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};
```

### 3.3 API Client Implementation

The ApiClient (`src/services/api-client.ts`) implements several advanced patterns:

1. **Request Deduplication**: Prevents duplicate API calls
2. **Request Cancellation**: Uses AbortController for cleanup
3. **Request Throttling**: Limits request frequency
4. **Error Handling**: Custom error class with status codes
5. **Authentication**: Token injection via interceptors

```typescript
// Request deduplication example
async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  // Generate a unique key for this request
  const requestKey = this.getRequestKey('GET', url);
  
  // Check if this exact request is already in progress
  if (this.ongoingRequests.has(requestKey)) {
    console.debug(`Duplicate GET request detected: ${requestKey}`);
    const request = this.ongoingRequests.get(requestKey);
    if (request) {
      return request.promise as Promise<T>;
    }
  }
  
  // Create an AbortController with proper signal handling
  const controller = this.setupAbortController(config);
  
  // Create the request promise
  const requestPromise = (async () => {
    try {
      const response: AxiosResponse<T> = await this.client.get(url, {
        ...config,
        signal: controller.signal
      });
      return response.data;
    } finally {
      // Remove from ongoing requests when done
      setTimeout(() => {
        this.ongoingRequests.delete(requestKey);
      }, 100);
    }
  })();
  
  // Store the promise and controller
  this.ongoingRequests.set(requestKey, { 
    promise: requestPromise,
    controller
  });
  
  return requestPromise;
}
```

### 3.4 Form Handling with React Hook Form and Zod

The landing page form uses React Hook Form with Zod validation:

```typescript
// Form schema definition
const promptSchema = z.object({
  prompt: z.string().min(10, 'Prompt must be at least 10 characters'),
  aspectRatio: z.enum(['16:9', '9:16', '1:1']).default('16:9'),
  duration: z.number().min(5).max(300).default(30),
  style: z.enum(['cinematic', 'cartoon', 'realistic', 'artistic']).default('cinematic'),
});

// Form initialization
const form = useForm<PromptFormValues>({
  resolver: zodResolver(promptSchema),
  defaultValues: {
    prompt: '',
    aspectRatio: '16:9',
    duration: 30,
    style: 'cinematic',
  },
});

// Form submission
const onSubmit = async (values: PromptFormValues) => {
  setIsSubmitting(true);
  try {
    await apiClient.post('/prompts', values);
    navigate('/scene-breakdown');
  } catch (error) {
    console.error('Error submitting prompt:', error);
  } finally {
    setIsSubmitting(false);
  }
};
```

### 3.5 TypedPlaceholder Component Implementation

The TypedPlaceholder component (`src/components/ui/typed-placeholder.tsx`) uses multiple useEffect hooks for animation control:

```typescript
export function TypedPlaceholder({
  staticText,
  examples,
  typingSpeed = 100,
  deletingSpeed = 50,
  delayAfterComplete = 2000,
  className = '',
  onFocus
}: TypedPlaceholderProps) {
  const [currentText, setCurrentText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  
  // Add ellipsis to each example
  const processedExamples = examples.map(example => `${example}...`);
  const currentExample = processedExamples[exampleIndex];
  
  // Prevent auto-focus on component mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsTyping(true);
    }, 500);
    
    return () => clearTimeout(timer);
  }, []);

  // Typing animation effect
  useEffect(() => {
    if (!isTyping) return;

    let timeout: NodeJS.Timeout;

    if (isDeleting) {
      // Deleting text logic
      if (currentText === '') {
        setIsDeleting(false);
        setExampleIndex((prev) => (prev + 1) % examples.length);
        timeout = setTimeout(() => {}, 500);
      } else {
        timeout = setTimeout(() => {
          setCurrentText(currentText.slice(0, -1));
        }, deletingSpeed);
      }
    } else {
      // Typing text logic
      if (currentText === currentExample) {
        timeout = setTimeout(() => {
          setIsDeleting(true);
        }, delayAfterComplete);
      } else {
        timeout = setTimeout(() => {
          setCurrentText(currentExample.slice(0, currentText.length + 1));
        }, typingSpeed);
      }
    }

    return () => clearTimeout(timeout);
  }, [currentText, isDeleting, exampleIndex, examples, currentExample, typingSpeed, deletingSpeed, delayAfterComplete, isTyping]);
}
```

## 4. Backend Services - Technical Details

### 4.1 FastAPI Application Structure

The FastAPI application (`backend/app/main.py`) uses the following patterns:

1. **Lifespan Context Manager**: For startup/shutdown events
2. **Dependency Injection**: For service instantiation
3. **Router Organization**: Modular API endpoints
4. **Global Exception Handler**: Centralized error handling

```python
# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup logic
    print("Starting up Pixora AI API...")
    yield
    # Shutdown logic
    print("Shutting down Pixora AI API...")

# Create FastAPI app
app = FastAPI(
    title="Pixora AI API",
    description="API for Pixora AI video generation platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_detail = str(exc)
    print(f"Unhandled exception: {error_detail}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Include routers
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(videos.router, prefix="/api/v1", tags=["videos"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(generation.router, prefix="/api/v1", tags=["generation"])
app.include_router(scenes.router, prefix="/api/v1", tags=["scenes"])
app.include_router(ai_chat.router, prefix="/api/v1", tags=["ai"])
```

### 4.2 Pydantic Models

The backend uses Pydantic for data validation and serialization:

```python
# Generation request schema
class GenerationRequest(BaseModel):
    video_id: Optional[str] = None
    prompt: str
    aspect_ratio: str = "16:9"
    duration: int = 30
    style: Optional[str] = "cinematic"
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Create a promotional video for a new smartphone",
                "aspect_ratio": "16:9",
                "duration": 30,
                "style": "cinematic"
            }
        }

# Generation status response schema
class GenerationStatusResponse(BaseModel):
    task_id: str
    video_id: Optional[str] = None
    status: GenerationStatus
    progress: float
    current_step: Optional[GenerationStep] = None
    step_progress: Optional[float] = None
    message: str
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]] = []
```

### 4.3 Background Task Processing

The generation router uses background tasks for long-running operations:

```python
@router.post("/start", response_model=GenerationStatusResponse)
async def start_generation(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    video_generator: VideoGenerator = Depends(),
    credit_service: CreditService = Depends(),
):
    # Generate a task ID
    task_id = f"full_video_{str(uuid.uuid4())[:8]}_{current_user.id}"
    
    # Create task info
    task_info = GenerationTaskInfo(...)
    
    # Store task info
    generation_tasks[task_id] = task_info
    
    # Start the generation in the background
    background_tasks.add_task(
        generate_video_in_background,
        task_id=task_id,
        request=request,
        user_id=current_user.id,
        video_generator=video_generator
    )
    
    # Return the initial status
    return GenerationStatusResponse(...)
```

### 4.4 Service Layer Pattern

The backend implements a service layer pattern for business logic:

```python
# Service class example
class TextToImageService:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        storage_manager: StorageManager = Depends(),
    ):
        self.api_key = settings.FAL_API_KEY
        self.api_url = settings.FAL_API_URL
        self.storage_manager = storage_manager
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_image(
        self,
        request: TextToImageRequest,
        user_id: str,
        progress_callback: Optional[Callable[[float, Optional[str]], None]] = None,
    ) -> TextToImageResponse:
        # Implementation details
        if progress_callback:
            progress_callback(10.0, "Preparing image generation request")
            
        # API call to Fal.ai
        response = await self.client.post(
            f"{self.api_url}/text-to-image",
            headers={"Authorization": f"Key {self.api_key}"},
            json=request.dict(),
        )
        
        if progress_callback:
            progress_callback(50.0, "Processing image generation results")
            
        # Process response
        result = response.json()
        
        # Store image in Supabase
        image_url = await self.storage_manager.store_image(
            image_data=result["image"],
            user_id=user_id,
            filename=f"generated_{uuid.uuid4()}.png",
        )
        
        if progress_callback:
            progress_callback(100.0, "Image generation complete")
            
        return TextToImageResponse(
            image_url=image_url,
            prompt=request.prompt,
            width=request.width,
            height=request.height,
        )
```

### 4.5 JWT Authentication

The JWT authentication system (`backend/app/auth/jwt.py`) uses:

1. **PyJWT**: For token encoding/decoding
2. **FastAPI Security**: For dependency injection
3. **Supabase Integration**: For token verification

```python
# JWT authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    supabase_client: SupabaseClient = Depends(get_supabase_client),
) -> User:
    try:
        # Verify token with Supabase
        response = await supabase_client.auth.get_user(token)
        user_data = response.data.user
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user profile from database
        user_profile = await get_user_profile(user_data.id, supabase_client)
        
        return User(
            id=user_data.id,
            email=user_data.email,
            name=user_profile.get("name"),
            avatar_url=user_profile.get("avatar_url"),
            credits=user_profile.get("credits", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

## 5. Authentication System - Technical Details

### 5.1 Authentication Flow Sequence

```
┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
│ Browser │          │ Frontend│          │ Backend │          │ Supabase│
└────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘
     │    Load App        │                    │                    │
     │───────────────────>│                    │                    │
     │                    │                    │                    │
     │                    │  Check Session     │                    │
     │                    │───────────────────>│                    │
     │                    │                    │  Verify Token      │
     │                    │                    │───────────────────>│
     │                    │                    │                    │
     │                    │                    │<───────────────────│
     │                    │<───────────────────│                    │
     │                    │                    │                    │
     │   Sign In Form     │                    │                    │
     │───────────────────>│                    │                    │
     │                    │                    │                    │
     │                    │  Sign In Request   │                    │
     │                    │───────────────────>│                    │
     │                    │                    │  Auth Request      │
     │                    │                    │───────────────────>│
     │                    │                    │                    │
     │                    │                    │<───────────────────│
     │                    │<───────────────────│                    │
     │                    │                    │                    │
     │   Auth Complete    │                    │                    │
     │<───────────────────│                    │                    │
     │                    │                    │                    │
```

### 5.2 Token Storage and Refresh

The auth client (`src/services/auth-client.ts`) handles token storage and refresh:

```typescript
export const authClient = {
  /**
   * Get the auth token from localStorage
   */
  getAuthToken: async (): Promise<string | null> => {
    // Check if we have a token in memory
    if (inMemoryToken) {
      return inMemoryToken;
    }
    
    // Check if we have a token in localStorage
    const token = localStorage.getItem('pixora_auth_token');
    
    if (!token) {
      return null;
    }
    
    // Check if the token is expired
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expiryTime = payload.exp * 1000; // Convert to milliseconds
      
      // If token is expired or about to expire (within 5 minutes)
      if (Date.now() >= expiryTime - 5 * 60 * 1000) {
        // Try to refresh the token
        const newToken = await refreshToken();
        return newToken;
      }
      
      // Token is valid
      inMemoryToken = token;
      return token;
    } catch (error) {
      console.error('Error parsing token:', error);
      return null;
    }
  },
  
  /**
   * Set the auth token in localStorage
   */
  setAuthToken: (token: string | null): void => {
    if (token) {
      localStorage.setItem('pixora_auth_token', token);
      inMemoryToken = token;
    } else {
      localStorage.removeItem('pixora_auth_token');
      inMemoryToken = null;
    }
  },
  
  /**
   * Clear the auth token
   */
  clearAuthToken: (): void => {
    localStorage.removeItem('pixora_auth_token');
    inMemoryToken = null;
  }
};
```

### 5.3 Direct Supabase Auth vs Backend Auth

The system supports two authentication modes:

1. **Direct Supabase Auth**: Frontend communicates directly with Supabase
2. **Backend Auth**: Frontend communicates with backend, which handles Supabase

```typescript
// Backend auth service with mode switching
export const backendAuthService = {
  signInWithEmail: async (email: string, password: string): Promise<AuthResponse> => {
    try {
      // Check if we should use direct Supabase auth
      const useDirectSupabaseAuth = import.meta.env.VITE_USE_DIRECT_SUPABASE_AUTH === 'true';
      
      if (useDirectSupabaseAuth) {
        // Sign in with Supabase directly
        const supabaseResponse = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (supabaseResponse.error) throw new Error(supabaseResponse.error.message);

        // Set the Supabase token in the API client
        apiClient.setAuthToken(supabaseResponse.data.session?.access_token || null);

        // Get the user profile
        const user = await apiClient.get<User>('/users/me');

        return {
          user,
          session: supabaseResponse.data.session,
          error: null,
        };
      } else {
        // Use the backend login endpoint
        const tokenResponse = await apiClient.post<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', {
          username: email,
          password,
        });

        // Set the token in the API client
        apiClient.setAuthToken(tokenResponse.access_token);

        // Get the user profile
        const user = await apiClient.get<User>('/users/me');

        // Create a session object
        const session: Session = {
          access_token: tokenResponse.access_token,
          refresh_token: '',
          expires_at: Math.floor(Date.now() / 1000) + tokenResponse.expires_in,
          user: {
            id: user.id,
            email: user.email,
          },
        };

        return {
          user,
          session,
          error: null,
        };
      }
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Invalid email or password',
      };
    }
  },
  // Other auth methods...
};
```

## 6. Video Generation Flow - Technical Details

### 6.1 Scene Breakdown Process

The scene breakdown process involves:

1. **Script Generation**: Convert prompt to structured script
2. **Scene Segmentation**: Break script into logical scenes
3. **Duration Allocation**: Assign time to each scene
4. **Visual Description**: Generate detailed visual descriptions
5. **Narration Creation**: Create narration text for each scene

```typescript
// Scene breakdown data structure
interface SceneBreakdownResponse {
  scenes: SceneResponse[];
  total_duration: number;
}

interface SceneResponse {
  id: string;
  title: string;
  description: string;
  duration: number;
  narration: string;
}

// Scene breakdown fetch logic
const fetchSceneBreakdown = async () => {
  setIsLoading(true);
  setError(null);
  
  try {
    // Get prompt data from localStorage
    const storedPrompt = localStorage.getItem('pixora_prompt');
    if (!storedPrompt) {
      throw new Error('No prompt data found.');
    }
    
    const promptData = JSON.parse(storedPrompt);
    setPrompt(promptData);
    
    // Step 1: Generate script from prompt
    const scriptResponse = await apiClient.post<ScriptResponse>('/scenes/script', {
      prompt: promptData.prompt,
      style: promptData.style
    });
    
    // Store script in localStorage
    localStorage.setItem('pixora_script', JSON.stringify(scriptResponse));
    setScript(scriptResponse);
    
    // Step 2: Generate scene breakdown from script
    const breakdownResponse = await apiClient.post<SceneBreakdownResponse>('/scenes/breakdown', {
      script: scriptResponse,
      duration: promptData.duration
    });
    
    // Store scenes in localStorage
    localStorage.setItem('pixora_scenes', JSON.stringify(breakdownResponse));
    
    // Convert API response to Scene format
    const formattedScenes = breakdownResponse.scenes.map(scene => ({
      id: scene.id,
      visual: scene.description,
      audio: scene.narration,
      duration: scene.duration,
      narration: scene.narration
    }));
    
    setScenes(formattedScenes);
    
  } catch (err) {
    console.error('Error fetching scene breakdown:', err);
    setError(err instanceof Error ? err.message : 'An unknown error occurred');
  } finally {
    setIsLoading(false);
  }
};
```

### 6.2 Video Generation Pipeline

The video generation pipeline involves multiple parallel processes:

```
                                ┌─────────────────┐
                                │ Scene Breakdown │
                                └────────┬────────┘
                                         │
                 ┌────────────┬──────────┼──────────┬────────────┐
                 │            │          │          │            │
        ┌────────▼─────┐ ┌────▼─────┐ ┌──▼───┐ ┌────▼─────┐ ┌────▼─────┐
        │ Image Gen    │ │ Text Gen │ │ TTS  │ │ Music Gen│ │ SFX Gen  │
        │ (Fal.ai)     │ │ (GPT-4)  │ │ (Fal)│ │ (Meta)   │ │ (Fal)    │
        └────────┬─────┘ └────┬─────┘ └──┬───┘ └────┬─────┘ └────┬─────┘
                 │            │          │          │            │
                 └────────────┴──────────┼──────────┴────────────┘
                                         │
                                ┌────────▼────────┐
                                │ Video Assembly  │
                                │ (Remotion)      │
                                └────────┬────────┘
                                         │
                                ┌────────▼────────┐
                                │ Final Video     │
                                └─────────────────┘
```

### 6.3 Progress Tracking Implementation

The generation page implements a sophisticated progress tracking system:

```typescript
// Backend progress tracking
generation_progress = {}

def track_progress(task_id: str, progress: float, message: Optional[str] = None):
    generation_progress[task_id] = {
        "progress": progress,
        "message": message or f"Processing: {progress:.0f}%",
    }

// Frontend progress polling
useEffect(() => {
  // If no task ID or already complete, don't poll
  if (!taskId || isComplete || isPolling) return;
  
  // Set polling flag to prevent multiple polling loops
  setIsPolling(true);
  
  // Check status function
  const checkStatus = async () => {
    try {
      // Get generation status
      const status = await apiClient.get<VideoStatusResponse>(`/scenes/video/${taskId}`);
      
      // Update overall progress
      setOverallProgress(status.progress);
      
      // Update step progress
      if (status.current_step) {
        const stepIndex = GENERATION_STEPS.findIndex(step => step.id === status.current_step);
        
        if (stepIndex !== -1) {
          setCurrentStep(stepIndex);
          
          // Update progress for all steps
          setProgress(prev => {
            const newProgress = [...prev];
            
            // Set previous steps to 100%
            for (let i = 0; i < stepIndex; i++) {
              newProgress[i].percentage = 100;
            }
            
            // Set current step progress
            newProgress[stepIndex].percentage = status.step_progress || 0;
            
            // Set next steps to 0%
            for (let i = stepIndex + 1; i < newProgress.length; i++) {
              newProgress[i].percentage = 0;
            }
            
            return newProgress;
          });
        }
      }
      
      // Check if generation is complete
      if (status.status === 'completed') {
        setIsComplete(true);
        setVideoUrl(status.result?.video_url);
        setThumbnailUrl(status.result?.thumbnail_url);
        clearInterval(intervalId);
      }
    } catch (err) {
      console.error('Error checking generation status:', err);
      clearInterval(intervalId);
    }
  };
  
  // Check status immediately
  checkStatus();
  
  // Then check every 2 seconds
  const intervalId = setInterval(checkStatus, 2000);
  
  return () => {
    clearInterval(intervalId);
  };
}, [taskId, currentStep]);
```

## 7. Deployment Process - Technical Details

### 7.1 Frontend Build Process

The frontend build process uses Vite with TypeScript:

```json
// package.json build scripts
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "start": "concurrently \"npm run start:frontend\" \"npm run start:backend\"",
    "start:frontend": "vite preview --port 3000",
    "start:backend": "cd backend && python run.py"
  }
}
```

### 7.2 Vercel Deployment Configuration

The project uses Vercel for deployment with the following configuration:

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
