# Pixora AI System Documentation

## Current Project Goal
Migrate the current backend's agent part with the POC (Proof of Concept) agent to create an improved backend with a better agent architecture. This approach will give us the best of both worlds: the solid agent architecture from the POC and the robust authentication, database, and storage systems from the current backend.

## Pixora Workflow: From User Prompt to Generated Video

### User Journey & Backend Flow

#### 1. User Authentication & Project Initialization

**User Journey:**
- User logs into the Pixora platform
- User navigates to "Create New Video" section
- User sees a form to enter a video prompt

**Backend Operations:**
- `/api/v1/auth` endpoint handles authentication using JWT tokens
- Supabase authentication service validates credentials
- User session is established and stored
- Backend prepares credit check for the user's account

#### 2. Video Prompt Submission

**User Journey:**
- User enters a detailed prompt describing the video they want
- User selects preferences (character consistency, duration, style)
- User submits the prompt and sees a "Processing" indicator

**Backend Operations:**
- Frontend sends request to `/api/v1/ai/generate` endpoint
- `ai_generation.py` router receives the request
- System creates a unique task ID
- Credit service checks if user has sufficient credits
- Redis stores initial task status (0% progress)
- Background task is initiated for script generation
- Response with task ID is sent back to frontend

#### 3. Script Generation & Review

**User Journey:**
- User sees the script being generated with real-time updates
- Once complete, user reviews the script breakdown showing:
  - Scene titles and descriptions
  - Narration text for each scene
  - Estimated duration
  - Character descriptions (if enabled)
- User can edit or refine the script

**Backend Operations:**
- `script_agent.py` processes the prompt using OpenAI's GPT-4o
- Agent structures the response into a `ScriptBreakdown` object
- Progress updates are sent to Redis
- Frontend polls `/api/v1/ai/generate/status/{task_id}` for updates
- If user edits script, `/api/scripts/{script_id}/refine` endpoint processes changes
- Updated script is stored in the database

#### 4. Asset Generation Phase

**User Journey:**
- User approves the script and initiates asset generation
- User sees progress indicators for different asset types:
  - Character images (if enabled)
  - Scene images
  - Voice overs
  - Background music
- User can view assets as they're generated

**Backend Operations:**
- `/api/projects/{project_id}` updates project status to GENERATING_ASSETS
- For character images:
  - `asset_tools.py` calls OpenAI's image generation API
  - Generated images are stored and linked to the project
- For each scene:
  - Scene images are generated using OpenAI's image API
  - Voice overs are created using Replicate's LLaSA-3B-Long
  - Audio duration is calculated for timing
- For music:
  - Background music is generated using Meta's MusicGen
  - Music is grouped by scene as defined in the script
- All assets are stored with their metadata
- Progress updates are continuously sent to Redis

#### 5. Video Creation & Stitching

**User Journey:**
- User sees progress of video creation for each scene
- User can preview individual scene videos as they're completed
- User sees final video being stitched together
- Progress bar shows overall completion percentage

**Backend Operations:**
- For each scene:
  - `video_tools.py` creates videos with motion using Kling 1.6 model
  - Scene image and audio are combined
  - Transitions are applied between scenes
- Final video stitching:
  - `stitch_video` function combines all scene videos
  - Adds transitions between scenes
  - Incorporates background music
  - Normalizes audio levels
- Video URL is stored in the project record
- Final progress update (100%) is sent to Redis

#### 6. Video Delivery & Sharing

**User Journey:**
- User receives notification that video is ready
- User can play the final video in the browser
- User can download the video
- User can share the video or make adjustments

**Backend Operations:**
- `/api/videos/project/{project_id}` serves the final video
- Download links are generated with `/api/videos/download/{video_id}`
- Credits are finalized and deducted from user's account
- Project status is updated to COMPLETED
- Analytics are recorded for the generation process

#### 7. Refinement & Regeneration (Optional)

**User Journey:**
- User can select specific scenes to regenerate
- User can adjust parameters for specific assets
- User can request variations of the video

**Backend Operations:**
- `/api/assets/scenes` or `/api/assets/video` endpoints handle regeneration
- Only the selected assets are regenerated
- New assets replace old ones in the project
- Video is re-stitched with new assets
- Credits are only charged for regenerated components

## Detailed Migration Plan

Based on analysis of both codebases, here's a detailed plan for migrating the POC agent to the current backend:

### Phase 1: Setup and Preparation (COMPLETED)

1. **Create Models** ✅
   - Implemented POC models in the current backend:
     - `Scene`, `Clip`, `MusicPrompt`, `CharacterProfile`, `ScriptBreakdown`
     - `Project`, `ProjectStatus`, `AssetGeneration`, `AssetGenerationStatus`
   - Ensured compatibility with existing models

2. **Database Migrations** ✅
   - Created migration script `20250509_001_video_generation_tables.sql`
   - Added proper indexes, triggers, and RLS policies
   - Ensured proper relationships between models

3. **Update Dependencies** ✅
   - Added `fal-client` and `requests` to requirements.txt
   - Ensured compatibility between dependencies

### Phase 2: Core Components Migration (COMPLETED)

4. **Migrate Utility Tools** ✅
   - Implemented `file_utils.py` with functions:
     - `save_file`, `read_file`, `ensure_directory_exists`
     - `get_file_extension`, `generate_unique_filename`
     - `get_file_size`, `delete_file`, `list_files`
   - Implemented `audio_utils.py` with functions:
     - `get_audio_duration`, `normalize_audio`, `combine_audio_tracks`
     - `add_background_music`, `extract_audio_from_video`
     - `convert_audio_format`, `get_audio_properties`
   - Added proper error handling and logging

5. **Migrate Asset Tools** ✅
   - Implemented `asset_tools.py` with functions:
     - `generate_character_images`
     - `generate_scene_image`
     - `generate_voice_over`
     - `generate_music`
     - `generate_assets_for_scene`
     - `generate_music_for_scenes`
   - Integrated with OpenAI, Replicate, and storage services

6. **Migrate Video Tools** ✅
   - Implemented `video_tools.py` with functions:
     - `create_scene_video_with_motion`
     - `normalize_duration`
     - `apply_transition`
     - `stitch_video`
     - `create_video_for_scene`
   - Added support for various transition types
   - Implemented proper error handling and cleanup

7. **Migrate Script Tools and Agent** ✅
   - Implemented `script_tools.py` with functions:
     - `generate_script`
     - `refine_script`
   - Implemented `script_agent.py` with `ScriptAgent` class
   - Implemented `video_agent.py` with `VideoAgent` class
   - Added proper integration with Redis for progress tracking

### Phase 3: API Integration (COMPLETED)

8. **Implement Unified Agent Endpoint** ✅
   - Created a unified `/api/v1/agent` endpoint for all AI interactions
   - Implemented WebSocket support at `/api/v1/agent/ws/{user_id}`
   - Added comprehensive error handling and validation
   - Integrated with authentication and credit systems

9. **Create Chat Agent** ✅
   - Implemented `ChatAgent` class that handles:
     - Script generation
     - Asset generation
     - Video creation
     - Interactive chat
   - Added support for tool calling with OpenAI
   - Implemented conversation history management
   - Added progress tracking and real-time updates

10. **Implement WebSocket Support** ✅
    - Added WebSocket support for real-time communication
    - Implemented progress updates for:
      - Script generation
      - Asset generation
      - Video creation
    - Added support for action buttons in responses
    - Ensured proper authentication for WebSocket connections

### Phase 4: Testing and Deployment

11. **Create Test Cases**
    - Implement unit tests for new components:
      - Test script generation with various prompts
      - Test asset generation with different parameters
      - Test video creation with various inputs
    - Create integration tests for end-to-end workflow
    - Test error handling and recovery

12. **End-to-End Testing**
    - Test the complete workflow from prompt to video
    - Verify all components work together correctly
    - Test with various input scenarios:
      - Short videos vs. long videos
      - Different styles and preferences
      - Character consistency enabled/disabled
    - Test performance and resource usage

13. **Deployment and Monitoring**
    - Deploy the updated backend
    - Set up monitoring for:
      - API endpoints
      - Background tasks
      - Resource usage
      - Error rates
    - Implement logging for debugging
    - Create documentation for the new system

## Technical Architecture

The new system combines the best components from both backends:

### From POC Backend
- Agent architecture with tool-based approach
- Script generation and scene breakdown
- Video processing tools
- Asset generation pipeline

### From Current Backend
- JWT authentication with Supabase
- Database integration and migrations
- Storage system for assets
- Credit management system
- WebSocket communication

## Key Components

### Agent System
The agent system is the core of the new backend, providing:
- Script generation from user prompts
- Scene breakdown and asset generation
- Video processing and stitching
- Interactive chat capabilities

### Authentication System
The authentication system provides:
- JWT token validation and creation
- Supabase integration for user management
- Role-based access control

### Database System
The database system stores:
- User profiles and authentication data
- Video metadata and scene information
- Asset references and URLs
- Credit transactions and usage history

### Storage System
The storage system manages:
- Asset files (images, audio, video)
- Temporary files during processing
- Final video outputs
- Secure access to stored files

## Implementation Timeline

1. **Week 1: Setup and Structure (COMPLETED)**
   - Created models and database migrations ✅
   - Updated dependencies ✅
   - Set up basic project structure ✅

2. **Week 2: Core Components Migration (COMPLETED)**
   - Migrated utility tools ✅
   - Migrated asset tools ✅
   - Migrated video tools ✅
   - Migrated script tools and agent ✅

3. **Week 3: API Integration (COMPLETED)**
   - Implemented unified agent endpoint ✅
   - Created chat agent with tool calling ✅
   - Implemented WebSocket support ✅

4. **Week 4: Frontend Integration (COMPLETED)**
   - Updated frontend services to use the new agent API ✅
   - Implemented WebSocket support for real-time updates ✅
   - Added support for action buttons in chat responses ✅
   - Created enhanced UI components for the chat interface ✅

## Comparison of Current Backend vs New Agent Architecture

### Current Backend:
- Uses a monolithic `VideoOrchestrator` class
- Handles all video generation in a single process
- Limited modularity and separation of concerns
- Uses a task-based approach with Redis for tracking

### New Agent Architecture:
- Uses a modular approach with separate components for scripts, assets, videos
- Clear separation between script generation, asset generation, and video stitching
- Project-based workflow with well-defined states
- More comprehensive tools for video generation, asset management, etc.

## Migration Benefits

1. **Improved Modularity**
   - Better separation of concerns
   - Easier to maintain and extend
   - More focused components

2. **Enhanced Video Generation**
   - Better script generation with character consistency
   - Improved scene generation with motion
   - More realistic voice overs and music

3. **More Robust Error Handling**
   - Better recovery from failures
   - More detailed error messages
   - Improved logging and monitoring

4. **Scalability**
   - More efficient resource usage
   - Better parallel processing
   - Improved performance for large videos

## Next Steps

1. **Testing and Validation**
   - Create unit tests for all new components:
     - Script generation and refinement
     - Asset generation (images, audio, music)
     - Video creation and stitching
     - Chat agent and tool calling
   - Implement integration tests for end-to-end workflow
   - Test with various input scenarios and edge cases

2. **Documentation and Deployment**
   - Update API documentation with new endpoints
   - Create developer guides for the agent architecture
   - Deploy to staging environment for user testing
   - Set up monitoring and logging for production

3. **Frontend Integration (COMPLETED)** ✅
   - Updated frontend to use the new unified agent endpoint ✅
   - Implemented WebSocket support for real-time updates ✅
   - Added support for action buttons in chat responses ✅
   - Created new UI components for the chat interface ✅

4. **Performance Optimization**
   - Profile the application to identify bottlenecks
   - Optimize asset generation and video processing
   - Implement caching for frequently accessed data
   - Add support for distributed processing for large videos
