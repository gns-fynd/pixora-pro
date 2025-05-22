# Pixora AI

Pixora AI is a video generation platform that uses AI to create videos from text prompts. This project includes both a frontend and backend component.

## Project Structure

```
pixora-ai/
├── client/              # Frontend code (React, TypeScript)
│   ├── src/             # Frontend source code
│   │   ├── components/  # Reusable UI components
│   │   ├── context/     # React context providers
│   │   ├── hooks/       # Custom React hooks
│   │   ├── interfaces/  # TypeScript interfaces
│   │   ├── pages/       # Application pages
│   │   ├── services/    # API services
│   │   ├── store/       # State management (Zustand)
│   │   └── utils/       # Utility functions
│   ├── public/          # Static assets
│   └── dist/            # Build output (generated)
│
├── server/              # Backend code (FastAPI)
│   ├── app/             # Application code
│   │   ├── agents/      # AI agents
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Data models
│   │   ├── schemas/     # Pydantic models
│   │   ├── services/    # Business logic
│   │   ├── tools/       # AI tools
│   │   └── utils/       # Utility functions
│   ├── sql/             # SQL scripts for database setup
│   └── storage/         # Storage for uploaded files
│
└── docs/                # Documentation
```

## Development

### Frontend

```bash
cd client
npm install
npm run dev
```

### Backend

```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python main.py
```

### Database Setup

To set up the database tables for conversation storage:

1. Log in to your Supabase dashboard
2. Navigate to the SQL Editor
3. Copy the contents of `server/sql/create_conversation_tables.sql`
4. Paste into the SQL Editor and run the script

### Full Stack Development

To run both frontend and backend together:

```bash
npm run dev
```

## Deployment

This project is set up for deployment to:
- Frontend: Vercel
- Backend: Render

### Vercel Deployment (Frontend)

1. Connect your GitHub repository to Vercel
2. Select the repository and configure:
   - Root Directory: `/` (the repository root)
   - Build Command: Vercel will use the one in vercel.json
   - Output Directory: Vercel will use the one in vercel.json
3. Add environment variables as needed
4. Deploy

### Render Deployment (Backend)

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Select the repository and configure:
   - Root Directory: `/` (the repository root)
   - Build Command: Render will use the one in render.yaml
   - Start Command: Render will use the one in render.yaml
4. Add environment variables as specified in render.yaml
5. Deploy

## Features

- **AI Video Generation**: Generate videos from text prompts
- **Scene Breakdown**: Break down videos into scenes for editing
- **Video Editing**: Edit generated videos in a timeline editor
- **User Authentication**: Sign up, sign in, and manage user profiles
- **Credits System**: Track and manage user credits for video generation
- **Conversation Storage**: Persistent storage of conversations with the AI assistant for context retention

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
  - OpenAI (AI Services)
  - Persistent Conversation Storage (Supabase PostgreSQL)

## License

This project is proprietary and confidential. All rights reserved.
