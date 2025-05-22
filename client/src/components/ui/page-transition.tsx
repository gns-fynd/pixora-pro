import { useState, useEffect } from 'react';
import { Loader } from './loader';

interface PageTransitionProps {
  duration?: number; // Duration in milliseconds
  message?: string;
  onComplete?: () => void;
}

export function PageTransition({
  duration = 3000, // Default 3 seconds
  message = 'Loading...',
  onComplete
}: PageTransitionProps) {
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  
  useEffect(() => {
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    const updateProgress = () => {
      const currentTime = Date.now();
      const elapsed = currentTime - startTime;
      const newProgress = Math.min(100, (elapsed / duration) * 100);
      
      setProgress(newProgress);
      
      if (currentTime < endTime) {
        requestAnimationFrame(updateProgress);
      } else {
        setIsComplete(true);
        if (onComplete) {
          onComplete();
        }
      }
    };
    
    requestAnimationFrame(updateProgress);
    
    return () => {
      // Cleanup if component unmounts
    };
  }, [duration, onComplete]);
  
  if (isComplete) {
    return null;
  }
  
  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex flex-col items-center justify-center z-50">
      <div className="max-w-md w-full px-4">
        <Loader progress={progress} message={message} />
        <div className="text-center mt-4">
          <p className="text-muted-foreground">
            {Math.ceil((duration * (100 - progress) / 100) / 1000)} seconds remaining...
          </p>
        </div>
      </div>
    </div>
  );
}
