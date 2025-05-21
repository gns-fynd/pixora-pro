import React from 'react';
import { Typography, Paper, Box, Button } from '@mui/material';

interface VideoResult {
  video_url?: string;
  thumbnail_url?: string;
  message?: string;
}

interface WebSocketChatProps {
  taskId?: string;
  initialPrompt?: string;
  onComplete?: (result: VideoResult) => void;
}

/**
 * @deprecated This component is deprecated. Please use the ChatContext from '@/context/ChatContext' instead.
 * 
 * Example:
 * ```tsx
 * import { useChat } from '@/context/ChatContext';
 * 
 * function MyComponent() {
 *   const { messages, sendMessage, isProcessing } = useChat();
 *   
 *   // Use the chat context for WebSocket communication
 *   const handleSendMessage = () => {
 *     sendMessage('My message');
 *   };
 *   
 *   return (
 *     // Your component JSX
 *   );
 * }
 * ```
 */
const WebSocketChat: React.FC<WebSocketChatProps> = () => {
  return (
    <Paper elevation={3} sx={{ p: 4, bgcolor: '#fff8e1' }}>
      <Typography variant="h5" color="error" gutterBottom>
        Deprecated Component
      </Typography>
      
      <Typography variant="body1" paragraph>
        This WebSocketChat component is deprecated and will be removed in a future release.
        Please use the ChatContext from '@/context/ChatContext' instead.
      </Typography>
      
      <Box sx={{ mt: 2 }}>
        <Button 
          variant="contained" 
          color="primary"
          onClick={() => window.location.href = '/websocket-demo'}
        >
          See Updated Demo
        </Button>
      </Box>
    </Paper>
  );
};

export default WebSocketChat;

// Also export a named export for compatibility
export { WebSocketChat };
