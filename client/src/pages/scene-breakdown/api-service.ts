/**
 * API Service for Scene Breakdown
 * 
 * IMPORTANT: This file contains workarounds for backend endpoints that are not yet implemented.
 * When the backend returns a "not yet implemented" message, this service provides mock data
 * to allow frontend development to continue without blocking on backend implementation.
 * 
 * These workarounds should be removed once the backend functionality is fully implemented.
 */

import { apiClient } from '@/services/api-client';
import { pollTaskStatus } from '@/utils/polling';
import { 
  ScriptResponse, 
  SceneResponse, 
  SceneBreakdownResponse, 
  UnifiedGenerationResponse,
  Scene,
  Prompt
} from './types';

/**
 * Fetches scene breakdown data from the API
 */
// Define the ChatMessage type to match what's expected by the addMessage function
type ChatMessage = {
  role: 'assistant' | 'user' | 'system';
  content: string;
  timestamp: Date;
};

export const fetchSceneBreakdown = async (
  promptData: Prompt,
  controller: AbortController,
  onProgress: (message: ChatMessage) => void
) => {
  // Make a single API call for both script generation and scene breakdown
  // Ensure the request format matches the UnifiedGenerationRequest schema
  const combinedRequestData = {
    prompt: promptData.prompt,
    preferences: {
      style: promptData.style,
      duration: promptData.duration
    },
    client_context: {
      current_page: 'scene_breakdown',
      operation: 'generate_scene_breakdown_with_script'
    }
  };
  
  // Wrap the request data in a 'request' field as required by the new backend
  const combinedRequest = {
    request: combinedRequestData
  };
  
  console.log('Sending combined script and scene breakdown request with data:', combinedRequest);
  
  const combinedResponse = await apiClient.post<UnifiedGenerationResponse>(
    '/ai/generate', 
    combinedRequest, 
    { signal: controller.signal }
  );
  
  console.log('Received combined response:', combinedResponse);
  
  // Extract the task ID from the combined response
  // The task_id is at the top level of the response, not inside data
  const combinedTaskId = combinedResponse.task_id;
  
  // Check if the response indicates the operation is not implemented
  if (combinedResponse.message && combinedResponse.message.includes('not yet implemented')) {
    console.warn('Operation not implemented in backend:', combinedResponse.message);
    
    // Create a mock response with dummy data for development/testing
    // This allows the frontend to continue working while the backend is being implemented
    const mockScriptData: ScriptResponse = {
      title: "Mock Script for " + promptData.prompt.substring(0, 30),
      description: promptData.prompt,
      style: promptData.style || "cinematic",
      narration: "This is a mock narration for development purposes while the backend implementation is completed."
    };
    
    // Return mock data
    return {
      scenes: [
        {
          id: "mock-scene-1",
          visual: "Mock scene 1 visual description based on: " + promptData.prompt.substring(0, 50),
          audio: "Mock scene 1 narration",
          duration: Math.floor(promptData.duration / 3),
          narration: "Mock scene 1 narration"
        },
        {
          id: "mock-scene-2",
          visual: "Mock scene 2 visual description based on: " + promptData.prompt.substring(0, 50),
          audio: "Mock scene 2 narration",
          duration: Math.floor(promptData.duration / 3),
          narration: "Mock scene 2 narration"
        },
        {
          id: "mock-scene-3",
          visual: "Mock scene 3 visual description based on: " + promptData.prompt.substring(0, 50),
          audio: "Mock scene 3 narration",
          duration: Math.floor(promptData.duration / 3),
          narration: "Mock scene 3 narration"
        }
      ],
      script: mockScriptData
    };
  }
  
  if (!combinedTaskId) {
    console.error('Response structure:', combinedResponse);
    throw new Error('No task ID returned from the server');
  }
  
  // Extract the script data from the combined response if available
  const scriptData = combinedResponse.data?.script as ScriptResponse || null;
  
  // Poll for the task result
  console.log(`Polling for task result with ID: ${combinedTaskId}`);
  
  // Add a message about waiting for the scene breakdown
  onProgress({
    role: 'assistant',
    content: 'Breaking down your script into scenes. This will take a moment...',
    timestamp: new Date()
  });
  
  // Use the generic polling utility with the SceneBreakdownResponse type
  const breakdownData = await pollTaskStatus<SceneBreakdownResponse>(
    combinedTaskId, 
    controller, 
    (message) => {
      // Customize the message for scene breakdown
      const customMessage = {
        ...message,
        content: message.content.replace('Still working on the task', 'Still working on breaking down your script')
      } as ChatMessage;
      // Pass the message to the onProgress callback
      onProgress(customMessage);
    }
  );
  
  if (!breakdownData) {
    throw new Error('Could not get scene breakdown result after multiple attempts');
  }
  
  // Log the full response for debugging
  console.log('Full scene breakdown response:', breakdownData);
  
  // Extract scenes from the response
  // The backend should now consistently return scenes in data.scenes
  const breakdownDataObj = breakdownData as Record<string, unknown>;
  const scenesArray = breakdownDataObj.scenes as SceneResponse[] | undefined;
  
  // If we couldn't find scenes, log the structure and throw an error
  if (!scenesArray || !Array.isArray(scenesArray)) {
    console.error('Could not find scenes in API response:', breakdownData);
    // Log the structure to help with debugging
    console.error('Response structure:', {
      hasData: !!breakdownData,
      dataKeys: breakdownData ? Object.keys(breakdownData as object) : [],
      scenesType: breakdownDataObj.scenes ? typeof breakdownDataObj.scenes : 'undefined',
      isArray: breakdownDataObj.scenes ? Array.isArray(breakdownDataObj.scenes) : false
    });
    throw new Error('Invalid scene data structure in API response');
  }
  
  const formattedScenes = scenesArray.map((scene: SceneResponse) => ({
    id: scene.id,
    visual: scene.description,
    audio: scene.narration,
    duration: scene.duration,
    narration: scene.narration
  }));
  
  return {
    scenes: formattedScenes,
    script: scriptData
  };
};

/**
 * Regenerates a specific scene
 */
export const regenerateScene = async (
  sceneId: string,
  prompt: Prompt,
  scriptTitle: string
) => {
  // Call the new unified API to regenerate the scene
  // Ensure the request format matches the UnifiedGenerationRequest schema
  const regenerateRequestData = {
    prompt: prompt.prompt,
    preferences: {
      scene_id: sceneId,
      script_id: scriptTitle // Using title as a script identifier
    },
    client_context: {
      current_page: 'scene_breakdown',
      operation: 'regenerate_scene'
    }
  };
  
  // Wrap the request data in a 'request' field as required by the new backend
  const regenerateRequest = {
    request: regenerateRequestData
  };
  
  const response = await apiClient.post<UnifiedGenerationResponse>(
    '/ai/generate', 
    regenerateRequest
  );
  
  // Check if the response indicates the operation is not implemented
  if (response.message && response.message.includes('not yet implemented')) {
    console.warn('Operation not implemented in backend:', response.message);
    
    // Create a mock response with dummy data for development/testing
    return {
      id: sceneId,
      visual: "Regenerated scene visual description based on: " + prompt.prompt.substring(0, 50),
      audio: "Regenerated scene narration",
      duration: Math.floor(prompt.duration / 3),
      narration: "Regenerated scene narration"
    };
  }
  
  // Extract the scene data from the response
  const sceneData = response.data?.scene as SceneResponse;
  
  if (!sceneData) {
    throw new Error('No scene data returned from the server');
  }
  
  return {
    id: sceneData.id,
    visual: sceneData.description,
    audio: sceneData.narration,
    duration: sceneData.duration,
    narration: sceneData.narration
  };
};

/**
 * Generates a video from scenes
 */
export const generateVideo = async (
  prompt: Prompt,
  scenes: Scene[]
) => {
  // Call the new unified API to start video generation
  // Ensure the request format matches the UnifiedGenerationRequest schema
  const videoRequestData = {
    prompt: prompt.prompt,
    preferences: {
      aspect_ratio: prompt.aspectRatio,
      duration: prompt.duration,
      style: prompt.style,
      // Structure the scenes data in the format expected by the backend
      scenes: scenes.map(scene => ({
        id: scene.id,
        description: scene.visual,
        narration: scene.audio,
        duration: scene.duration
      }))
    },
    client_context: {
      current_page: 'scene_breakdown',
      operation: 'generate_video'
    }
  };
  
  // Wrap the request data in a 'request' field as required by the new backend
  const videoRequest = {
    request: videoRequestData
  };
  
  const response = await apiClient.post<UnifiedGenerationResponse>(
    '/ai/generate', 
    videoRequest
  );
  
  // Check if the response indicates the operation is not implemented
  if (response.message && response.message.includes('not yet implemented')) {
    console.warn('Operation not implemented in backend:', response.message);
    
    // Create a mock task ID for development/testing
    const mockTaskId = `mock-task-${Date.now()}`;
    console.log('Using mock task ID:', mockTaskId);
    
    // Return the mock task ID
    return mockTaskId;
  }
  
  // Extract the task ID from the response
  const taskId = response.task_id;
  
  if (!taskId) {
    throw new Error('No task ID returned from the server');
  }
  
  return taskId;
};
