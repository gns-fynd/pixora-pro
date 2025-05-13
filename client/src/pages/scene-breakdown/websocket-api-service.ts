/**
 * WebSocket API Service for Scene Breakdown
 * 
 * This file implements the scene breakdown API using WebSocket communication
 * instead of REST API calls. It uses the WebSocketChat component to handle
 * the WebSocket connection and message handling.
 */

import { 
  ScriptResponse, 
  SceneResponse, 
  Scene,
  Prompt
} from './types';

// Define the ChatMessage type to match what's expected by the addMessage function
type ChatMessage = {
  role: 'assistant' | 'user' | 'system';
  content: string;
  timestamp: Date;
};

// Define the WebSocket message types
interface WebSocketMessage {
  type: string;
  data?: Record<string, unknown>;
  message?: string;
}

// Define the WebSocket message handler type
type WebSocketMessageHandler = (message: WebSocketMessage) => void;

/**
 * Creates a WebSocket connection for scene breakdown
 */
export const createWebSocketConnection = (
  token: string,
  taskId: string,
  onMessage: WebSocketMessageHandler,
  onError: (error: string) => void,
  onConnected: () => void
): WebSocket => {
  // Get WebSocket URL from environment variables or construct it
  const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/chat/ws`;
  
  // Append token and task ID as query parameters
  // Make sure to encode the token to avoid URL parsing issues
  const wsUrlWithParams = `${wsUrl}?token=${encodeURIComponent(token)}${taskId ? `&task_id=${encodeURIComponent(taskId)}` : ''}`;
  
  console.log('Connecting to WebSocket with URL:', wsUrlWithParams.split('?')[0]);
  
  const ws = new WebSocket(wsUrlWithParams);

  ws.onopen = () => {
    console.log('WebSocket connected');
    // Send token for authentication
    ws.send(token);
    onConnected();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);
      onMessage(data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError('Error parsing WebSocket message');
    }
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    onError('WebSocket disconnected');
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError('WebSocket connection error');
  };

  return ws;
};

/**
 * Fetches scene breakdown data using WebSocket
 */
export const fetchSceneBreakdownWs = (
  ws: WebSocket,
  taskId: string,
  promptData: Prompt,
  onProgress: (message: ChatMessage) => void,
  onSceneBreakdown: (breakdown: { scenes: Scene[], script: ScriptResponse }) => void,
  onError: (error: string) => void
): void => {
  // Set up message handler
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WebSocketMessage;
      console.log('WebSocket message:', data);
      
      if (data.type === 'scene_breakdown' && data.data) {
        // Process scene breakdown data
        const breakdownData = data.data;
        
        // Extract scenes from the response
        const scenesArray = breakdownData.scenes as SceneResponse[] | undefined;
        
        // If we couldn't find scenes, log the structure and report an error
        if (!scenesArray || !Array.isArray(scenesArray)) {
          console.error('Could not find scenes in WebSocket response:', breakdownData);
          onError('Invalid scene data structure in WebSocket response');
          return;
        }
        
        // Format the scenes
        const formattedScenes = scenesArray.map((scene: SceneResponse) => ({
          id: scene.id,
          visual: scene.description,
          audio: scene.narration,
          duration: scene.duration,
          narration: scene.narration
        }));
        
        // Extract script data
        const scriptData = breakdownData.script as ScriptResponse || null;
        
        // Call the callback with the formatted data
        onSceneBreakdown({
          scenes: formattedScenes,
          script: scriptData
        });
      } else if (data.type === 'progress_update' && data.data) {
        // Update progress
        onProgress({
          role: 'assistant',
          content: typeof data.data.message === 'string' ? data.data.message : 'Processing your request...',
          timestamp: new Date()
        });
      } else if (data.type === 'error') {
        // Handle error
        onError(data.message || 'An error occurred');
      } else if (data.type === 'message' && data.data) {
        // Handle regular message
        onProgress({
          role: (data.data.role as 'assistant' | 'user' | 'system') || 'assistant',
          content: typeof data.data.content === 'string' ? data.data.content : '',
          timestamp: new Date()
        });
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError('Error parsing WebSocket message');
    }
  };

  // Send the command to generate scene breakdown
  try {
    ws.send(JSON.stringify({
      message: 'generate_scene_breakdown',
      task_id: taskId,
      context: {
        prompt: promptData.prompt,
        style: promptData.style || 'cinematic',
        duration: promptData.duration || 60
      }
    }));
    
    // Add a message about waiting for the scene breakdown
    onProgress({
      role: 'assistant',
      content: 'Breaking down your script into scenes. This will take a moment...',
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Error sending WebSocket message:', error);
    onError('Error sending WebSocket message');
  }
};

/**
 * Regenerates a specific scene using WebSocket
 */
export const regenerateSceneWs = (
  ws: WebSocket,
  taskId: string,
  sceneId: string,
  prompt: Prompt,
  scriptTitle: string,
  onProgress: (message: ChatMessage) => void,
  onSceneRegenerated: (scene: Scene) => void,
  onError: (error: string) => void
): void => {
  // Set up message handler
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WebSocketMessage;
      console.log('WebSocket message:', data);
      
      if (data.type === 'scene_regenerated' && data.data) {
        // Process regenerated scene data
        const sceneData = data.data.scene as SceneResponse;
        
        if (!sceneData) {
          onError('No scene data returned from the server');
          return;
        }
        
        // Format the scene
        const formattedScene = {
          id: sceneData.id,
          visual: sceneData.description,
          audio: sceneData.narration,
          duration: sceneData.duration,
          narration: sceneData.narration
        };
        
        // Call the callback with the formatted data
        onSceneRegenerated(formattedScene);
      } else if (data.type === 'progress_update' && data.data) {
        // Update progress
        onProgress({
          role: 'assistant',
          content: typeof data.data.message === 'string' ? data.data.message : 'Regenerating scene...',
          timestamp: new Date()
        });
      } else if (data.type === 'error') {
        // Handle error
        onError(data.message || 'An error occurred');
      } else if (data.type === 'message' && data.data) {
        // Handle regular message
        onProgress({
          role: (data.data.role as 'assistant' | 'user' | 'system') || 'assistant',
          content: typeof data.data.content === 'string' ? data.data.content : '',
          timestamp: new Date()
        });
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError('Error parsing WebSocket message');
    }
  };

  // Send the command to regenerate the scene
  try {
    ws.send(JSON.stringify({
      message: 'regenerate_scene',
      task_id: taskId,
      context: {
        scene_id: sceneId,
        prompt: prompt.prompt,
        script_id: scriptTitle
      }
    }));
    
    // Add a message about regenerating the scene
    onProgress({
      role: 'assistant',
      content: `Regenerating scene ${sceneId}. This will take a moment...`,
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Error sending WebSocket message:', error);
    onError('Error sending WebSocket message');
  }
};

/**
 * Generates a video from scenes using WebSocket
 */
export const generateVideoWs = (
  ws: WebSocket,
  taskId: string,
  prompt: Prompt,
  scenes: Scene[],
  onProgress: (message: ChatMessage) => void,
  onVideoGenerated: (videoUrl: string) => void,
  onError: (error: string) => void
): void => {
  // Set up message handler
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WebSocketMessage;
      console.log('WebSocket message:', data);
      
      if (data.type === 'completion' && data.data) {
        // Process video completion data
        const videoData = data.data;
        
        if (!videoData.video_url) {
          onError('No video URL returned from the server');
          return;
        }
        
        // Call the callback with the video URL
        onVideoGenerated(videoData.video_url as string);
      } else if (data.type === 'progress_update' && data.data) {
        // Update progress
        onProgress({
          role: 'assistant',
          content: typeof data.data.message === 'string' ? data.data.message : 'Generating video...',
          timestamp: new Date()
        });
      } else if (data.type === 'error') {
        // Handle error
        onError(data.message || 'An error occurred');
      } else if (data.type === 'message' && data.data) {
        // Handle regular message
        onProgress({
          role: (data.data.role as 'assistant' | 'user' | 'system') || 'assistant',
          content: typeof data.data.content === 'string' ? data.data.content : '',
          timestamp: new Date()
        });
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError('Error parsing WebSocket message');
    }
  };

  // Send the command to generate the video
  try {
    ws.send(JSON.stringify({
      message: 'generate_video',
      task_id: taskId,
      context: {
        prompt: prompt.prompt,
        aspect_ratio: prompt.aspectRatio,
        style: prompt.style,
        scenes: scenes.map(scene => ({
          id: scene.id,
          description: scene.visual,
          narration: scene.audio,
          duration: scene.duration
        }))
      }
    }));
    
    // Add a message about generating the video
    onProgress({
      role: 'assistant',
      content: 'Generating your video. This will take a moment...',
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Error sending WebSocket message:', error);
    onError('Error sending WebSocket message');
  }
};
