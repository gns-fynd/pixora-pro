interface VideoGenerationStep {
  id: string;
  label: string;
  icon: 'video' | 'audio' | 'music' | 'transcript';
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
}

interface CompactVideoGenerationLoaderProps {
  isVisible: boolean;
  overallProgress: number;
  steps: VideoGenerationStep[];
  message?: string;
}

export function CompactVideoGenerationLoader({
  isVisible,
  overallProgress,
  steps,
  message = 'Generating your video...'
}: CompactVideoGenerationLoaderProps) {
  if (!isVisible) return null;

  return (
    <div className="p-4 bg-primary/5 border-b border-primary/20">
      <div className="mb-2 flex justify-between items-center">
        <h3 className="text-sm font-medium">{message}</h3>
        <span className="text-xs text-muted-foreground">{overallProgress}%</span>
      </div>
      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden mb-3">
        <div 
          className="h-full bg-primary rounded-full transition-all duration-300 ease-out"
          style={{ width: `${overallProgress}%` }}
        />
      </div>
      <div className="grid grid-cols-5 gap-1">
        {steps.map((step) => (
          <div key={step.id} className="text-center">
            <div 
              className={`h-1 w-full rounded-full mb-1 ${
                step.status === 'completed' ? 'bg-green-500' :
                step.status === 'processing' ? 'bg-primary' :
                step.status === 'error' ? 'bg-red-500' : 'bg-muted-foreground/30'
              }`}
            />
            <span className="text-[10px] text-muted-foreground truncate block">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
