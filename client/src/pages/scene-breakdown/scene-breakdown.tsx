import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/button';
import { IconArrowRight, IconEdit, IconRefresh, IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import { SplitScreenLayout } from '@/components/layouts/SplitScreenLayout';
import { useChat } from '@/context/ChatContext';
import { Loader } from '@/components/ui/loader';
import { Scene, Prompt, ScriptResponse } from './types';
import { fetchSceneBreakdown, regenerateScene, generateVideo } from './api-service';

export default function SceneBreakdown() {
  const navigate = useNavigate();
  const { addMessage } = useChat();
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSceneId, setExpandedSceneId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [script, setScript] = useState<ScriptResponse | null>(null);
  
  // Fetch scene breakdown from the API
  useEffect(() => {
    // Create a flag to track if the component is mounted
    let isMounted = true;
    
    // Create a flag to track if a request is in progress
    // This prevents multiple simultaneous API calls
    let isRequestInProgress = false;
    
    // Check if we already have a script and scenes in localStorage
    const storedScript = localStorage.getItem('pixora_script');
    const storedScenes = localStorage.getItem('pixora_scenes');
    const storedPrompt = localStorage.getItem('pixora_prompt');
    
    // Check if we have all the required data in localStorage
    const hasAllStoredData = storedScript && storedScenes && storedPrompt;
    
    // Check if the stored data is still valid (not expired)
    const storedDataExpiry = localStorage.getItem('pixora_data_expiry');
    const isStoredDataValid = storedDataExpiry && parseInt(storedDataExpiry, 10) > Date.now();
    
    // If we have all stored data and it's still valid, use it instead of making API calls
    if (hasAllStoredData && isStoredDataValid) {
      try {
        console.debug('Using cached scene breakdown data from localStorage');
        
        const scriptData = JSON.parse(storedScript);
        const scenesData = JSON.parse(storedScenes);
        const promptData = JSON.parse(storedPrompt);
        
        if (isMounted) {
          setScript(scriptData);
          // Check if scenesData has a data property (new API structure)
          let scenesArray;
          
          // Try to extract scenes from various possible locations in the response
          if (scenesData.data?.scenes?.scenes) {
            // New structure: data.scenes.scenes
            scenesArray = scenesData.data.scenes.scenes;
          } else if (scenesData.data?.scenes) {
            // New unified API format: data.scenes
            scenesArray = scenesData.data.scenes;
          } else if (scenesData.scenes?.scenes) {
            // Another possible structure: scenes.scenes
            scenesArray = scenesData.scenes.scenes;
          } else if (scenesData.scenes) {
            // Legacy API format: direct scenes array
            scenesArray = scenesData.scenes;
          } else if (scenesData.data?.data?.scenes) {
            // Nested data structure: data.data.scenes
            scenesArray = scenesData.data.data.scenes;
          } else if (
            typeof scenesData.data === 'object' && 
            scenesData.data !== null && 
            Object.values(scenesData.data).length > 0 && 
            Array.isArray(Object.values(scenesData.data)[0])
          ) {
            // If data contains a single property that is an array, use that
            scenesArray = Object.values(scenesData.data)[0];
          } else if (Array.isArray(scenesData)) {
            // Direct array response
            scenesArray = scenesData;
          } else if (scenesData.intent === 'generate_scene_breakdown') {
            // Handle the specific error case mentioned in the issue
            throw new Error('Backend returned not implemented error for scene breakdown');
          }
          
          if (!scenesArray) {
            console.error('Could not find scenes in stored data:', scenesData);
            throw new Error('Invalid scene data structure');
          }
          
          setScenes(scenesArray.map((scene: { id: string; description: string; narration: string; duration: number }) => ({
            id: scene.id,
            visual: scene.description,
            audio: scene.narration,
            duration: scene.duration,
            narration: scene.narration
          })));
          
          // Set the first scene as expanded
          if (scenesArray.length > 0) {
            setExpandedSceneId(scenesArray[0].id);
          }
          
          setPrompt(promptData);
          setIsLoading(false);
        }
        return; // Exit early since we have the data
      } catch (err) {
        console.error('Error parsing stored data:', err);
        // Continue with API calls if parsing fails
      }
    }
    
    // If we don't have stored data, make the API calls
    const loadSceneBreakdown = async () => {
      if (!isMounted || isRequestInProgress) return;
      
      // Set the flag to prevent multiple simultaneous API calls
      isRequestInProgress = true;
      
      setIsLoading(true);
      setError(null);
      
      try {
        // Get prompt data from localStorage
        const storedPrompt = localStorage.getItem('pixora_prompt');
        if (!storedPrompt) {
          throw new Error('No prompt data found. Please return to the home page and try again.');
        }
        
        const promptData = JSON.parse(storedPrompt);
        if (isMounted) {
          setPrompt(promptData);
          
          // Add AI message about analyzing the prompt (with a unique identifier to prevent duplicates)
          const analyzeMessage = 'I\'m analyzing your prompt to break it down into scenes. This will help us create a well-structured video.';
          
          // Check if this message already exists in the chat
          const messageExists = localStorage.getItem('pixora_analyze_message_sent') === 'true';
          
          if (!messageExists) {
          addMessage({
            role: 'assistant' as const,
            content: analyzeMessage,
            timestamp: new Date()
          });
            
            // Mark this message as sent
            localStorage.setItem('pixora_analyze_message_sent', 'true');
          }
        }

        // Clear any previous cached script and scenes data to force new API calls
        localStorage.removeItem('pixora_script');
        localStorage.removeItem('pixora_scenes');
        localStorage.removeItem('pixora_data_expiry');
        localStorage.removeItem('pixora_completed_message_sent');
        localStorage.removeItem('pixora_error_message_sent');
        
        // Create an AbortController to cancel requests if component unmounts
        const controller = new AbortController();
        
        // Fetch scene breakdown using the API service
        const result = await fetchSceneBreakdown(
          promptData,
          controller,
          (message) => addMessage(message)
        );
        
        if (!isMounted) return;
        
        // Store script in localStorage if available
        if (result.script) {
          localStorage.setItem('pixora_script', JSON.stringify(result.script));
          setScript(result.script);
        }
        
        // Store scenes in localStorage
        localStorage.setItem('pixora_scenes', JSON.stringify({ scenes: result.scenes }));
        
        // Set expiry time for cached data (30 minutes)
        const expiryTime = Date.now() + (30 * 60 * 1000);
        localStorage.setItem('pixora_data_expiry', expiryTime.toString());
        
        setScenes(result.scenes);
        
        // Set the first scene as expanded
        if (result.scenes.length > 0) {
          setExpandedSceneId(result.scenes[0].id);
        }
        
        // Add AI message about the completed breakdown (with a unique identifier to prevent duplicates)
        const completedMessage = `I've broken down your prompt into ${result.scenes.length} scenes. You can review them on the right and make any changes before we generate the video.`;
        
        // Check if this message already exists in the chat
        const completedMessageExists = localStorage.getItem('pixora_completed_message_sent') === 'true';
        
        if (!completedMessageExists) {
          addMessage({
            role: 'assistant' as const,
            content: completedMessage,
            timestamp: new Date()
          });
          
          // Mark this message as sent
          localStorage.setItem('pixora_completed_message_sent', 'true');
        }
        
        setIsLoading(false);
      } catch (err) {
        if (!isMounted) return;
        
        console.error('Error fetching scene breakdown:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        
        // Add AI message about the error (with a unique identifier to prevent duplicates)
        const errorMessage = `I encountered an error while breaking down your prompt: ${err instanceof Error ? err.message : 'An unknown error occurred'}. Please try again or modify your prompt.`;
        
        // Check if this message already exists in the chat
        const errorMessageExists = localStorage.getItem('pixora_error_message_sent') === 'true';
        
        if (!errorMessageExists) {
          addMessage({
            role: 'assistant' as const,
            content: errorMessage,
            timestamp: new Date()
          });
          
          // Mark this message as sent
          localStorage.setItem('pixora_error_message_sent', 'true');
        }
        
        setIsLoading(false);
      }
    };
    
    loadSceneBreakdown();
    
    // Cleanup function to prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, [addMessage]); // Only depend on addMessage
  
  
  const handleRegenerateScene = async (sceneId: string) => {
    if (!prompt || !script) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Add AI message about regenerating the scene
      addMessage({
        role: 'assistant' as const,
        content: `I'm regenerating scene ${scenes.findIndex(s => s.id === sceneId) + 1} for you...`,
        timestamp: new Date()
      });
      
      // Use the API service to regenerate the scene
      const updatedScene = await regenerateScene(sceneId, prompt, script.title);
      
      // Update the scene in the local state
      setScenes(prevScenes => 
        prevScenes.map(scene => 
          scene.id === sceneId ? updatedScene : scene
        )
      );
      
      // Add AI message about the regenerated scene
      addMessage({
        role: 'assistant' as const,
        content: `I've regenerated the scene with new content. Take a look at the updated version.`,
        timestamp: new Date()
      });
    } catch (err) {
      console.error('Error regenerating scene:', err);
      setError(err instanceof Error ? err.message : 'Failed to regenerate scene');
      
      // Add AI message about the error
      addMessage({
        role: 'assistant' as const,
        content: `I encountered an error while regenerating the scene: ${err instanceof Error ? err.message : 'An unknown error occurred'}. Please try again.`,
        timestamp: new Date()
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleEditScene = (sceneId: string) => {
    // Find the scene to edit
    const sceneToEdit = scenes.find(scene => scene.id === sceneId);
    if (!sceneToEdit) return;
    
    // In a real implementation, this would open a modal to edit the scene
    console.log(`Editing scene ${sceneId}:`, sceneToEdit);
    
    // Add AI message about editing the scene
    addMessage({
      role: 'user' as const,
      content: `I want to edit scene ${scenes.findIndex(s => s.id === sceneId) + 1}`,
      timestamp: new Date()
    });
    
    addMessage({
      role: 'assistant' as const,
      content: `What would you like to change about scene ${scenes.findIndex(s => s.id === sceneId) + 1}? You can modify the visual description, narration, or duration.`,
      timestamp: new Date()
    });
    
    // For now, just alert the user
    alert(`This would open an editor for scene ${sceneId}`);
  };
  
  // State to track if a video generation request is in progress
  const [isGenerating, setIsGenerating] = useState(false);
  
  // State for confirmation dialog
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleGenerateVideo = async () => {
    if (!prompt || isGenerating) return;
    
    // Show confirmation dialog instead of immediately generating
    setShowConfirmation(true);
  };
  
  const confirmAndGenerateVideo = async () => {
    if (!prompt || isGenerating) return;
    
    // Close confirmation dialog
    setShowConfirmation(false);
    
    // Set generating state to prevent multiple clicks
    setIsGenerating(true);
    
    try {
      // Add AI message about starting video generation
      addMessage({
        role: 'user' as const,
        content: 'Generate the video with these scenes',
        timestamp: new Date()
      });
      
      addMessage({
        role: 'assistant' as const,
        content: 'I\'m starting the video generation process now. This will take a few minutes, but you can chat with me while you wait.',
        timestamp: new Date()
      });
      
      // Use the API service to generate the video
      const taskId = await generateVideo(prompt, scenes);
      
      // Store the task ID in localStorage
      localStorage.setItem('pixora_task_id', taskId);
      
      // Navigate to the generation page to show progress
      navigate('/generation');
      
      console.log('Video generation started with task ID:', taskId);
    } catch (err) {
      console.error('Error starting video generation:', err);
      setError(err instanceof Error ? err.message : 'Failed to start video generation');
      
      // Add AI message about the error
      addMessage({
        role: 'assistant' as const,
        content: `I encountered an error while starting video generation: ${err instanceof Error ? err.message : 'An unknown error occurred'}. Please try again.`,
        timestamp: new Date()
      });
      
      // Reset generating state after a delay to prevent rapid retries
      setTimeout(() => {
        setIsGenerating(false);
      }, 3000);
    }
  };
  
  const toggleSceneExpansion = (sceneId: string) => {
    // If the scene is already expanded, collapse it
    // Otherwise, expand it and collapse any other expanded scene
    setExpandedSceneId(expandedSceneId === sceneId ? null : sceneId);
  };
  
  if (isLoading) {
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
  
  return (
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
                onClick={() => {
                  // Clear localStorage to force a fresh API call
                  localStorage.removeItem('pixora_script');
                  localStorage.removeItem('pixora_scenes');
                  localStorage.removeItem('pixora_data_expiry');
                  localStorage.removeItem('pixora_completed_message_sent');
                  localStorage.removeItem('pixora_error_message_sent');
                  localStorage.removeItem('pixora_analyze_message_sent');
                  
                  // Reload the page to trigger the API calls
                  window.location.reload();
                }}
                className="bg-yellow-500 hover:bg-yellow-600 text-white"
              >
                Regenerate Scene Breakdown
              </Button>
            </div>
          )}
        </div>
        
        {/* Scene list with collapsible scenes */}
        <div className="space-y-4">
          {scenes.map((scene, index) => (
            <div key={scene.id} className="glass-morphism rounded-2xl overflow-hidden">
              {/* Scene header - always visible */}
              <div 
                className={`p-4 flex justify-between items-center cursor-pointer transition-colors ${
                  expandedSceneId === scene.id ? 'bg-white/5' : 'hover:bg-white/5'
                }`}
                onClick={() => toggleSceneExpansion(scene.id)}
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
                  <Button 
                    variant="simple" 
                    className="p-2 h-9 w-9 flex items-center justify-center"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleEditScene(scene.id);
                    }}
                    title="Edit scene"
                  >
                    <IconEdit size={18} />
                  </Button>
                  <Button 
                    variant="simple" 
                    className="p-2 h-9 w-9 flex items-center justify-center"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleRegenerateScene(scene.id);
                    }}
                    title="Regenerate scene"
                  >
                    <IconRefresh size={18} />
                  </Button>
                  <div className="h-9 w-9 flex items-center justify-center text-muted-foreground">
                    {expandedSceneId === scene.id ? (
                      <IconChevronUp size={18} />
                    ) : (
                      <IconChevronDown size={18} />
                    )}
                  </div>
                </div>
              </div>
              
              {/* Scene content - only visible when expanded */}
              {expandedSceneId === scene.id && (
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
          ))}
        </div>
        
        {/* Action buttons */}
        <div className="mt-8 flex justify-end">
          <Button 
            onClick={handleGenerateVideo}
            className="px-6 py-2 flex items-center gap-2"
            disabled={isGenerating}
            variant="primary"
          >
            {isGenerating ? (
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
        
        {/* Confirmation Dialog */}
        {showConfirmation && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-background border border-border rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Confirm Video Generation</h3>
              <p className="mb-6">Are you ready to generate your video with the current scene breakdown? This process will take a few minutes and cannot be interrupted once started.</p>
              
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
                <p className="text-sm text-blue-400">
                  <span className="font-medium block mb-1">Please confirm that:</span>
                  <ul className="list-disc list-inside space-y-1">
                    <li>You've reviewed all scene descriptions and narrations</li>
                    <li>The scene sequence matches your creative vision</li>
                    <li>All scene durations are appropriate</li>
                  </ul>
                </p>
              </div>
              
              <div className="flex justify-end gap-3">
                <Button 
                  variant="outline" 
                  onClick={() => setShowConfirmation(false)}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={confirmAndGenerateVideo}
                  className="px-4 py-2 flex items-center gap-2"
                  variant="primary"
                >
                  Proceed with Generation
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </SplitScreenLayout>
  );
}
