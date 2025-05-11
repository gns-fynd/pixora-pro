import { useState } from 'react';
import { Link } from 'react-router-dom';
import { IconChevronDown, IconUser, IconSettings, IconLogout } from '@tabler/icons-react';
import useAuthStore from '@/store/use-auth-store';
import { useTheme } from '@/components/theme-provider';
import { ThemeToggle } from './ThemeToggle';

interface NavbarProps {
  transparent?: boolean;
  showLinks?: boolean;
}

export default function Navbar({ transparent = true, showLinks = true }: NavbarProps) {
  const { isAuthenticated, signOut, user } = useAuthStore();
  const { theme } = useTheme();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  // Handle sign out
  const handleSignOut = async () => {
    if (signOut) {
      await signOut();
    }
    setIsDropdownOpen(false);
  };
  
  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
      <nav className="max-w-7xl mx-auto">
        <div className={`${transparent ? 'glass-morphism-light' : 'bg-background'} rounded-full px-8 py-4 flex items-center justify-between`}>
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center">
              <img 
                src={theme === "dark" ? "/logo-light.png" : "/logo-dark.png"} 
                alt="Pixora AI" 
                className="h-8" 
              />
            </Link>
            
            {showLinks && (
              <div className="hidden md:flex items-center gap-6">
                <a href="#features" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Features
                </a>
                <a href="#pricing" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Pricing
                </a>
                <a href="#about" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  About
                </a>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            <ThemeToggle />
            {isAuthenticated ? (
              <div className="relative">
                <button 
                  className="flex items-center gap-2 hover:bg-white/10 px-3 py-2 rounded-lg transition-colors"
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                >
                  {user?.avatarUrl ? (
                    <div className="h-8 w-8 rounded-full overflow-hidden">
                      <img 
                        src={user.avatarUrl} 
                        alt={user.name || "User"} 
                        className="h-full w-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                      <span className="text-primary font-medium">
                        {user?.name?.charAt(0) || user?.email?.charAt(0) || "U"}
                      </span>
                    </div>
                  )}
                  <span className="text-sm font-medium">
                    {user?.name || "User"}
                  </span>
                  <IconChevronDown className="h-4 w-4 text-foreground/60" />
                </button>
                
                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 glass-morphism rounded-lg shadow-lg overflow-hidden">
                    <div className="py-1">
                      <Link 
                        to="/dashboard" 
                        className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
                        onClick={() => setIsDropdownOpen(false)}
                      >
                        <IconUser className="h-4 w-4" />
                        Dashboard
                      </Link>
                      <Link 
                        to="/profile" 
                        className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-white/10 transition-colors"
                        onClick={() => setIsDropdownOpen(false)}
                      >
                        <IconSettings className="h-4 w-4" />
                        Profile
                      </Link>
                      <button 
                        className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-white/10 transition-colors w-full text-left"
                        onClick={handleSignOut}
                      >
                        <IconLogout className="h-4 w-4" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link to="/auth" className="text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Sign In
                </Link>
                <Link 
                  to="/auth/sign-up" 
                  className="px-5 py-2.5 rounded-lg bg-primary/90 hover:bg-primary transition-colors text-primary-foreground text-sm font-medium"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
