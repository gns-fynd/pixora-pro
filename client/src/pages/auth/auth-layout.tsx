import { ReactNode, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/shared/ThemeToggle';

interface AuthLayoutProps {
  children: ReactNode;
}

/**
 * Layout component for authentication pages with glassmorphism effect
 */
export const AuthLayout = ({ children }: AuthLayoutProps) => {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  // Only show the theme toggle after mounting to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);
  
  return (
    <div className={`h-screen ${theme === 'dark' ? 'bg-[#0A0A0F]' : 'bg-[#F0F2F5]'} font-['Space_Grotesk',sans-serif] relative overflow-hidden`}>
      {/* Enhanced animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Animated gradient background */}
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
      
      {/* Theme toggle */}
      {mounted && (
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
      )}
      
      {/* Logo */}
      <div className="absolute top-6 left-6">
        <Link to="/" className="flex items-center gap-2">
          <img 
            src={theme === "dark" ? "/logo-light.png" : "/logo-dark.png"} 
            alt="Pixora AI" 
            className="h-12" 
          />
        </Link>
      </div>
      
      {/* Content */}
      <div className="flex h-screen items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className={`glass-morphism rounded-2xl shadow-xl p-8 ${theme === 'dark' ? 'bg-[#0F0A19]/80' : 'bg-white/80'}`}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
