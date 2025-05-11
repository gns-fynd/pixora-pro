import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiClient } from '@/services/api-client';
import { VideoGenerationLoader } from '@/components/ui/video-generation-loader';
import { CompactVideoGenerationLoader } from '@/components/ui/compact-video-generation-loader';
import { useChat, ChatMessage, ChatAction } from '@/context/ChatContext';

interface ChatApiResponse {
  message: string;
  actions?: ChatAction[];
  video_updates?: Record<string, unknown>;
}

interface GenerationStatusResponse {
  task_id: string;
  video_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step?: 'analyzing_prompt' | 'generating_images' | 'generating_audio' | 'generating_music' | 'assembling_video';
  step_progress?: number;
  message?: string;
  error?: string;
  result?: Record<string, unknown>;
  steps: Array<Record<string, unknown>>;
}

interface ChatInterfaceProps {
  videoId: string;
  onVideoUpdate?: (updates: Record<string, unknown>) => void;
}

export function ChatInterface({ videoId, onVideoUpdate }: ChatInterfaceProps) {
  // Use the global chat context
  const { messages, addMessage } = useChat();
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Add request throttling
  const lastRequestTimeRef = useRef<number>(0);
  const REQUEST_THROTTLE_MS = 2000; // 2 seconds minimum between requests
  const pendingRequestRef = useRef<AbortController | null>(null);
  
  // Video generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationTaskId, setGenerationTaskId] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationSteps, setGenerationSteps] = useState([
    { id: "analyze", label: "Analyzing prompt", icon: "transcript" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "images", label: "Creating visuals", icon: "video" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "audio", label: "Generating audio", icon: "audio" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "music", label: "Creating background music", icon: "music" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "assembly", label: "Assembling video", icon: "video" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 }
  ]);
  
  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Poll for generation status when a generation is in progress
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isGenerating && generationTaskId) {
      interval = setInterval(async () => {
        try {
          // Get generation status from the new unified endpoint
          const status = await apiClient.get<GenerationStatusResponse>(`/ai/generate/status/${generationTaskId}`);
          
          console.log('Generation status update:', status);
          
          // Update progress
          setGenerationProgress(status.progress);
          
          // Update steps
          const updatedSteps = [...generationSteps];
          
          // Map backend status to steps
          if (status.current_step === 'analyzing_prompt') {
            updatedSteps[0].status = 'processing';
            updatedSteps[0].progress = status.step_progress || 0;
          } else if (status.current_step === 'generating_images') {
            updatedSteps[0].status = 'completed';
            updatedSteps[0].progress = 100;
            updatedSteps[1].status = 'processing';
            updatedSteps[1].progress = status.step_progress || 0;
          } else if (status.current_step === 'generating_audio') {
            updatedSteps[0].status = 'completed';
            updatedSteps[0].progress = 100;
            updatedSteps[1].status = 'completed';
            updatedSteps[1].progress = 100;
            updatedSteps[2].status = 'processing';
            updatedSteps[2].progress = status.step_progress || 0;
          } else if (status.current_step === 'generating_music') {
            updatedSteps[0].status = 'completed';
            updatedSteps[0].progress = 100;
            updatedSteps[1].status = 'completed';
            updatedSteps[1].progress = 100;
            updatedSteps[2].status = 'completed';
            updatedSteps[2].progress = 100;
            updatedSteps[3].status = 'processing';
            updatedSteps[3].progress = status.step_progress || 0;
          } else if (status.current_step === 'assembling_video') {
            updatedSteps[0].status = 'completed';
            updatedSteps[0].progress = 100;
            updatedSteps[1].status = 'completed';
            updatedSteps[1].progress = 100;
            updatedSteps[2].status = 'completed';
            updatedSteps[2].progress = 100;
            updatedSteps[3].status = 'completed';
            updatedSteps[3].progress = 100;
            updatedSteps[4].status = 'processing';
            updatedSteps[4].progress = status.step_progress || 0;
          }
          
          setGenerationSteps(updatedSteps);
          
          // Check if generation is complete
          if (status.status === 'completed') {
            setIsGenerating(false);
            clearInterval(interval);
            
            // Add success message
            addMessage({ 
              role: 'assistant', 
              content: 'Your video has been generated successfully! You can now view and download it.',
              timestamp: new Date()
            });
            
            // Update video if needed
            if (status.result && onVideoUpdate) {
              onVideoUpdate(status.result);
            }
          } else if (status.status === 'failed') {
            setIsGenerating(false);
            clearInterval(interval);
            
            // Add error message
            addMessage({ 
              role: 'assistant', 
              content: `Sorry, video generation failed: ${status.error || 'Unknown error'}`,
              timestamp: new Date()
            });
          }
        } catch (error) {
          console.error('Error checking generation status:', error);
        }
      }, 2000); // Poll every 2 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGenerating, generationTaskId, generationSteps, onVideoUpdate, addMessage]);
  
  // Send message to AI agent
  const sendMessage = async () => {
    if (!input.trim() || isProcessing) return;
    
    // Check if we should throttle this request
    const now = Date.now();
    if (now - lastRequestTimeRef.current < REQUEST_THROTTLE_MS) {
      console.debug('Throttling chat request (too frequent)');
      return;
    }
    
    // Update last request time
    lastRequestTimeRef.current = now;
    
    // Cancel any pending request
    if (pendingRequestRef.current) {
      pendingRequestRef.current.abort();
    }
    
    // Create a new abort controller for this request
    const abortController = new AbortController();
    pendingRequestRef.current = abortController;
    
    // Add user message to chat
    const userMessage: ChatMessage = { 
      role: 'user', 
      content: input,
      timestamp: new Date()
    };
    addMessage(userMessage);
    setInput('');
    setIsProcessing(true);
    
    // Check if this is a video generation request
    const lowerInput = input.toLowerCase();
    if (
      lowerInput.includes('generate video') || 
      lowerInput.includes('create video') || 
      lowerInput.includes('make a video') ||
      lowerInput.includes('produce video')
    ) {
      // This is a video generation request
      await startVideoGeneration(input);
      return;
    }
    
    try {
      // Call AI agent endpoint with abort signal
      const response = await apiClient.post<ChatApiResponse>('/ai/chat', {
        message: input,
        video_id: videoId
      }, {
        signal: abortController.signal
      });
      
      // Add AI response to chat
      const assistantMessage: ChatMessage = { 
        role: 'assistant', 
        content: response.message,
        actions: response.actions,
        timestamp: new Date()
      };
      addMessage(assistantMessage);
      
      // If the AI made changes to the video, update the parent component
      if (response.video_updates && onVideoUpdate) {
        onVideoUpdate(response.video_updates);
      }
    } catch (error) {
      console.error('Error sending message to AI:', error);
      
      // Add error message
      addMessage({ 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date()
      });
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Handle action button click
  const handleActionClick = async (action: ChatAction) => {
    // Check if we should throttle this request
    const now = Date.now();
    if (now - lastRequestTimeRef.current < REQUEST_THROTTLE_MS) {
      console.debug('Throttling action request (too frequent)');
      return;
    }
    
    // Update last request time
    lastRequestTimeRef.current = now;
    
    // Cancel any pending request
    if (pendingRequestRef.current) {
      pendingRequestRef.current.abort();
    }
    
    // Create a new abort controller for this request
    const abortController = new AbortController();
    pendingRequestRef.current = abortController;
    
    try {
      setIsProcessing(true);
      
      // Different handling based on action type
      if (action.type === 'regenerate_image') {
        // Add message about the action
        addMessage({ 
          role: 'user', 
          content: `Regenerate image for scene ${action.scene_id}`,
          timestamp: new Date()
        });
        
        // Call AI agent with the action
        const response = await apiClient.post<ChatApiResponse>('/ai/chat', {
          message: `Regenerate the image for scene ${action.scene_id}`,
          video_id: videoId
        }, {
          signal: abortController.signal
        });
        
        // Add AI response
        addMessage({ 
          role: 'assistant', 
          content: response.message,
          actions: response.actions,
          timestamp: new Date()
        });
        
        // Update video if needed
        if (response.video_updates && onVideoUpdate) {
          onVideoUpdate(response.video_updates);
        }
      } 
      else if (action.type === 'change_voice') {
        // Add message about the action
        addMessage({ 
          role: 'user', 
          content: 'Select a new voice for the video',
          timestamp: new Date()
        });
        
        // Call AI agent with the action
        const response = await apiClient.post<ChatApiResponse>('/ai/chat', {
          message: 'Can you select a different voice for this video?',
          video_id: videoId
        }, {
          signal: abortController.signal
        });
        
        // Add AI response
        addMessage({ 
          role: 'assistant', 
          content: response.message,
          actions: response.actions,
          timestamp: new Date()
        });
        
        // Update video if needed
        if (response.video_updates && onVideoUpdate) {
          onVideoUpdate(response.video_updates);
        }
      }
      else if (action.type === 'change_music') {
        // Add message about the action
        addMessage({ 
          role: 'user', 
          content: `Change music to ${action.style} style`,
          timestamp: new Date()
        });
        
        // Call AI agent with the action
        const response = await apiClient.post<ChatApiResponse>('/ai/chat', {
          message: `Can you change the background music to a ${action.style} style?`,
          video_id: videoId
        }, {
          signal: abortController.signal
        });
        
        // Add AI response
        addMessage({ 
          role: 'assistant', 
          content: response.message,
          actions: response.actions,
          timestamp: new Date()
        });
        
        // Update video if needed
        if (response.video_updates && onVideoUpdate) {
          onVideoUpdate(response.video_updates);
        }
      }
      else if (action.type === 'generate_video') {
        // Start video generation with the provided prompt
        const prompt = action.prompt as string || 'Generate a video';
        await startVideoGeneration(prompt);
      }
      // Handle other action types as needed
      
    } catch (error) {
      console.error('Error executing action:', error);
      
      // Add error message
      addMessage({ 
        role: 'assistant', 
        content: 'Sorry, I encountered an error executing that action. Please try again.',
        timestamp: new Date()
      });
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Format timestamp
  const formatTime = (date?: Date) => {
    if (!date) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  // Start a video generation
  const startVideoGeneration = async (prompt: string) => {
    // Cancel any pending request
    if (pendingRequestRef.current) {
      pendingRequestRef.current.abort();
    }
    
    // Create a new abort controller for this request
    const abortController = new AbortController();
    pendingRequestRef.current = abortController;
    
    try {
      setIsProcessing(true);
      
      // Call the new unified generation endpoint
      // Wrap the request data in a 'request' field as required by the new backend
      const requestData = {
        prompt,
        video_id: videoId,
        client_context: {
          current_page: 'chat'
        }
      };
      
      const response = await apiClient.post<{ task_id: string, data?: Record<string, unknown> }>('/ai/generate', {
        request: requestData
      }, {
        signal: abortController.signal
      });
      
      // Set the task ID and start polling
      setGenerationTaskId(response.task_id);
      setIsGenerating(true);
      
      // Add message about the generation
      addMessage({ 
        role: 'assistant', 
        content: 'I\'m generating your video now. This may take a few minutes.',
        timestamp: new Date()
      });
      
      console.log('Video generation started with task ID:', response.task_id);
      
    } catch (error) {
      console.error('Error starting video generation:', error);
      
      // Add error message
      addMessage({ 
        role: 'assistant', 
        content: 'Sorry, I encountered an error starting the video generation. Please try again.',
        timestamp: new Date()
      });
      
    } finally {
      setIsProcessing(false);
    }
  };
  
  return (
    <div className="flex flex-col h-full border-r bg-background">
      {/* Compact Video Generation Loader for chat interface */}
      <CompactVideoGenerationLoader
        isVisible={isGenerating}
        overallProgress={generationProgress}
        steps={generationSteps}
        message="Generating your video..."
      />
      
      {/* Full screen loader for critical operations */}
      <VideoGenerationLoader 
        isVisible={isGenerating && generationProgress > 0 && generationProgress < 10}
        overallProgress={generationProgress}
        steps={generationSteps}
        message="Initializing video generation..."
      />
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">AI Assistant</h2>
        <p className="text-sm text-muted-foreground">
          Ask me anything about your video project
        </p>
      </div>
      
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="flex flex-col max-w-[80%]">
                <div 
                  className={`p-3 rounded-lg ${
                    msg.role === 'user' 
                      ? 'bg-primary text-primary-foreground ml-auto' 
                      : 'bg-muted'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {msg.actions.map((action, i) => (
                      <Button
                        key={i}
                        variant="outline"
                        size="sm"
                        onClick={() => handleActionClick(action)}
                        disabled={isProcessing}
                        className="text-xs"
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                )}
                
                <span className="text-xs text-muted-foreground mt-1">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your message..."
            disabled={isProcessing}
            className="flex-1"
          />
          <Button
            onClick={sendMessage}
            disabled={isProcessing || !input.trim()}
          >
            {isProcessing ? '...' : 'Send'}
          </Button>
        </div>
      </div>
    </div>
  );
}
