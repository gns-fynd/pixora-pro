# Pixora AI

Pixora AI is a video generation platform that uses AI to create videos from text prompts. This project includes both a frontend and backend component.

## Project Structure

```
pixora-ai/
├── src/                  # Frontend source code (React, TypeScript)
│   ├── components/       # Reusable UI components
│   ├── context/          # React context providers
│   ├── hooks/            # Custom React hooks
│   ├── interfaces/       # TypeScript interfaces
│   ├── pages/            # Application pages
│   ├── services/         # API services
│   ├── store/            # State management (Zustand)
│   └── utils/            # Utility functions
│
├── new_backend/          # New backend code (FastAPI)
│   ├── app/              # Application code
│   │   ├── core/         # Core functionality
│   │   ├── routers/      # API endpoints
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utility functions
│   └── tests/            # Unit and integration tests
│
├── archived_code/        # Archived code (for reference)
│   ├── backend/          # Old backend code
│   └── frontend/         # Unused frontend code
│
└── scripts/              # Utility scripts
    ├── analyze_frontend.js  # Script to analyze frontend code
    ├── cleanup_backend.sh   # Script to clean up backend code
    └── cleanup_project.sh   # Script to clean up the entire project
```

## Getting Started

### Frontend

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173) in your browser.

### Backend

1. Create a virtual environment:
   ```
   cd new_backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the development server:
   ```
   uvicorn app.main:app --reload
   ```

5. Open [http://localhost:8000/api/docs](http://localhost:8000/api/docs) to view the API documentation.

## Features

- **AI Video Generation**: Generate videos from text prompts
- **Scene Breakdown**: Break down videos into scenes for editing
- **Video Editing**: Edit generated videos in a timeline editor
- **User Authentication**: Sign up, sign in, and manage user profiles
- **Credits System**: Track and manage user credits for video generation

## Recent Improvements

1. **UI Enhancements**:
   - Improved scene breakdown page with collapsible scenes
   - Enhanced video generation progress tracking
   - Added visual indicators for scene duration

2. **Backend Fixes**:
   - Fixed storage service bucket creation issue
   - Added error handling to user update function
   - Improved credit display and tracking

3. **Project Cleanup**:
   - Created scripts to analyze and archive unused code
   - Restructured backend for better maintainability
   - Improved documentation

## Development Workflow

1. **Analyze Frontend Code**:
   ```
   node analyze_frontend.js
   ```
   This will identify unused components, files, and redundant code.

2. **Clean Up Project**:
   ```
   ./cleanup_project.sh
   ```
   This will archive the old backend code and set up a new backend structure.

## Technologies Used

- **Frontend**:
  - React
  - TypeScript
  - Zustand (State Management)
  - TailwindCSS (Styling)

- **Backend**:
  - FastAPI
  - Supabase (Authentication, Database, Storage)
  - Pydantic (Data Validation)

## License

This project is proprietary and confidential. All rights reserved.
