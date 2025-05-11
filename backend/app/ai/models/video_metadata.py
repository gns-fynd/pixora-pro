"""
Advanced request and response models for the video agent API.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class CharacterProfile(BaseModel):
    """Model for character profile with image prompt."""
    name: str = Field(..., description="Name of the character")
    image_prompt: str = Field(..., description="Prompt for generating character images with 4 angles")
    image_urls: Dict[str, str] = Field(default_factory=dict, description="URLs of generated character images")


class MusicDefinition(BaseModel):
    """Model for music definition with scene grouping."""
    prompt: str = Field(..., description="Prompt for generating music")
    scene_indexes: List[int] = Field(..., description="Indexes of scenes this music applies to")
    music_url: Optional[str] = Field(None, description="URL of the generated music")


class SceneClip(BaseModel):
    """Model for scene clip with title, script, and video prompt."""
    index: int = Field(..., description="Index of the scene")
    title: str = Field(..., description="Title of the scene")
    script: str = Field(..., description="Narration script for the scene")
    video_prompt: str = Field(..., description="Prompt for generating the scene video")
    duration: Optional[float] = Field(None, description="Duration of the scene in seconds")
    transition: Optional[str] = Field(None, description="Transition to the next scene")


class ClipData(BaseModel):
    """Model for clip data containing scene information."""
    scene: SceneClip = Field(..., description="Scene information for the clip")
    audio_url: Optional[str] = Field(None, description="URL of the generated audio")
    image_url: Optional[str] = Field(None, description="URL of the generated image")
    video_url: Optional[str] = Field(None, description="URL of the generated video")


class VideoMetadata(BaseModel):
    """Advanced model for video metadata with detailed structure."""
    user_prompt: str = Field(..., description="Original user prompt")
    rewritten_prompt: str = Field(..., description="Rewritten prompt for better clarity")
    voice_character: Optional[str] = Field(None, description="URL to a voice sample for TTS")
    character_consistency: bool = Field(False, description="Whether character consistency is needed")
    music: List[MusicDefinition] = Field(default_factory=list, description="Music definitions with scene groupings")
    character_profiles: List[CharacterProfile] = Field(default_factory=list, description="Character profiles with image prompts")
    clips: List[ClipData] = Field(..., description="List of clips with scene information")
    
    # Duration settings
    expected_duration: int = Field(30, description="Expected total duration of the video in seconds")
    
    # Additional fields for tracking
    task_id: Optional[str] = Field(None, description="ID of the associated task")
    user_id: Optional[str] = Field(None, description="ID of the user who created this video")
    final_video_url: Optional[str] = Field(None, description="URL of the final composed video")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_prompt": "Make a video on the story of Surya Putra Karna from Mahabharata",
                "rewritten_prompt": "Create a compelling video narrative of Karna's life, the son of Surya from the Mahabharata, emphasizing his virtues, struggles, and legacy.",
                "voice_character": "https://storage.googleapis.com/falserverless/model_tests/zonos/demo_voice_zonos.wav",
                "character_consistency": True,
                "music": [
                    {
                        "prompt": "Gentle, mysterious flute music evolving into inspirational and powerful orchestral tones",
                        "scene_indexes": [1, 2, 3]
                    },
                    {
                        "prompt": "Melancholic and heroic strings",
                        "scene_indexes": [4]
                    }
                ],
                "character_profiles": [
                    {
                        "name": "Karna",
                        "image_prompt": "Generate a character profile with 4 angles: front, side, back, and 3/4 view. A regal, muscular warrior with golden armor and earrings, medium-dark skin, long black hair tied back, intense brown eyes, dressed in royal dhoti and chestplate, holding a bow, standing under the sun."
                    },
                    {
                        "name": "Kunti",
                        "image_prompt": "Generate a character profile with 4 angles: front, side, back, and 3/4 view. A graceful, middle-aged Indian woman in a royal saree, expressive sad eyes, traditional gold jewelry, elegant posture, standing near palace interiors with natural light."
                    }
                ],
                "clips": [
                    {
                        "scene": {
                            "index": 1,
                            "title": "The Birth of Karna",
                            "script": "Born to an unwed mother, Princess Kunti, and blessed by the Sun God Surya, Karna was set adrift in a basket on a river to avoid disgrace. Discovered and raised by a charioteer, his origins remained a mystery, shadowing his future.",
                            "video_prompt": "Soft morning light over a tranquil river. A basket gently floats along the water, a baby inside, wrapped in royal cloth. Cut to a humble charioteer family discovering the baby."
                        }
                    },
                    {
                        "scene": {
                            "index": 2,
                            "title": "Karna's Quest for Knowledge",
                            "script": "Undeterred by societal boundaries, Karna fervently pursued martial arts under Parashurama, the great sage who taught warriors of Brahmin lineage, deceiving the sage about his origins.",
                            "video_prompt": "Visuals of a young Karna practicing archery with immense focus and skill in a lush forest setting. Transition to Karna respectfully approaching Parashurama, who is teaching other Brahmin students."
                        }
                    }
                ]
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the video metadata to a dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoMetadata":
        """Create video metadata from a dictionary."""
        return cls.model_validate(data)
