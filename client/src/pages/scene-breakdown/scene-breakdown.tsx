import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/button';
import { IconArrowRight, IconEdit, IconRefresh, IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import { SplitScreenLayout } from '@/components/layouts/SplitScreenLayout';
import { useChat, ChatMessage } from '@/context/ChatContext';
import { Loader } from '@/components/ui/loader';
import { PageTransition } from '@/components/ui/page-transition';
import { Scene, Prompt } from './types';
import { handleError as globalHandleError } from '@/utils/error-handler';
import { convertToSceneBreakdownFormat, getPromptData } from '@/data/dummy-data';

/**
 * SceneBreakdown component
 * 
 * This component displays the scene breakdown for a video prompt.
 * It uses the ChatContext to communicate with the agent and
 * displays the scenes extracted from the chat messages.
 */
export default function SceneBreakdown() {
  const navigate = useNavigate();
  const { messages, addMessage, sendMessage, executeAction, isProcessing, authInitialized, authError, clearMessages } = useChat();

  // Local UI state
  const [error, setError] = useState<string | null>(null);
  const [expandedSceneId, setExpandedSceneId] = useState<string | null>(null);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);

  // Use our dummy data instead of extracting from messages
  const { scenes, script } = useMemo(() => {
    return convertToSceneBreakdownFormat();
  }, []);
  const prompt = useMemo(() => getPromptData(), []);

  // Set the first scene as expanded when scenes are loaded
  useEffect(() => {
    if (scenes && Array.isArray(scenes) && scenes.length > 0 && !expandedSceneId) {
      setExpandedSceneId(scenes[0].id);
    }
  }, [scenes, expandedSceneId]);

  // State-based request tracking
  const [requestState, setRequestState] = useState<{
    attempted: boolean;
    inProgress: boolean;
    completed: boolean;
  }>({
    attempted: false,
    inProgress: false,
    completed: false
  });

  // Reset request state when component unmounts
  useEffect(() => {
    return () => {
      setRequestState({
        attempted: false,
        inProgress: false,
        completed: false
      });
    };
  }, []);



  // No longer need a ref for tracking initialization since we use localStorage

  // Clear messages and control message flow when component mounts
  useEffect(() => {
    // Skip if not authenticated yet
    if (!authInitialized || !prompt) {
      return;
    }

    // Check if we've already initialized this session
    const sessionInitialized = localStorage.getItem('pixora_session_initialized');
    if (sessionInitialized === 'true') {
      console.log('Session already initialized, skipping message setup');
      return;
    }

    // Clear existing messages
    console.log('Clearing existing messages and setting up controlled message flow');
    
    // Set session as initialized to prevent duplicate initialization
    localStorage.setItem('pixora_session_initialized', 'true');
    
    // Clear messages
    clearMessages();
    
    // Add user prompt as first message
    addMessage({
      role: 'user',
      content: prompt.prompt,
      timestamp: new Date(Date.now() - 2000)
    });
    
    // Add analyzing message
    addMessage({
      role: 'assistant',
      content: "I'm analyzing your prompt to break it down into scenes. This will help us create a well-structured video.",
      timestamp: new Date(Date.now() - 1000)
    });
    
    // Start scene breakdown generation if we don't already have scenes
    if (!scenes || !Array.isArray(scenes) || scenes.length === 0 && !requestState.inProgress && !isProcessing) {
      fetchSceneBreakdown();
    }
  }, [authInitialized, prompt, clearMessages, addMessage]);

  // Mock function to fetch scene breakdown - just sets the state
  const fetchSceneBreakdown = async () => {
    // Set request state to simulate loading
    setRequestState({
      attempted: true,
      inProgress: true,
      completed: false
    });

    // Store prompt in localStorage
    localStorage.setItem('pixora_prompt', JSON.stringify(prompt));
    
    // Simulate API delay
    setTimeout(() => {
      // Update request state
      setRequestState({
        attempted: true,
        inProgress: false,
        completed: true
      });
    }, 1000);
  };

  // Toggle scene expansion
  const handleToggleExpansion = (sceneId: string) => {
    setExpandedSceneId(expandedSceneId === sceneId ? null : sceneId);
  };

  // Regenerate a scene
  const handleRegenerateScene = (sceneId: string) => {
    if (!prompt || !script) {
      setError('Missing required data');
      return;
    }

    try {
      // Find the scene index
      const sceneIndex = Array.isArray(scenes) ? scenes.findIndex((s: Scene) => s.id === sceneId) : -1;
      if (sceneIndex === -1) {
        setError('Scene not found');
        return;
      }

      // Execute the regenerate action
      executeAction({
        type: 'regenerate_scene',
        label: 'Regenerate Scene',
        scene_id: sceneId
      }, {
        prompt: prompt.prompt,
        script_title: script.title
      });
    } catch (err) {
      handleComponentError(err);
    }
  };

  // Handle scene edit (placeholder function)
  const handleEditScene = (sceneId: string) => {
    // In a real implementation, this would open a modal to edit the scene
    console.log(`Editing scene ${sceneId}`);

    // For now, just alert the user
    alert(`This would open an editor for scene ${sceneId}`);
  };

  // State for page transition
  const [showTransition, setShowTransition] = useState(false);

  // Generate video - simplified to just navigate to generation page
  const handleGenerateVideo = async () => {
    if (!prompt || !scenes || !Array.isArray(scenes) || scenes.length === 0) {
      setError('Missing required data');
      return;
    }

    setIsGeneratingVideo(true);

    try {
      // Add message about starting video generation
      addMessage({
        role: 'user',
        content: 'Generate the video with these scenes',
        timestamp: new Date()
      });

      // Add message about the process
      addMessage(createVideoGenerationMessage());

      // Store the scenes and prompt in localStorage for the generation page
      localStorage.setItem('pixora_scenes', JSON.stringify({ scenes }));
      localStorage.setItem('pixora_script', JSON.stringify(script));
      localStorage.setItem('pixora_prompt', JSON.stringify(prompt));
      
      // Generate a random task ID
      const taskId = crypto.randomUUID();
      localStorage.setItem('pixora_task_id', taskId);

      // Show transition before navigating
      setShowTransition(true);
    } catch (err) {
      handleComponentError(err);
      setIsGeneratingVideo(false);
    }
  };

  // Handle transition completion
  const handleTransitionComplete = () => {
    // Navigate to the generation page
    navigate('/generation');
  };

  // Handle regenerate all scenes
  const handleRegenerateAll = () => {
    if (!prompt) {
      setError('No prompt data found');
      return;
    }

    try {
      // Clear localStorage to force a fresh API call
      localStorage.removeItem('pixora_script');
      localStorage.removeItem('pixora_scenes');

      // Reset request state
      setRequestState({
        attempted: false,
        inProgress: false,
        completed: false
      });

      // Add loading message
      addMessage(createLoadingMessage());

      // Mark as in progress
      setRequestState({
        attempted: true,
        inProgress: true,
        completed: false
      });

      // Send message to generate scene breakdown
      sendMessage('Regenerate scene breakdown for my video', {
        prompt: prompt.prompt,
        style: prompt.style || 'cinematic',
        duration: prompt.duration || 60,
        aspect_ratio: prompt.aspectRatio || '16:9'
      }).then(() => {
        // Mark as completed
        setRequestState({
          attempted: true,
          inProgress: false,
          completed: true
        });
      }).catch((err) => {
        // Handle error
        handleComponentError(err);

        // Reset request state
        setRequestState({
          attempted: false,
          inProgress: false,
          completed: false
        });
      });
    } catch (err) {
      handleComponentError(err);

      // Reset request state
      setRequestState({
        attempted: false,
        inProgress: false,
        completed: false
      });
    }
  };

  // Create a component-specific error handler
  const handleComponentError = (error: unknown) => {
    return globalHandleError(error, (message) => {
      console.error('Error in SceneBreakdown:', error);
      setError(message);
    });
  };

  // Show auth error if not authenticated
  if (!authInitialized) {
    return (
      <SplitScreenLayout videoId="scene-breakdown">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            {authError ? (
              <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 mb-6 text-red-500">
                <h3 className="font-semibold mb-1">Authentication Error</h3>
                <p>{authError}</p>
                <Button
                  onClick={() => window.location.href = '/auth/login'}
                  className="mt-4"
                >
                  Return to Login
                </Button>
              </div>
            ) : (
              <>
                <Loader
                  autoAnimate={true}
                  message="Connecting to server..."
                />
                <h2 className="text-xl font-semibold mt-6 mb-2">Initializing connection</h2>
              </>
            )}
          </div>
        </div>
      </SplitScreenLayout>
    );
  }

  // Show loading view if processing and no scenes
  if (isProcessing && (!scenes || !Array.isArray(scenes) || scenes.length === 0)) {
    return (
      <SplitScreenLayout videoId="scene-breakdown">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <Loader
              autoAnimate={true}
              message="Breaking down your video into scenes..."
            />
            <h2 className="text-xl font-semibold mt-6 mb-2">Analyzing your prompt</h2>
          </div>
        </div>
      </SplitScreenLayout>
    );
  }

  // Show debug view if we have messages but no scenes were extracted
  if (messages.length > 0 && (!scenes || !Array.isArray(scenes) || scenes.length === 0) && !isProcessing) {
    // Get the last few assistant messages
    const assistantMessages = messages
      .filter(m => m.role === 'assistant')
      .slice(-3);

    return (
      <SplitScreenLayout videoId="scene-breakdown">
        <div className="p-6">
          <div className="glass-morphism rounded-2xl p-6 mb-8">
            <h1 className="text-2xl font-bold mb-4">Debug: Scene Extraction Failed</h1>
            <p className="text-muted-foreground mb-4">
              Messages were received but no scenes could be extracted. Here are the last few messages:
            </p>
            {assistantMessages.map((message, idx) => (
              <div key={idx} className="bg-white/5 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-medium mb-2">Message {idx + 1}:</h3>
                <pre className="text-xs overflow-auto max-h-60 p-2 bg-black/20 rounded">
                  {message.content}
                </pre>
              </div>
            ))}
            <Button
              onClick={handleRegenerateAll}
              className="bg-yellow-500 hover:bg-yellow-600 text-white"
            >
              Regenerate Scene Breakdown
            </Button>
          </div>
        </div>
      </SplitScreenLayout>
    );
  }

  // Render main content
  return (
    <React.Fragment>
      {/* Page transition overlay */}
      {showTransition && (
        <PageTransition 
          duration={5000} 
          message="Preparing your video generation..." 
          onComplete={handleTransitionComplete}
        />
      )}
      
      <SplitScreenLayout videoId="scene-breakdown">
        <div className="p-6">
        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 mb-6 text-red-500">
            <h3 className="font-semibold mb-1">Error</h3>
            <p>{error}</p>
          </div>
        )}

        {/* Prompt summary */}
        <div className="glass-morphism rounded-2xl p-6 mb-8">
          <h1 className="text-2xl font-bold mb-4">Your Video Breakdown</h1>
          {prompt && (
            <div className="mb-4">
              <p className="text-lg font-medium mb-2">Original Prompt:</p>
              <p className="text-muted-foreground">{prompt.prompt}</p>
              <div className="flex flex-wrap gap-4 mt-4">
                <div className="bg-white/5 rounded-full px-4 py-1 text-sm">
                  {prompt.aspectRatio} aspect ratio
                </div>
                <div className="bg-white/5 rounded-full px-4 py-1 text-sm">
                  {prompt.duration} seconds
                </div>
                <div className="bg-white/5 rounded-full px-4 py-1 text-sm capitalize">
                  {prompt.style} style
                </div>
              </div>
            </div>
          )}
          <p className="text-muted-foreground">
            We've analyzed your prompt and broken it down into the following scenes. You can edit or regenerate any scene before proceeding to video generation.
          </p>

          {/* Manual regenerate button */}
          {scenes.length === 0 && (
            <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <p className="text-sm text-yellow-500 mb-2">No scenes found. Try regenerating the scene breakdown.</p>
              <Button
                onClick={handleRegenerateAll}
                className="bg-yellow-500 hover:bg-yellow-600 text-white"
              >
                Regenerate Scene Breakdown
              </Button>
            </div>
          )}
        </div>

        {/* Scene list */}
        <div className="space-y-4">
          {Array.isArray(scenes) && scenes.map((scene: Scene, index: number) => (
            <SceneItem
              key={scene.id}
              scene={scene}
              index={index}
              isExpanded={expandedSceneId === scene.id}
              prompt={prompt}
              onToggleExpansion={() => handleToggleExpansion(scene.id)}
              onRegenerate={handleRegenerateScene}
              onEdit={handleEditScene}
            />
          ))}
        </div>

        {/* Action buttons */}
        {scenes && Array.isArray(scenes) && scenes.length > 0 && (
          <div className="mt-8 flex justify-end">
            <Button
              onClick={handleGenerateVideo}
              className="px-6 py-2 flex items-center gap-2"
              disabled={isGeneratingVideo || isProcessing}
              variant="primary"
            >
              {isGeneratingVideo ? (
                <>
                  <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                  Generating...
                </>
              ) : (
                <>
                  Generate Video
                  <IconArrowRight size={18} />
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </SplitScreenLayout>
  </React.Fragment>
);
}

// ===== INLINED COMPONENTS =====

interface SceneItemProps {
  scene: Scene;
  index: number;
  isExpanded: boolean;
  prompt?: Prompt | null;
  onToggleExpansion: () => void;
  onRegenerate: (sceneId: string) => void;
  onEdit?: (sceneId: string) => void;
}

/**
 * SceneItem component displays a single scene in the scene breakdown
 */
function SceneItem({
  scene,
  index,
  isExpanded,
  prompt,
  onToggleExpansion,
  onRegenerate,
  onEdit
}: SceneItemProps) {
  return (
    <div className="glass-morphism rounded-2xl overflow-hidden">
      {/* Scene header - always visible */}
      <div
        className={`p-4 flex justify-between items-center cursor-pointer transition-colors ${isExpanded ? 'bg-white/5' : 'hover:bg-white/5'
          }`}
        onClick={onToggleExpansion}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center h-8 w-8 rounded-full bg-primary/20 text-primary font-medium">
            {index + 1}
          </div>
          <h2 className="text-xl font-semibold">Scene {index + 1}</h2>
          <div className="hidden sm:flex items-center gap-1 text-sm text-muted-foreground">
            <span className="inline-block h-2 w-2 rounded-full bg-primary/60"></span>
            <span>{scene.duration}s</span>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-sm text-muted-foreground sm:hidden">{scene.duration}s</span>
          {onEdit && (
            <Button
              variant="simple"
              className="p-2 h-9 w-9 flex items-center justify-center"
              onClick={(e: React.MouseEvent) => {
                e.stopPropagation();
                onEdit(scene.id);
              }}
              title="Edit scene"
            >
              <IconEdit size={18} />
            </Button>
          )}
          <Button
            variant="simple"
            className="p-2 h-9 w-9 flex items-center justify-center"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              onRegenerate(scene.id);
            }}
            title="Regenerate scene"
          >
            <IconRefresh size={18} />
          </Button>
          <div className="h-9 w-9 flex items-center justify-center text-muted-foreground">
            {isExpanded ? (
              <IconChevronUp size={18} />
            ) : (
              <IconChevronDown size={18} />
            )}
          </div>
        </div>
      </div>

      {/* Scene content - only visible when expanded */}
      {isExpanded && (
        <div className="p-6 pt-0 border-t border-white/10">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-5 w-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <span className="text-blue-500 text-xs">V</span>
                </div>
                <h3 className="text-sm font-medium">Visual Description</h3>
              </div>
              <div className="bg-white/5 rounded-lg p-4 mb-4">
                <p className="text-sm text-muted-foreground">{scene.visual}</p>
              </div>

              {/* Image preview placeholder */}
              <div className="mt-4 aspect-video bg-black/30 rounded-lg flex items-center justify-center overflow-hidden border border-white/10">
                {scene.image_url ? (
                  <img
                    src={scene.image_url}
                    alt={`Scene ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-center p-4">
                    <svg className="mx-auto h-12 w-12 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="mt-2 text-sm text-muted-foreground">Image will be generated during video creation</p>
                  </div>
                )}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-5 w-5 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <span className="text-purple-500 text-xs">A</span>
                </div>
                <h3 className="text-sm font-medium">Narration</h3>
              </div>
              <div className="bg-white/5 rounded-lg p-4 mb-4">
                <p className="text-sm text-muted-foreground">{scene.audio}</p>
              </div>
              
              {/* Character information if available */}
              {scene.character && (
                <div className="mt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-5 w-5 rounded-full bg-yellow-500/20 flex items-center justify-center">
                      <span className="text-yellow-500 text-xs">C</span>
                    </div>
                    <h3 className="text-sm font-medium">Character</h3>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4 mb-4">
                    <p className="text-sm font-medium">{scene.character.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">{scene.character.description}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 mb-3 mt-6">
                <div className="h-5 w-5 rounded-full bg-green-500/20 flex items-center justify-center">
                  <span className="text-green-500 text-xs">M</span>
                </div>
                <h3 className="text-sm font-medium">Background Music</h3>
              </div>
              <div className="bg-white/5 rounded-lg p-4 flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center">
                  <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm">Ambient soundtrack</p>
                  <p className="text-xs text-muted-foreground">Selected based on video style</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-white/5 rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 rounded-full bg-amber-500/20 flex items-center justify-center">
                <span className="text-amber-500 text-xs">T</span>
              </div>
              <h3 className="text-sm font-medium">Duration</h3>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-16 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full"
                  style={{ width: `${(scene.duration / (prompt?.duration || 30)) * 100}%` }}
                ></div>
              </div>
              <p className="text-sm font-medium">{scene.duration} seconds</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ===== INLINED UTILITY FUNCTIONS =====


/**
 * Create a loading message for the scene breakdown process
 */
function createLoadingMessage(): ChatMessage {
  return {
    role: 'assistant',
    content: "I'm analyzing your prompt to break it down into scenes. This will help us create a well-structured video.",
    timestamp: new Date()
  };
}

/**
 * Create a video generation message
 */
function createVideoGenerationMessage(): ChatMessage {
  return {
    role: 'assistant',
    content: "I'm starting the video generation process now. This will take a few minutes, but you can chat with me while you wait.",
    timestamp: new Date()
  };
}
