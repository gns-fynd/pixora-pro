import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '@/store/use-auth-store';
import { supabase } from '@/services/supabase';
import { apiClient } from '@/services/api-client';

/**
 * Auth callback handler component for processing OAuth and magic link redirects
 */
export const AuthCallback = () => {
  const navigate = useNavigate();
  const { checkSession } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Parse error from URL if present
    const params = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    
    console.log('Auth callback triggered');
    console.log('URL params:', window.location.search);
    console.log('Hash params:', window.location.hash);
    
    const errorMsg = params.get('error_description') || hashParams.get('error_description');
    if (errorMsg) {
      setError(decodeURIComponent(errorMsg));
      console.error('Auth error:', errorMsg);
      return;
    }
    
    // Handle the callback
    const handleCallback = async () => {
      try {
        // Get the Supabase session
        const { data, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          throw new Error(`Session error: ${sessionError.message}`);
        }
        
        console.log('Session data:', data);
        
        if (!data.session?.access_token) {
          throw new Error('No session found');
        }
        
        // Determine if this is an SSO authentication by checking the provider
        const provider = data.session?.user?.app_metadata?.provider;
        const isSSO = !!provider;
        console.log('Authentication provider:', provider || 'email/password');
        
        // Always exchange the token with the backend for all auth types
        console.log('Exchanging token with backend');
        
        let tokenExchangeSuccessful = false;
        
        try {
          // Exchange the Supabase token for a backend token
          // Adjust the URL path to match the backend API structure
          const apiUrl = import.meta.env.VITE_API_URL;
          // Remove '/api/v1' if it's included in the URL to avoid path duplication
          const baseUrl = apiUrl.endsWith('/api/v1') 
            ? apiUrl.replace('/api/v1', '') 
            : apiUrl;
          
          console.log(`Making token exchange request to ${baseUrl}/api/auth/token`);
          
          const response = await fetch(`${baseUrl}/api/auth/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${data.session.access_token}`
            },
            credentials: 'include', // Important: This enables sending/receiving cookies
            body: JSON.stringify({ token: data.session.access_token }) // Explicitly include token in body
          });
          
          console.log(`Token exchange response status: ${response.status}`);
          
          if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`Token exchange failed: ${response.status} - ${errorData}`);
          }
          
          const tokenData = await response.json();
          console.log('Token exchange successful:', tokenData);
          
          // Set the backend token in the API client
          apiClient.setAuthToken(tokenData.access_token);
          tokenExchangeSuccessful = true;
        } catch (exchangeError) {
          console.error('Token exchange error:', exchangeError);
          // For SSO users, token exchange is critical - throw the error
          if (isSSO) {
            throw exchangeError;
          }
          // For non-SSO users, we can try to continue with the Supabase token
          console.warn('Continuing with Supabase token as fallback');
        }
        
        // Now check the session to get the user profile
        // Add a small delay to ensure token is properly set
        if (tokenExchangeSuccessful) {
          // Small delay to ensure token is properly processed
          await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        await checkSession();
        
        // Redirect to the home page
        navigate('/');
      } catch (err) {
        console.error('Auth callback error:', err);
        setError(err instanceof Error ? err.message : 'Failed to authenticate. Please try again.');
      }
    };
    
    handleCallback();
  }, [checkSession, navigate]);
  
  if (error) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-background to-background/80 dark:from-background dark:to-background/90">
        <div className="space-y-4 text-center max-w-md p-6 bg-white/5 rounded-lg border border-white/10">
          <div className="text-red-500 text-xl">Authentication Error</div>
          <p className="text-muted-foreground">{error}</p>
          <button 
            onClick={() => navigate('/auth')}
            className="px-4 py-2 bg-primary text-white rounded-md"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-background to-background/80 dark:from-background dark:to-background/90">
      <div className="space-y-4 text-center">
        <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto"></div>
        <p className="text-muted-foreground">Authenticating...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
