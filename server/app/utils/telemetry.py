"""
Telemetry utilities for Pixora AI Video Creation Platform
"""
import os
import logging
import functools
import time
import json
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for function signatures
T = TypeVar('T')
AsyncFunc = Callable[..., Any]
TracedFunc = TypeVar('TracedFunc', bound=AsyncFunc)

# Check if OpenTelemetry is available
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.span import Span
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    logger.warning("OpenTelemetry not installed. Tracing will be disabled.")
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    Status = None
    StatusCode = None
    Span = None

# Initialize tracer
tracer = None
if OPENTELEMETRY_AVAILABLE:
    tracer = trace.get_tracer(__name__)

def traced(span_name_or_func: Optional[str] = None) -> Callable[[TracedFunc], TracedFunc]:
    """
    Decorator for tracing async functions.
    
    This decorator can be used in two ways:
    1. With a span name: @traced("span_name")
    2. Without arguments: @traced
    
    Args:
        span_name_or_func: Optional name for the span or the function to decorate.
        
    Returns:
        Callable: Decorator function or decorated function
    """
    # Check if this is being used as @traced (without parentheses)
    if callable(span_name_or_func):
        # This is being used as @traced
        func = span_name_or_func
        span_name = None
        
        @functools.wraps(func)
        async def direct_wrapper(*args: Any, **kwargs: Any) -> Any:
            # If OpenTelemetry is not available, just call the function
            if not OPENTELEMETRY_AVAILABLE or not tracer:
                return await func(*args, **kwargs)
            
            # Get the span name
            name = func.__name__
            
            # Start a new span
            with tracer.start_as_current_span(name) as span:
                # Add attributes to the span
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.args_length", len(args))
                span.set_attribute("function.kwargs_length", len(kwargs))
                
                # Add the start time
                start_time = time.time()
                
                try:
                    # Call the function
                    result = await func(*args, **kwargs)
                    
                    # Add the end time and duration
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Add attributes to the span
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", True)
                    
                    # Set the span status
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                except Exception as e:
                    # Add the end time and duration
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Add attributes to the span
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.type", e.__class__.__name__)
                    span.set_attribute("error.message", str(e))
                    
                    # Add the stack trace
                    stack_trace = traceback.format_exc()
                    span.set_attribute("error.stack_trace", stack_trace)
                    
                    # Set the span status
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Re-raise the exception
                    raise
        
        return cast(TracedFunc, direct_wrapper)
    
    # This is being used as @traced("span_name")
    span_name = span_name_or_func
    
    def decorator(func: TracedFunc) -> TracedFunc:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # If OpenTelemetry is not available, just call the function
            if not OPENTELEMETRY_AVAILABLE or not tracer:
                return await func(*args, **kwargs)
            
            # Get the span name
            name = span_name or func.__name__
            
            # Start a new span
            with tracer.start_as_current_span(name) as span:
                # Add attributes to the span
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.args_length", len(args))
                span.set_attribute("function.kwargs_length", len(kwargs))
                
                # Add the start time
                start_time = time.time()
                
                try:
                    # Call the function
                    result = await func(*args, **kwargs)
                    
                    # Add the end time and duration
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Add attributes to the span
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", True)
                    
                    # Set the span status
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                except Exception as e:
                    # Add the end time and duration
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Add attributes to the span
                    span.set_attribute("function.duration", duration)
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.type", e.__class__.__name__)
                    span.set_attribute("error.message", str(e))
                    
                    # Add the stack trace
                    stack_trace = traceback.format_exc()
                    span.set_attribute("error.stack_trace", stack_trace)
                    
                    # Set the span status
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Re-raise the exception
                    raise
        
        return cast(TracedFunc, wrapper)
    
    return decorator

def log_event(event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an event with structured data.
    
    Args:
        event_type: Type of the event
        message: Message describing the event
        data: Optional data to include with the event
    """
    # Create the event data
    event_data = {
        "event_type": event_type,
        "message": message,
        "timestamp": time.time(),
        "data": data or {}
    }
    
    # Log the event
    logger.info(f"Event: {event_type} - {message}", extra={"event": event_data})
    
    # If OpenTelemetry is available, add the event to the current span
    if OPENTELEMETRY_AVAILABLE and trace:
        current_span = trace.get_current_span()
        if current_span:
            # Add the event to the span
            current_span.add_event(
                name=event_type,
                attributes={
                    "message": message,
                    "data": json.dumps(data) if data else "{}"
                }
            )
