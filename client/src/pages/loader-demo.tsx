import { useState } from 'react';
import { Loader } from '@/components/ui/loader';
import { Button } from '@/components/button';

export default function LoaderDemo() {
  const [progress, setProgress] = useState(0);
  const [autoAnimate, setAutoAnimate] = useState(false);
  
  const handleIncrement = () => {
    setProgress(prev => Math.min(prev + 10, 100));
  };
  
  const handleDecrement = () => {
    setProgress(prev => Math.max(prev - 10, 0));
  };
  
  const handleReset = () => {
    setProgress(0);
  };
  
  const toggleAutoAnimate = () => {
    setAutoAnimate(prev => !prev);
  };
  
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <div className="max-w-3xl w-full glass-morphism rounded-2xl p-8">
        <h1 className="text-3xl font-bold mb-8 text-center">Loader Component Demo</h1>
        
        <div className="mb-12 flex flex-col items-center">
          <Loader 
            progress={progress} 
            autoAnimate={autoAnimate}
            message={autoAnimate ? "Auto-animating loader" : `Current progress: ${progress}%`}
          />
        </div>
        
        <div className="flex flex-col gap-6">
          <div className="flex justify-center gap-4">
            <Button onClick={handleDecrement} disabled={progress === 0 || autoAnimate}>
              -10%
            </Button>
            <Button onClick={handleIncrement} disabled={progress === 100 || autoAnimate}>
              +10%
            </Button>
            <Button onClick={handleReset} disabled={progress === 0 || autoAnimate}>
              Reset
            </Button>
          </div>
          
          <div className="flex justify-center">
            <Button 
              onClick={toggleAutoAnimate}
              variant={autoAnimate ? "outline" : "primary"}
            >
              {autoAnimate ? "Stop Auto Animation" : "Start Auto Animation"}
            </Button>
          </div>
        </div>
        
        <div className="mt-12 space-y-6">
          <h2 className="text-xl font-semibold">Usage Examples</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="glass-morphism-light rounded-xl p-6">
              <h3 className="text-lg font-medium mb-4">Static Progress</h3>
              <Loader progress={25} message="25% Complete" />
              <div className="mt-4 text-sm text-muted-foreground">
                <code>{`<Loader progress={25} message="25% Complete" />`}</code>
              </div>
            </div>
            
            <div className="glass-morphism-light rounded-xl p-6">
              <h3 className="text-lg font-medium mb-4">Auto-Animated</h3>
              <Loader autoAnimate={true} message="Processing..." />
              <div className="mt-4 text-sm text-muted-foreground">
                <code>{`<Loader autoAnimate={true} message="Processing..." />`}</code>
              </div>
            </div>
            
            <div className="glass-morphism-light rounded-xl p-6">
              <h3 className="text-lg font-medium mb-4">Complete</h3>
              <Loader progress={100} message="Task completed!" />
              <div className="mt-4 text-sm text-muted-foreground">
                <code>{`<Loader progress={100} message="Task completed!" />`}</code>
              </div>
            </div>
            
            <div className="glass-morphism-light rounded-xl p-6">
              <h3 className="text-lg font-medium mb-4">Custom Duration</h3>
              <Loader autoAnimate={true} duration={3000} message="Faster animation (3s)" />
              <div className="mt-4 text-sm text-muted-foreground">
                <code>{`<Loader autoAnimate={true} duration={3000} message="Faster animation (3s)" />`}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
