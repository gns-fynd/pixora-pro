# Pixora AI - Backend

This is the backend part of the Pixora AI application, built with FastAPI and Python.

## Development

To start the development server:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the server
python run.py
```

## Deployment

The backend is configured to be deployed to Render. The deployment configuration is in the root `render.yaml` file.

### Environment Variables

The following environment variables are required:

- `SUPABASE_URL`: The URL of your Supabase instance
- `SUPABASE_KEY`: The anonymous key for your Supabase instance
- `SUPABASE_SERVICE_KEY`: The service role key for your Supabase instance
- `SUPABASE_JWT_SECRET`: The JWT secret for your Supabase instance
- `FAL_API_KEY`: Your Fal.ai API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `REPLICATE_API_TOKEN`: Your Replicate API token

See `.env.example` for a complete list of environment variables.

## Project Structure

- `app/ai`: AI-related functionality
- `app/auth`: Authentication
- `app/core`: Core functionality
- `app/models`: Data models
- `app/routers`: API endpoints
- `app/schemas`: Pydantic models
- `app/services`: Business logic
- `app/utils`: Utility functions
- `db`: Database migrations and schema
- `storage`: Storage for uploaded files
