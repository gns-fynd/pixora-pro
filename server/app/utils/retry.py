"""
Retry utilities for Pixora AI Video Creation Platform
"""
import logging
import time
import random
import asyncio
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for function signatures
T = TypeVar('T')
AsyncFunc = Callable[..., Any]
RetryableFunc = TypeVar('RetryableFunc', bound=AsyncFunc)

# Custom exceptions
class RetryableError(Exception):
    """Base class for errors that can be retried."""
    pass

class RateLimitExceeded(RetryableError):
    """Exception raised when a rate limit is exceeded."""
    pass

class ServiceUnavailable(RetryableError):
    """Exception raised when a service is unavailable."""
    pass

def extract_rate_limit_info(response: Any) -> Dict[str, Any]:
    """
    Extract rate limit information from a response.
    
    Args:
        response: Response object with headers
        
    Returns:
        Dict[str, Any]: Dictionary with rate limit information
    """
    rate_limit_info = {}
    
    # Try to extract rate limit headers
    try:
        headers = getattr(response, 'headers', {})
        
        # Common rate limit headers
        rate_limit_headers = [
            'x-ratelimit-limit',
            'x-ratelimit-remaining',
            'x-ratelimit-reset',
            'ratelimit-limit',
            'ratelimit-remaining',
            'ratelimit-reset',
            'retry-after',
            'x-retry-after'
        ]
        
        # Extract headers
        for header in rate_limit_headers:
            if header in headers:
                rate_limit_info[header] = headers[header]
    except Exception as e:
        logger.warning(f"Error extracting rate limit info: {str(e)}")
    
    return rate_limit_info

def handle_rate_limit_response(response: Any, service_name: str = "API") -> Optional[float]:
    """
    Handle a rate limit response and return the retry delay.
    
    Args:
        response: Response object with headers
        service_name: Name of the service for logging purposes
        
    Returns:
        Optional[float]: Retry delay in seconds, or None if not rate limited
    """
    # Check if response status code indicates rate limiting
    status_code = getattr(response, 'status_code', None)
    
    if status_code == 429:
        # Extract rate limit information
        rate_limit_info = extract_rate_limit_info(response)
        
        # Check for retry-after header
        retry_after = rate_limit_info.get('retry-after') or rate_limit_info.get('x-retry-after')
        if retry_after:
            try:
                delay = float(retry_after)
                logger.warning(f"{service_name} rate limit exceeded. Retry after {delay:.2f}s")
                raise RateLimitExceeded(f"{service_name} rate limit exceeded. Please retry after {delay:.2f} seconds")
            except (ValueError, TypeError):
                # If conversion fails, use a default value
                delay = 60.0
                logger.warning(f"{service_name} rate limit exceeded. Using default retry delay of {delay:.2f}s")
                raise RateLimitExceeded(f"{service_name} rate limit exceeded. Using default retry delay of {delay:.2f}s")
        
        # Check for reset time
        reset_time = rate_limit_info.get('x-ratelimit-reset') or rate_limit_info.get('ratelimit-reset')
        if reset_time:
            try:
                # Convert to float
                reset_timestamp = float(reset_time)
                
                # Calculate delay
                current_time = time.time()
                delay = reset_timestamp - current_time
                
                # Ensure delay is positive
                delay = max(1.0, delay)
                logger.warning(f"{service_name} rate limit exceeded. Retry after {delay:.2f}s")
                raise RateLimitExceeded(f"{service_name} rate limit exceeded. Please retry after {delay:.2f} seconds")
            except (ValueError, TypeError):
                # If conversion fails, use a default value
                delay = 60.0
                logger.warning(f"{service_name} rate limit exceeded. Using default retry delay of {delay:.2f}s")
                raise RateLimitExceeded(f"{service_name} rate limit exceeded. Using default retry delay of {delay:.2f}s")
        
        # No specific retry information, use default
        logger.warning(f"{service_name} rate limit exceeded. Using default retry delay of 60.0s")
        raise RateLimitExceeded(f"{service_name} rate limit exceeded. Using default retry delay of 60.0s")
    
    # Check for server errors (5xx)
    if status_code and 500 <= status_code < 600:
        logger.warning(f"{service_name} server error: {status_code}")
        raise ServiceUnavailable(f"{service_name} server error: {status_code}")
    
    # No rate limit or server error detected
    return None

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (RetryableError, asyncio.TimeoutError)
) -> Callable[[RetryableFunc], RetryableFunc]:
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        backoff_factor: Backoff factor for exponential backoff
        jitter: Whether to add jitter to wait times
        retryable_exceptions: Tuple of exceptions to retry
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: RetryableFunc) -> RetryableFunc:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Call the function
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if we've reached the maximum number of attempts
                    if attempt >= max_attempts:
                        logger.warning(f"Maximum retry attempts ({max_attempts}) reached for {func.__name__}")
                        raise
                    
                    # Calculate wait time with exponential backoff
                    wait_time = min_wait * (backoff_factor ** (attempt - 1))
                    
                    # Add jitter if enabled
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())
                    
                    # Cap wait time at max_wait
                    wait_time = min(wait_time, max_wait)
                    
                    # Check for rate limit information
                    if isinstance(e, RateLimitExceeded):
                        # Try to extract retry delay from exception message
                        import re
                        match = re.search(r'retry after (\d+(\.\d+)?) seconds', str(e), re.IGNORECASE)
                        if match:
                            rate_limit_delay = float(match.group(1))
                            wait_time = max(wait_time, rate_limit_delay)
                    
                    logger.warning(f"Retrying {func.__name__} in {wait_time:.2f}s after error: {str(e)}")
                    
                    # Wait before retrying
                    await asyncio.sleep(wait_time)
            
            # If we get here, we've exhausted all retries
            if last_exception:
                raise last_exception
            
            # This should never happen, but just in case
            raise Exception(f"Unexpected error in retry logic for {func.__name__}")
        
        return cast(RetryableFunc, wrapper)
    
    return decorator
