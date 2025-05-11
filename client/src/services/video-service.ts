import { apiClient } from './api-client';

// Types for video-related data
export interface Video {
  id: string;
  user_id: string;
  title: string;
  prompt: string;
  aspect_ratio: string;
  duration: number;
  style: string;
  status: 'draft' | 'processing' | 'completed' | 'failed';
  thumbnail_url?: string;
  output_url?: string;
  credits_used: number;
  created_at: string;
  updated_at: string;
}

export interface VideoCreate {
  title?: string;
  prompt: string;
  aspect_ratio?: string;
  duration?: number;
  style?: string;
}

export interface VideoUpdate {
  title?: string;
  prompt?: string;
  aspect_ratio?: string;
  duration?: number;
  style?: string;
  status?: string;
}

export interface Scene {
  id: string;
  video_id: string;
  order_index: number;
  visual_description: string;
  audio_description?: string;
  duration: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  image_url?: string;
  video_url?: string;
  audio_url?: string;
  created_at: string;
  updated_at: string;
}

export interface SceneUpdate {
  visual_description?: string;
  audio_description?: string;
  duration?: number;
}

export interface PromptAnalysisRequest {
  video_id: string;
  prompt: string;
  style?: string;
  duration?: number;
}

export interface GenerationRequest {
  video_id: string;
}

export interface GenerationResponse {
  id: string;
  video_id: string;
  status: string;
  progress: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Service for video-related operations
 */
export const videoService = {
  /**
   * Create a new video
   */
  createVideo: async (videoData: VideoCreate): Promise<Video> => {
    return apiClient.post<Video>('/videos', videoData);
  },

  /**
   * Get all videos for the current user
   */
  getVideos: async (): Promise<Video[]> => {
    return apiClient.get<Video[]>('/videos');
  },

  /**
   * Get a specific video by ID
   */
  getVideo: async (videoId: string): Promise<Video> => {
    return apiClient.get<Video>(`/videos/${videoId}`);
  },

  /**
   * Update a video
   */
  updateVideo: async (videoId: string, videoData: VideoUpdate): Promise<Video> => {
    return apiClient.put<Video>(`/videos/${videoId}`, videoData);
  },

  /**
   * Delete a video
   */
  deleteVideo: async (videoId: string): Promise<void> => {
    return apiClient.delete(`/videos/${videoId}`);
  },

  /**
   * Upload a thumbnail for a video
   */
  uploadThumbnail: async (videoId: string, file: File): Promise<Video> => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post<Video>(`/videos/${videoId}/thumbnail`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  /**
   * Analyze a prompt and generate scene breakdown
   */
  analyzePrompt: async (data: PromptAnalysisRequest): Promise<Scene[]> => {
    return apiClient.post<Scene[]>('/videos/scenes/analyze', data);
  },

  /**
   * Update a scene
   */
  updateScene: async (sceneId: string, sceneData: SceneUpdate): Promise<Scene> => {
    return apiClient.put<Scene>(`/videos/scenes/${sceneId}`, sceneData);
  },

  /**
   * Start video generation
   */
  startGeneration: async (data: GenerationRequest): Promise<GenerationResponse> => {
    return apiClient.post<GenerationResponse>('/videos/generation/start', data);
  },

  /**
   * Get generation status
   */
  getGenerationStatus: async (jobId: string): Promise<GenerationResponse> => {
    return apiClient.get<GenerationResponse>(`/videos/generation/${jobId}/status`);
  },

  /**
   * Cancel generation
   */
  cancelGeneration: async (jobId: string): Promise<GenerationResponse> => {
    return apiClient.post<GenerationResponse>(`/videos/generation/${jobId}/cancel`);
  },

  /**
   * Get all scenes for a video
   */
  getScenes: async (videoId: string): Promise<Scene[]> => {
    return apiClient.get<Scene[]>(`/videos/scenes?video_id=${videoId}`);
  },
};
