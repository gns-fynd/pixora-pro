import { useEffect, useState } from 'react';

interface LoaderProps {
  /**
   * The progress percentage (0-100)
   */
  progress?: number;
  
  /**
   * Whether to animate the progress automatically
   */
  autoAnimate?: boolean;
  
  /**
   * The duration of the animation in milliseconds (only used when autoAnimate is true)
   */
  duration?: number;
  
  /**
   * Optional message to display below the loader
   */
  message?: string;
  
  /**
   * Optional className for additional styling
   */
  className?: string;
}

/**
 * Animated loader component with progress indicator
 */
export function Loader({
  progress: initialProgress = 0,
  autoAnimate = false,
  duration = 6000,
  message,
  className = '',
}: LoaderProps) {
  // Add event listener for the closeLoader event
  useEffect(() => {
    const handleCloseLoader = () => {
      // Create a custom event to minimize the loader
      const minimizeEvent = new CustomEvent('minimizeLoader');
      window.dispatchEvent(minimizeEvent);
    };
    
    window.addEventListener('closeLoader', handleCloseLoader);
    
    return () => {
      window.removeEventListener('closeLoader', handleCloseLoader);
    };
  }, []);
  const [progress, setProgress] = useState(initialProgress);
  
  // Update progress when prop changes (if not auto-animating)
  useEffect(() => {
    if (!autoAnimate) {
      setProgress(initialProgress);
    }
  }, [initialProgress, autoAnimate]);
  
  // Auto-animate progress if enabled
  useEffect(() => {
    if (!autoAnimate) return;
    
    const startTime = Date.now();
    
    const updateProgress = () => {
      const elapsed = (Date.now() - startTime) % duration;
      const calculatedProgress = Math.min(100, Math.floor((elapsed / duration) * 100));
      
      setProgress(calculatedProgress);
      
      if (autoAnimate) {
        requestAnimationFrame(updateProgress);
      }
    };
    
    const animationFrame = requestAnimationFrame(updateProgress);
    
    return () => {
      cancelAnimationFrame(animationFrame);
    };
  }, [autoAnimate, duration]);
  
  return (
    <div className={`flex flex-col items-center relative ${className}`}>
      <button 
        className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
        onClick={() => {
          // Create a custom event to minimize the loader
          const event = new CustomEvent('minimizeLoader');
          window.dispatchEvent(event);
        }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
      <div className="relative w-64">
        <div className="h-5 w-full relative clip-path-inset-[-40px_0_-5px]">
          <div 
            className="absolute inset-auto left-[calc(50%-28px)] bottom-0 h-[70px] w-[56px] bg-no-repeat animate-loader-icons"
            style={{
              backgroundImage: `
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M21 6h-7.59l3.29-3.29L16 2l-4 4-4-4-.71.71L10.59 6H3a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1zm-1 14H4V8h16v12zM9 10v8l7-4z'/%3E%3C/svg%3E"),
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z'/%3E%3C/svg%3E"),
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M12 3l.01 10.55c-.59-.34-1.27-.55-2-.55-2.22 0-4.01 1.79-4.01 4s1.79 4 4.01 4 3.99-1.79 3.99-4V7h4V3h-6zm-1.99 16c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z'/%3E%3C/svg%3E"),
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='28' height='24' fill='%23914de6'%3E%3Cpath d='M3 18h12v-2H3v2zM3 6v2h18V6H3zm0 7h18v-2H3v2z'/%3E%3C/svg%3E")
              `,
              backgroundPosition: '0 -70px, 100% -70px, 0 -70px, 100% -70px',
              backgroundSize: '28px 24px',
              animationDuration: `${duration}ms`,
            }}
          />
        </div>
        
        <div className="mt-5 w-full h-[3px] bg-white/15 rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        
        <div className="mt-2 text-center text-primary font-bold text-lg">
          {progress}%
        </div>
      </div>
      
      {message && (
        <p className="mt-4 text-muted-foreground text-sm">{message}</p>
      )}
    </div>
  );
}

// Add the necessary animation to the global CSS
if (typeof document !== 'undefined') {
  // Only run in browser environment
  const style = document.createElement('style');
  style.textContent = `
    @keyframes loader-icons-1 {
      0%, 100%  {background-position: 0 -70px, 100% -70px, 0 -70px, 100% -70px}
      17.5% {background-position: 0 100%, 100% -70px, 0 -70px, 100% -70px}
      35%   {background-position: 0 100%, 100% 100%, 0 -70px, 100% -70px}
      52.5% {background-position: 0 100%, 100% 100%, 0 calc(100% - 24px), 100% -70px}
      70%, 98%  {background-position: 0 100%, 100% 100%, 0 calc(100% - 24px), 100% calc(100% - 24px)}
    }
    
    @keyframes loader-icons-2 {
      0%, 70% {transform: translate(0)}
      100%  {transform: translate(200%)}
    }
    
    .animate-loader-icons {
      animation: loader-icons-1 6s infinite linear, loader-icons-2 6s infinite linear;
    }
    
    .clip-path-inset-[-40px_0_-5px] {
      clip-path: inset(-40px 0 -5px);
    }
  `;
  document.head.appendChild(style);
}

export default Loader;
