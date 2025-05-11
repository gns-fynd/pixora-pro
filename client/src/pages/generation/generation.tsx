import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/button';
import { IconDownload, IconEdit } from '@tabler/icons-react';
import { apiClient } from '@/services/api-client';
import { SplitScreenLayout } from '@/components/layouts/SplitScreenLayout';
import { useChat } from '@/context/ChatContext';
import { Loader } from '@/components/ui/loader';

// Define types for API responses
interface VideoStatusResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  current_step?: 'analyzing_prompt' | 'generating_images' | 'generating_audio' | 'generating_music' | 'assembling_video';
  step_progress?: number;
  error?: string;
  result?: {
    video_url?: string;
    thumbnail_url?: string;
    [key: string]: unknown;
  };
}

// Define prompt type
interface VideoPrompt {
  prompt: string;
  aspectRatio: string;
  duration: number;
  style: string;
}

// Define generation steps
const GENERATION_STEPS = [
  { id: 'analyzing_prompt', label: 'Analyzing prompt', percentage: 0 },
  { id: 'generating_scenes', label: 'Generating scenes', percentage: 0 },
  { id: 'generating_images', label: 'Creating visuals', percentage: 0 },
  { id: 'generating_audio', label: 'Generating audio', percentage: 0 },
  { id: 'generating_music', label: 'Creating background music', percentage: 0 },
  { id: 'assembling_video', label: 'Assembling video', percentage: 0 },
];

export default function Generation() {
  const navigate = useNavigate();
  const location = useLocation();
  const { addMessage } = useChat();
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(GENERATION_STEPS);
  const [overallProgress, setOverallProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<VideoPrompt | null>(null);
  
  // Get task ID and prompt data from URL or localStorage
  useEffect(() => {
    // Check if task ID is in the URL
    const params = new URLSearchParams(location.search);
    const urlTaskId = params.get('task_id');
    
    if (urlTaskId) {
      setTaskId(urlTaskId);
    } else {
      // Check if task ID is in localStorage
      const storedTaskId = localStorage.getItem('pixora_task_id');
      if (storedTaskId) {
        setTaskId(storedTaskId);
      } else {
        // No task ID found, show error
        setError('No video generation task found. Please return to the home page and try again.');
        
        // Add AI message about the error
        addMessage({
          role: 'assistant',
          content: 'I couldn\'t find any active video generation task. Would you like to start a new video generation?',
          timestamp: new Date()
        });
      }
    }
    
    // Get prompt data from localStorage
    try {
      const storedPrompt = localStorage.getItem('pixora_prompt');
      if (storedPrompt) {
        const promptData = JSON.parse(storedPrompt) as VideoPrompt;
        setPrompt(promptData);
      }
    } catch (err) {
      console.error('Error parsing stored prompt:', err);
    }
  }, [location, addMessage]);
  
  // Track if polling is active
  const [isPolling, setIsPolling] = useState(false);
  
  // Poll for generation status
  useEffect(() => {
    // If no task ID or already complete, don't poll
    if (!taskId || isComplete || isPolling) return;
    
    // Set polling flag to prevent multiple polling loops
    setIsPolling(true);
    
    // Store task ID in localStorage
    localStorage.setItem('pixora_task_id', taskId);
    
    // Create an AbortController to cancel requests if component unmounts
    const controller = new AbortController();
    
    // Check if we have cached status data
    const cachedStatusKey = `pixora_status_${taskId}`;
    const cachedStatus = localStorage.getItem(cachedStatusKey);
    const cachedStatusExpiry = localStorage.getItem(`${cachedStatusKey}_expiry`);
    
    // If we have valid cached status and it's complete, use it
    if (cachedStatus && cachedStatusExpiry) {
      try {
        const statusData = JSON.parse(cachedStatus);
        const expiryTime = parseInt(cachedStatusExpiry, 10);
        
        // If the cached status is still valid and shows completion
        if (expiryTime > Date.now() && statusData.status === 'completed') {
          console.debug('Using cached completed status');
          
          // Update state with cached data
          setOverallProgress(100);
          setIsComplete(true);
          
          if (statusData.result?.video_url) {
            setVideoUrl(statusData.result.video_url);
          }
          
          if (statusData.result?.thumbnail_url) {
            setThumbnailUrl(statusData.result.thumbnail_url);
          }
          
          // Add AI message about completion
          addMessage({
            role: 'assistant',
            content: 'Your video has been generated successfully! You can now view it, download it, or edit it in the timeline.',
            timestamp: new Date()
          });
          
          // Reset polling flag
          setIsPolling(false);
          return;
        }
      } catch (err) {
        console.error('Error parsing cached status:', err);
        // Continue with API polling if parsing fails
      }
    }
    
    // Define the status check function
    const checkStatus = async () => {
      try {
        // Get generation status
        const status = await apiClient.get<VideoStatusResponse>(`/scenes/video/${taskId}`, {
          signal: controller.signal
        });
        
        // Update overall progress
        setOverallProgress(status.progress);
        
        // Update step progress
        if (status.current_step) {
          const stepIndex = GENERATION_STEPS.findIndex(step => step.id === status.current_step);
          
          if (stepIndex !== -1) {
            // If we've moved to a new step, add an AI message
            if (stepIndex > currentStep) {
              const stepMessages = [
                'I\'m analyzing your prompt to understand exactly what you want in your video.',
                'Now I\'m breaking down your video into individual scenes.',
                'I\'m creating high-quality visuals for each scene in your video.',
                'I\'m generating the voiceover narration for your video.',
                'I\'m composing a custom background soundtrack that matches the mood of your video.',
                'I\'m putting everything together into your final video.'
              ];
              
              addMessage({
                role: 'assistant',
                content: stepMessages[stepIndex],
                timestamp: new Date()
              });
            }
            
            setCurrentStep(stepIndex);
            
            // Update progress for all steps
            setProgress(prev => {
              const newProgress = [...prev];
              
              // Set previous steps to 100%
              for (let i = 0; i < stepIndex; i++) {
                newProgress[i].percentage = 100;
              }
              
              // Set current step progress
              newProgress[stepIndex].percentage = status.step_progress || 0;
              
              // Set next steps to 0%
              for (let i = stepIndex + 1; i < newProgress.length; i++) {
                newProgress[i].percentage = 0;
              }
              
              return newProgress;
            });
          }
        }
        
        // Check if generation is complete
        if (status.status === 'completed') {
          setIsComplete(true);
          
          // Set video URL if available
          if (status.result?.video_url) {
            setVideoUrl(status.result.video_url);
          }
          
          // Set thumbnail URL if available
          if (status.result?.thumbnail_url) {
            setThumbnailUrl(status.result.thumbnail_url);
          }
          
          // Cache the completed status (valid for 24 hours)
          const cachedStatusKey = `pixora_status_${taskId}`;
          localStorage.setItem(cachedStatusKey, JSON.stringify(status));
          const expiryTime = Date.now() + (24 * 60 * 60 * 1000); // 24 hours
          localStorage.setItem(`${cachedStatusKey}_expiry`, expiryTime.toString());
          
          // Add AI message about completion
          addMessage({
            role: 'assistant',
            content: 'Your video has been generated successfully! You can now view it, download it, or edit it in the timeline.',
            timestamp: new Date()
          });
          
          // Clear interval
          clearInterval(intervalId);
          setIsPolling(false); // Reset polling flag on completion
        } else if (status.status === 'failed') {
          setError(status.error || 'Video generation failed');
          
          // Add AI message about the error
          addMessage({
            role: 'assistant',
            content: `I encountered an error while generating your video: ${status.error || 'Unknown error'}. Would you like to try again?`,
            timestamp: new Date()
          });
          
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error('Error checking generation status:', err);
        setError('Failed to check generation status');
        
        // Add AI message about the error
        addMessage({
          role: 'assistant',
          content: 'I\'m having trouble checking the status of your video generation. Please try refreshing the page.',
          timestamp: new Date()
        });
        
        clearInterval(intervalId);
      }
    };
    
    // Check status immediately
    checkStatus();
    
    // Then check every 2 seconds
    const intervalId = setInterval(checkStatus, 2000);
    
    return () => {
      clearInterval(intervalId);
      controller.abort(); // Abort any pending requests
      setIsPolling(false); // Reset polling flag when component unmounts
    };
  }, [taskId, currentStep, addMessage]);
  
  const handleViewVideo = () => {
    // Add AI message about viewing the video
    addMessage({
      role: 'user',
      content: 'I want to edit this video in the timeline',
      timestamp: new Date()
    });
    
    addMessage({
      role: 'assistant',
      content: 'Great! I\'ll take you to the editor where you can make further adjustments to your video.',
      timestamp: new Date()
    });
    
    // Navigate to the editor with the video
    if (videoUrl) {
      navigate('/editor', { state: { videoUrl } });
    } else {
      navigate('/editor');
    }
  };
  
  const handleDownload = () => {
    // Add AI message about downloading the video
    addMessage({
      role: 'user',
      content: 'I want to download this video',
      timestamp: new Date()
    });
    
    addMessage({
      role: 'assistant',
      content: 'Your video is being downloaded. You can also edit it in our timeline editor if you want to make any changes.',
      timestamp: new Date()
    });
    
    // Download the video if URL is available
    if (videoUrl) {
      window.open(videoUrl, '_blank');
    } else {
      alert('Video URL not available');
    }
  };
  
  return (
    <SplitScreenLayout videoId="generation">
      <div className="p-6">
        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 mb-6 text-red-500">
            <h3 className="font-semibold mb-1">Error</h3>
            <p>{error}</p>
          </div>
        )}
        
        {/* Generation progress */}
        <div className="glass-morphism rounded-2xl p-6 mb-8">
          <h1 className="text-2xl font-bold mb-6">Generating Your Video</h1>
          
          {/* Overall progress with Loader */}
          <div className="mb-8 flex flex-col items-center">
            <Loader 
              progress={overallProgress} 
              message={!isComplete ? `Estimated time remaining: ~${Math.max(5 - Math.floor(overallProgress / 20), 0)} minutes` : undefined}
            />
          </div>
          
          {/* Step-by-step progress */}
          <div className="space-y-6">
            {progress.map((step, index) => (
              <div key={step.id} className={`transition-opacity duration-300 ${index > currentStep + 1 ? 'opacity-50' : 'opacity-100'}`}>
                <div className="flex items-center gap-3 mb-2">
                  <div className={`flex items-center justify-center h-6 w-6 rounded-full text-xs font-medium ${
                    index < currentStep 
                      ? 'bg-primary text-white' 
                      : index === currentStep 
                        ? 'bg-primary/20 text-primary border border-primary/50' 
                        : 'bg-white/10 text-muted-foreground'
                  }`}>
                    {index < currentStep ? '✓' : index + 1}
                  </div>
                  <span className={`text-sm font-medium ${
                    index === currentStep ? 'text-primary' : 'text-foreground'
                  }`}>
                    {step.label}
                  </span>
                  <div className="flex-1 h-px bg-white/10"></div>
                  <span className={`text-sm font-medium ${
                    index < currentStep 
                      ? 'text-primary' 
                      : index === currentStep 
                        ? 'text-foreground' 
                        : 'text-muted-foreground'
                  }`}>
                    {step.percentage}%
                  </span>
                </div>
                <div className="ml-9 pl-3 border-l border-white/10">
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ease-out ${
                        index < currentStep 
                          ? 'bg-primary/80' 
                          : index === currentStep 
                            ? 'bg-primary' 
                            : 'bg-white/10'
                      }`}
                      style={{ width: `${step.percentage}%` }}
                    ></div>
                  </div>
                  
                  {/* Step description */}
                  {index === currentStep && (
                    <div className="mt-2 text-sm text-muted-foreground">
                      {index === 0 && 'Analyzing your prompt to understand your vision...'}
                      {index === 1 && 'Breaking down your video into individual scenes...'}
                      {index === 2 && 'Creating high-quality visuals for each scene...'}
                      {index === 3 && 'Generating voiceover narration for your video...'}
                      {index === 4 && 'Composing a custom background soundtrack...'}
                      {index === 5 && 'Assembling everything into your final video...'}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Video preview (shown when complete) */}
        {isComplete && (
          <div className="glass-morphism rounded-2xl overflow-hidden mb-8">
            <div className="bg-gradient-to-r from-primary/20 to-primary/5 p-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold">Video Generated Successfully!</h2>
              </div>
            </div>
            
            <div className="p-6">
              <div className="aspect-video bg-black/50 rounded-lg flex items-center justify-center mb-6 overflow-hidden border border-white/10">
                {videoUrl ? (
                  <video 
                    src={videoUrl} 
                    controls 
                    className="w-full h-full rounded-lg"
                    poster={thumbnailUrl || undefined}
                    autoPlay
                    muted
                    playsInline
                  />
                ) : (
                  <div className="text-center">
                    <svg className="mx-auto h-12 w-12 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <p className="mt-2 text-sm text-muted-foreground">Video preview not available</p>
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-sm text-muted-foreground mb-1">Duration</div>
                  <div className="font-medium">{prompt?.duration || "30"} seconds</div>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-sm text-muted-foreground mb-1">Resolution</div>
                  <div className="font-medium">{prompt?.aspectRatio || "16:9"}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-sm text-muted-foreground mb-1">Style</div>
                  <div className="font-medium capitalize">{prompt?.style || "Standard"}</div>
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-end">
                <Button 
                  variant="simple"
                  onClick={handleDownload}
                  className="flex items-center gap-2"
                  disabled={!videoUrl}
                >
                  <IconDownload size={18} />
                  Download MP4
                </Button>
                <Button 
                  onClick={handleViewVideo}
                  className="flex items-center gap-2"
                >
                  <IconEdit size={18} />
                  Edit in Timeline
                </Button>
              </div>
            </div>
          </div>
        )}
        
        {/* Generation tips */}
        <div className="glass-morphism-light rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">While You Wait</h2>
          <p className="text-muted-foreground mb-4">
            Our AI is hard at work generating your video. This process involves several steps:
          </p>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Analyzing your prompt to understand your vision</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Creating high-quality visuals for each scene</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Generating audio narration and sound effects</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Composing a custom background soundtrack</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Assembling everything into a cohesive video</span>
            </li>
          </ul>
          <p className="text-muted-foreground mt-4">
            Feel free to chat with our AI assistant while you wait. You can ask questions about the video generation process or get suggestions for your next project.
          </p>
        </div>
      </div>
    </SplitScreenLayout>
  );
}
