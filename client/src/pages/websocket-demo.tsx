import React from 'react';
import { useChat } from '../context/ChatContext';
import { Button, Container, Typography, Box, Paper } from '@mui/material';
import { SplitScreenLayout } from '@/components/layouts/SplitScreenLayout';

/**
 * WebSocket Demo Page
 * 
 * This demo showcases the WebSocket-based video generation system using the unified ChatContext.
 * It demonstrates how to use the ChatContext for WebSocket communication.
 */
const WebSocketDemoPage: React.FC = () => {
  const { 
    messages, 
    sendMessage, 
    isProcessing, 
    activeGeneration,
    authInitialized,
    authError
  } = useChat();

  // Handle sending a demo message
  const handleSendDemoMessage = () => {
    sendMessage('Create a video about space exploration', {
      style: 'cinematic',
      duration: 60,
      aspect_ratio: '16:9'
    });
  };

  // Show auth error if not authenticated
  if (!authInitialized) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
          {authError ? (
            <>
              <Typography variant="h5" color="error" gutterBottom>
                Authentication Error
              </Typography>
              <Typography variant="body1" paragraph>
                {authError}
              </Typography>
              <Button 
                variant="contained" 
                color="primary"
                onClick={() => window.location.href = '/auth/login'}
              >
                Return to Login
              </Button>
            </>
          ) : (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 rounded-full border-t-transparent"></div>
              </Box>
              <Typography variant="h5" gutterBottom>
                Connecting to server...
              </Typography>
              <Typography variant="body1">
                Please wait while we establish a connection.
              </Typography>
            </>
          )}
        </Paper>
      </Container>
    );
  }

  return (
    <SplitScreenLayout videoId="websocket-demo">
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          WebSocket Video Generation Demo
        </Typography>
        
        <Typography variant="body1" paragraph>
          This demo showcases the WebSocket-based video generation system using the unified ChatContext.
          Click the button below to generate a video about space exploration.
        </Typography>
        
        <Button 
          variant="contained" 
          color="primary" 
          onClick={handleSendDemoMessage}
          disabled={isProcessing}
          sx={{ mb: 4 }}
        >
          {isProcessing ? 'Processing...' : 'Generate Space Video'}
        </Button>
        
        {/* Messages display */}
        <Paper elevation={3} sx={{ p: 2, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Chat Messages
          </Typography>
          
          <Box sx={{ maxHeight: '400px', overflow: 'auto', mb: 2 }}>
            {messages.map((msg, index) => (
              <Box 
                key={index} 
                sx={{ 
                  mb: 1, 
                  p: 1, 
                  borderRadius: 1,
                  backgroundColor: msg.role === 'user' ? 'primary.light' : 
                                  msg.role === 'assistant' ? 'background.paper' : 'grey.100',
                  color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                }}
              >
                <Typography variant="subtitle2">
                  {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Assistant' : 'System'}
                </Typography>
                <Typography variant="body1">{msg.content}</Typography>
                <Typography variant="caption" sx={{ display: 'block', mt: 0.5, opacity: 0.7 }}>
                  {msg.timestamp.toLocaleTimeString()}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
        
        {/* Generation progress */}
        {activeGeneration && (
          <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Generation Progress
            </Typography>
            
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" gutterBottom>
                Status: {activeGeneration.status}
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Box sx={{ width: '100%', mr: 1 }}>
                  <div 
                    style={{ 
                      height: '8px', 
                      width: `${activeGeneration.progress}%`, 
                      backgroundColor: '#3f51b5',
                      borderRadius: '4px'
                    }} 
                  />
                </Box>
                <Typography variant="body2">
                  {Math.round(activeGeneration.progress)}%
                </Typography>
              </Box>
              
              {activeGeneration.message && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {activeGeneration.message}
                </Typography>
              )}
            </Box>
            
            {activeGeneration.videoUrl && (
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Generated Video
                </Typography>
                <video 
                  controls 
                  src={activeGeneration.videoUrl} 
                  style={{ width: '100%', maxHeight: '300px' }}
                />
              </Box>
            )}
          </Paper>
        )}
      </Container>
    </SplitScreenLayout>
  );
};

export default WebSocketDemoPage;
