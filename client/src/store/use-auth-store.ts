import { User } from "@/interfaces/user";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { authService } from "@/services/auth-service";

/**
 * Auth store state interface
 */
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isInitialized: boolean; // Indicates if auth has completed initialization
}

/**
 * Auth store actions interface
 */
interface AuthActions {
  // Auth methods
  signUp: (email: string, password: string) => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signInWithMagicLink: (email: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signInWithApple: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
  signOut: () => Promise<void>;
  
  // Profile methods
  updateProfile: (userData: Partial<User>) => Promise<void>;
  
  // Session management
  checkSession: () => Promise<void>;
  initializeAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
}

/**
 * Combined auth store type
 */
type AuthStore = AuthState & AuthActions;

/**
 * Helper to handle errors consistently
 */
const handleError = (error: unknown): string => {
  return error instanceof Error ? error.message : 'An unexpected error occurred';
};

// Global auth initialization promise to prevent race conditions
let authInitPromise: Promise<void> | null = null;

// Function to initialize auth - used by both initializeAuth and checkSession
const initializeAuthLogic = async (
  set: (fn: (state: AuthState) => void) => void
): Promise<void> => {
  // If we already have an initialization promise, return it
  if (authInitPromise) {
    return authInitPromise;
  }
  
  // Create a new initialization promise
  authInitPromise = (async () => {
    set((state) => {
      state.isLoading = true;
      state.isInitialized = false;
    });
    
    try {
      // Check if we have a cached session state
      const cachedState = localStorage.getItem('pixora_auth_state');
      const cachedExpiry = localStorage.getItem('pixora_auth_state_expiry');
      
      // If we have valid cached state, use it
      if (cachedState && cachedExpiry) {
        try {
          const expiryTime = parseInt(cachedExpiry, 10);
          
          // If the cached state is still valid (not expired)
          if (expiryTime > Date.now()) {
            console.debug('Using cached auth state');
            const authState = JSON.parse(cachedState);
            
      // Update state with cached data
      set((state) => {
        state.user = authState.user;
        state.isAuthenticated = !!authState.user;
        state.error = null;
        state.isInitialized = true;
      });
            
            return;
          }
        } catch (err) {
          console.error('Error parsing cached auth state:', err);
          // Continue with API call if parsing fails
        }
      }
      
      // Get the session from the auth service
      const { user, error } = await authService.getSession();
      
      if (error) {
        throw new Error(error);
      }
      
      // Update state
      set((state) => {
        state.user = user;
        state.isAuthenticated = !!user;
        state.error = null;
        state.isInitialized = true;
      });
      
      // Cache the auth state (valid for 5 minutes)
      try {
        const authState = { user };
        localStorage.setItem('pixora_auth_state', JSON.stringify(authState));
        const expiryTime = Date.now() + (5 * 60 * 1000); // 5 minutes
        localStorage.setItem('pixora_auth_state_expiry', expiryTime.toString());
      } catch (cacheError) {
        console.error('Error caching auth state:', cacheError);
      }
    } catch (error) {
      set((state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.error = handleError(error);
        state.isInitialized = true;
      });
    } finally {
      set((state) => {
        state.isLoading = false;
      });
      
      // Clear the promise after completion
      setTimeout(() => {
        if (authInitPromise) {
          authInitPromise = null;
        }
      }, 100);
    }
  })();
  
  return authInitPromise;
};

/**
 * Auth store implementation
 */
const useAuthStore = create<AuthStore>()(
  immer((set) => ({
    // Initial state
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    isInitialized: false,
    
    // Set user action
    setUser: (user) => set((state) => {
      state.user = user;
      state.isAuthenticated = !!user;
      state.error = null;
    }),
    
    // Sign up action
    signUp: async (email, password) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { user, error } = await authService.signUp(email, password);
        
        if (error) {
          throw new Error(error);
        }
        
        set((state) => {
          state.user = user;
          state.isAuthenticated = !!user;
          state.error = null;
        });
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Sign in with email action
    signInWithEmail: async (email, password) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { user, error } = await authService.signInWithEmail(email, password);
        
        if (error) {
          throw new Error(error);
        }
        
        set((state) => {
          state.user = user;
          state.isAuthenticated = !!user;
          state.error = null;
        });
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Sign in with magic link action
    signInWithMagicLink: async (email) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { error } = await authService.signInWithMagicLink(email);
        
        if (error) {
          throw new Error(error);
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Sign in with Google action
    signInWithGoogle: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { error } = await authService.signInWithGoogle();
        
        if (error) {
          throw new Error(error);
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Sign in with Apple action
    signInWithApple: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { error } = await authService.signInWithApple();
        
        if (error) {
          throw new Error(error);
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Reset password action
    resetPassword: async (email) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { error } = await authService.resetPassword(email);
        
        if (error) {
          throw new Error(error);
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Update password action
    updatePassword: async (newPassword) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { user, error } = await authService.updatePassword(newPassword);
        
        if (error) {
          throw new Error(error);
        }
        
        if (user) {
          set((state) => {
            state.user = user;
          });
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Sign out action
    signOut: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { error } = await authService.signOut();
        
        if (error) {
          throw new Error(error);
        }
        
        set((state) => {
          state.user = null;
          state.isAuthenticated = false;
        });
        
        // Reset the auth initialization promise
        authInitPromise = null;
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Update profile action
    updateProfile: async (userData) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      try {
        const { user, error } = await authService.updateProfile(userData);
        
        if (error) {
          throw new Error(error);
        }
        
        if (user) {
          set((state) => {
            state.user = user;
          });
        }
      } catch (error) {
        set((state) => {
          state.error = handleError(error);
        });
      } finally {
        set((state) => {
          state.isLoading = false;
        });
      }
    },
    
    // Initialize auth with race condition prevention
    initializeAuth: async () => {
      return initializeAuthLogic(set);
    },
    
    // Check session action (uses the same logic as initializeAuth)
    checkSession: async () => {
      return initializeAuthLogic(set);
    },
  }))
);

export default useAuthStore;
