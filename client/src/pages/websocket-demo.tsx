import React from 'react';
import { WebSocketChat } from '../components/websocket-chat';
import { Box, Container, Typography } from '@mui/material';

const WebSocketDemoPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        WebSocket Video Generation Demo
      </Typography>
      
      <Typography variant="body1" paragraph>
        This demo showcases the WebSocket-based video generation system. Enter a prompt below to generate a video.
      </Typography>
      
      <Box sx={{ height: 'calc(100vh - 200px)', mt: 4 }}>
        <WebSocketChat initialPrompt="Create a video about space exploration" />
      </Box>
    </Container>
  );
};

export default WebSocketDemoPage;
