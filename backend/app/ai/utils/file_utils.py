"""
File utilities for the Pixora AI application.

This module provides utilities for file operations.
"""
import os
import uuid
import shutil
from typing import Optional, BinaryIO, Union, List
import logging

# Set up logging
logger = logging.getLogger(__name__)


def save_file(content: Union[bytes, BinaryIO], file_path: str) -> bool:
    """
    Save binary content to a file.

    Args:
        content: The binary content to save
        file_path: The path to save the file to

    Returns:
        True if the file was saved successfully, False otherwise
    """
    try:
        # Ensure the directory exists
        ensure_directory_exists(os.path.dirname(file_path))
        
        # Save the file
        if isinstance(content, bytes):
            with open(file_path, "wb") as f:
                f.write(content)
        else:
            # Assume it's a file-like object
            with open(file_path, "wb") as f:
                shutil.copyfileobj(content, f)
        
        return True
    except Exception as e:
        logger.error(f"Error saving file to {file_path}: {str(e)}")
        return False


def read_file(file_path: str) -> Optional[bytes]:
    """
    Read binary content from a file.

    Args:
        file_path: The path to read the file from

    Returns:
        The binary content of the file, or None if the file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None
        
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file from {file_path}: {str(e)}")
        return None


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Create a directory if it doesn't exist.

    Args:
        directory_path: The path to the directory

    Returns:
        True if the directory exists or was created successfully, False otherwise
    """
    try:
        if not directory_path:
            return True
        
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
        
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {str(e)}")
        return False


def get_file_extension(file_path: str) -> str:
    """
    Extract the file extension from a file path.

    Args:
        file_path: The path to the file

    Returns:
        The file extension (including the dot)
    """
    _, extension = os.path.splitext(file_path)
    return extension


def generate_unique_filename(prefix: str = "", extension: str = "") -> str:
    """
    Generate a unique filename.

    Args:
        prefix: Optional prefix for the filename
        extension: Optional extension for the filename (including the dot)

    Returns:
        A unique filename
    """
    unique_id = str(uuid.uuid4())
    
    if prefix:
        unique_id = f"{prefix}_{unique_id}"
    
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    
    return f"{unique_id}{extension}"


def get_file_size(file_path: str) -> Optional[int]:
    """
    Get the size of a file in bytes.

    Args:
        file_path: The path to the file

    Returns:
        The size of the file in bytes, or None if the file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None
        
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {str(e)}")
        return None


def delete_file(file_path: str) -> bool:
    """
    Delete a file.

    Args:
        file_path: The path to the file

    Returns:
        True if the file was deleted successfully, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return False
        
        os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False


def list_files(directory_path: str, pattern: Optional[str] = None) -> List[str]:
    """
    List files in a directory.

    Args:
        directory_path: The path to the directory
        pattern: Optional glob pattern to filter files

    Returns:
        List of file paths
    """
    try:
        if not os.path.exists(directory_path):
            logger.warning(f"Directory not found: {directory_path}")
            return []
        
        if pattern:
            import glob
            return glob.glob(os.path.join(directory_path, pattern))
        else:
            return [os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                   if os.path.isfile(os.path.join(directory_path, f))]
    except Exception as e:
        logger.error(f"Error listing files in {directory_path}: {str(e)}")
        return []
