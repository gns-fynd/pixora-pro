# Duration Adjustment Utilities

This module provides utilities for adjusting the duration of audio, video, and music files, as well as managing scene durations in a video.

## Module Structure

The duration adjustment utilities are organized into the following modules:

- `audio_adjuster.py`: Audio duration adjustment functionality
- `video_adjuster.py`: Video duration adjustment functionality
- `scene_manager.py`: Scene duration management
- `common.py`: Shared utilities used by multiple adjusters
- `media_utils.py`: General media file utilities

## Main Classes

### AudioDurationAdjuster

Utility for adjusting the duration of audio files.

```python
from app.ai.utils.duration import AudioDurationAdjuster

# Adjust audio duration
adjusted_audio_path = await AudioDurationAdjuster.adjust_duration(
    audio_path="path/to/audio.mp3",
    target_duration=10.0,
    fade_out=True,
    fade_in=False,
    preserve_pitch=True
)
```

### VideoDurationAdjuster

Utility for adjusting the duration of video files.

```python
from app.ai.utils.duration import VideoDurationAdjuster

# Adjust video duration
adjusted_video_path = await VideoDurationAdjuster.adjust_duration(
    video_path="path/to/video.mp4",
    target_duration=15.0,
    fade_out=True,
    fade_in=False,
    preserve_audio_pitch=True
)
```

### SceneDurationManager

Utility for managing the duration of scenes in a video.

```python
from app.ai.utils.duration import SceneDurationManager

# Calculate scene durations
scenes = [
    {"title": "Scene 1", "weight": 1.0},
    {"title": "Scene 2", "weight": 2.0},
    {"title": "Scene 3", "weight": 1.0}
]
durations = SceneDurationManager.calculate_scene_durations(
    scenes=scenes,
    total_duration=60.0,
    min_scene_duration=3.0
)

# Adjust scene durations
updated_scenes = SceneDurationManager.adjust_scene_durations(
    scenes=scenes,
    target_durations=durations
)

# Adjust scene media durations
updated_scenes_with_media = await SceneDurationManager.adjust_scene_media_durations(
    scenes=scenes_with_media_paths,
    target_durations=durations
)
```

## Utility Functions

### Common Utilities

```python
from app.ai.utils.duration import get_duration, copy_file

# Get the duration of a media file
duration = await get_duration("path/to/media.mp4")

# Copy a file
await copy_file("path/to/input.mp4", "path/to/output.mp4")
```

### Media Utilities

```python
from app.ai.utils.duration import (
    get_media_info,
    get_media_type,
    extract_audio,
    extract_frame,
    combine_audio_video,
    convert_image_to_video
)

# Get media information
media_info = await get_media_info("path/to/media.mp4")

# Get media type
media_type = get_media_type("path/to/media.mp4")

# Extract audio from video
audio_path = await extract_audio(
    video_path="path/to/video.mp4",
    output_path="path/to/audio.mp3"
)

# Extract a frame from video
frame_path = await extract_frame(
    video_path="path/to/video.mp4",
    output_path="path/to/frame.jpg",
    time_position=5.0
)

# Combine audio and video
combined_path = await combine_audio_video(
    video_path="path/to/video.mp4",
    audio_path="path/to/audio.mp3",
    output_path="path/to/combined.mp4",
    audio_volume=1.0
)

# Convert image to video
video_path = await convert_image_to_video(
    image_path="path/to/image.jpg",
    output_path="path/to/video.mp4",
    duration=5.0,
    motion_type="zoom_in"
)
```

## Backward Compatibility

For backward compatibility, all classes and functions are also available through the `duration_adjuster.py` module:

```python
from app.ai.utils.duration_adjuster import (
    AudioDurationAdjuster,
    VideoDurationAdjuster,
    SceneDurationManager,
    get_duration,
    copy_file,
    get_media_info,
    get_media_type,
    extract_audio,
    extract_frame,
    combine_audio_video,
    convert_image_to_video
)
