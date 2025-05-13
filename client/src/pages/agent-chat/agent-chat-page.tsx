import { AgentChat } from '@/components/ai-chat';

/**
 * Agent Chat Page
 * 
 * This page demonstrates the agent chat functionality.
 */
export function AgentChatPage() {
  const handleComplete = (result: Record<string, unknown>) => {
    console.log('Task completed:', result);
  };
  
  return (
    <div className="flex flex-col h-screen">
      <header className="bg-gray-800 text-white p-4">
        <h1 className="text-xl font-bold">Pixora AI Agent</h1>
        <p className="text-sm opacity-75">Ask me anything about video creation</p>
      </header>
      
      <main className="flex-1 overflow-hidden">
        <AgentChat 
          className="h-full"
          onComplete={handleComplete}
        />
      </main>
    </div>
  );
}
