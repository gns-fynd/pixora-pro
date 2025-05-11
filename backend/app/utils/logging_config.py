"""
Logging configuration for the Pixora AI application.

This module provides a centralized configuration for logging throughout the application.
It sets up formatters, handlers, and log levels for different environments.
"""
import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Define log levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    
    This allows for structured logging that can be easily parsed by log aggregation tools.
    """
    def __init__(self, **kwargs):
        self.json_default = kwargs.pop("json_default", str)
        self.json_encoder = kwargs.pop("json_encoder", json.JSONEncoder)
        self.json_indent = kwargs.pop("json_indent", None)
        self.json_separators = kwargs.pop("json_separators", None)
        self.reserved_attrs = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module",
            "msecs", "message", "msg", "name", "pathname", "process",
            "processName", "relativeCreated", "stack_info", "thread", "threadName"
        }
        super().__init__(**kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        """
        log_record = {}
        
        # Add basic log record attributes
        log_record["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()
        
        # Add source location
        log_record["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
            "module": record.module
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra attributes
        for key, value in record.__dict__.items():
            if key not in self.reserved_attrs and not key.startswith("_"):
                log_record[key] = value
        
        # Convert to JSON
        return json.dumps(log_record, default=self.json_default, 
                         cls=self.json_encoder, indent=self.json_indent,
                         separators=self.json_separators)


class RequestIdFilter(logging.Filter):
    """
    Filter that adds request_id to log records.
    
    This allows for tracking related log entries across a request lifecycle.
    """
    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id or "unknown"
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Always add request_id attribute, even if it's not set elsewhere
        if not hasattr(record, 'request_id'):
            record.request_id = self.request_id
        return True


def setup_logging(
    log_level: str = "info",
    log_dir: str = "logs",
    app_name: str = "pixora",
    enable_json_logs: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: The log level (debug, info, warning, error, critical)
        log_dir: Directory to store log files
        app_name: Application name for log file naming
        enable_json_logs: Whether to output logs in JSON format
        console_output: Whether to output logs to console
    
    Returns:
        Configured root logger
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Get the log level
    level = LOG_LEVELS.get(log_level.lower(), logging.INFO)
    
    # Create formatters
    standard_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
    )
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(filename)s:%(lineno)d - %(message)s'
    )
    json_formatter = JsonFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add request ID filter
    root_logger.addFilter(RequestIdFilter())
    
    # Create handlers
    handlers = []
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(standard_formatter)
        console_handler.setLevel(level)
        handlers.append(console_handler)
    
    # File handlers
    current_date = datetime.now().strftime('%Y%m%d')
    
    # Main log file with rotation
    main_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, f"{app_name}_{current_date}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_file_handler.setFormatter(detailed_formatter if not enable_json_logs else json_formatter)
    main_file_handler.setLevel(level)
    handlers.append(main_file_handler)
    
    # Error log file with rotation
    error_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, f"{app_name}_error_{current_date}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_file_handler.setFormatter(detailed_formatter if not enable_json_logs else json_formatter)
    error_file_handler.setLevel(logging.ERROR)
    handlers.append(error_file_handler)
    
    # Add all handlers to the root logger and ensure they have the request ID filter
    request_id_filter = RequestIdFilter()
    for handler in handlers:
        # Add the filter to each handler
        handler.addFilter(request_id_filter)
        root_logger.addHandler(handler)
    
    # Set specific levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Log the configuration
    root_logger.info(f"Logging configured with level={log_level}, app_name={app_name}, json_logs={enable_json_logs}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    This is a convenience function to get a logger with the correct configuration.
    
    Args:
        name: Logger name, typically __name__ of the calling module
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Create a request ID filter
    request_id_filter = RequestIdFilter()
    
    # Ensure the logger has the request ID filter
    has_request_id_filter = False
    for filter in logger.filters:
        if isinstance(filter, RequestIdFilter):
            has_request_id_filter = True
            break
    
    if not has_request_id_filter:
        logger.addFilter(request_id_filter)
    
    # Also ensure all handlers have the request ID filter
    for handler in logger.handlers:
        # Check if handler already has a RequestIdFilter
        has_filter = False
        for filter in handler.filters:
            if isinstance(filter, RequestIdFilter):
                has_filter = True
                break
        
        if not has_filter:
            handler.addFilter(request_id_filter)
    
    return logger


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.
    
    This updates all RequestIdFilter instances in the logging system.
    
    Args:
        request_id: The request ID to set
    """
    # Update filters on the root logger
    root_logger = logging.getLogger()
    
    # Update the root logger's filters
    for filter in root_logger.filters:
        if isinstance(filter, RequestIdFilter):
            filter.request_id = request_id
    
    # Update filters on all handlers of the root logger
    for handler in root_logger.handlers:
        for filter in handler.filters:
            if isinstance(filter, RequestIdFilter):
                filter.request_id = request_id
    
    # Also update any existing loggers that might have their own filters
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        
        # Update the logger's filters
        for filter in logger.filters:
            if isinstance(filter, RequestIdFilter):
                filter.request_id = request_id
        
        # Update filters on all handlers of this logger
        for handler in logger.handlers:
            for filter in handler.filters:
                if isinstance(filter, RequestIdFilter):
                    filter.request_id = request_id


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log records.
    
    This allows for adding additional context to log records without modifying the logger.
    """
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the log record by adding extra context.
        """
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        return msg, kwargs



def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger with additional context information.
    
    Args:
        name: Logger name
        **context: Additional context to add to log records
    
    Returns:
        Logger adapter with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
