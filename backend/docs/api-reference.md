# Pixora AI API Reference

This document provides a comprehensive reference for the Pixora AI API endpoints.

## Base URL

All API endpoints are prefixed with `/api/v1`.

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

To obtain a token, use the authentication endpoints.

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses include a JSON body with error details:

```json
{
  "detail": "Error message"
}
```

## Endpoints

### Authentication

#### Register a new user

```
POST /auth/register
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

Response:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-04-18T10:00:00Z"
}
```

#### Login with email and password

```
POST /auth/login
```

Request body:
```json
{
  "username": "user@example.com",
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 691200
}
```

#### Exchange Supabase token for JWT

```
POST /auth/exchange-token
```

Request body:
```json
{
  "supabase_token": "supabase_access_token"
}
```

Response:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 691200
}
```

#### Logout

```
POST /auth/logout
```

Response:
```json
{
  "message": "Successfully logged out"
}
```

#### Request password reset

```
POST /auth/reset-password
```

Request body:
```json
{
  "email": "user@example.com"
}
```

Response:
```json
{
  "message": "Password reset email sent"
}
```

#### Change password

```
POST /auth/change-password
```

Request body:
```json
{
  "password": "new_secure_password"
}
```

Response:
```json
{
  "message": "Password changed successfully"
}
```

### Users

#### Get current user

```
GET /users/me
```

Response:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "credits": 10,
  "created_at": "2025-04-18T10:00:00Z"
}
```

#### Update user

```
PUT /users/{user_id}
```

Request body:
```json
{
  "name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg"
}
```

Response:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "credits": 10,
  "created_at": "2025-04-18T10:00:00Z",
  "updated_at": "2025-04-18T11:00:00Z"
}
```

#### Get user credits

```
GET /users/credits
```

Response:
```json
{
  "credits": 10
}
```

#### Add credits

```
POST /users/credits/add
```

Request body:
```json
{
  "amount": 5,
  "description": "Promotional credits"
}
```

Response:
```json
{
  "credits": 15,
  "transaction": {
    "id": "transaction_id",
    "amount": 5,
    "description": "Promotional credits",
    "created_at": "2025-04-18T11:30:00Z"
  }
}
```

### Videos

#### List videos

```
GET /videos
```

Query parameters:
- `limit` (optional): Maximum number of videos to return (default: 10)
- `offset` (optional): Number of videos to skip (default: 0)
- `status` (optional): Filter by status (pending, processing, completed, failed)

Response:
```json
{
  "total": 25,
  "videos": [
    {
      "id": "video_id_1",
      "title": "New York City Showcase",
      "description": "A cinematic journey through NYC",
      "status": "completed",
      "style": "cinematic",
      "aspect_ratio": "16:9",
      "duration": 24,
      "output_url": "https://example.com/videos/video_id_1.mp4",
      "thumbnail_url": "https://example.com/thumbnails/video_id_1.jpg",
      "created_at": "2025-04-18T10:00:00Z"
    },
    {
      "id": "video_id_2",
      "title": "Mountain Adventure",
      "description": "Exploring mountain landscapes",
      "status": "processing",
      "style": "documentary",
      "aspect_ratio": "16:9",
      "duration": 30,
      "created_at": "2025-04-18T11:00:00Z"
    }
  ]
}
```

#### Create a new video

```
POST /videos
```

Request body:
```json
{
  "title": "Beach Sunset",
  "description": "Beautiful beach sunset scenes",
  "style": "cinematic",
  "aspect_ratio": "16:9",
  "duration": 20
}
```

Response:
```json
{
  "id": "video_id_3",
  "title": "Beach Sunset",
  "description": "Beautiful beach sunset scenes",
  "status": "pending",
  "style": "cinematic",
  "aspect_ratio": "16:9",
  "duration": 20,
  "created_at": "2025-04-18T12:00:00Z"
}
```

#### Get video details

```
GET /videos/{video_id}
```

Response:
```json
{
  "id": "video_id_1",
  "title": "New York City Showcase",
  "description": "A cinematic journey through NYC",
  "status": "completed",
  "style": "cinematic",
  "aspect_ratio": "16:9",
  "duration": 24,
  "output_url": "https://example.com/videos/video_id_1.mp4",
  "thumbnail_url": "https://example.com/thumbnails/video_id_1.jpg",
  "created_at": "2025-04-18T10:00:00Z",
  "updated_at": "2025-04-18T10:30:00Z"
}
```

#### Update video

```
PUT /videos/{video_id}
```

Request body:
```json
{
  "title": "New York City Tour",
  "description": "Updated description"
}
```

Response:
```json
{
  "id": "video_id_1",
  "title": "New York City Tour",
  "description": "Updated description",
  "status": "completed",
  "style": "cinematic",
  "aspect_ratio": "16:9",
  "duration": 24,
  "output_url": "https://example.com/videos/video_id_1.mp4",
  "thumbnail_url": "https://example.com/thumbnails/video_id_1.jpg",
  "created_at": "2025-04-18T10:00:00Z",
  "updated_at": "2025-04-18T12:30:00Z"
}
```

#### Delete video

```
DELETE /videos/{video_id}
```

Response:
```json
{
  "message": "Video deleted successfully"
}
```

### Scenes

#### List scenes for a video

```
GET /scenes
```

Query parameters:
- `video_id` (required): Video ID
- `limit` (optional): Maximum number of scenes to return (default: 10)
- `offset` (optional): Number of scenes to skip (default: 0)

Response:
```json
{
  "total": 5,
  "scenes": [
    {
      "id": "scene_id_1",
      "video_id": "video_id_1",
      "order_index": 0,
      "visual_description": "A cinematic aerial shot of New York City skyline at sunset",
      "audio_description": "Soft ambient music with subtle city sounds",
      "script": "Our journey begins with a breathtaking view of New York City",
      "duration": 5,
      "status": "completed",
      "image_url": "https://example.com/images/scene_id_1.jpg",
      "video_url": "https://example.com/videos/scene_id_1.mp4",
      "audio_url": "https://example.com/audio/scene_id_1.mp3",
      "created_at": "2025-04-18T10:05:00Z"
    },
    {
      "id": "scene_id_2",
      "video_id": "video_id_1",
      "order_index": 1,
      "visual_description": "Street-level view of Times Square with vibrant digital billboards",
      "audio_description": "Upbeat music tempo increases, with muffled crowd noises",
      "script": "In the heart of the city, Times Square pulses with energy",
      "duration": 4,
      "status": "completed",
      "image_url": "https://example.com/images/scene_id_2.jpg",
      "video_url": "https://example.com/videos/scene_id_2.mp4",
      "audio_url": "https://example.com/audio/scene_id_2.mp3",
      "created_at": "2025-04-18T10:05:00Z"
    }
  ]
}
```

#### Create a new scene

```
POST /scenes
```

Request body:
```json
{
  "video_id": "video_id_1",
  "order_index": 5,
  "visual_description": "Closing shot of the Brooklyn Bridge at night",
  "audio_description": "Gentle piano music fading out",
  "script": "As we conclude our journey through New York City",
  "duration": 6
}
```

Response:
```json
{
  "id": "scene_id_6",
  "video_id": "video_id_1",
  "order_index": 5,
  "visual_description": "Closing shot of the Brooklyn Bridge at night",
  "audio_description": "Gentle piano music fading out",
  "script": "As we conclude our journey through New York City",
  "duration": 6,
  "status": "pending",
  "created_at": "2025-04-18T13:00:00Z"
}
```

#### Get scene details

```
GET /scenes/{scene_id}
```

Response:
```json
{
  "id": "scene_id_1",
  "video_id": "video_id_1",
  "order_index": 0,
  "visual_description": "A cinematic aerial shot of New York City skyline at sunset",
  "audio_description": "Soft ambient music with subtle city sounds",
  "script": "Our journey begins with a breathtaking view of New York City",
  "duration": 5,
  "status": "completed",
  "image_url": "https://example.com/images/scene_id_1.jpg",
  "video_url": "https://example.com/videos/scene_id_1.mp4",
  "audio_url": "https://example.com/audio/scene_id_1.mp3",
  "created_at": "2025-04-18T10:05:00Z",
  "updated_at": "2025-04-18T10:15:00Z"
}
```

#### Update scene

```
PUT /scenes/{scene_id}
```

Request body:
```json
{
  "visual_description": "Updated visual description",
  "audio_description": "Updated audio description",
  "script": "Updated script",
  "duration": 7
}
```

Response:
```json
{
  "id": "scene_id_1",
  "video_id": "video_id_1",
  "order_index": 0,
  "visual_description": "Updated visual description",
  "audio_description": "Updated audio description",
  "script": "Updated script",
  "duration": 7,
  "status": "completed",
  "image_url": "https://example.com/images/scene_id_1.jpg",
  "video_url": "https://example.com/videos/scene_id_1.mp4",
  "audio_url": "https://example.com/audio/scene_id_1.mp3",
  "created_at": "2025-04-18T10:05:00Z",
  "updated_at": "2025-04-18T13:30:00Z"
}
```

#### Delete scene

```
DELETE /scenes/{scene_id}
```

Response:
```json
{
  "message": "Scene deleted successfully"
}
```

### Generation

#### Analyze prompt

```
POST /generation/analyze
```

Request body:
```json
{
  "prompt": "Create a video showcasing the beauty of Paris",
  "style": "cinematic",
  "duration": 30
}
```

Response:
```json
{
  "scenes": [
    {
      "visual_description": "Aerial view of Paris with the Eiffel Tower in the center",
      "audio_description": "Soft French accordion music",
      "script": "Paris, the city of lights, a timeless beacon of culture and beauty",
      "duration": 6
    },
    {
      "visual_description": "Close-up of a Parisian café with people enjoying coffee",
      "audio_description": "Gentle café ambiance with quiet conversations",
      "script": "The café culture of Paris invites you to slow down and savor life's simple pleasures",
      "duration": 5
    },
    {
      "visual_description": "Tracking shot along the Seine River at sunset",
      "audio_description": "Flowing water sounds with string instruments",
      "script": "The Seine River flows through the heart of the city, reflecting centuries of history",
      "duration": 7
    },
    {
      "visual_description": "Interior of the Louvre Museum focusing on the Mona Lisa",
      "audio_description": "Reverberant space with subtle classical music",
      "script": "Home to countless masterpieces, the Louvre stands as a testament to human creativity",
      "duration": 6
    },
    {
      "visual_description": "Night time-lapse of the Eiffel Tower with twinkling lights",
      "audio_description": "Crescendo of orchestral music",
      "script": "As night falls, the City of Light truly lives up to its name",
      "duration": 6
    }
  ],
  "style": "cinematic",
  "total_duration": 30
}
```

#### Generate video

```
POST /generation/video/{video_id}
```

Response:
```json
{
  "video_id": "video_id_1",
  "job_id": "job_id_1",
  "status": "processing"
}
```

#### Check generation status

```
GET /generation/status/{job_id}
```

Response:
```json
{
  "job_id": "job_id_1",
  "video_id": "video_id_1",
  "status": "processing",
  "progress": 45,
  "started_at": "2025-04-18T14:00:00Z",
  "estimated_completion": "2025-04-18T14:10:00Z"
}
```

## Models

### User

```json
{
  "id": "string (UUID)",
  "email": "string (email)",
  "name": "string",
  "avatar_url": "string (URL)",
  "credits": "integer",
  "created_at": "string (datetime)",
  "updated_at": "string (datetime)"
}
```

### Video

```json
{
  "id": "string (UUID)",
  "user_id": "string (UUID)",
  "title": "string",
  "description": "string",
  "status": "string (pending, processing, completed, failed)",
  "style": "string",
  "aspect_ratio": "string",
  "duration": "integer",
  "output_url": "string (URL)",
  "thumbnail_url": "string (URL)",
  "created_at": "string (datetime)",
  "updated_at": "string (datetime)"
}
```

### Scene

```json
{
  "id": "string (UUID)",
  "video_id": "string (UUID)",
  "order_index": "integer",
  "visual_description": "string",
  "audio_description": "string",
  "script": "string",
  "duration": "integer",
  "status": "string (pending, processing, completed, failed)",
  "image_url": "string (URL)",
  "video_url": "string (URL)",
  "audio_url": "string (URL)",
  "created_at": "string (datetime)",
  "updated_at": "string (datetime)"
}
```

### Generation Job

```json
{
  "id": "string (UUID)",
  "video_id": "string (UUID)",
  "status": "string (pending, processing, completed, failed)",
  "progress": "integer (0-100)",
  "error_message": "string",
  "started_at": "string (datetime)",
  "completed_at": "string (datetime)",
  "estimated_completion": "string (datetime)"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- Authentication endpoints: 10 requests per minute
- User endpoints: 60 requests per minute
- Video endpoints: 30 requests per minute
- Scene endpoints: 60 requests per minute
- Generation endpoints: 10 requests per minute

When rate limited, the API returns a `429 Too Many Requests` status code with a `Retry-After` header indicating the number of seconds to wait before retrying.

## Pagination

List endpoints support pagination using `limit` and `offset` query parameters:

- `limit`: Maximum number of items to return (default: 10, max: 100)
- `offset`: Number of items to skip (default: 0)

The response includes a `total` field with the total number of items available.

## Filtering

Some list endpoints support filtering using query parameters. See the endpoint documentation for available filters.

## Sorting

Some list endpoints support sorting using the `sort` query parameter:

- `sort=created_at`: Sort by creation date (ascending)
- `sort=-created_at`: Sort by creation date (descending)

## Versioning

The API is versioned using the URL path (`/api/v1`). When breaking changes are introduced, a new version will be created (`/api/v2`).

---

For more information or support, contact the API team.
