# Pixora AI Codebase Analysis Checklist

This document tracks the progress of analyzing the Pixora AI Video Generation System codebase. Each file will be marked as analyzed once its modules, functions, classes, parameters, and return values have been documented.

## Backend

### Core

- [x] backend/app/main.py
- [x] backend/app/core/config.py
- [x] backend/run.py
- [x] backend/run_server.py
- [x] backend/test_websocket.py

### AI Module

#### Base Components
- [x] backend/app/ai/agent.py
- [x] backend/app/ai/orchestrator.py
- [x] backend/app/ai/prompt_analyzer.py
- [x] backend/app/ai/video_generator.py
- [x] backend/app/ai/websocket_manager.py

#### Agent System
- [x] backend/app/ai/agent/controller.py
- [x] backend/app/ai/agent/memory.py
- [x] backend/app/ai/agent/orchestrator.py
- [x] backend/app/ai/agent/task.py
- [x] backend/app/ai/agent/task_manager.py

#### Agents and Tools
- [x] backend/app/ai/agents/video_agent.py
- [x] backend/app/ai/agents/tools/character_generator.py
- [x] backend/app/ai/agents/tools/music_generator.py
- [x] backend/app/ai/agents/tools/scene_asset_generator.py
- [x] backend/app/ai/agents/tools/scene_generator.py
- [x] backend/app/ai/agents/tools/video_composer.py
- [x] backend/app/ai/agents/tools/audio_generator.py
- [x] backend/app/ai/agents/tools/image_generator.py
- [x] backend/app/ai/agents/tools/video_generator.py

#### Agent Utilities
- [x] backend/app/ai/agents/utils/dependency_graph.py
- [x] backend/app/ai/agents/utils/parallel.py

#### Models
- [x] backend/app/ai/models/request.py
- [x] backend/app/ai/models/task.py
- [x] backend/app/ai/models/video_metadata.py

#### SDK
- [x] backend/app/ai/sdk/agent.py
- [x] backend/app/ai/sdk/context.py

#### Tasks
- [x] backend/app/ai/tasks/task_manager.py

#### Tools
- [x] backend/app/ai/tools/audio_tools.py
- [x] backend/app/ai/tools/base.py
- [x] backend/app/ai/tools/image_tools.py
- [x] backend/app/ai/tools/script_tools.py
- [x] backend/app/ai/tools/utility_tools.py
- [x] backend/app/ai/tools/video_tools.py

#### Utilities
- [x] backend/app/ai/utils/json_utils.py
- [x] backend/app/ai/utils/model_converters.py
- [x] backend/app/ai/utils/storage_adapter.py
- [x] backend/app/ai/utils/hierarchical_storage_adapter.py
- [x] backend/app/ai/utils/duration_adjuster.py

#### Duration Utilities
- [x] backend/app/ai/utils/duration/audio_adjuster.py
- [x] backend/app/ai/utils/duration/common.py
- [x] backend/app/ai/utils/duration/media_utils.py
- [x] backend/app/ai/utils/duration/scene_manager.py
- [x] backend/app/ai/utils/duration/video_adjuster.py

### Auth
- [x] backend/app/auth/jwt.py
- [x] backend/app/auth/supabase.py

### Routers
- [x] backend/app/routers/admin.py
- [x] backend/app/routers/agent_chat.py
- [x] backend/app/routers/ai_chat.py
- [x] backend/app/routers/ai_generation.py
- [x] backend/app/routers/auth.py
- [x] backend/app/routers/generation.py
- [x] backend/app/routers/scenes.py
- [x] backend/app/routers/tasks.py
- [x] backend/app/routers/users.py
- [x] backend/app/routers/videos.py
- [x] backend/app/routers/voice_samples.py
- [ ] backend/app/routers/websocket_router.py

### Schemas
- [ ] backend/app/schemas/ai_generation.py
- [ ] backend/app/schemas/generation.py
- [ ] backend/app/schemas/scene_image.py
- [ ] backend/app/schemas/user.py
- [ ] backend/app/schemas/voice_sample.py

### Services

#### Core Services
- [ ] backend/app/services/credit_service.py
- [ ] backend/app/services/credits.py
- [ ] backend/app/services/dependencies.py
- [ ] backend/app/services/redis_client.py
- [ ] backend/app/services/supabase.py
- [ ] backend/app/services/voice_sample.py

#### Fal.ai Services
- [ ] backend/app/services/fal_ai/base.py
- [ ] backend/app/services/fal_ai/image_to_video.py
- [ ] backend/app/services/fal_ai/text_to_image.py
- [ ] backend/app/services/fal_ai/text_to_music.py
- [ ] backend/app/services/fal_ai/text_to_speech.py

#### OpenAI Services
- [ ] backend/app/services/openai/service.py
- [ ] backend/app/services/openai/image_generation.py

#### Replicate Services
- [ ] backend/app/services/replicate/base.py
- [ ] backend/app/services/replicate/tts.py
- [ ] backend/app/services/replicate/music_generation.py

#### Storage Services
- [ ] backend/app/services/storage/base.py
- [ ] backend/app/services/storage/manager.py
- [ ] backend/app/services/storage/supabase.py

### Utils
- [ ] backend/app/utils/logging_config.py
- [ ] backend/app/utils/logging_utils.py

### Database
- [ ] backend/db/schema.sql
- [ ] backend/db/apply_fix.sh
- [ ] backend/db/migrations/20250421_001_fix_user_trigger.sql
- [ ] backend/db/migrations/apply_migration.py
- [ ] backend/db/migrations/voice_samples.sql

## Frontend

### Core
- [ ] src/app.tsx
- [ ] src/main.tsx
- [ ] src/index.css
- [ ] src/vite-env.d.ts

### Components
- [ ] src/components/admin-protected-route.tsx
- [ ] src/components/button.tsx
- [ ] src/components/password.tsx
- [ ] src/components/protected-route.tsx
- [ ] src/components/theme-provider.tsx

#### AI Chat Components
- [ ] src/components/ai-chat/AgentChat.tsx
- [ ] src/components/ai-chat/ChatInterface.tsx
- [ ] src/components/ai-chat/index.ts

#### Dashboard Components
- [ ] src/components/dashboard/task-list.tsx

#### Layout Components
- [ ] src/components/layouts/SplitScreenLayout.tsx

#### Shared Components
- [ ] src/components/shared/AppLayout.tsx
- [ ] src/components/shared/draggable.tsx
- [ ] src/components/shared/icons.tsx
- [ ] src/components/shared/Navbar.tsx
- [ ] src/components/shared/ThemeToggle.tsx

#### UI Components
- [ ] src/components/ui/animated-circular-progress.tsx
- [ ] src/components/ui/animated-tooltip.tsx
- [ ] src/components/ui/avatar.tsx
- [ ] src/components/ui/button.tsx
- [ ] src/components/ui/card.tsx

### Context
- [ ] src/context/ChatContext.tsx

### Data
- [ ] src/data/audio.ts
- [ ] src/data/fonts.ts
- [ ] src/data/images.ts
- [ ] src/data/transitions.ts
- [ ] src/data/uploads.ts
- [ ] src/data/video.ts

### Global
- [ ] src/global/events.ts
- [ ] src/global/index.ts

### Hooks
- [ ] src/hooks/use-current-frame.tsx
- [ ] src/hooks/use-scroll-top.ts
- [ ] src/hooks/use-timeline-events.ts

### Interfaces
- [ ] src/interfaces/captions.ts
- [ ] src/interfaces/editor.ts
- [ ] src/interfaces/layout.ts
- [ ] src/interfaces/user.ts

### Lib
- [ ] src/lib/utils.ts

### Pages
- [ ] src/pages/loader-demo.tsx
- [ ] src/pages/websocket-demo.tsx

### Services
- [ ] src/services/agent-service.ts
- [ ] src/services/api-client.ts
- [ ] src/services/auth-client.ts
- [ ] src/services/auth-service.ts
- [ ] src/services/backend-auth-service.ts
- [ ] src/services/index.ts
- [ ] src/services/supabase.ts
- [ ] src/services/task-service.ts
- [ ] src/services/user-service.ts
- [ ] src/services/video-service.ts

### Store
- [ ] src/store/use-auth-store.ts

### Types
- [ ] src/types/global.d.ts

### Utils
- [ ] src/utils/download.ts
- [ ] src/utils/upload.ts

## Documentation
- [ ] backend/docs/ARCHITECTURE.md
- [ ] backend/docs/DEVELOPER_GUIDE.md
- [ ] backend/docs/agent-guide.md
- [ ] backend/docs/websocket_architecture.md
