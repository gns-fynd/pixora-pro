# Pixora AI Developer Guide

This guide provides essential information for developers who want to contribute to the Pixora AI video generation platform.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [API Documentation](#api-documentation)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

## Getting Started

Pixora AI is a full-stack application with a React/TypeScript frontend and a FastAPI Python backend. The platform uses Supabase for authentication, database, and storage, and integrates with fal.ai for AI-powered video generation.

### Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.9+
- Docker and Docker Compose (for local development)
- Supabase account
- fal.ai API key

## Development Environment Setup

### Frontend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/pixora-ai.git
   cd pixora-ai
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Create a `.env` file in the root directory:
   ```
   VITE_SUPABASE_URL=your-supabase-url
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

4. Start the development server:
   ```bash
   pnpm dev
   ```

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory:
   ```
   # API settings
   API_V1_STR=/api/v1
   PROJECT_NAME=Pixora AI

   # Security
   SECRET_KEY=your-secret-key
   ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8 days

   # Supabase
   SUPABASE_URL=your-supabase-url
   SUPABASE_KEY=your-supabase-service-role-key

   # Fal.ai
   FAL_AI_KEY=your-fal-ai-key

   # OpenAI
   OPENAI_API_KEY=your-openai-api-key

   # Redis
   REDIS_URL=redis://localhost:6379/0

   # Celery
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0

   # Server
   HOST=0.0.0.0
   PORT=8000
   RELOAD=True
   ```

5. Start Redis using Docker:
   ```bash
   docker-compose up -d redis
   ```

6. Start the FastAPI development server:
   ```bash
   python run_dev.py
   ```

7. In a separate terminal, start the Celery worker:
   ```bash
   python run_worker.py
   ```

## Project Structure

### Frontend Structure

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

### Backend Structure

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

## Development Workflow

### Git Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with descriptive messages:
   ```bash
   git commit -m "feat: add new feature"
   ```

3. Push your branch to the remote repository:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request on GitHub.

### Coding Standards

- Follow the guidelines in `CODING_STANDARDS.md`
- Use TypeScript for all frontend code
- Use type hints for all Python code
- Write unit tests for new features
- Document your code with docstrings and comments

## API Documentation

When the backend server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Frontend Testing

```bash
# Run unit tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run e2e tests
pnpm test:e2e
```

### Backend Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=app tests/
```

## Database Migrations

The project uses SQL migrations for database schema changes:

1. Create a new migration:
   ```bash
   cd backend/db
   python migrations/create_migration.py "description_of_changes"
   ```

2. Apply migrations:
   ```bash
   cd backend/db
   python migrations/apply_migration.py
   ```

## Deployment

### Docker Deployment

The project includes Docker configuration for deployment:

```bash
# Build and start containers
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop containers
docker-compose -f docker-compose.prod.yml down
```

### Manual Deployment

For manual deployment, follow these steps:

1. Build the frontend:
   ```bash
   pnpm build
   ```

2. Deploy the frontend to a static hosting service (Vercel, Netlify, etc.)

3. Deploy the backend to a server with Python and Redis installed

4. Set up environment variables on the server

5. Start the backend services:
   ```bash
   # Start the API server
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Start the Celery worker
   celery -A app.tasks.worker worker --loglevel=info
   ```

## Troubleshooting

### Common Issues

1. **Authentication Issues**:
   - Check Supabase configuration
   - Verify JWT secret key
   - Check token expiration

2. **Database Connection Issues**:
   - Verify Supabase URL and key
   - Check database schema

3. **AI Service Issues**:
   - Verify fal.ai API key
   - Check API rate limits
   - Verify model availability

### Debugging

- Frontend: Use browser developer tools and React DevTools
- Backend: Use logging and FastAPI debug mode
- Database: Use Supabase dashboard for query debugging

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](backend/docs/api-reference.md)
- [Supabase Documentation](https://supabase.io/docs)
- [fal.ai Documentation](https://docs.fal.ai)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [React Documentation](https://reactjs.org/docs)

---

For any questions or issues, please contact the project maintainers or open an issue on GitHub.
