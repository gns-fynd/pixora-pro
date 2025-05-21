import React, { useEffect, useRef } from 'react';
import { ChatInterface } from '@/components/ai-chat/ChatInterface';
import { ThemeToggle } from '@/components/shared/ThemeToggle';

interface SplitScreenLayoutProps {
  videoId: string;
  children: React.ReactNode;
  onVideoUpdate?: (updates: Record<string, unknown>) => void;
}

export function SplitScreenLayout({ videoId, children, onVideoUpdate }: SplitScreenLayoutProps) {
  // Reference to the chat container to ensure it's always scrolled to show the input
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Ensure chat input is visible when the component mounts or updates
  useEffect(() => {
    // Scroll to the bottom of the chat container to ensure input is visible
    if (chatContainerRef.current) {
      const chatContainer = chatContainerRef.current;
      // Use a small timeout to ensure the DOM has fully rendered
      setTimeout(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }, 100);
    }
  }, []);

  return (
    <div className="flex h-screen bg-background">
      {/* Left side - Chat Interface (1/3 width) */}
      <div 
        className="w-1/3 border-r border-border/20 h-screen flex flex-col"
      >
        {/* Theme toggle in top-right corner of left panel */}
        <div className="absolute top-4 right-4 z-10">
          <ThemeToggle />
        </div>
        {/* Chat interface fills the column, input always visible */}
        <div className="flex flex-col flex-1 min-h-0">
          <ChatInterface videoId={videoId} onVideoUpdate={onVideoUpdate} />
        </div>
      </div>
      
      {/* Right side - Content (2/3 width) */}
      <div className="w-2/3 h-screen overflow-auto">
        {children}
      </div>
    </div>
  );
}
