import { supabase } from './supabase';
import { User, AuthResponse } from '@/interfaces/user';
import { User as SupabaseUser } from '@supabase/supabase-js';
import { authClient } from './auth-client';
import { apiClient } from './api-client';

/**
 * Map Supabase user to our User interface
 */
const mapSupabaseUser = (supabaseUser: SupabaseUser): User => {
  // Get the role from app_metadata, defaulting to 'user' if not present
  const role = supabaseUser.app_metadata?.role as 'user' | 'admin' || 'user';
  
  return {
    id: supabaseUser.id,
    email: supabaseUser.email || '',
    name: supabaseUser.user_metadata?.full_name || '',
    avatarUrl: supabaseUser.user_metadata?.avatar_url || '',
    role,
    credits: 0, // Will be updated by fetchUserCredits
  };
};

/**
 * Create a standard error response
 */
const createErrorResponse = (error: unknown, defaultMessage: string): AuthResponse => ({
  user: null,
  session: null,
  error: error instanceof Error ? error.message : defaultMessage,
});

/**
 * Authentication service for handling all auth operations with Supabase
 */
export const authService = {
  /**
   * Sign up a new user with email and password
   */
  signUp: async (email: string, password: string): Promise<AuthResponse> => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) throw error;

      return {
        user: data.user ? mapSupabaseUser(data.user) : null,
        session: data.session,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'An error occurred during sign up');
    }
  },

  /**
   * Sign in with email and password
   */
  signInWithEmail: async (email: string, password: string): Promise<AuthResponse> => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      return {
        user: data.user ? mapSupabaseUser(data.user) : null,
        session: data.session,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Invalid email or password');
    }
  },

  /**
   * Sign in with magic link (passwordless)
   */
  signInWithMagicLink: async (email: string): Promise<AuthResponse> => {
    try {
      const { data, error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) throw error;

      return {
        user: null, // User will be available after they click the magic link
        session: data.session,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to send magic link');
    }
  },

  /**
   * Sign in with Google OAuth
   */
  signInWithGoogle: async (): Promise<AuthResponse> => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) throw error;

      return {
        user: null, // User will be available after OAuth redirect
        session: null, // Session will be created after redirect
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to sign in with Google');
    }
  },

  /**
   * Sign in with Apple OAuth
   */
  signInWithApple: async (): Promise<AuthResponse> => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'apple',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) throw error;

      return {
        user: null, // User will be available after OAuth redirect
        session: null, // Session will be created after redirect
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to sign in with Apple');
    }
  },

  /**
   * Reset password
   */
  resetPassword: async (email: string): Promise<AuthResponse> => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });

      if (error) throw error;

      return {
        user: null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to send password reset email');
    }
  },

  /**
   * Update password
   */
  updatePassword: async (newPassword: string): Promise<AuthResponse> => {
    try {
      const { data, error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) throw error;

      return {
        user: data.user ? mapSupabaseUser(data.user) : null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to update password');
    }
  },

  /**
   * Sign out
   */
  signOut: async (): Promise<AuthResponse> => {
    try {
      const { error } = await supabase.auth.signOut();

      if (error) throw error;
      
      // Clear auth client token
      authClient.clearAuthToken();
      
      // Clear all ongoing API requests
      apiClient.clearAllRequests();
      
      // Clear cached auth state
      try {
        localStorage.removeItem('pixora_auth_state');
        localStorage.removeItem('pixora_auth_state_expiry');
      } catch (cacheError) {
        console.error('Error clearing cached auth state:', cacheError);
      }

      return {
        user: null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to sign out');
    }
  },

  // Debounce mechanism to prevent multiple simultaneous session checks
  _lastSessionCheck: 0,
  _sessionCheckPromise: null as Promise<AuthResponse> | null,
  
  /**
   * Get current session with debouncing to prevent infinite loops
   */
  getSession: async (): Promise<AuthResponse> => {
    const now = Date.now();
    
    // If we've checked the session in the last 2 seconds, return the cached promise
    if (now - authService._lastSessionCheck < 2000 && authService._sessionCheckPromise) {
      console.log('Using cached session check (debounced)');
      return authService._sessionCheckPromise;
    }
    
    // Update the last check time
    authService._lastSessionCheck = now;
    
    // Create a new promise for this check
    authService._sessionCheckPromise = (async () => {
      try {
        console.log('Performing session check');
        
          // First try to get the user profile directly from the backend
          // This will work if we've already exchanged the token
          try {
            const backendUser = await apiClient.get<User>('/api/users/me');
            console.log('Successfully got user profile from backend');
            
            // If we got the user, we have a valid session
            return {
              user: backendUser,
              session: null, // We don't need the session details
              error: null,
            };
          } catch (error) {
            console.log('Could not get user profile from backend, falling back to Supabase:', error);
            // Fall back to Supabase if backend request fails
          }
        
        // If backend request failed, try Supabase
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  
        if (sessionError) throw sessionError;
  
        if (!sessionData.session) {
          console.log('No active Supabase session found');
          return {
            user: null,
            session: null,
            error: null,
          };
        }
  
        // If we have a session, get the user data
        const { data: userData, error: userError } = await supabase.auth.getUser();
  
        if (userError) throw userError;
  
        // We only set up the auth state change listener once
        if (!window._authListenerInitialized) {
          window._authListenerInitialized = true;
          
          supabase.auth.onAuthStateChange((event, newSession) => {
            console.log('Auth state changed:', event);
            if (event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN') {
              console.log('Token refreshed or signed in, new session:', newSession?.expires_at);
              // Don't call checkSession here - it will be handled by the Root component
            } else if (event === 'SIGNED_OUT') {
              console.log('Signed out');
              // You might want to redirect to login page here
              window.location.href = '/auth';
            }
          });
        }
        
        // Create the user object
        let user = null;
        if (userData.user) {
          user = mapSupabaseUser(userData.user);
          
          // Fetch and update credits
          if (user) {
            const credits = await authClient.getUserCredits();
            user.credits = credits;
          }
        }
  
        return {
          user,
          session: sessionData.session,
          error: null,
        };
      } catch (error: unknown) {
        console.error('Session retrieval error:', error);
        return createErrorResponse(error, 'Failed to get session');
      }
    })();
    
    return authService._sessionCheckPromise;
  },

  /**
   * Update user profile
   */
  updateProfile: async (userData: Partial<User>): Promise<AuthResponse> => {
    try {
      const { data, error } = await supabase.auth.updateUser({
        data: {
          full_name: userData.name,
          avatar_url: userData.avatarUrl,
        },
      });

      if (error) throw error;

      return {
        user: data.user ? mapSupabaseUser(data.user) : null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return createErrorResponse(error, 'Failed to update profile');
    }
  },
};
