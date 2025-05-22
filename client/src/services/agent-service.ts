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
  type: 'agent_message' | 'progress_update' | 'video_complete' | 'error' | 'task_status' | 'system';
  content?: string;
  task_id?: string;
  actions?: ChatAction[];
  progress?: number;
  message?: string;
  status?: 'processing' | 'completed' | 'error' | 'pending';
  video_url?: string;
  error?: string;
}

/**
 * Agent service for interacting with the unified agent API
 * Implemented as a singleton to ensure only one WebSocket connection is maintained
 */
export class AgentService {
  // Singleton instance
  private static instance: AgentService | null = null;
  
  // Shared WebSocket connection
  private static socket: WebSocket | null = null;
  
  // Track the current connection attempt
  private static connectionPromise: Promise<void> | null = null;
  
  // Centralized handler management
  private static handlers: Map<string, Set<(data: AgentMessageData) => void>> = new Map();
  
  // Connection tracking
  private static reconnectAttempts = 0;
  private static maxReconnectAttempts = 5;
  private static connectionId: number = 0;
  
  // Auth token
  private authToken: string;
  private userId: string;
  
  /**
   * Private constructor to enforce singleton pattern
   * @param userId User ID
   */
  private constructor(userId: string) {
    this.userId = userId;
    this.authToken = ''; // No longer needed with cookie-based auth
  }
  
  /**
   * Get the singleton instance of AgentService
   * @param userId User ID
   * @returns Promise that resolves with the AgentService instance
   */
  static async getInstance(userId: string): Promise<AgentService> {
    if (!AgentService.instance) {
      console.log('Creating new AgentService instance');
      AgentService.instance = new AgentService(userId);
      
      // Connect only once
      await AgentService.instance.connect();
    }
    
    return AgentService.instance;
  }
  
  /**
   * Connect to the agent WebSocket
   * @returns Promise that resolves when connected
   */
  connect(): Promise<void> {
    // If we already have a connection promise, return it
    if (AgentService.connectionPromise) {
      console.log('Connection attempt already in progress, reusing existing promise');
      return AgentService.connectionPromise;
    }
    
    // If socket is already connected, return resolved promise
    if (AgentService.socket && AgentService.socket.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected, reusing existing connection');
      return Promise.resolve();
    }
    
    // Create a new connection promise
    AgentService.connectionPromise = new Promise((resolve, reject) => {
      try {
        // Close existing socket if any
        if (AgentService.socket) {
          console.log('Closing existing socket before creating a new one');
          AgentService.socket.close();
          AgentService.socket = null;
        }
        
        // Get WebSocket URL from environment variables or construct it
        const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 
          `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/chat/ws`;
        
        // Assign a unique ID to this connection
        AgentService.connectionId = Date.now();
        
        console.log(`Connecting to WebSocket at ${wsUrl} (connection #${AgentService.connectionId})`);
        
        // Create WebSocket connection with withCredentials to ensure cookies are sent
        console.log(`Creating WebSocket connection to ${wsUrl} with cookies`);
        AgentService.socket = new WebSocket(wsUrl);
        
        // Set up event handlers
        AgentService.socket.onopen = async () => {
          try {
            console.log(`WebSocket connection #${AgentService.connectionId} established`);
            
            // Reset reconnect attempts
            AgentService.reconnectAttempts = 0;
            
            // Resolve the promise
            resolve();
          } catch (error) {
            console.error(`Error during WebSocket connection #${AgentService.connectionId} setup:`, error);
            reject(error);
          } finally {
            // Clear the connection promise
            AgentService.connectionPromise = null;
          }
        };
        
        AgentService.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as AgentMessageData;
            console.log(`Received WebSocket message on connection #${AgentService.connectionId}:`, data);
            
            // Call all registered handlers for this message type
            const handlersForType = AgentService.handlers.get(data.type);
            if (handlersForType) {
              handlersForType.forEach(handler => handler(data));
            }
          } catch (error) {
            console.error(`Error parsing WebSocket message on connection #${AgentService.connectionId}:`, error);
          }
        };
        
        AgentService.socket.onerror = (error) => {
          console.error(`WebSocket error on connection #${AgentService.connectionId}:`, error);
          reject(error);
          AgentService.connectionPromise = null;
        };
        
        AgentService.socket.onclose = () => {
          console.log(`WebSocket connection #${AgentService.connectionId} closed`);
          AgentService.socket = null;
          AgentService.connectionPromise = null;
          
          // Attempt to reconnect, but only if this was an unexpected close
          if (AgentService.reconnectAttempts < AgentService.maxReconnectAttempts) {
            AgentService.reconnectAttempts++;
            const delay = 1000 * AgentService.reconnectAttempts;
            console.log(`Will attempt to reconnect in ${delay}ms (attempt ${AgentService.reconnectAttempts}/${AgentService.maxReconnectAttempts})`);
            
            // Create a new instance to reconnect
            setTimeout(() => {
              if (AgentService.instance) {
                AgentService.instance.connect().catch(err => {
                  console.error('Reconnection attempt failed:', err);
                });
              }
            }, delay);
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        AgentService.connectionPromise = null;
        reject(error);
      }
    });
    
    return AgentService.connectionPromise;
  }
  
  // Track the last message sent to prevent duplicates
  private static lastMessageSent: {
    message: string;
    timestamp: number;
    messageData: string;
  } | null = null;
  
  /**
   * Send a message to the agent via WebSocket
   * @param message Message to send
   * @param task_id Optional task ID or context for continuing a conversation
   * @param context Optional context information
   */
  sendMessageWs(message: string, task_id?: string | Record<string, unknown>, context?: Record<string, unknown>): void {
    if (!AgentService.socket || AgentService.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    
    // Format the message according to the backend's expected format
    let messageData;
    
    // Handle the case where task_id is actually a context object
    if (typeof task_id === 'object') {
      // Ensure context is properly formatted
      const formattedContext = task_id || {};
      
      // Log the context for debugging
      if (formattedContext.prompt && typeof formattedContext.prompt === 'string') {
        console.log('Sending prompt in context:', formattedContext.prompt.substring(0, 50) + '...');
      }
      
      messageData = {
        message: message,
        context: formattedContext
      };
    } else {
      // Ensure context is properly formatted
      const formattedContext = context || {};
      
      // Log the context for debugging
      if (formattedContext.prompt && typeof formattedContext.prompt === 'string') {
        console.log('Sending prompt in context:', formattedContext.prompt.substring(0, 50) + '...');
      }
      
      messageData = {
        message: message,
        task_id: task_id,
        context: formattedContext
      };
    }
    
    // Convert to string for comparison
    const messageDataString = JSON.stringify(messageData);
    
    // Check if this is a duplicate message (same content within the last 500ms)
    const now = Date.now();
    if (AgentService.lastMessageSent && 
        AgentService.lastMessageSent.message === message && 
        AgentService.lastMessageSent.messageData === messageDataString &&
        now - AgentService.lastMessageSent.timestamp < 500) {
      console.log('Preventing duplicate WebSocket message:', message);
      return;
    }
    
    // Update last message sent
    AgentService.lastMessageSent = { 
      message, 
      timestamp: now,
      messageData: messageDataString
    };
    
    console.log('Sending WebSocket message:', {
      message: messageData.message,
      task_id: messageData.task_id,
      context: messageData.context ? 'Context object present' : 'No context'
    });
    
    // Send the message
    AgentService.socket.send(messageDataString);
  }
  
  // REST API sendMessage method has been removed in favor of WebSocket communication
  
  /**
   * Execute an action via WebSocket
   * @param action Action to execute
   * @param task_id Optional task ID or context for continuing a conversation
   * @param context Optional context information
   */
  executeAction(
    action: ChatAction, 
    task_id?: string | Record<string, unknown>,
    context?: Record<string, unknown>
  ): void {
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
    
    // Handle the case where task_id is actually a context object
    if (typeof task_id === 'object') {
      finalContext = {
        ...task_id,
        action: action
      };
    } else {
      finalContext = {
        ...(context || {}),
        action: action
      };
    }
    
    // Send the message via WebSocket
    this.sendMessageWs(message, finalContext);
  }
  
  /**
   * Register a handler for a specific message type
   * @param type Message type ('message', 'progress', 'video', 'error')
   * @param handler Handler function
   */
  registerHandler(type: string, handler: (data: AgentMessageData) => void): void {
    if (!AgentService.handlers.has(type)) {
      AgentService.handlers.set(type, new Set());
    }
    
    AgentService.handlers.get(type)!.add(handler);
  }
  
  /**
   * Unregister a handler for a specific message type
   * @param type Message type
   * @param handler Handler function to remove
   */
  unregisterHandler(type: string, handler: (data: AgentMessageData) => void): void {
    const handlers = AgentService.handlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }
  
  /**
   * Disconnect from the agent WebSocket
   * This will close the shared WebSocket connection
   */
  disconnect(): void {
    if (AgentService.socket) {
      AgentService.socket.close();
      AgentService.socket = null;
    }
    
    // Clear the instance to allow creating a new one if needed
    AgentService.instance = null;
  }
  
  /**
   * Check if the WebSocket is connected
   * @returns True if connected, false otherwise
   */
  isConnected(): boolean {
    return AgentService.socket !== null && AgentService.socket.readyState === WebSocket.OPEN;
  }
  
  // Store task status promises for deduplication
  private static taskStatusPromises: Map<string, {
    promise: Promise<{
      status: string;
      progress: number;
      message?: string;
      video_url?: string;
    }>;
    resolve: (value: {
      status: string;
      progress: number;
      message?: string;
      video_url?: string;
    }) => void;
    reject: (reason?: Error) => void;
    timestamp: number;
  }> = new Map();

  // Store task status handlers
  private static taskStatusHandlers: Map<string, (data: AgentMessageData) => void> = new Map();

  /**
   * Get the status of a task using WebSocket
   * @param taskId Task ID
   * @returns Promise that resolves with the task status
   */
  async getTaskStatus(taskId: string): Promise<{
    status: string;
    progress: number;
    message?: string;
    video_url?: string;
  }> {
    try {
      console.log(`Getting task status for task ${taskId} via WebSocket`);

      // Check if we already have a pending request for this task
      const existingPromise = AgentService.taskStatusPromises.get(taskId);
      if (existingPromise && Date.now() - existingPromise.timestamp < 1000) {
        console.log(`Reusing existing task status request for task ${taskId}`);
        return existingPromise.promise;
      }

      // Create a new promise for this task status request
      const promise = new Promise<{
        status: string;
        progress: number;
        message?: string;
        video_url?: string;
      }>((resolve, reject) => {
        // Ensure WebSocket is connected
        if (!AgentService.socket || AgentService.socket.readyState !== WebSocket.OPEN) {
          // If not connected, try to connect
          console.log(`WebSocket not connected, attempting to connect for task ${taskId}`);
          this.connect()
            .then(() => {
              // After connecting, send the task status request
              this.getTaskStatus(taskId)
                .then(resolve)
                .catch(reject);
            })
            .catch(error => {
              console.error(`Error connecting WebSocket for task ${taskId}:`, error);
              reject(new Error('WebSocket connection failed. Please try again.'));
            });
          return;
        }

        // Create a handler for the task status response
        const handler = (data: AgentMessageData) => {
          if (data.type === 'task_status' && data.task_id === taskId) {
            // Remove the handler
            AgentService.taskStatusHandlers.delete(taskId);
            AgentService.handlers.get('task_status')?.delete(handler);

            // Resolve the promise
            resolve({
              status: data.status || 'error',
              progress: data.progress || 0,
              message: data.message,
              video_url: data.video_url
            });
          }
        };

        // Register the handler
        if (!AgentService.handlers.has('task_status')) {
          AgentService.handlers.set('task_status', new Set());
        }
        AgentService.handlers.get('task_status')!.add(handler);
        AgentService.taskStatusHandlers.set(taskId, handler);

        // Set a timeout to reject the promise if no response is received
        setTimeout(() => {
          // Check if the handler is still registered
          if (AgentService.taskStatusHandlers.has(taskId)) {
            // Remove the handler
            AgentService.taskStatusHandlers.delete(taskId);
            AgentService.handlers.get('task_status')?.delete(handler);

            // Reject with timeout error
            console.log(`WebSocket task status request timed out for task ${taskId}`);
            reject(new Error('WebSocket request timed out. Please try again.'));
          }
        }, 5000); // 5 second timeout

        // Send the task status request via WebSocket
        AgentService.socket.send(JSON.stringify({
          type: 'task_status',
          task_id: taskId
        }));
      });

      // Store the promise
      AgentService.taskStatusPromises.set(taskId, {
        promise,
        resolve: () => {}, // Placeholder, not actually used
        reject: () => {}, // Placeholder, not actually used
        timestamp: Date.now()
      });

      // Clean up the promise after it resolves or rejects
      promise.finally(() => {
        // Remove the promise after a delay to allow for deduplication
        setTimeout(() => {
          AgentService.taskStatusPromises.delete(taskId);
        }, 1000);
      });

      return promise;
    } catch (error) {
      console.error(`Error getting task status for task ${taskId}:`, error);
      
      // Return a default status on error
      return {
        status: 'error',
        progress: 0,
        message: 'Failed to get task status. Please try again later.'
      };
    }
  }
}

/**
 * Create an agent service for the current user
 * This is a factory function that returns the singleton instance
 * @returns Promise that resolves with the agent service
 */
export async function createAgentService(): Promise<AgentService> {
  const authStore = useAuthStore.getState();

  // Wait for auth to be initialized if not already
  if (!authStore.isInitialized) {
    if (typeof authStore.initializeAuth === "function") {
      await authStore.initializeAuth();
    }
  }

  // Re-fetch state after possible async init
  const updatedAuthStore = useAuthStore.getState();

  if (!updatedAuthStore.user) {
    console.error('User not authenticated when creating agent service');
    throw new Error('User not authenticated');
  }

  try {
    console.debug('Creating agent service with cookie-based authentication');
    return await AgentService.getInstance(updatedAuthStore.user.id);
  } catch (error) {
    console.error('Error creating agent service:', error);
    throw error;
  }
}
