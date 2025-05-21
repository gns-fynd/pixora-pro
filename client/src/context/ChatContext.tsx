import { createContext, useState, useEffect, useContext, useRef } from 'react';
import { AgentService, createAgentService, ChatAction, AgentMessageData } from '@/services/agent-service';
import useAuthStore from '@/store/use-auth-store';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  actions?: ChatAction[];
  timestamp: Date;
}

// Re-export ChatAction from agent-service to ensure type consistency
export type { ChatAction };

export interface GenerationProgress {
  taskId: string;
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'error';
  message?: string;
  videoUrl?: string;
  retryCount?: number;
}

interface ChatContextType {
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  sendMessage: (content: string, context?: Record<string, unknown>, silent?: boolean) => Promise<void>;
  executeAction: (action: ChatAction, context?: Record<string, unknown>) => Promise<void>;
  isProcessing: boolean;
  activeGeneration: GenerationProgress | null;
  authInitialized: boolean;
  authError: string | null;
  latestSceneData: any | null; // Add latest scene data to context
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeGeneration, setActiveGeneration] = useState<GenerationProgress | null>(null);
  const [authInitialized, setAuthInitialized] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  
  // Reference to the agent service
  const agentServiceRef = useRef<AgentService | null>(null);
  
  // Track initialization state to prevent multiple initializations
  const isInitializingRef = useRef(false);
  
  // Initialize agent service only once, after auth is initialized and user is authenticated
  useEffect(() => {
    let isMounted = true;

    const tryInitAgentService = async () => {
      if (isInitializingRef.current) {
        return;
      }
      if (agentServiceRef.current) {
        return;
      }

      const authStore = useAuthStore.getState();
      if (!authStore.isInitialized || !authStore.user) {
        // Wait for auth to be initialized and user to be authenticated
        return;
      }

      isInitializingRef.current = true;
      try {
        setAuthError(null);
        const service = await createAgentService();
        if (!isMounted) {
          isInitializingRef.current = false;
          return;
        }
        agentServiceRef.current = service;

        // Register handlers
        service.registerHandler('agent_message', handleAgentMessage);
        service.registerHandler('progress_update', handleProgressUpdate);
        service.registerHandler('video_complete', handleVideoComplete);
        service.registerHandler('error', handleError);

        setAuthInitialized(true);
      } catch (error) {
        if (isMounted) {
          setAuthError(error instanceof Error ? error.message : 'Unknown error');
          setAuthInitialized(false);
        }
      } finally {
        if (isMounted) {
          isInitializingRef.current = false;
        }
      }
    };

    tryInitAgentService();

    // Listen for auth state changes to re-attempt initialization
    const unsubscribe = useAuthStore.subscribe(
      (state) => {
        if (state.isInitialized && state.user && !agentServiceRef.current && !isInitializingRef.current) {
          tryInitAgentService();
        }
        if (state.isInitialized && !state.user) {
          setAuthInitialized(false);
          setAuthError('User not authenticated. Please log in to continue.');
        }
      }
    );

    return () => {
      isMounted = false;
      unsubscribe();
      if (agentServiceRef.current) {
        const service = agentServiceRef.current;
        service.unregisterHandler('agent_message', handleAgentMessage);
        service.unregisterHandler('progress_update', handleProgressUpdate);
        service.unregisterHandler('video_complete', handleVideoComplete);
        service.unregisterHandler('error', handleError);
      }
    };
  }, []);
  
  // Handle auth state changes separately
  useEffect(() => {
    let isMounted = true;
    
    const unsubscribe = useAuthStore.subscribe(
      (state: { isAuthenticated: boolean }) => {
        // Check if authentication state changed
        if (state.isAuthenticated && !agentServiceRef.current && !isInitializingRef.current) {
          // Initialize if authenticated and not already initializing
          const initAgentService = async () => {
            isInitializingRef.current = true;
            try {
              console.log('Auth state changed, initializing agent service');
              const service = await createAgentService();
              
              // Only proceed if component is still mounted
              if (!isMounted) {
                isInitializingRef.current = false;
                return;
              }
              
              agentServiceRef.current = service;
              
              // Register handlers
              service.registerHandler('message', handleAgentMessage);
              service.registerHandler('progress', handleProgressUpdate);
              service.registerHandler('video', handleVideoComplete);
              service.registerHandler('error', handleError);
              
              setAuthInitialized(true);
              setAuthError(null);
            } catch (error) {
              console.error('Error initializing agent service after auth change:', error);
              if (isMounted) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                setAuthError(`Authentication error: ${errorMessage}`);
                setAuthInitialized(false);
              }
            } finally {
              if (isMounted) {
                isInitializingRef.current = false;
              }
            }
          };
          
          initAgentService();
        } else if (!state.isAuthenticated && agentServiceRef.current) {
          // Just unregister handlers if logged out, don't disconnect
          const service = agentServiceRef.current;
          service.unregisterHandler('message', handleAgentMessage);
          service.unregisterHandler('progress', handleProgressUpdate);
          service.unregisterHandler('video', handleVideoComplete);
          service.unregisterHandler('error', handleError);
          
          agentServiceRef.current = null;
          
          if (isMounted) {
            setAuthInitialized(false);
            setAuthError('User logged out. Please log in to continue.');
          }
        }
      }
    );
    
    // Cleanup on unmount
    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, []);
  
  // Load messages from localStorage on mount
  useEffect(() => {
    const storedMessages = localStorage.getItem('pixora_chat_messages');
    if (storedMessages) {
      try {
        // Parse the stored messages and convert string dates back to Date objects
        const parsedMessages = JSON.parse(storedMessages, (key, value) => {
          if (key === 'timestamp' && typeof value === 'string') {
            return new Date(value);
          }
          return value;
        });
        setMessages(parsedMessages);
      } catch (error) {
        console.error('Error parsing stored chat messages:', error);
        setInitialMessage();
      }
    } else {
      setInitialMessage();
    }
  }, []);
  
  const setInitialMessage = () => {
    // Initial welcome message
    setMessages([{
      role: 'assistant',
      content: 'Hi! I\'m your AI video assistant. How can I help with your video project today?',
      timestamp: new Date()
    }]);
  };
  
  // Save messages to localStorage when they change
  useEffect(() => {
    localStorage.setItem('pixora_chat_messages', JSON.stringify(messages));
  }, [messages]);
  
  // Handle agent message from WebSocket
  // Store the latest scene breakdown data for use in the scene breakdown UI
  const latestSceneDataRef = useRef<any>(null);
  const [latestSceneData, setLatestSceneData] = useState<any | null>(null);

  const handleAgentMessage = (data: AgentMessageData & { data?: any }) => {
    if (data.data) {
      // Store the scene breakdown data for use in the scene breakdown UI
      latestSceneDataRef.current = data.data;
      setLatestSceneData(data.data); // Trigger re-render
    }
    if (data.content) {
      addMessage({
        role: 'assistant',
        content: data.content,
        actions: data.actions,
        timestamp: new Date()
      });
    }
    setIsProcessing(false);
  };
  
  // Handle progress update from WebSocket
  const handleProgressUpdate = (data: AgentMessageData) => {
    if (data.task_id && data.progress !== undefined) {
      setActiveGeneration({
        taskId: data.task_id,
        progress: data.progress,
        status: data.status as 'pending' | 'processing' | 'completed' | 'error',
        message: data.message
      });
    }
  };
  
  // Handle video completion from WebSocket
  const handleVideoComplete = (data: AgentMessageData) => {
    if (data.task_id && data.video_url) {
      setActiveGeneration({
        taskId: data.task_id,
        progress: 100,
        status: 'completed',
        videoUrl: data.video_url
      });
      
      // Add a message about the video completion
      addMessage({
        role: 'assistant',
        content: `Your video is ready! You can view it now.`,
        timestamp: new Date()
      });
    }
  };
  
  // Handle error from WebSocket
  const handleError = (data: AgentMessageData) => {
    console.error('Agent error:', data.error);
    
    if (data.task_id) {
      setActiveGeneration({
        taskId: data.task_id,
        progress: 0,
        status: 'error',
        message: data.error
      });
    }
    
    // Add error message
    addMessage({
      role: 'assistant',
      content: `Sorry, I encountered an error: ${data.error || 'Unknown error'}`,
      timestamp: new Date()
    });
    
    setIsProcessing(false);
  };
  
  const addMessage = (message: ChatMessage) => {
    // Aggressive deduplication: prevent adding if the same content and role exist in the last 5 messages
    const recentMessages = messages.slice(-5);
    const isDuplicate = recentMessages.some(existingMsg =>
      existingMsg.role === message.role &&
      existingMsg.content === message.content
    );

    if (!isDuplicate) {
      setMessages(prev => [...prev, message]);
    } else {
      console.debug('Prevented duplicate message:', message.content);
    }
  };
  
  const clearMessages = () => {
    setMessages([{
      role: 'assistant',
      content: 'Hi! I\'m your AI video assistant. How can I help with your video project today?',
      timestamp: new Date()
    }]);
    
    // Clear active generation
    setActiveGeneration(null);
  };
  
  // Send a message to the agent
  const sendMessage = async (
    content: string,
    context?: Record<string, unknown>,
    silent: boolean = false
  ) => {
    if (!content.trim()) return;

    // Log the message and context for debugging
    console.log('Sending message to agent:', { content, context, silent });

    // Add user message to chat unless silent
    if (!silent) {
      addMessage({
        role: 'user',
        content,
        timestamp: new Date()
      });
    }

    setIsProcessing(true);

    try {
      // Ensure we have an agent service
      if (!agentServiceRef.current && !isInitializingRef.current) {
        console.log('Creating new agent service before sending message');
        isInitializingRef.current = true;
        try {
          agentServiceRef.current = await createAgentService();
          setAuthInitialized(true);
        } finally {
          isInitializingRef.current = false;
        }
      } else if (!agentServiceRef.current) {
        throw new Error('Agent service is initializing, please try again in a moment');
      }

      // Always use WebSocket for chat messages
      const formattedContext = context ? { ...context } : {};

      // Ensure WebSocket is connected before sending
      if (!agentServiceRef.current.isConnected()) {
        console.log('WebSocket not connected, attempting to connect...');
        await agentServiceRef.current.connect();
      }

      // Ensure prompt is properly formatted if it exists in context
      if (formattedContext.prompt && typeof formattedContext.prompt === 'string') {
        console.log('Prompt found in context:', formattedContext.prompt);
      }

      agentServiceRef.current.sendMessageWs(content, formattedContext);
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date()
      });

      setIsProcessing(false);
    }
  };
  
  // Execute an action
  const executeAction = async (action: ChatAction, context?: Record<string, unknown>) => {
    // Log the action and context for debugging
    console.log('Executing action:', { action, context });
    
    // Ensure we have an agent service
    if (!agentServiceRef.current && !isInitializingRef.current) {
      try {
        console.log('Creating new agent service before executing action');
        isInitializingRef.current = true;
        agentServiceRef.current = await createAgentService();
        setAuthInitialized(true);
      } catch (error) {
        console.error('Error creating agent service:', error);
        
        // Add error message
        addMessage({
          role: 'assistant',
          content: 'Sorry, I encountered an error connecting to the server. Please try again.',
          timestamp: new Date()
        });
        
        return;
      } finally {
        isInitializingRef.current = false;
      }
    } else if (!agentServiceRef.current) {
      // Add error message if service is initializing
      addMessage({
        role: 'assistant',
        content: 'Service is initializing, please try again in a moment.',
        timestamp: new Date()
      });
      
      return;
    }
    
    // Add user message about the action
    let actionMessage = '';
    
    switch (action.type) {
      case 'regenerate_image':
        actionMessage = `Regenerate image for scene ${action.scene_id}`;
        break;
      case 'change_voice':
        actionMessage = 'Select a new voice for the video';
        break;
      case 'change_music':
        actionMessage = `Change music to ${action.style} style`;
        break;
      case 'generate_video':
        actionMessage = action.prompt ? `Generate a video about ${action.prompt}` : 'Generate a video';
        break;
      default:
        actionMessage = `Execute ${action.label}`;
    }
    
    addMessage({
      role: 'user',
      content: actionMessage,
      timestamp: new Date()
    });
    
    setIsProcessing(true);
    
    try {
      // Format context for better compatibility
      const formattedContext = context ? { ...context } : {};
      
      // Ensure prompt is properly formatted if it exists in context
      if (formattedContext.prompt && typeof formattedContext.prompt === 'string') {
        console.log('Prompt found in context:', formattedContext.prompt);
      }
      
      // Execute the action via WebSocket
      console.log('Sending action to agent service via WebSocket');
      agentServiceRef.current.executeAction(action, formattedContext);
      
      // Add a processing message
      addMessage({
        role: 'assistant',
        content: 'Processing your request...',
        timestamp: new Date()
      });
      
      // For video generation actions, set active generation
      if (action.type === 'generate_video') {
        // Create a task ID for tracking
        const taskId = crypto.randomUUID();
        console.log('Created task ID for video generation:', taskId);
        
        setActiveGeneration({
          taskId,
          progress: 0,
          status: 'processing',
          message: 'Starting video generation...'
        });
        
        // Start polling for status
        pollTaskStatus(taskId);
      }
      
      setIsProcessing(false);
    } catch (error) {
      console.error('Error executing action:', error);
      
      // Add error message
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error executing that action. Please try again.',
        timestamp: new Date()
      });
      
      setIsProcessing(false);
    }
  };
  
  // Register a handler for task status updates
  useEffect(() => {
    if (agentServiceRef.current) {
      // Register handler for task status updates
      agentServiceRef.current.registerHandler('task_status', handleTaskStatus);
      
      // Clean up on unmount
      return () => {
        if (agentServiceRef.current) {
          agentServiceRef.current.unregisterHandler('task_status', handleTaskStatus);
        }
      };
    }
  }, []);
  
  // Handle task status updates from WebSocket
  const handleTaskStatus = (data: AgentMessageData) => {
    if (data.task_id) {
      console.log(`Received task status update for task ${data.task_id}:`, data);
      
      setActiveGeneration({
        taskId: data.task_id,
        progress: data.progress || 0,
        status: data.status as 'pending' | 'processing' | 'completed' | 'error',
        message: data.message,
        videoUrl: data.video_url
      });
      
      // If task is completed with a video URL, add a message
      if (data.status === 'completed' && data.video_url) {
        console.log(`Task ${data.task_id} completed with video URL:`, data.video_url);
        
        // Add message about video completion
        addMessage({
          role: 'assistant',
          content: `Your video is ready! You can view it now.`,
          timestamp: new Date()
        });
      } else if (data.status === 'error') {
        console.error(`Task ${data.task_id} failed with error:`, data.message);
        
        // Add error message
        addMessage({
          role: 'assistant',
          content: `Sorry, there was an error generating your video: ${data.message || 'Unknown error'}`,
          timestamp: new Date()
        });
      }
    }
  };
  
  // Poll for task status using WebSocket
  const pollTaskStatus = async (taskId: string) => {
    if (!agentServiceRef.current) {
      console.error('Cannot poll task status: agent service is not initialized');
      return;
    }
    
    console.log(`Polling status for task ${taskId} via WebSocket`);
    
    try {
      // Get task status via WebSocket
      const status = await agentServiceRef.current.getTaskStatus(taskId);
      
      console.log(`Task ${taskId} status:`, status);
      
      // Update active generation
      setActiveGeneration({
        taskId,
        progress: status.progress,
        status: status.status as 'pending' | 'processing' | 'completed' | 'error',
        message: status.message,
        videoUrl: status.video_url
      });
      
      // If task is still processing, poll again after a delay
      if (status.status === 'processing' || status.status === 'pending') {
        console.log(`Task ${taskId} is still processing, polling again in 2 seconds`);
        setTimeout(() => pollTaskStatus(taskId), 2000);
      } else if (status.status === 'completed' && status.video_url) {
        console.log(`Task ${taskId} completed with video URL:`, status.video_url);
        
        // Add message about video completion
        addMessage({
          role: 'assistant',
          content: `Your video is ready! You can view it now.`,
          timestamp: new Date()
        });
      } else if (status.status === 'error') {
        console.error(`Task ${taskId} failed with error:`, status.message);
        
        // Add error message
        addMessage({
          role: 'assistant',
          content: `Sorry, there was an error generating your video: ${status.message || 'Unknown error'}`,
          timestamp: new Date()
        });
      }
    } catch (error) {
      console.error(`Error polling task status for task ${taskId}:`, error);
      
      // Retry polling after a delay, but with a maximum number of retries
      const maxRetries = 3;
      const retryCount = (activeGeneration?.retryCount || 0) + 1;
      
      if (retryCount <= maxRetries) {
        console.log(`Retrying poll for task ${taskId} (attempt ${retryCount}/${maxRetries})`);
        
        // Update retry count in active generation
        setActiveGeneration(prev => {
          if (!prev || prev.taskId !== taskId) return prev;
          return {
            ...prev,
            retryCount
          };
        });
        
        // Retry after a delay with exponential backoff
        const retryDelay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => pollTaskStatus(taskId), retryDelay);
      } else {
        console.error(`Exceeded maximum retries (${maxRetries}) for task ${taskId}`);
        
        // Update status to error
        setActiveGeneration(prev => {
          if (!prev || prev.taskId !== taskId) return prev;
          return {
            ...prev,
            status: 'error',
            message: 'Failed to get task status after multiple attempts'
          };
        });
        
        // Add error message
        addMessage({
          role: 'assistant',
          content: 'Sorry, I lost connection with the server. Please try again.',
          timestamp: new Date()
        });
      }
    }
  };
  
  return (
    <ChatContext.Provider value={{ 
      messages, 
      addMessage, 
      clearMessages, 
      sendMessage, 
      executeAction, 
      isProcessing, 
      activeGeneration,
      authInitialized,
      authError,
      latestSceneData
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
