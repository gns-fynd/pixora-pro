# Storage Service

This module provides a unified interface for storage operations in the Pixora AI platform.

## Overview

The storage service is designed with a clean architecture that separates the interface from the implementation. This allows for easy swapping of storage backends if needed in the future.

## Components

### StorageService (Abstract Base Class)

Defines the interface that all storage implementations must adhere to. Key operations include:

- `upload_file`: Upload a file to storage
- `download_file`: Download a file from storage
- `get_file_url`: Get the URL for a file
- `delete_file`: Delete a file from storage
- `list_files`: List files in a bucket
- `create_bucket`: Create a new bucket
- `delete_bucket`: Delete a bucket

### SupabaseStorageService

Concrete implementation of the `StorageService` interface using Supabase Storage. This implementation:

- Handles authentication with Supabase
- Manages bucket creation and permissions
- Provides file upload/download functionality
- Generates public and signed URLs

### StorageManager

High-level manager that provides simplified methods for common operations:

- `upload_video`: Upload a video file
- `upload_image`: Upload an image file
- `upload_audio`: Upload an audio file
- `upload_file_from_url`: Download a file from a URL and upload it to storage
- `delete_file`: Delete a file
- `get_file_url`: Get the URL for a file
- `list_files`: List files in a bucket

## Usage Examples

### Uploading a Video

```python
from fastapi import Depends, UploadFile
from app.services.storage import StorageManager

async def upload_video_endpoint(
    file: UploadFile,
    user_id: str,
    storage_manager: StorageManager = Depends()
):
    # Upload the video
    video_url = await storage_manager.upload_video(
        file_data=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
        user_id=user_id
    )
    
    return {"url": video_url}
```

### Uploading an Image from a URL

```python
from app.services.storage import StorageManager

async def upload_image_from_url(
    url: str,
    storage_manager: StorageManager = Depends()
):
    # Upload the image
    image_url = await storage_manager.upload_file_from_url(
        url=url,
        bucket=storage_manager.images_bucket
    )
    
    return {"url": image_url}
```

### Listing Files

```python
from app.services.storage import StorageManager

async def list_user_videos(
    user_id: str,
    storage_manager: StorageManager = Depends()
):
    # List videos for the user
    videos = await storage_manager.list_files(
        bucket=storage_manager.videos_bucket,
        prefix=f"{user_id}/"
    )
    
    return {"videos": videos}
```

## Configuration

The storage service is configured through environment variables:

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/public key
- `SUPABASE_SERVICE_KEY`: Supabase service role key for admin operations
- `STORAGE_VIDEOS_BUCKET`: Bucket name for videos (default: "videos")
- `STORAGE_IMAGES_BUCKET`: Bucket name for images (default: "images")
- `STORAGE_AUDIO_BUCKET`: Bucket name for audio files (default: "audio")
- `STORAGE_PUBLIC_URL`: Public URL for storage assets (optional)
