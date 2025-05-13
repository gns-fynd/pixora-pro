import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Button, CircularProgress, Paper, Stack, Divider } from '@mui/material';
import { authClient } from '../../services/auth-client';
import { Prompt, Scene, ScriptResponse } from './types';
import { createWebSocketConnection, fetchSceneBreakdownWs, regenerateSceneWs, generateVideoWs } from './websocket-api-service';

// Define the ChatMessage type
type ChatMessage = {
  role: 'assistant' | 'user' | 'system';
  content: string;
  timestamp: Date;
};

const SceneBreakdownWs: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [taskId] = useState<string>(crypto.randomUUID());
  const [connected, setConnected] = useState<boolean>(false);
  const [prompt, setPrompt] = useState<Prompt>({
    prompt: '',
    style: 'cinematic',
    duration: 60,
    aspectRatio: '16:9'
  });
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [script, setScript] = useState<ScriptResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get auth token
  useEffect(() => {
    const getToken = async () => {
      const authToken = await authClient.getAuthToken();
      setToken(authToken);
    };
    
    getToken();
  }, []);

  // Connect to WebSocket when token is available
  useEffect(() => {
    if (!token) return;

    // Create WebSocket connection
    const ws = createWebSocketConnection(
      token,
      taskId,
      (message) => {
        console.log('WebSocket message received:', message);
      },
      (error) => {
        setError(error);
        setConnected(false);
      },
      () => {
        setConnected(true);
        setMessages(prev => [...prev, {
          role: 'system',
          content: 'Connected to Pixora AI',
          timestamp: new Date()
        }]);
      }
    );
    
    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, taskId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Add a message to the chat
  const addMessage = (message: ChatMessage) => {
    setMessages(prev => [...prev, message]);
  };

  // Handle prompt submission
  const handlePromptSubmit = () => {
    if (!prompt.prompt.trim() || !connected || !wsRef.current) {
      setError('Please enter a prompt and ensure WebSocket is connected');
      return;
    }

    // Add user message to the list
    addMessage({
      role: 'user',
      content: prompt.prompt,
      timestamp: new Date()
    });

    // Set loading state
    setIsLoading(true);
    setError(null);

    // Fetch scene breakdown
    fetchSceneBreakdownWs(
      wsRef.current,
      taskId,
      prompt,
      addMessage,
      (breakdown) => {
        setScenes(breakdown.scenes);
        setScript(breakdown.script);
        setIsLoading(false);
      },
      (error) => {
        setError(error);
        setIsLoading(false);
      }
    );
  };

  // Handle scene regeneration
  const handleRegenerateScene = (sceneId: string) => {
    if (!connected || !wsRef.current || !script) {
      setError('WebSocket not connected or script not available');
      return;
    }

    // Set loading state
    setIsLoading(true);
    setError(null);

    // Regenerate scene
    regenerateSceneWs(
      wsRef.current,
      taskId,
      sceneId,
      prompt,
      script.title,
      addMessage,
      (scene) => {
        // Update the scene in the scenes array
        setScenes(prev => prev.map(s => s.id === sceneId ? scene : s));
        setIsLoading(false);
      },
      (error) => {
        setError(error);
        setIsLoading(false);
      }
    );
  };

  // Handle video generation
  const handleGenerateVideo = () => {
    if (!connected || !wsRef.current || scenes.length === 0) {
      setError('WebSocket not connected or no scenes available');
      return;
    }

    // Set loading state
    setIsLoading(true);
    setError(null);

    // Generate video
    generateVideoWs(
      wsRef.current,
      taskId,
      prompt,
      scenes,
      addMessage,
      (videoUrl) => {
        setVideoUrl(videoUrl);
        setIsLoading(false);
      },
      (error) => {
        setError(error);
        setIsLoading(false);
      }
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        AI Video Creation
      </Typography>
      
      <Stack direction="row" spacing={3} sx={{ width: '100%' }}>
        {/* Left side - Chat and Input */}
        <Box sx={{ width: { xs: '100%', md: '50%' } }}>
          <Paper elevation={3} sx={{ p: 2, height: '70vh', display: 'flex', flexDirection: 'column' }}>
            {/* Status display */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color={connected ? 'success.main' : 'error.main'}>
                {connected ? 'Connected to AI' : 'Disconnected'}
              </Typography>
              {error && (
                <Typography color="error" variant="body2">
                  Error: {error}
                </Typography>
              )}
            </Box>
            
            {/* Messages display */}
            <Box sx={{ flexGrow: 1, overflow: 'auto', mb: 2 }}>
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
                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '80%',
                    wordBreak: 'break-word'
                  }}
                >
                  <Typography variant="body1">{msg.content}</Typography>
                  {msg.timestamp && (
                    <Typography variant="caption" sx={{ display: 'block', mt: 0.5, opacity: 0.7 }}>
                      {msg.timestamp.toLocaleTimeString()}
                    </Typography>
                  )}
                </Box>
              ))}
              <div ref={messagesEndRef} />
            </Box>
            
            {/* Input area */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <textarea
                value={prompt.prompt}
                onChange={(e) => setPrompt({ ...prompt, prompt: e.target.value })}
                placeholder="Enter your video prompt..."
                style={{ 
                  width: '100%', 
                  padding: '10px',
                  minHeight: '100px',
                  borderRadius: '4px',
                  border: '1px solid #ccc'
                }}
                disabled={isLoading}
              />
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button 
                  variant="contained" 
                  color="primary" 
                  onClick={handlePromptSubmit}
                  disabled={!connected || isLoading || !prompt.prompt.trim()}
                >
                  {isLoading ? <CircularProgress size={24} /> : 'Generate Scene Breakdown'}
                </Button>
                
                <Button 
                  variant="contained" 
                  color="secondary" 
                  onClick={handleGenerateVideo}
                  disabled={!connected || isLoading || scenes.length === 0}
                >
                  Generate Video
                </Button>
              </Box>
            </Box>
          </Paper>
        </Box>
        
        {/* Right side - Scene Breakdown and Video */}
        <Box sx={{ width: { xs: '100%', md: '50%' } }}>
          <Paper elevation={3} sx={{ p: 2, height: '70vh', overflow: 'auto' }}>
            {script && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="h5" gutterBottom>
                  {script.title}
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {script.description}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Style: {script.style}
                </Typography>
                <Divider sx={{ my: 2 }} />
              </Box>
            )}
            
            {scenes.length > 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Scene Breakdown
                </Typography>
                
                {scenes.map((scene, index) => (
                  <Paper key={scene.id} sx={{ p: 2, mb: 2, position: 'relative' }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Scene {index + 1}
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Visual:</strong> {scene.visual}
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Narration:</strong> {scene.narration}
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <strong>Duration:</strong> {scene.duration}s
                    </Typography>
                    
                    <Button 
                      variant="outlined" 
                      size="small" 
                      onClick={() => handleRegenerateScene(scene.id)}
                      disabled={isLoading}
                      sx={{ mt: 1 }}
                    >
                      Regenerate Scene
                    </Button>
                  </Paper>
                ))}
              </Box>
            )}
            
            {videoUrl && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Generated Video
                </Typography>
                <video 
                  controls 
                  width="100%" 
                  src={videoUrl}
                  poster="https://via.placeholder.com/640x360?text=Video+Loading"
                />
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <a href={videoUrl} target="_blank" rel="noopener noreferrer">
                    Open video in new tab
                  </a>
                </Typography>
              </Box>
            )}
          </Paper>
        </Box>
      </Stack>
    </Box>
  );
};

export default SceneBreakdownWs;
