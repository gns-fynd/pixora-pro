"""
User schemas for request and response models
"""
from typing import Optional, Annotated
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr = Field(description="User's email address")
    name: Optional[str] = Field(default=None, description="User's full name")
    avatar_url: Optional[str] = Field(default=None, description="URL to user's avatar image")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: Annotated[str, Field(min_length=8, description="User's password (min 8 characters)")]


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    name: Optional[str] = Field(default=None, description="User's full name")
    avatar_url: Optional[str] = Field(default=None, description="URL to user's avatar image")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user response"""
    id: str = Field(description="User's unique identifier")
    role: str = Field(default="user", description="User's role (user or admin)")
    credits: int = Field(default=0, ge=0, description="User's available credits")

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """Schema for user in database"""
    hashed_password: Optional[str] = Field(default=None, description="Hashed password (not returned to clients)")
