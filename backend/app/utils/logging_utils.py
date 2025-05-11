"""
Logging utilities for the Pixora AI application.

This module provides utility functions and decorators for logging throughout the application.
"""
import functools
import logging
import time
import uuid
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast
from contextlib import contextmanager

from .logging_config import get_logger, get_context_logger, set_request_id

# Type variable for generic function type
F = TypeVar('F', bound=Callable[..., Any])

# Get module logger
logger = get_logger(__name__)


def generate_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        Unique request ID string
    """
    return str(uuid.uuid4())


@contextmanager
def log_context(context_name: str, **context_data):
    """
    Context manager for logging with additional context.
    
    Args:
        context_name: Name of the context for logging
        **context_data: Additional context data to include in logs
    
    Yields:
        None
    """
    context_logger = get_context_logger(__name__, **context_data)
    context_logger.info(f"Entering {context_name}")
    
    start_time = time.time()
    try:
        yield
    except Exception as e:
        context_logger.exception(f"Error in {context_name}: {str(e)}")
        raise
    finally:
        elapsed = time.time() - start_time
        context_logger.info(f"Exiting {context_name} (took {elapsed:.3f}s)")


@contextmanager
def log_timing(operation_name: str, log_level: int = logging.INFO):
    """
    Context manager for timing operations and logging the duration.
    
    Args:
        operation_name: Name of the operation being timed
        log_level: Logging level to use
    
    Yields:
        None
    """
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.log(log_level, f"{operation_name} completed in {elapsed:.3f}s")


def log_function_call(func: F) -> F:
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_logger = get_logger(func.__module__)
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        # Log function call
        arg_str = ", ".join([str(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        params = f"{arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str}"
        func_logger.debug(f"Calling {func_name}({params})")
        
        # Call function and log result
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            func_logger.debug(f"{func_name} returned {result} (took {elapsed:.3f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            func_logger.exception(f"{func_name} raised {type(e).__name__}: {str(e)} (took {elapsed:.3f}s)")
            raise
    
    return cast(F, wrapper)


def log_method_call(method: F) -> F:
    """
    Decorator to log method calls with arguments and return values.
    
    This is similar to log_function_call but handles 'self' correctly.
    
    Args:
        method: Method to decorate
    
    Returns:
        Decorated method
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        method_logger = get_logger(self.__class__.__module__)
        method_name = f"{self.__class__.__name__}.{method.__name__}"
        
        # Log method call
        arg_str = ", ".join([str(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        params = f"{arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str}"
        method_logger.debug(f"Calling {method_name}({params})")
        
        # Call method and log result
        start_time = time.time()
        try:
            result = method(self, *args, **kwargs)
            elapsed = time.time() - start_time
            method_logger.debug(f"{method_name} returned {result} (took {elapsed:.3f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            method_logger.exception(f"{method_name} raised {type(e).__name__}: {str(e)} (took {elapsed:.3f}s)")
            raise
    
    return cast(F, wrapper)


def log_api_request(func: F) -> F:
    """
    Decorator to log API requests with detailed information.
    
    Args:
        func: API endpoint function to decorate
    
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the request object
        request = None
        for arg in args:
            if hasattr(arg, 'method') and hasattr(arg, 'url'):
                request = arg
                break
        
        # Generate request ID if not already set
        request_id = generate_request_id()
        set_request_id(request_id)
        
        # Get logger with request context
        endpoint_logger = get_context_logger(
            func.__module__,
            request_id=request_id,
            endpoint=func.__name__
        )
        
        # Log request details
        if request:
            endpoint_logger.info(
                f"API Request: {request.method} {request.url.path} "
                f"from {request.client.host if hasattr(request.client, 'host') else 'unknown'}"
            )
            
            # Log query params and headers (excluding sensitive info)
            if hasattr(request, 'query_params') and request.query_params:
                endpoint_logger.debug(f"Query params: {dict(request.query_params)}")
            
            if hasattr(request, 'headers'):
                # Filter out sensitive headers
                safe_headers = {k: v for k, v in request.headers.items() 
                               if k.lower() not in ('authorization', 'cookie', 'x-api-key')}
                endpoint_logger.debug(f"Headers: {safe_headers}")
        else:
            endpoint_logger.info(f"API Request to {func.__name__}")
        
        # Call the endpoint function
        start_time = time.time()
        try:
            response = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # Log response
            status_code = getattr(response, 'status_code', None)
            endpoint_logger.info(
                f"API Response: {status_code} (took {elapsed:.3f}s)"
            )
            
            return response
        except Exception as e:
            elapsed = time.time() - start_time
            endpoint_logger.exception(
                f"API Error: {type(e).__name__}: {str(e)} (took {elapsed:.3f}s)"
            )
            raise
    
    return cast(F, wrapper)


def log_external_api_call(service_name: str, operation: str) -> Callable[[F], F]:
    """
    Decorator factory to log calls to external APIs.
    
    Args:
        service_name: Name of the external service (e.g., 'OpenAI', 'Replicate')
        operation: Name of the operation being performed
    
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get logger with context
            api_logger = get_context_logger(
                func.__module__,
                service=service_name,
                operation=operation
            )
            
            # Filter sensitive parameters
            safe_kwargs = {k: v for k, v in kwargs.items() 
                          if k.lower() not in ('api_key', 'token', 'secret')}
            
            # Log API call
            api_logger.info(f"Calling {service_name} API: {operation}")
            api_logger.debug(f"Parameters: {safe_kwargs}")
            
            # Call the API function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Log success
                api_logger.info(f"{service_name} API call successful (took {elapsed:.3f}s)")
                
                # Log result summary (avoid logging large responses)
                if isinstance(result, dict):
                    keys = list(result.keys())
                    api_logger.debug(f"Response keys: {keys}")
                elif isinstance(result, list):
                    api_logger.debug(f"Response is a list with {len(result)} items")
                else:
                    api_logger.debug(f"Response type: {type(result).__name__}")
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                api_logger.exception(
                    f"{service_name} API error: {type(e).__name__}: {str(e)} (took {elapsed:.3f}s)"
                )
                raise
        
        return cast(F, wrapper)
    
    return decorator


def log_task_progress(task_id: str, progress: float, message: str, stage: Optional[str] = None) -> None:
    """
    Log task progress with structured information.
    
    Args:
        task_id: Task ID
        progress: Progress value (0-100)
        message: Progress message
        stage: Current processing stage
    """
    task_logger = get_context_logger(
        __name__,
        task_id=task_id,
        progress=progress,
        stage=stage
    )
    task_logger.info(f"Task progress: {progress:.1f}% - {message}")


def log_exception_with_context(e: Exception, context: Dict[str, Any]) -> None:
    """
    Log an exception with additional context information.
    
    Args:
        e: Exception to log
        context: Additional context information
    """
    exc_logger = get_context_logger(__name__, **context)
    exc_type = type(e).__name__
    exc_message = str(e)
    exc_traceback = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    
    exc_logger.error(
        f"Exception: {exc_type}: {exc_message}\n"
        f"Context: {context}\n"
        f"Traceback: {exc_traceback}"
    )


def sanitize_log_data(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """
    Sanitize data for logging by removing sensitive information.
    
    Args:
        data: Data to sanitize
        sensitive_keys: List of sensitive key names to redact
    
    Returns:
        Sanitized data
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'auth', 'credential',
            'jwt', 'api_key', 'access_token', 'refresh_token'
        ]
    
    result = {}
    
    for key, value in data.items():
        # Check if this key should be redacted
        should_redact = any(
            sensitive_key in key.lower()
            for sensitive_key in sensitive_keys
        )
        
        if should_redact:
            # Redact the value
            result[key] = '[REDACTED]'
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            result[key] = sanitize_log_data(value, sensitive_keys)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # Recursively sanitize lists of dictionaries
            result[key] = [sanitize_log_data(item, sensitive_keys) 
                          if isinstance(item, dict) else item 
                          for item in value]
        else:
            # Pass through other values
            result[key] = value
    
    return result
