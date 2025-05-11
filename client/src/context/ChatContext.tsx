import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
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
}

interface ChatContextType {
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  sendMessage: (content: string, context?: Record<string, unknown>) => Promise<void>;
  executeAction: (action: ChatAction, context?: Record<string, unknown>) => Promise<void>;
  isProcessing: boolean;
  activeGeneration: GenerationProgress | null;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeGeneration, setActiveGeneration] = useState<GenerationProgress | null>(null);
  
  // Reference to the agent service
  const agentServiceRef = useRef<AgentService | null>(null);
  
  // Initialize agent service
  useEffect(() => {
    const initAgentService = async () => {
      try {
        // Check if user is authenticated using auth store
        const authStore = useAuthStore.getState();
        if (!authStore.user) {
          console.log('User not authenticated, skipping agent service initialization');
          return;
        }
        
        const service = await createAgentService();
        agentServiceRef.current = service;
        
        // Connect to WebSocket
        await service.connect();
        
        // Register handlers
        service.registerHandler('message', handleAgentMessage);
        service.registerHandler('progress', handleProgressUpdate);
        service.registerHandler('video', handleVideoComplete);
        service.registerHandler('error', handleError);
        
        console.log('Agent service initialized');
      } catch (error) {
        console.error('Error initializing agent service:', error);
      }
    };
    
    // Initialize agent service when component mounts
    initAgentService();
    
    // Also initialize when auth state changes
    const unsubscribe = useAuthStore.subscribe(
      (state: { isAuthenticated: boolean }) => {
        // Check if authentication state changed
        if (state.isAuthenticated) {
          initAgentService();
        } else if (agentServiceRef.current) {
          // Disconnect if user logs out
          agentServiceRef.current.disconnect();
          agentServiceRef.current = null;
        }
      }
    );
    
    // Cleanup on unmount
    return () => {
      if (agentServiceRef.current) {
        agentServiceRef.current.disconnect();
        agentServiceRef.current = null;
      }
      // Unsubscribe from auth store
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
  const handleAgentMessage = (data: AgentMessageData) => {
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
    // Check if this is a duplicate message (same content and role within the last 2 seconds)
    const isDuplicate = messages.some(existingMsg => 
      existingMsg.role === message.role && 
      existingMsg.content === message.content &&
      message.timestamp.getTime() - existingMsg.timestamp.getTime() < 2000
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
  const sendMessage = async (content: string, context?: Record<string, unknown>) => {
    if (!content.trim()) return;
    
    // Add user message to chat
    addMessage({
      role: 'user',
      content,
      timestamp: new Date()
    });
    
    setIsProcessing(true);
    
    try {
      // Try to use WebSocket if connected
      if (agentServiceRef.current && agentServiceRef.current.isConnected()) {
        agentServiceRef.current.sendMessageWs(content, context);
      } else {
        // Fall back to REST API
        if (!agentServiceRef.current) {
          agentServiceRef.current = await createAgentService();
        }
        
        const response = await agentServiceRef.current.sendMessage(content, context);
        
        // Add assistant response to chat
        addMessage({
          role: 'assistant',
          content: response.message,
          actions: response.actions,
          timestamp: new Date()
        });
        
        // If a task was created, set active generation
        if (response.task_id) {
          setActiveGeneration({
            taskId: response.task_id,
            progress: 0,
            status: 'processing',
            message: 'Starting generation...'
          });
          
          // Start polling for status
          pollTaskStatus(response.task_id);
        }
        
        setIsProcessing(false);
      }
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
    if (!agentServiceRef.current) {
      try {
        agentServiceRef.current = await createAgentService();
      } catch (error) {
        console.error('Error creating agent service:', error);
        return;
      }
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
      // Execute the action
      const response = await agentServiceRef.current.executeAction(action, context);
      
      // Add assistant response to chat
      addMessage({
        role: 'assistant',
        content: response.message,
        actions: response.actions,
        timestamp: new Date()
      });
      
      // If a task was created, set active generation
      if (response.task_id) {
        setActiveGeneration({
          taskId: response.task_id,
          progress: 0,
          status: 'processing',
          message: 'Starting generation...'
        });
        
        // Start polling for status
        pollTaskStatus(response.task_id);
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
  
  // Poll for task status
  const pollTaskStatus = async (taskId: string) => {
    if (!agentServiceRef.current) return;
    
    try {
      const status = await agentServiceRef.current.getTaskStatus(taskId);
      
      setActiveGeneration({
        taskId,
        progress: status.progress,
        status: status.status as 'pending' | 'processing' | 'completed' | 'error',
        message: status.message,
        videoUrl: status.video_url
      });
      
      // If task is still processing, poll again after a delay
      if (status.status === 'processing' || status.status === 'pending') {
        setTimeout(() => pollTaskStatus(taskId), 2000);
      } else if (status.status === 'completed' && status.video_url) {
        // Add message about video completion
        addMessage({
          role: 'assistant',
          content: `Your video is ready! You can view it now.`,
          timestamp: new Date()
        });
      }
    } catch (error) {
      console.error('Error polling task status:', error);
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
      activeGeneration 
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
