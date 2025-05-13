import { apiClient } from './api-client';
import { authClient } from './auth-client';
import useAuthStore from '@/store/use-auth-store';

/**
 * Chat action type for the agent
 */
export interface ChatAction {
  type: string;
  label: string;
  scene_id?: string;
  style?: string;
  prompt?: string;
}

/**
 * Agent message type
 */
export interface AgentMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  actions?: ChatAction[];
}

/**
 * Agent message data type for WebSocket communication
 */
export interface AgentMessageData {
  type: 'agent_message' | 'progress_update' | 'video_complete' | 'error';
  content?: string;
  task_id?: string;
  actions?: ChatAction[];
  progress?: number;
  message?: string;
  status?: 'processing' | 'completed' | 'error';
  video_url?: string;
  error?: string;
}

/**
 * Agent service for interacting with the unified agent API
 */
export class AgentService {
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, (data: AgentMessageData) => void> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private authToken: string;
  
  /**
   * Create a new agent service
   * @param _userId User ID (not used but kept for backward compatibility)
   * @param token Authentication token
   */
  constructor(_userId: string, token: string) {
    this.authToken = token;
  }
  
  /**
   * Connect to the agent WebSocket
   * @returns Promise that resolves when connected
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Get WebSocket URL from environment variables or construct it
        const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 
          `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/chat/ws`;
        
        // Append token as query parameter
        const wsUrlWithToken = `${wsUrl}?token=${this.authToken}`;
        
        console.log(`Connecting to WebSocket at ${wsUrl}`);
        
        // Create WebSocket connection with token
        this.socket = new WebSocket(wsUrlWithToken);
        
        // Set up event handlers
        this.socket.onopen = async () => {
          try {
            console.log('WebSocket connection established');
            
            // Reset reconnect attempts
            this.reconnectAttempts = 0;
            
            // Resolve the promise
            resolve();
          } catch (error) {
            console.error('Error during WebSocket connection setup:', error);
            reject(error);
          }
        };
        
        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as AgentMessageData;
            console.log('Received WebSocket message:', data);
            
            // Handle different message types
            let handler;
            
            switch (data.type) {
              case 'agent_message':
                // Call registered handler for agent messages
                handler = this.messageHandlers.get('message');
                if (handler) {
                  handler(data);
                }
                break;
              
              case 'progress_update':
                // Call registered handler for progress updates
                handler = this.messageHandlers.get('progress');
                if (handler && data.task_id) {
                  handler(data);
                }
                break;
              
              case 'video_complete':
                // Call registered handler for video completion
                handler = this.messageHandlers.get('video');
                if (handler && data.task_id) {
                  handler(data);
                }
                break;
              
              case 'error':
                console.error('Agent error:', data.message);
                // Call error handler if registered
                handler = this.messageHandlers.get('error');
                if (handler) {
                  handler(data);
                }
                break;
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
        
        this.socket.onclose = () => {
          console.log('WebSocket connection closed');
          // Attempt to reconnect
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        reject(error);
      }
    });
  }
  
  /**
   * Send a message to the agent via WebSocket
   * @param message Message to send
   * @param task_id Optional task ID or context for continuing a conversation
   * @param context Optional context information
   */
  sendMessageWs(message: string, task_id?: string | Record<string, unknown>, context?: Record<string, unknown>): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    
    // Format the message according to the backend's expected format
    let messageData;
    
    // Handle the case where task_id is actually a context object
    if (typeof task_id === 'object') {
      messageData = {
        message: message,
        context: task_id || {}
      };
    } else {
      messageData = {
        message: message,
        task_id: task_id,
        context: context || {}
      };
    }
    
    console.log('Sending WebSocket message:', messageData);
    
    // Send the message
    this.socket.send(JSON.stringify(messageData));
  }
  
  /**
   * Send a message to the agent via REST API
   * @param message Message to send
   * @param task_id Optional task ID or context for continuing a conversation
   * @param context Optional context information
   * @returns Promise that resolves with the response
   */
  async sendMessage(message: string, task_id?: string | Record<string, unknown>, context?: Record<string, unknown>): Promise<{
    type: string;
    content: string;
    message: string;
    task_id?: string;
    actions?: ChatAction[];
    function_call?: Record<string, unknown>;
    function_response?: Record<string, unknown>;
  }> {
    let requestData;
    
    // Handle the case where task_id is actually a context object
    if (typeof task_id === 'object') {
      requestData = {
        message,
        context: task_id || {}
      };
    } else {
      requestData = {
        message,
        task_id,
        context: context || {}
      };
    }
    
    const response = await apiClient.post<{
      type: string;
      content: string;
      task_id?: string;
      function_call?: Record<string, unknown>;
      function_response?: Record<string, unknown>;
    }>('/api/chat', requestData);
    
    // Add message and actions properties for compatibility with ChatContext
    return {
      ...response,
      message: response.content,
      actions: []
    };
  }
  
  /**
   * Execute an action
   * @param action Action to execute
   * @param task_id Optional task ID or context for continuing a conversation
   * @param context Optional context information
   * @returns Promise that resolves with the response
   */
  async executeAction(
    action: ChatAction, 
    task_id?: string | Record<string, unknown>,
    context?: Record<string, unknown>
  ): Promise<{
    type: string;
    content: string;
    message: string;
    task_id?: string;
    actions?: ChatAction[];
    function_call?: Record<string, unknown>;
    function_response?: Record<string, unknown>;
  }> {
    // Construct a message based on the action type
    let message = '';
    
    switch (action.type) {
      case 'regenerate_image':
        message = `Regenerate the image for scene ${action.scene_id}`;
        break;
      case 'change_voice':
        message = 'Can you select a different voice for this video?';
        break;
      case 'change_music':
        message = `Can you change the background music to a ${action.style} style?`;
        break;
      case 'generate_video':
        message = action.prompt || 'Generate a video';
        break;
      default:
        message = `Execute action: ${action.type}`;
    }
    
    // Create context with action
    let finalContext;
    let finalTaskId;
    
    // Handle the case where task_id is actually a context object
    if (typeof task_id === 'object') {
      finalContext = {
        ...task_id,
        action: action
      };
      finalTaskId = undefined;
    } else {
      finalContext = {
        ...(context || {}),
        action: action
      };
      finalTaskId = task_id;
    }
    
    // Send the message
    const response = await this.sendMessage(message, finalTaskId, finalContext);
    
    return response;
  }
  
  /**
   * Register a handler for a specific message type
   * @param type Message type ('message', 'progress', 'video', 'error')
   * @param handler Handler function
   */
  registerHandler(type: string, handler: (data: AgentMessageData) => void): void {
    this.messageHandlers.set(type, handler);
  }
  
  /**
   * Unregister a handler for a specific message type
   * @param type Message type
   */
  unregisterHandler(type: string): void {
    this.messageHandlers.delete(type);
  }
  
  /**
   * Disconnect from the agent WebSocket
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
  
  /**
   * Check if the WebSocket is connected
   * @returns True if connected, false otherwise
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
  
  /**
   * Get the status of a task
   * @param taskId Task ID
   * @returns Promise that resolves with the task status
   */
  async getTaskStatus(taskId: string): Promise<{
    status: string;
    progress: number;
    message?: string;
    video_url?: string;
  }> {
    return await apiClient.get<{
      status: string;
      progress: number;
      message?: string;
      video_url?: string;
    }>(`/api/chat/tasks/${taskId}/status`);
  }
}

/**
 * Create an agent service for the current user
 * @returns Promise that resolves with the agent service
 */
export async function createAgentService(): Promise<AgentService> {
  const authStore = useAuthStore.getState();
  
  if (!authStore.user) {
    throw new Error('User not authenticated');
  }
  
  // Get token from auth client
  const token = await authClient.getAuthToken();
  
  if (!token) {
    throw new Error('No authentication token available');
  }
  
  return new AgentService(authStore.user.id, token);
}
