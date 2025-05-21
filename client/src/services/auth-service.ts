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

// Global auth initialization promise to prevent race conditions
let authInitPromise: Promise<AuthResponse> | null = null;

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

      // If we have a session, exchange the token
      if (data.session?.access_token) {
        await authService.exchangeToken(data.session.access_token);
      }

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

      // Exchange the token for a backend token
      if (data.session?.access_token) {
        await authService.exchangeToken(data.session.access_token);
      }

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
      // First, clear all local storage and cookies
      authClient.clearAuthToken();
      
      // Clear all cached auth state
      try {
        localStorage.removeItem('pixora_auth_state');
        localStorage.removeItem('pixora_auth_state_expiry');
        localStorage.removeItem('pixora_user_credits');
        localStorage.removeItem('pixora_user_credits_expiry');
      } catch (cacheError) {
        console.error('Error clearing cached auth state:', cacheError);
      }
      
      // Make a request to the logout endpoint to clear server-side cookies
      await apiClient.logout();
      
      // Then sign out from Supabase
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      // Clear API client state
      apiClient.clearAllRequests();
      
      // Reset auth initialization promise
      authInitPromise = null;
      
      return {
        user: null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      console.error('Error during sign out:', error);
      
      // Even if there's an error, clear local state
      authClient.clearAuthToken();
      apiClient.clearAllRequests();
      authInitPromise = null;
      
      return createErrorResponse(error, 'Failed to sign out');
    }
  },

  /**
   * Exchange a Supabase token for a backend token
   * This is used after OAuth sign-in or when refreshing the session
   */
  exchangeToken: async (supabaseToken: string): Promise<boolean> => {
    try {
      // Adjust the URL path to match the backend API structure
      const apiUrl = import.meta.env.VITE_API_URL;
      const baseUrl = apiUrl.endsWith('/api/v1') 
        ? apiUrl.replace('/api/v1', '') 
        : apiUrl;
      
      const response = await fetch(`${baseUrl}/api/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${supabaseToken}`
        },
        body: JSON.stringify({ token: supabaseToken }),
        credentials: 'include' // Important: This enables sending/receiving cookies
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to exchange token: ${response.status} - ${errorText}`);
      }
      
      const tokenData = await response.json();
      
      if (tokenData.success) {
        console.debug('Successfully exchanged token');
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error exchanging token:', error);
      return false;
    }
  },
  
  /**
   * Get current session with global initialization promise to prevent race conditions
   */
  getSession: async (): Promise<AuthResponse> => {
    // If we already have an initialization promise, return it
    if (authInitPromise) {
      return authInitPromise;
    }
    
    // Create a new initialization promise
    authInitPromise = (async () => {
      try {
        console.log('Performing session check');
        
        // First try to get the user profile directly from the backend
        // This will work if we have a valid cookie
        try {
          const backendUser = await apiClient.get<User>('/api/users/me');
          console.log('Successfully got user profile from backend');
          
          // If we got the user, we have a valid session
          return {
            user: backendUser,
            session: null, // We don't need the session details
            error: null,
          };
        } catch (backendError) {
          console.log('Could not get user profile from backend, falling back to Supabase:', backendError);
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
        
        // Exchange the token for a backend token
        if (sessionData.session?.access_token) {
          await authService.exchangeToken(sessionData.session.access_token);
        }
  
        // We only set up the auth state change listener once
        if (!window._authListenerInitialized) {
          window._authListenerInitialized = true;
          
          supabase.auth.onAuthStateChange(async (event, newSession) => {
            console.log('Auth state changed:', event);
            if (event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN') {
              console.log('Token refreshed or signed in, new session:', newSession?.expires_at);
              
              // Exchange the token for a backend token
              if (newSession?.access_token) {
                await authService.exchangeToken(newSession.access_token);
              }
              
              // Reset the auth initialization promise so it will be refreshed on next check
              authInitPromise = null;
            } else if (event === 'SIGNED_OUT') {
              console.log('Signed out');
              // Reset the auth initialization promise
              authInitPromise = null;
              
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
      } finally {
        // Reset the promise after a delay to allow for subsequent checks
        setTimeout(() => {
          authInitPromise = null;
        }, 5000);
      }
    })();
    
    return authInitPromise;
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

// Add the auth listener initialized flag to the window object
declare global {
  interface Window {
    _authListenerInitialized?: boolean;
  }
}
