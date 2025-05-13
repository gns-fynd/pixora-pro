import { useState, useEffect, useRef } from 'react';
import { AgentService, AgentMessageData, ChatAction, createAgentService } from '@/services/agent-service';

interface AgentChatProps {
  initialPrompt?: string;
  onComplete?: (result: Record<string, unknown>) => void;
  className?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  actions?: ChatAction[];
}

export function AgentChat({ initialPrompt, onComplete, className = '' }: AgentChatProps) {
  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(initialPrompt || '');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  // Refs
  const agentServiceRef = useRef<AgentService | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Connect to the agent service
  useEffect(() => {
    const connectToAgent = async () => {
      try {
        // Create agent service
        const service = await createAgentService();
        agentServiceRef.current = service;
        
        // Connect to the WebSocket
        await service.connect();
        setIsConnected(true);
        
        // If there's an initial prompt, send it after connection
        if (initialPrompt) {
          setTimeout(() => {
            // Set the input value
            setInput(initialPrompt);
            // Then send the message (without arguments, it will use the input state)
            sendMessage();
          }, 500); // Small delay to ensure connection is fully established
        }
      } catch (error) {
        console.error('Error connecting to agent:', error);
        setError('Failed to connect to agent. Please try again.');
      }
    };
    
    connectToAgent();
    
    // Cleanup on unmount
    return () => {
      if (agentServiceRef.current) {
        agentServiceRef.current.disconnect();
      }
    };
  }, [initialPrompt]); // Add initialPrompt as a dependency
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Handle message from agent
  const handleAgentMessage = (data: AgentMessageData) => {
    if (data.message) {
      // Update messages
      setMessages(prev => {
        // Check if we already have an assistant message for this task
        const existingIndex = prev.findIndex(m => 
          m.role === 'assistant' && m.content.includes(`Task ID: ${data.task_id}`)
        );
        
        if (existingIndex >= 0) {
          // Update existing message
          const updated = [...prev];
          updated[existingIndex] = {
            role: 'assistant',
            content: data.message || 'No content',
            actions: data.actions
          };
          return updated;
        } else {
          // Add new message
          return [...prev, {
            role: 'assistant',
            content: data.message || 'No content',
            actions: data.actions
          }];
        }
      });
    }
    
    // Update progress
    if (data.progress !== undefined) {
      setProgress(data.progress);
    }
    
    // Handle completion
    if (data.type === 'video_complete' && onComplete && data.video_url) {
      onComplete({ video_url: data.video_url });
    }
    
    // Clear loading state when complete
    if (data.type === 'video_complete') {
      setIsLoading(false);
    }
  };
  
  // Send message to agent
  const sendMessage = async () => {
    if (!input.trim() || !agentServiceRef.current || !isConnected) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      // Add user message
      setMessages(prev => [...prev, { role: 'user', content: input }]);
      
      // Send message to agent
      const response = await agentServiceRef.current.sendMessage(input);
      const taskId = response.task_id;
      
      // Register handler for this task
      if (taskId) {
        agentServiceRef.current.registerHandler('message', handleAgentMessage);
      }
      
      // Clear input
      setInput('');
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message. Please try again.');
      setIsLoading(false);
    }
  };
  
  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };
  
  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };
  
  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };
  
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-3/4 p-3 rounded-lg ${
                message.role === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100 dark:bg-gray-800'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              
              {/* Actions */}
              {message.actions && message.actions.length > 0 && (
                <div className="mt-2 text-xs opacity-75">
                  <div>Actions:</div>
                  <ul className="list-disc pl-4">
                    {message.actions.map((action, i) => (
                      <li key={i}>{action.type}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-3/4 p-3 rounded-lg bg-gray-100 dark:bg-gray-800">
              <div className="flex items-center space-x-2">
                <div className="animate-pulse flex space-x-1">
                  <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                  <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                  <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                </div>
                <div className="text-sm text-gray-500">
                  {progress > 0 ? `${Math.round(progress)}%` : 'Processing...'}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Error message */}
        {error && (
          <div className="flex justify-center">
            <div className="max-w-3/4 p-3 rounded-lg bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
              {error}
            </div>
          </div>
        )}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <textarea
            value={input}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 p-2 border rounded-lg resize-none h-12 max-h-32"
            disabled={!isConnected || isLoading}
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
            disabled={!isConnected || isLoading || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
