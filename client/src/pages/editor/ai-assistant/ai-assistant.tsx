import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";
import { ChatInterface } from "@/components/ai-chat/ChatInterface";

export const AIAssistant = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  // Use a fixed video ID for now - in a real implementation, this would come from the editor state
  const videoId = 'current_editor_video';
  
  // Handle video updates from the AI assistant
  const handleVideoUpdate = (updates: Record<string, unknown>) => {
    console.log('Video updates received:', updates);
    // Here we would update the video in the editor
    // This would involve dispatching events to the editor's state manager
  };

  if (isCollapsed) {
    return (
      <div className="h-full glass-morphism">
        <div className="flex h-full flex-col">
          <Button
            variant="ghost"
            className="h-12 w-12 rounded-none text-primary hover:text-primary/80"
            onClick={() => setIsCollapsed(false)}
          >
            <ChevronLeft size={20} />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full glass-morphism">
      <div className="flex h-full flex-col">
        <div className="flex h-14 items-center justify-between border-b border-border/20 px-4">
          <h2 className="text-base font-medium text-primary">AI Assistant</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(true)}
            className="text-foreground/70 hover:text-foreground"
          >
            <ChevronLeft size={18} />
          </Button>
        </div>

        <div className="flex-1">
          <ChatInterface 
            videoId={videoId} 
            onVideoUpdate={handleVideoUpdate} 
          />
        </div>
      </div>
    </div>
  );
};
