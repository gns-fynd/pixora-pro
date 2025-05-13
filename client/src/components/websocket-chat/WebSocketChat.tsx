import React, { useState, useEffect, useRef } from 'react';
import { Button, TextField, Paper, Typography, Box, CircularProgress, Divider } from '@mui/material';
import useAuthStore from '../../store/use-auth-store';
import { authClient } from '../../services/auth-client';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
}

interface Scene {
  index: number;
  title: string;
  script: string;
  video_prompt: string;
  duration: number;
  transition?: string;
}

interface SceneBreakdown {
  scenes: Scene[];
  style: string;
  mood: string;
  transitions: Array<{
    from: number;
    to: number;
    type: string;
    duration: number;
  }>;
  estimated_duration: number;
}

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

const WebSocketChat: React.FC<WebSocketChatProps> = ({ 
  taskId: propTaskId, 
  initialPrompt,
  onComplete 
}) => {
  const { isAuthenticated } = useAuthStore();
  const [token, setToken] = useState<string | null>(null);
  const [taskId] = useState<string>(propTaskId || crypto.randomUUID());
  const [connected, setConnected] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>(initialPrompt || '');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [sceneBreakdown, setSceneBreakdown] = useState<SceneBreakdown | null>(null);
  const [result, setResult] = useState<VideoResult | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get auth token
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const getToken = async () => {
      const authToken = await authClient.getAuthToken();
      setToken(authToken);
    };
    
    getToken();
  }, [isAuthenticated]);

  // Connect to WebSocket
  useEffect(() => {
    if (!token || !isAuthenticated) return;

    const connectWebSocket = () => {
      // Get WebSocket URL from environment variables or construct it
      const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 
        `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/chat/ws`;
      
      // Append token and task ID as query parameters
      // Make sure to encode the token to avoid URL parsing issues
      const wsUrlWithParams = `${wsUrl}?token=${encodeURIComponent(token)}${taskId ? `&task_id=${encodeURIComponent(taskId)}` : ''}`;
      
      console.log('Connecting to WebSocket with URL:', wsUrlWithParams.split('?')[0]);
      
      const ws = new WebSocket(wsUrlWithParams);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        // Send token for authentication
        ws.send(token);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        if (data.type === 'connected') {
          setConnected(true);
          setMessages(prev => [...prev, {
            role: 'system',
            content: 'Connected to Pixora AI'
          }]);
        } else if (data.type === 'token') {
          // Update the last assistant message with the new token
          setMessages(prev => {
            const lastAssistantIndex = [...prev].reverse().findIndex(m => m.role === 'assistant');
            if (lastAssistantIndex === -1) {
              // No assistant message yet, create a new one
              return [...prev, {
                role: 'assistant',
                content: data.content
              }];
            } else {
              // Update the last assistant message
              const newMessages = [...prev];
              const actualIndex = prev.length - 1 - lastAssistantIndex;
              newMessages[actualIndex] = {
                ...newMessages[actualIndex],
                content: newMessages[actualIndex].content + data.content
              };
              return newMessages;
            }
          });
        } else if (data.type === 'message') {
          setMessages(prev => [...prev, {
            role: data.data.role,
            content: data.data.content,
            timestamp: Date.now()
          }]);
          setIsLoading(false);
        } else if (data.type === 'tool_call') {
          setMessages(prev => [...prev, {
            role: 'system',
            content: `Using tool: ${data.data.tool}`,
            timestamp: Date.now()
          }]);
        } else if (data.type === 'tool_result') {
          // Tool results are usually not displayed directly
          console.log('Tool result:', data.data);
        } else if (data.type === 'progress_update') {
          setProgress(data.data.progress);
          setStatus(data.data.message);
        } else if (data.type === 'scene_breakdown') {
          setSceneBreakdown(data.data);
        } else if (data.type === 'error') {
          setError(data.message);
          setIsLoading(false);
        } else if (data.type === 'completion') {
          setResult(data.data);
          if (onComplete) {
            onComplete(data.data);
          }
          setIsLoading(false);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        // Attempt to reconnect after a delay
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
      };
    };

    connectWebSocket();

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

  // Send a message
  const sendMessage = () => {
    if (!input.trim() || !connected || !wsRef.current) return;

    // Add user message to the list
    setMessages(prev => [...prev, {
      role: 'user',
      content: input,
      timestamp: Date.now()
    }]);

    // Send message to WebSocket using the new format
    wsRef.current.send(JSON.stringify({
      message: input,
      task_id: taskId
    }));

    // Clear input and set loading
    setInput('');
    setIsLoading(true);
    setError(null);
  };

  // Send a command as a message with context
  const sendCommand = (command: string, params: Record<string, unknown> = {}) => {
    if (!connected || !wsRef.current) return;

    // Send command as a message with context
    wsRef.current.send(JSON.stringify({
      message: command,
      task_id: taskId,
      context: params
    }));

    // Set loading
    setIsLoading(true);
    setError(null);
  };

  // Generate scene breakdown
  const generateSceneBreakdown = () => {
    if (!input.trim()) return;

    sendCommand('generate_scene_breakdown', {
      prompt: input,
      style: 'cinematic',
      duration: 60
    });
  };

  // Generate video
  const generateVideo = () => {
    if (!sceneBreakdown) return;

    sendCommand('generate_video');
  };

  // Check generation status
  const checkStatus = () => {
    sendCommand('check_generation_status');
  };

  return (
    <Paper elevation={3} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" gutterBottom>
        Pixora AI Video Generation
      </Typography>
      
      {/* Status display */}
      {(isLoading || progress > 0) && (
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
          <CircularProgress variant={progress > 0 ? "determinate" : "indeterminate"} value={progress} size={24} sx={{ mr: 2 }} />
          <Typography variant="body2">
            {status || 'Processing...'}
            {progress > 0 && ` (${progress}%)`}
          </Typography>
        </Box>
      )}
      
      {/* Error display */}
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          Error: {error}
        </Typography>
      )}
      
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
                {new Date(msg.timestamp).toLocaleTimeString()}
              </Typography>
            )}
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>
      
      {/* Result display */}
      {result && (
        <Box sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'primary.main', borderRadius: 1 }}>
          <Typography variant="h6" gutterBottom>Video Generated!</Typography>
          {result.video_url && (
            <Box sx={{ mb: 1 }}>
              <Typography variant="body2" gutterBottom>Video URL:</Typography>
              <a href={result.video_url} target="_blank" rel="noopener noreferrer">
                {result.video_url}
              </a>
            </Box>
          )}
          {result.message && (
            <Typography variant="body2">{result.message}</Typography>
          )}
        </Box>
      )}
      
      {/* Scene breakdown display */}
      {sceneBreakdown && (
        <Box sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'primary.main', borderRadius: 1 }}>
          <Typography variant="h6" gutterBottom>Scene Breakdown</Typography>
          <Typography variant="body2" gutterBottom>
            Style: {sceneBreakdown.style}, Estimated Duration: {sceneBreakdown.estimated_duration}s
          </Typography>
          
          {sceneBreakdown.scenes.map((scene, index) => (
            <Box key={index} sx={{ mb: 1 }}>
              <Typography variant="subtitle2">
                Scene {scene.index}: {scene.title} ({scene.duration}s)
              </Typography>
              <Typography variant="body2" gutterBottom>
                {scene.script}
              </Typography>
              <Divider sx={{ my: 1 }} />
            </Box>
          ))}
          
          <Button 
            variant="contained" 
            color="primary" 
            onClick={generateVideo}
            disabled={isLoading}
            sx={{ mt: 1 }}
          >
            Generate Video
          </Button>
        </Box>
      )}
      
      {/* Input area */}
      <Box sx={{ display: 'flex', mt: 'auto' }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Enter your prompt..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          disabled={isLoading}
          sx={{ mr: 1 }}
        />
        <Button 
          variant="contained" 
          color="primary" 
          onClick={sendMessage}
          disabled={!connected || isLoading || !input.trim()}
        >
          Send
        </Button>
      </Box>
      
      {/* Action buttons */}
      <Box sx={{ display: 'flex', mt: 2, justifyContent: 'space-between' }}>
        <Button 
          variant="outlined" 
          color="primary" 
          onClick={generateSceneBreakdown}
          disabled={!connected || isLoading || !input.trim()}
        >
          Generate Scene Breakdown
        </Button>
        
        <Button 
          variant="outlined" 
          color="secondary" 
          onClick={checkStatus}
          disabled={!connected || isLoading}
        >
          Check Status
        </Button>
      </Box>
    </Paper>
  );
};

export default WebSocketChat;
