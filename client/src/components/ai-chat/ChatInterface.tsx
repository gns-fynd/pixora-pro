import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { VideoGenerationLoader } from '@/components/ui/video-generation-loader';
import { CompactVideoGenerationLoader } from '@/components/ui/compact-video-generation-loader';
import { useChat, ChatAction } from '@/context/ChatContext';

interface ChatInterfaceProps {
  videoId: string;
  onVideoUpdate?: (updates: Record<string, unknown>) => void;
}

export function ChatInterface({ videoId, onVideoUpdate }: ChatInterfaceProps) {
  // Use the global chat context
  const { 
    messages, 
    sendMessage: contextSendMessage, 
    executeAction: contextExecuteAction,
    isProcessing,
    activeGeneration
  } = useChat();
  
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Video generation state for UI display
  const generationSteps = [
    { id: "analyze", label: "Analyzing prompt", icon: "transcript" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "images", label: "Creating visuals", icon: "video" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "audio", label: "Generating audio", icon: "audio" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "music", label: "Creating background music", icon: "music" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 },
    { id: "assembly", label: "Assembling video", icon: "video" as const, status: "pending" as "pending" | "processing" | "completed" | "error", progress: 0 }
  ];
  
  // Scroll to bottom of messages when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Update steps based on activeGeneration
  const updatedSteps = [...generationSteps];
  if (activeGeneration) {
    const progress = activeGeneration.progress || 0;
    
    // Map progress to steps (simplified version)
    if (progress < 20) {
      updatedSteps[0].status = 'processing';
      updatedSteps[0].progress = progress * 5;
    } else if (progress < 40) {
      updatedSteps[0].status = 'completed';
      updatedSteps[0].progress = 100;
      updatedSteps[1].status = 'processing';
      updatedSteps[1].progress = (progress - 20) * 5;
    } else if (progress < 60) {
      updatedSteps[0].status = 'completed';
      updatedSteps[0].progress = 100;
      updatedSteps[1].status = 'completed';
      updatedSteps[1].progress = 100;
      updatedSteps[2].status = 'processing';
      updatedSteps[2].progress = (progress - 40) * 5;
    } else if (progress < 80) {
      updatedSteps[0].status = 'completed';
      updatedSteps[0].progress = 100;
      updatedSteps[1].status = 'completed';
      updatedSteps[1].progress = 100;
      updatedSteps[2].status = 'completed';
      updatedSteps[2].progress = 100;
      updatedSteps[3].status = 'processing';
      updatedSteps[3].progress = (progress - 60) * 5;
    } else {
      updatedSteps[0].status = 'completed';
      updatedSteps[0].progress = 100;
      updatedSteps[1].status = 'completed';
      updatedSteps[1].progress = 100;
      updatedSteps[2].status = 'completed';
      updatedSteps[2].progress = 100;
      updatedSteps[3].status = 'completed';
      updatedSteps[3].progress = 100;
      updatedSteps[4].status = 'processing';
      updatedSteps[4].progress = (progress - 80) * 5;
    }
    
    // Update parent component if there are video updates
    if (activeGeneration.videoUrl && onVideoUpdate) {
      onVideoUpdate({ video_url: activeGeneration.videoUrl });
    }
  }
  
  // Send message to AI agent using WebSocket
  const handleSendMessage = async () => {
    if (!input.trim() || isProcessing) return;
    
    // Store the input and clear it immediately for better UX
    const messageText = input;
    setInput('');
    
    // Check if this is a video generation request
    const lowerInput = messageText.toLowerCase();
    if (
      lowerInput.includes('generate video') || 
      lowerInput.includes('create video') || 
      lowerInput.includes('make a video') ||
      lowerInput.includes('produce video')
    ) {
      // This is a video generation request
      await startVideoGeneration(messageText);
      return;
    }
    
    // Send the message using the context method
    await contextSendMessage(messageText, { video_id: videoId });
  };
  
  // Handle action button click using WebSocket
  const handleActionClick = async (action: ChatAction) => {
    // Execute the action using the context method
    await contextExecuteAction(action, { video_id: videoId });
  };
  
  // Start a video generation using WebSocket
  const startVideoGeneration = async (prompt: string) => {
    // Execute the generate_video action
    await contextExecuteAction({
      type: 'generate_video',
      label: 'Generate Video',
      prompt: prompt
    }, {
      video_id: videoId,
      client_context: {
        current_page: 'chat'
      }
    });
  };
  
  // Format timestamp
  const formatTime = (date?: Date) => {
    if (!date) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  return (
    <div className="flex flex-col h-full border-r bg-background">
      {/* Compact Video Generation Loader for chat interface */}
      <CompactVideoGenerationLoader
        isVisible={!!activeGeneration && activeGeneration.status === 'processing'}
        overallProgress={activeGeneration?.progress || 0}
        steps={updatedSteps}
        message="Generating your video..."
      />
      
      {/* Full screen loader for critical operations */}
      <VideoGenerationLoader 
        isVisible={!!activeGeneration && activeGeneration.status === 'processing' && (activeGeneration.progress || 0) < 10}
        overallProgress={activeGeneration?.progress || 0}
        steps={updatedSteps}
        message="Initializing video generation..."
      />
      <div className="p-2 border-b">
        <h2 className="text-base font-semibold">AI Assistant</h2>
        <p className="text-xs text-muted-foreground">
          Ask me anything about your video project
        </p>
      </div>
      
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-2">
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="flex flex-col max-w-[80%]">
                <div 
                  className={`p-2 rounded-lg ${
                    msg.role === 'user' 
                      ? 'bg-primary text-primary-foreground ml-auto' 
                      : 'bg-muted'
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
                
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
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
      
      <div className="p-2 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            disabled={isProcessing}
            className="flex-1 text-sm py-2"
          />
          <Button
            onClick={handleSendMessage}
            disabled={isProcessing || !input.trim()}
            className="text-xs px-3 py-2"
          >
            {isProcessing ? '...' : 'Send'}
          </Button>
        </div>
      </div>
    </div>
  );
}
