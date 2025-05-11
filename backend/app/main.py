"""
Main FastAPI application entry point
"""
import os
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.utils.logging_config import setup_logging, get_logger
from app.utils.logging_utils import generate_request_id, set_request_id, log_exception_with_context
from app.core.config import get_settings

# Load environment variables
load_dotenv()

# Set up logging
settings = get_settings()
log_level = os.getenv("LOG_LEVEL", "info")
log_dir = os.getenv("LOG_DIR", "logs")
enable_json_logs = os.getenv("ENABLE_JSON_LOGS", "false").lower() == "true"

logger = setup_logging(
    log_level=log_level,
    log_dir=log_dir,
    app_name="pixora",
    enable_json_logs=enable_json_logs
)

# Get module logger
logger = get_logger(__name__)

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = generate_request_id()
        set_request_id(request_id)
        
        # Add request ID to response headers
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if hasattr(request.client, 'host') else 'unknown'}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            logger.info(
                f"Response: {response.status_code} "
                f"(took {process_time:.3f}s)"
            )
            
            return response
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.exception(
                f"Request failed: {str(e)} "
                f"(took {process_time:.3f}s)"
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "request_id": request_id}
            )

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application
    Handles startup and shutdown events
    """
    # Startup logic
    logger.info("Starting up Pixora AI API...")
    
    # Start WebSocket connection manager cleanup
    from app.ai.websocket_manager import ConnectionManager
    connection_manager = ConnectionManager()
    await connection_manager.schedule_periodic_cleanup(
        interval_seconds=300,  # 5 minutes
        idle_threshold_seconds=1800  # 30 minutes
    )
    logger.info("Started WebSocket connection cleanup scheduler")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down Pixora AI API...")


# Create FastAPI app
app = FastAPI(
    title="Pixora AI API",
    description="API for Pixora AI video generation platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions
    """
    # Generate a unique error ID
    error_id = generate_request_id()
    
    # Log the exception with context
    log_exception_with_context(
        exc,
        {
            "error_id": error_id,
            "url": str(request.url),
            "method": request.method,
            "client_host": request.client.host if hasattr(request.client, "host") else "unknown",
            "headers": dict(request.headers)
        }
    )
    
    # Return a user-friendly error response with the error ID
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "error_id": error_id
        },
    )

# Import routers
from app.routers import users, videos, auth, ai_generation, websocket_router, agent_router

# Include routers
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(videos.router, prefix="/api/v1", tags=["videos"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(ai_generation.router, prefix="/api/v1", tags=["ai-generation"])
app.include_router(websocket_router.router, prefix="/api/v1", tags=["websocket"])
app.include_router(agent_router.router, tags=["agent"])  # No prefix as it's already defined in the router

@app.get("/api/v1/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
