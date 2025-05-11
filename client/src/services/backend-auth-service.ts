import { User, AuthResponse, Session } from '@/interfaces/user';
import { apiClient } from './api-client';
import { supabase } from './supabase';

/**
 * Authentication service for communicating with the backend API
 */
export const backendAuthService = {
  /**
   * Sign up a new user with email and password
   */
  signUp: async (email: string, password: string): Promise<AuthResponse> => {
    try {
      // Check if we should use direct Supabase auth
      const useDirectSupabaseAuth = import.meta.env.VITE_USE_DIRECT_SUPABASE_AUTH === 'true';
      
      // Register with Supabase
      const supabaseResponse = await supabase.auth.signUp({
        email,
        password,
      });

      if (supabaseResponse.error) throw new Error(supabaseResponse.error.message);
      
      if (useDirectSupabaseAuth) {
        // Set the Supabase token in the API client
        apiClient.setAuthToken(supabaseResponse.data.session?.access_token || null);
        
        // The profile will be created automatically by the database trigger
        // or by the backend when we make the first API call
        
        // Get the user profile if we have a session
        let user = null;
        if (supabaseResponse.data.session) {
          try {
            user = await apiClient.get<User>('/users/me');
          } catch (e) {
            console.warn('Could not fetch user profile after signup:', e);
            // Continue without the user profile
          }
        }
        
        return {
          user,
          session: supabaseResponse.data.session,
          error: null,
        };
      } else {
        // Register with our backend (existing behavior)
        const user = await apiClient.post<User>('/auth/register', {
          email,
          password,
        });

        return {
          user,
          session: supabaseResponse.data.session,
          error: null,
        };
      }
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'An error occurred during sign up',
      };
    }
  },

  /**
   * Sign in with email and password
   */
  signInWithEmail: async (email: string, password: string): Promise<AuthResponse> => {
    try {
      // Check if we should use direct Supabase auth
      const useDirectSupabaseAuth = import.meta.env.VITE_USE_DIRECT_SUPABASE_AUTH === 'true';
      
      if (useDirectSupabaseAuth) {
        // Sign in with Supabase directly
        const supabaseResponse = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (supabaseResponse.error) throw new Error(supabaseResponse.error.message);

        // Set the Supabase token in the API client
        apiClient.setAuthToken(supabaseResponse.data.session?.access_token || null);

        // Get the user profile
        const user = await apiClient.get<User>('/users/me');

        return {
          user,
          session: supabaseResponse.data.session,
          error: null,
        };
      } else {
        // Use the backend login endpoint (existing behavior)
        const tokenResponse = await apiClient.post<{ access_token: string; token_type: string; expires_in: number }>('/auth/login', {
          username: email, // The backend expects 'username' due to OAuth2PasswordRequestForm
          password,
        });

        // Set the token in the API client
        apiClient.setAuthToken(tokenResponse.access_token);

        // Get the user profile
        const user = await apiClient.get<User>('/users/me');

        // Create a session object
        const session: Session = {
          access_token: tokenResponse.access_token,
          refresh_token: '', // We don't get a refresh token from the backend yet
          expires_at: Math.floor(Date.now() / 1000) + tokenResponse.expires_in,
          user: {
            id: user.id,
            email: user.email,
          },
        };

        return {
          user,
          session,
          error: null,
        };
      }
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Invalid email or password',
      };
    }
  },

  /**
   * Sign out
   */
  signOut: async (): Promise<AuthResponse> => {
    try {
      // Check if we should use direct Supabase auth
      const useDirectSupabaseAuth = import.meta.env.VITE_USE_DIRECT_SUPABASE_AUTH === 'true';
      
      if (useDirectSupabaseAuth) {
        // Sign out with Supabase directly
        const { error } = await supabase.auth.signOut();
        
        if (error) throw error;
      } else {
        // Call the backend logout endpoint
        await apiClient.post('/auth/logout');
      }
      
      // Clear the token from the API client
      apiClient.setAuthToken(null);

      return {
        user: null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to sign out',
      };
    }
  },

  /**
   * Get current session
   */
  getSession: async (): Promise<AuthResponse> => {
    try {
      // Try to get the user profile from the backend
      const user = await apiClient.get<User>('/users/me');

      // If we got the user, we have a valid session
      return {
        user,
        session: null, // We don't have the session details yet
        error: null,
      };
    } catch {
      // Clear the token if we got an authentication error
      apiClient.setAuthToken(null);
      
      return {
        user: null,
        session: null,
        error: null, // Don't return an error for session checks
      };
    }
  },

  /**
   * Reset password
   */
  resetPassword: async (email: string): Promise<AuthResponse> => {
    try {
      // Call the backend reset password endpoint
      await apiClient.post('/auth/reset-password', { email });

      return {
        user: null,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to send password reset email',
      };
    }
  },

  /**
   * Update password
   */
  updatePassword: async (newPassword: string): Promise<AuthResponse> => {
    try {
      // Call the backend change password endpoint
      await apiClient.post('/auth/change-password', { password: newPassword });

      return {
        user: null, // We don't get the user back from this endpoint
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to update password',
      };
    }
  },

  /**
   * Sign in with magic link (passwordless)
   */
  signInWithMagicLink: async (email: string): Promise<AuthResponse> => {
    try {
      // Use Supabase for magic link
      const supabaseResponse = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (supabaseResponse.error) throw new Error(supabaseResponse.error.message);

      // The token exchange and user fetching will happen in the callback
      // See AuthCallback component in main.tsx
      
      return {
        user: null, // User will be available after they click the magic link and token exchange
        session: supabaseResponse.data.session,
        error: null,
      };
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to send magic link',
      };
    }
  },

  /**
   * Sign in with Google OAuth
   */
  signInWithGoogle: async (): Promise<AuthResponse> => {
    try {
      console.log("Starting Google OAuth flow");
      
      // Log the redirect URL for debugging
      const redirectUrl = `${window.location.origin}/auth/callback`;
      console.log("OAuth redirect URL:", redirectUrl);
      
      // Use Supabase for Google OAuth
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUrl,
          scopes: 'email profile',
          queryParams: {
            prompt: 'select_account',
            access_type: 'offline'
          }
        },
      });

      console.log("OAuth initiation response:", data);
      
      if (error) {
        console.error("OAuth initiation error:", error);
        throw error;
      }

      // The token exchange and user fetching will happen in the callback
      console.log("OAuth flow started, redirecting to provider");
      
      return {
        user: null, // User will be available after OAuth redirect and token exchange
        session: null, // Session will be created after redirect
        error: null,
      };
    } catch (error: unknown) {
      console.error("Google OAuth error:", error);
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to sign in with Google',
      };
    }
  },

  /**
   * Sign in with Apple OAuth
   */
  signInWithApple: async (): Promise<AuthResponse> => {
    try {
      console.log("Starting Apple OAuth flow");
      
      // Log the redirect URL for debugging
      const redirectUrl = `${window.location.origin}/auth/callback`;
      console.log("OAuth redirect URL:", redirectUrl);
      
      // Use Supabase for Apple OAuth
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'apple',
        options: {
          redirectTo: redirectUrl,
        },
      });

      if (error) throw error;

      // The token exchange and user fetching will happen in the callback
      console.log("OAuth flow started, redirecting to provider");
      
      return {
        user: null, // User will be available after OAuth redirect and token exchange
        session: null, // Session will be created after redirect
        error: null,
      };
    } catch (error: unknown) {
      console.error("Apple OAuth error:", error);
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to sign in with Apple',
      };
    }
  },

  /**
   * Update user profile
   */
  updateProfile: async (userData: Partial<User>): Promise<AuthResponse> => {
    try {
      // Call the backend update profile endpoint
      const user = await apiClient.put<User>(`/users/${userData.id}`, userData);

      return {
        user,
        session: null,
        error: null,
      };
    } catch (error: unknown) {
      return {
        user: null,
        session: null,
        error: error instanceof Error ? error.message : 'Failed to update profile',
      };
    }
  },
};
