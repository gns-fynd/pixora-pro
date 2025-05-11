import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import useAuthStore from '@/store/use-auth-store';
import { IconArrowRight, IconAspectRatio, IconClock, IconPalette } from '@tabler/icons-react';
import { useTheme } from '@/components/theme-provider';
import Navbar from '@/components/shared/Navbar';
import { TypedPlaceholder } from '@/components/ui/typed-placeholder';

// Form schema for the prompt input
const promptSchema = z.object({
  prompt: z.string().min(10, 'Prompt must be at least 10 characters'),
  aspectRatio: z.enum(['16:9', '9:16', '1:1']).default('16:9'),
  duration: z.number().min(5).max(300).default(30),
  style: z.enum(['cinematic', 'cartoon', 'realistic', 'artistic']).default('cinematic'),
});

type PromptFormValues = z.infer<typeof promptSchema>;

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Input and form refs
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const [isInputFocused, setIsInputFocused] = useState(false);
  
  // Example prompts for the typing animation
  const examplePrompts = [
    "an Instagram reel about your product",
    "a promotional video for your business",
    "a cinematic trailer for your next project",
    "an explainer video for your app",
    "a product showcase with stunning visuals",
    "a social media ad that converts",
    "a travel montage of your latest adventure",
    "a tutorial video with step-by-step instructions",
    "a testimonial video highlighting customer stories",
    "a brand story that connects with your audience"
  ];
  
  // Initialize form with default values
  const form = useForm<PromptFormValues>({
    resolver: zodResolver(promptSchema),
    defaultValues: {
      prompt: '',
      aspectRatio: '16:9',
      duration: 30,
      style: 'cinematic',
    },
  });

  // Handle form submission
  const onSubmit = async (values: PromptFormValues) => {
    setIsSubmitting(true);
    
    try {
      // Store the prompt data in localStorage for now
      // In a real app, this would be sent to an API
      localStorage.setItem('pixora_prompt', JSON.stringify(values));
      
      // If user is authenticated, go to scene breakdown
      // Otherwise, go to auth page
      if (isAuthenticated) {
        navigate('/scene-breakdown');
      } else {
        navigate('/auth');
      }
    } catch (error) {
      console.error('Error submitting prompt:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // No need for click outside handler as the input is always expanded

  // Removed auto-focus effect to prevent stopping the animation

  const { theme } = useTheme();
  
  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'bg-[#0A0A0F]' : 'bg-[#F0F2F5]'} font-['Space_Grotesk',sans-serif] relative overflow-hidden`}>
      {/* Enhanced animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Toned down animated gradient background */}
        <div 
          className="absolute inset-0 bg-[size:200%_200%] animate-gradient-xy opacity-30"
          style={{
            backgroundImage: `
              radial-gradient(circle at 50% 0%, hsl(var(--primary)) 0%, transparent 60%),
              radial-gradient(circle at 85% 30%, hsl(var(--secondary)) 0%, transparent 60%),
              radial-gradient(circle at 15% 70%, hsl(var(--accent)) 0%, transparent 60%),
              radial-gradient(circle at 50% 100%, hsl(var(--primary)) 0%, transparent 60%),
              radial-gradient(circle at 20% 20%, rgba(147, 51, 234, 0.3) 0%, transparent 70%)
            `
          }}
        />
        
        {/* Moving gradient overlay - different for light and dark modes */}
        <div 
          className="absolute inset-0 animate-pulse-glow"
          style={{
            background: theme === 'dark' 
              ? `linear-gradient(45deg, 
                  rgba(0,0,0,0.2) 0%,
                  rgba(0,0,0,0.1) 100%
                )`
              : `linear-gradient(45deg, 
                  rgba(255,255,255,0.7) 0%,
                  rgba(255,255,255,0.5) 100%
                )`
          }}
        />
        
        {/* Grid pattern - different for light and dark modes */}
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: theme === 'dark'
              ? `
                linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
              `
              : `
                linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px)
              `,
            backgroundSize: '72px 72px',
            maskImage: 'radial-gradient(circle at 50% 50%, black 0%, transparent 80%)'
          }}
        />

        {/* Floating particles - different for light and dark modes */}
        <div className="absolute inset-0">
          {Array.from({ length: 30 }).map((_, i) => {
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const hue = Math.random() * 360;
            const delay = Math.random() * 5;
            const duration = 5 + Math.random() * 5;
            
            return (
              <div
                key={i}
                className="absolute w-1.5 h-1.5 rounded-full animate-float"
                style={{
                  left: `${left}%`,
                  top: `${top}%`,
                  background: theme === 'dark'
                    ? `hsla(${hue}, 70%, 70%, 0.15)`
                    : `hsla(${hue}, 70%, 40%, 0.15)`,
                  filter: 'blur(1px)',
                  animationDelay: `${delay}s`,
                  animationDuration: `${duration}s`
                }}
              />
            );
          })}
        </div>

        {/* Vignette effect - different for light and dark modes */}
        <div 
          className="absolute inset-0"
          style={{
            background: theme === 'dark'
              ? 'radial-gradient(circle at 50% 50%, transparent 0%, rgba(0,0,0,0.3) 100%)'
              : 'radial-gradient(circle at 50% 50%, transparent 0%, rgba(0,0,0,0.1) 100%)'
          }}
        />
      </div>
      
      {/* Navbar */}
      <Navbar transparent={true} showLinks={true} />
      
      {/* Main content - increased top padding by 15% */}
      <main className="relative z-10 px-4 pt-36 pb-12 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          {/* Hero section */}
          <div className="text-center mb-16">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              Create Amazing Videos with <span className="text-primary">AI</span>
            </h1>
            <p className="mt-6 text-lg text-foreground/70 max-w-3xl mx-auto">
              Transform your ideas into professional videos in minutes. Just describe what you want, and our AI will generate a complete video for you.
            </p>
          </div>
          
          {/* Prompt input section - simplified as per the second image */}
          <div className="max-w-3xl mx-auto">
            <form 
              ref={formRef}
              onSubmit={form.handleSubmit(onSubmit)} 
              className="relative"
            >
              {/* Static container with border */}
              <div className="relative rounded-[24px] p-[1px] overflow-hidden">
                {/* Static border */}
                <div 
                  className="absolute inset-0 bg-gradient-to-r from-[#4776E6] to-[#8E54E9] opacity-80"
                ></div>
                
                {/* Inner container */}
                <div 
                  className={`relative ${theme === 'dark' ? 'bg-[#0F0A19]' : 'bg-white/80'} backdrop-blur-sm rounded-[24px] p-6`}
                >
                  {/* Main input area */}
                  <div className="flex flex-col space-y-6">
                    {/* Input with typing animation */}
                    <div className="mb-6 relative">
                      {!isInputFocused ? (
                        <div 
                          className="w-full px-4 pt-2 h-[96px] flex items-start"
                          onClick={() => {
                            setIsInputFocused(true);
                            if (inputRef.current) {
                              inputRef.current.focus();
                            }
                          }}
                        >
                          <TypedPlaceholder
                            staticText="Ask Pixora to create&nbsp;"
                            examples={examplePrompts}
                            typingSpeed={80}
                            deletingSpeed={40}
                            delayAfterComplete={2000}
                            className="text-base"
                            onFocus={() => {
                              setIsInputFocused(true);
                              if (inputRef.current) {
                                inputRef.current.focus();
                              }
                            }}
                          />
                        </div>
                      ) : null}
                      <textarea
                        id="prompt"
                        rows={3}
                        className={`w-full bg-transparent border-none outline-none resize-none px-4 pt-2 pb-2 text-base text-foreground ${!isInputFocused ? 'opacity-0 absolute top-0 left-0' : ''}`}
                        placeholder={isInputFocused ? "Describe the video you want to create..." : ""}
                        {...form.register('prompt')}
                        style={{
                          height: 'auto',
                        }}
                        ref={(element) => {
                          inputRef.current = element;
                          const { ref } = form.register('prompt');
                          if (typeof ref === 'function') {
                            ref(element);
                          }
                        }}
                        onFocus={() => setIsInputFocused(true)}
                        onBlur={() => {
                          if (!inputRef.current?.value) {
                            setIsInputFocused(false);
                          }
                        }}
                      ></textarea>
                      {form.formState.errors.prompt && (
                        <p className="mt-1 text-sm text-red-500 px-4">
                          {form.formState.errors.prompt.message}
                        </p>
                      )}
                    </div>
                    
                    {/* Settings dropdowns and button - always visible */}
                    <div className="flex items-center justify-between gap-4">
                      {/* Dropdowns in a container with reduced width */}
                      <div className="flex gap-4 flex-1">
                        {/* Aspect ratio with icon */}
                        <div className="w-[120px]">
                          <div className="relative">
                            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                              <IconAspectRatio size={16} />
                            </div>
                            <select
                              id="aspectRatio"
                              className="w-full rounded-lg border border-border bg-background/5 pl-9 pr-3 py-2 text-sm text-foreground"
                              {...form.register('aspectRatio')}
                            >
                              <option value="16:9">16:9</option>
                              <option value="9:16">9:16</option>
                              <option value="1:1">1:1</option>
                            </select>
                          </div>
                        </div>
                        
                        {/* Duration with icon */}
                        <div className="w-[140px]">
                          <div className="relative">
                            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                              <IconClock size={16} />
                            </div>
                            <select
                              id="duration"
                              className="w-full rounded-lg border border-border bg-background/5 pl-9 pr-3 py-2 text-sm text-foreground"
                              {...form.register('duration', { valueAsNumber: true })}
                            >
                              <option value="30">30 seconds</option>
                              <option value="60">1 minute</option>
                              <option value="120">2 minutes</option>
                              <option value="180">3 minutes</option>
                            </select>
                          </div>
                        </div>
                        
                        {/* Style with icon */}
                        <div className="w-[140px]">
                          <div className="relative">
                            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-foreground/60">
                              <IconPalette size={16} />
                            </div>
                            <select
                              id="style"
                              className="w-full rounded-lg border border-border bg-background/5 pl-9 pr-3 py-2 text-sm text-foreground"
                              {...form.register('style')}
                            >
                              <option value="cinematic">Cinematic</option>
                              <option value="cartoon">Cartoon</option>
                              <option value="realistic">Realistic</option>
                              <option value="artistic">Artistic</option>
                            </select>
                          </div>
                        </div>
                      </div>
                      
                      {/* Generate button */}
                      <div>
                        <button 
                          type="submit"
                          disabled={isSubmitting}
                          className="flex items-center justify-center bg-primary hover:bg-primary/90 text-white rounded-full px-8 py-2"
                        >
                          {isSubmitting ? 'Processing...' : 'Generate Video'}
                          {!isSubmitting && <IconArrowRight size={18} className="ml-2" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </form>
          </div>
          
          {/* Suggested prompts section */}
          <div className="mt-6 max-w-4xl mx-auto">
            <h3 className="text-center text-lg text-foreground/70 mb-4">
              Try these examples:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button 
                className="example-prompt text-left"
                onClick={() => {
                  form.setValue('prompt', "Create a cinematic trailer for a sci-fi movie with epic space battles and futuristic technology", { shouldValidate: true });
                  setIsInputFocused(true);
                  if (inputRef.current) {
                    inputRef.current.focus();
                  }
                }}
              >
                Create a cinematic trailer for a sci-fi movie with epic space battles and futuristic technology
              </button>
              
              <button 
                className="example-prompt text-left"
                onClick={() => {
                  form.setValue('prompt', "Generate an explainer video about quantum computing with visual demonstrations and real-world applications", { shouldValidate: true });
                  setIsInputFocused(true);
                  if (inputRef.current) {
                    inputRef.current.focus();
                  }
                }}
              >
                Generate an explainer video about quantum computing with visual demonstrations and real-world applications
              </button>
              
              <button 
                className="example-prompt text-left"
                onClick={() => {
                  form.setValue('prompt', "Make a product showcase for a new smartphone highlighting its innovative features and design", { shouldValidate: true });
                  setIsInputFocused(true);
                  if (inputRef.current) {
                    inputRef.current.focus();
                  }
                }}
              >
                Make a product showcase for a new smartphone highlighting its innovative features and design
              </button>
              
              <button 
                className="example-prompt text-left"
                onClick={() => {
                  form.setValue('prompt', "Create a nature documentary about deep sea creatures exploring their unique adaptations and behaviors", { shouldValidate: true });
                  setIsInputFocused(true);
                  if (inputRef.current) {
                    inputRef.current.focus();
                  }
                }}
              >
                Create a nature documentary about deep sea creatures exploring their unique adaptations and behaviors
              </button>
            </div>
          </div>
        </div>
      </main>
      
      {/* Footer */}
      <footer className="relative z-10 px-4 py-12 sm:px-6 lg:px-8 border-t border-border/20">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center mb-4 md:mb-0">
              <img 
                src={useTheme().theme === "dark" ? "/logo-light.png" : "/logo-dark.png"} 
                alt="Pixora AI" 
                className="h-10" 
              />
            </div>
            <div className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} Pixora AI. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
