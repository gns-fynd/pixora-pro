// Define types for API responses
export interface ScriptResponse {
  title: string;
  description: string;
  style: string;
  narration: string;
  tone?: string;
  target_audience?: string;
  key_points?: string[];
}

export interface SceneResponse {
  id: string;
  title: string;
  description: string;
  duration: number;
  narration: string;
}

export interface SceneBreakdownResponse {
  scenes?: SceneResponse[];
  total_duration?: number;
  data?: {
    scenes?: SceneResponse[];
    total_duration?: number;
    data?: {
      scenes?: SceneResponse[];
      total_duration?: number;
    };
    [key: string]: unknown; // Allow for any other properties in the data object
  };
  [key: string]: unknown; // Allow for any other properties at the top level
}

// Define a type for the UnifiedGenerationResponse
export interface UnifiedGenerationResponse {
  response_type: string;
  message: string;
  data: Record<string, unknown>;
  task_id?: string;
  ui_action?: Record<string, unknown>;
}

// Define a Character interface
export interface Character {
  name: string;
  description: string;
  image_url?: string;
}

// Define the Scene interface for the component state
export interface Scene {
  id: string;
  title?: string;
  visual: string;
  audio: string;
  duration: number;
  narration?: string;
  image_url?: string;
  character?: Character;
}

// Define the Script interface for the component state
export interface Script {
  id: string;
  title: string;
  content: string;
}

// Define the Prompt interface for the component state
export interface Prompt {
  prompt: string;
  aspectRatio: string;
  duration: number;
  style: string;
}
