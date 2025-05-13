"""
Main FastAPI application entry point for Pixora AI Video Creation Platform
"""
import os
import pathlib
import logging
import json
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
from app.utils.logging_utils import configure_logging

# Get log level from environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
enable_json_logs = os.getenv("ENABLE_JSON_LOGS", "false").lower() == "true"
log_file = os.getenv("LOG_FILE")

# Configure logging
configure_logging(level=log_level, enable_json_logs=enable_json_logs, log_file=log_file)

# Get logger for this module
logger = logging.getLogger(__name__)

# Import API routers
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router

# Import services
from app.services.auth import auth_service

# Create FastAPI app
app = FastAPI(
    title="Pixora AI API",
    description="API for Pixora AI video generation service",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage directory for static files
storage_path = pathlib.Path(__file__).parent / "storage"
if storage_path.exists():
    app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")
else:
    print(f"Warning: Storage directory {storage_path} does not exist. Creating it...")
    storage_path.mkdir(parents=True, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {request.method} {request.url.path} - {response.status_code}")
    return response

# Include API routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(users_router)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Pixora AI API is running"}

# Auth token endpoint (for compatibility with client)
@app.post("/auth/token")
async def auth_token_compat(
    request: Request
):
    """
    Handle /auth/token requests for compatibility with client.
    This forwards the request to the actual endpoint at /api/auth/token.
    """
    logger.info("Handling /auth/token request")
    
    # Get the request body
    body = await request.body()
    
    # Get the authorization header
    auth_header = request.headers.get("Authorization")
    
    # Try to get token from Authorization header
    token = None
    if auth_header:
        token = auth_header.replace("Bearer ", "")
    
    # If no token in header, try to get it from request body
    if not token:
        try:
            # Parse the request body as JSON
            body_json = json.loads(body)
            token = body_json.get("token")
        except:
            # If body is not valid JSON, ignore it
            pass
    
    # If still no token, return error
    if not token:
        logger.warning("No token provided in request to /auth/token")
        return JSONResponse(
            status_code=400,
            content={"error": "No token provided. Please provide a token in the Authorization header or request body."}
        )
    
    # Call the auth_service directly
    try:
        # Verify the Supabase token
        user_data = await auth_service.verify_supabase_token(token)
        
        if not user_data:
            logger.warning("Invalid token in request to /auth/token")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token"}
            )
        
        # Create a session token for WebSocket authentication
        session_token = auth_service.create_session_token(user_data)
        
        if not session_token:
            logger.error("Failed to create session token in /auth/token")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create session token"}
            )
        
        # Get the expiry timestamp
        expires_at = auth_service.get_expiry_timestamp(session_token)
        
        return JSONResponse(
            content={
                "access_token": session_token,
                "expires_at": expires_at,
                "expires_in": (expires_at - int(time.time())) if expires_at else 3600
            }
        )
    except Exception as e:
        logger.error(f"Error in /auth/token: {str(e)}")
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid token"}
        )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Pixora AI API",
        "docs": "/docs",
        "health": "/api/health",
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    logger.info("Starting Pixora AI API")
    
    # Check required environment variables
    required_env_vars = [
        "OPENAI_API_KEY",
        "REPLICATE_API_TOKEN",
        "FAL_CLIENT_API_KEY",
        "JWT_SECRET"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in the .env file or environment")
    else:
        logger.info("All required environment variables are set")
    
    # Initialize Supabase if configured
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        from app.services.supabase import supabase_service
        supabase_service.initialize()
        logger.info("Supabase service initialized")
    else:
        logger.warning("Supabase not configured. Some features may not work properly.")
    
    logger.info("Pixora AI API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Pixora AI API")
    
    # Clean up any resources here
    
    logger.info("Pixora AI API shut down successfully")

# Run the application
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port} (reload={reload})")
    uvicorn.run("main:app", host=host, port=port, reload=reload)
