"""
Utility functions for working with JSON data.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)


def parse_json(json_str: str) -> Dict[str, Any]:
    """
    Parse a JSON string into a Python dictionary.
    
    Args:
        json_str: The JSON string to parse
        
    Returns:
        The parsed JSON as a dictionary
    """
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return {}


def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format a Python dictionary as a JSON string.
    
    Args:
        data: The dictionary to format
        indent: The indentation level
        
    Returns:
        The formatted JSON string
    """
    try:
        return json.dumps(data, indent=indent)
    except Exception as e:
        logger.error(f"Error formatting JSON: {e}")
        return "{}"

# Default logs directory
DEFAULT_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")

# Create logs directory structure
def get_logs_dir(base_dir: Optional[str] = None) -> str:
    """
    Get the logs directory.
    
    Args:
        base_dir: Optional base directory
        
    Returns:
        The logs directory
    """
    logs_dir = base_dir or DEFAULT_LOGS_DIR
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_category_dir(category: str, base_dir: Optional[str] = None) -> str:
    """
    Get a category directory within the logs directory.
    
    Args:
        category: The category (e.g., 'scene_breakdowns', 'character_profiles')
        base_dir: Optional base directory
        
    Returns:
        The category directory
    """
    logs_dir = get_logs_dir(base_dir)
    category_dir = os.path.join(logs_dir, category)
    os.makedirs(category_dir, exist_ok=True)
    return category_dir


def save_json_response(data: Dict[str, Any], category: str, name: str, base_dir: Optional[str] = None) -> str:
    """
    Save a JSON response to a file.
    
    Args:
        data: The data to save
        category: The category (e.g., 'scene_breakdowns', 'character_profiles')
        name: The name of the file (without extension)
        base_dir: Optional base directory
        
    Returns:
        The path to the saved file
    """
    # Get the category directory
    directory = get_category_dir(category, base_dir)
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.json"
    filepath = os.path.join(directory, filename)
    
    # Save the data
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {category} to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving {category} to {filepath}: {e}")
        return ""


def load_json_file(filepath: str) -> Dict[str, Any]:
    """
    Load a JSON file.
    
    Args:
        filepath: The path to the file
        
    Returns:
        The loaded data
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        logger.error(f"Error loading JSON file {filepath}: {e}")
        return {}


def load_latest_json(category: str, name_prefix: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the latest JSON file in a category with a given name prefix.
    
    Args:
        category: The category (e.g., 'scene_breakdowns', 'character_profiles')
        name_prefix: The prefix of the file name
        base_dir: Optional base directory
        
    Returns:
        The loaded data
    """
    # Get the category directory
    directory = get_category_dir(category, base_dir)
    
    # Get all files in the directory
    try:
        files = [f for f in os.listdir(directory) if f.startswith(name_prefix) and f.endswith(".json")]
        
        if not files:
            logger.warning(f"No files found in {directory} with prefix {name_prefix}")
            return {}
        
        # Sort files by modification time (newest first)
        files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
        
        # Load the latest file
        latest_file = os.path.join(directory, files[0])
        return load_json_file(latest_file)
    
    except Exception as e:
        logger.error(f"Error loading latest JSON file: {e}")
        return {}
