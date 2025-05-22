interface VideoGenerationStep {
  id: string;
  label: string;
  icon: 'video' | 'audio' | 'music' | 'transcript';
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
}

interface VideoGenerationLoaderProps {
  isVisible: boolean;
  overallProgress: number;
  steps: VideoGenerationStep[];
  message?: string;
}

export function VideoGenerationLoader({
  isVisible,
  overallProgress,
  steps,
  message = 'Generating your video...'
}: VideoGenerationLoaderProps) {
  if (!isVisible) return null;

  return (
    <div className="glass-morphism rounded-xl p-6 max-w-md w-full relative">
      <button 
        className="absolute top-2 right-2 text-muted-foreground hover:text-foreground transition-colors"
        onClick={() => {
          // Create a custom event to notify the parent component
          const event = new CustomEvent('closeLoader');
          window.dispatchEvent(event);
        }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
      <h3 className="text-xl font-semibold mb-4">{message}</h3>
      
      {/* Loader animation */}
      <div className="loader-container relative w-full h-20 mb-4">
        <div className="loader"></div>
      </div>
      
      {/* Overall progress */}
      <div className="mb-6">
        <div className="flex justify-between text-sm mb-1">
          <span>Overall Progress</span>
          <span>{overallProgress}%</span>
        </div>
        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary rounded-full transition-all duration-300 ease-out"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>
      
      {/* Step-by-step progress */}
      <div className="space-y-4">
        {steps.map(step => (
          <div key={step.id} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{step.label}</span>
              <span>{step.progress}%</span>
            </div>
            <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-300 ease-out ${
                  step.status === 'completed' ? 'bg-green-500' :
                  step.status === 'processing' ? 'bg-primary' :
                  step.status === 'error' ? 'bg-red-500' : 'bg-muted-foreground/30'
                }`}
                style={{ width: `${step.progress}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      
      <style>{`
        .loader {
          width: 100%;
          height: 20px;
          position: relative;
          clip-path: inset(-40px 0 -5px);
        }
        
        .loader:before {
          content: "";
          position: absolute;
          inset: auto calc(50% - 28px) 0;
          height: 70px;
          --icon-video: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M21 6h-7.59l3.29-3.29L16 2l-4 4-4-4-.71.71L10.59 6H3a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1zm-1 14H4V8h16v12zM9 10v8l7-4z'/%3E%3C/svg%3E");
          --icon-audio: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z'/%3E%3C/svg%3E");
          --icon-music: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M12 3l.01 10.55c-.59-.34-1.27-.55-2-.55-2.22 0-4.01 1.79-4.01 4s1.79 4 4.01 4 3.99-1.79 3.99-4V7h4V3h-6zm-1.99 16c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z'/%3E%3C/svg%3E");
          --icon-transcript: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M3 18h12v-2H3v2zM3 6v2h18V6H3zm0 7h18v-2H3v2z'/%3E%3C/svg%3E");
          
          background: 
            var(--icon-video) no-repeat,
            var(--icon-audio) no-repeat,
            var(--icon-music) no-repeat,
            var(--icon-transcript) no-repeat;
          
          background-size: 28px 24px;
          animation:
            l7-1 6s infinite linear,
            l7-2 6s infinite linear;
        }
        
        @keyframes l7-1 {
          0%,
          100%  {background-position: 0 -70px, 100% -70px, 0 -70px, 100% -70px}
          17.5% {background-position: 0 100%, 100% -70px, 0 -70px, 100% -70px}
          35%   {background-position: 0 100%, 100% 100%, 0 -70px, 100% -70px}
          52.5% {background-position: 0 100%, 100% 100%, 0 calc(100% - 24px), 100% -70px}
          70%,
          98%  {background-position: 0 100%, 100% 100%, 0 calc(100% - 24px), 100% calc(100% - 24px)}
        }
        
        @keyframes l7-2 {
          0%,70% {transform: translate(0)}
          100%  {transform: translate(200%)}
        }
      `}</style>
    </div>
  );
}
