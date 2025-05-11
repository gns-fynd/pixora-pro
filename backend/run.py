"""
Run script for the Pixora AI backend.

This script starts the FastAPI server for the Pixora AI backend.
It supports both local development and production deployment on Render.
"""
import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This won't override existing environment variables
load_dotenv()

# Detect if running on Render
is_render = os.environ.get('RENDER', '') != ''

# Get server settings from environment variables
host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "8000"))

# In production (Render), always disable reload
if is_render:
    reload = False
    print("Running in production mode on Render")
else:
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")

if __name__ == "__main__":
    print(f"Starting Pixora AI backend on {host}:{port}")
    print(f"Reload mode: {'enabled' if reload else 'disabled'}")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
