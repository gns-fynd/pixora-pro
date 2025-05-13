import { supabase } from './supabase';

// API base URL - will be different in development vs production
const API_BASE_URL = import.meta.env.VITE_API_URL;

// Constants for token management
const TOKEN_STORAGE_KEY = 'pixora_auth_token';
const TOKEN_EXPIRY_KEY = 'pixora_auth_token_expiry';
const CREDITS_STORAGE_KEY = 'pixora_user_credits';
const CREDITS_EXPIRY_KEY = 'pixora_user_credits_expiry';
const TOKEN_REFRESH_COOLDOWN_MS = 10000; // 10 seconds cooldown between token refreshes
const CREDITS_CACHE_DURATION_MS = 300000; // 5 minutes cache for credits

// Circuit breaker settings
const MAX_AUTH_FAILURES = 5;
const CIRCUIT_BREAKER_RESET_MS = 60000; // 1 minute

/**
 * Auth client for handling authentication-related requests
 */
class AuthClient {
  private authToken: string | null = null;
  private tokenExpiryTime: number = 0;
  private lastTokenRefresh: number = 0;
  private authFailureCount: number = 0;
  private circuitBreakerTripped: boolean = false;
  private circuitBreakerResetTimeout: NodeJS.Timeout | null = null;
  
  constructor() {
    // Try to load token from localStorage on initialization
    this.loadTokenFromStorage();
  }
  
  /**
   * Load token from localStorage
   */
  private loadTokenFromStorage(): void {
    try {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      const storedExpiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
      
      if (storedToken && storedExpiry) {
        const expiryTime = parseInt(storedExpiry, 10);
        
        // Only use the stored token if it's not expired
        if (expiryTime > Date.now()) {
          console.debug('Using stored auth token from localStorage');
          this.authToken = storedToken;
          this.tokenExpiryTime = expiryTime;
        } else {
          console.debug('Stored auth token is expired, will refresh');
          // Clear expired token
          this.clearTokenStorage();
        }
      }
    } catch (error) {
      console.error('Error loading token from localStorage:', error);
      this.clearTokenStorage();
    }
  }
  
  /**
   * Save token to localStorage with expiry
   */
  private saveTokenToStorage(token: string, expiryTime: number): void {
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
    } catch (error) {
      console.error('Error saving token to localStorage:', error);
    }
  }
  
  /**
   * Clear token from localStorage
   */
  private clearTokenStorage(): void {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(TOKEN_EXPIRY_KEY);
      this.authToken = null;
      this.tokenExpiryTime = 0;
    } catch (error) {
      console.error('Error clearing token from localStorage:', error);
    }
  }
  
  /**
   * Check if circuit breaker is tripped
   */
  private checkCircuitBreaker(): boolean {
    if (this.circuitBreakerTripped) {
      console.warn('Circuit breaker is tripped, blocking auth requests');
      return true;
    }
    
    return false;
  }
  
  /**
   * Trip the circuit breaker after too many failures
   */
  private tripCircuitBreaker(): void {
    this.circuitBreakerTripped = true;
    console.warn('Circuit breaker tripped due to too many auth failures');
    
    // Reset the circuit breaker after a timeout
    this.circuitBreakerResetTimeout = setTimeout(() => {
      console.debug('Resetting circuit breaker');
      this.circuitBreakerTripped = false;
      this.authFailureCount = 0;
    }, CIRCUIT_BREAKER_RESET_MS);
  }
  
  /**
   * Record an auth failure and potentially trip the circuit breaker
   */
  private recordAuthFailure(): void {
    this.authFailureCount++;
    
    if (this.authFailureCount >= MAX_AUTH_FAILURES) {
      this.tripCircuitBreaker();
    }
  }
  
  /**
   * Reset auth failure count after successful auth
   */
  private resetAuthFailureCount(): void {
    this.authFailureCount = 0;
  }
  
  /**
   * Get the auth token, refreshing if necessary
   */
  async getAuthToken(): Promise<string | null> {
    // If circuit breaker is tripped, block the request
    if (this.checkCircuitBreaker()) {
      return null;
    }
    
    // If we have a valid token that's not expired, return it
    if (this.authToken && this.tokenExpiryTime > Date.now()) {
      return this.authToken;
    }
    
    // Check if we're in the cooldown period after a token refresh
    const now = Date.now();
    if (now - this.lastTokenRefresh < TOKEN_REFRESH_COOLDOWN_MS) {
      console.debug('In token refresh cooldown period, using existing token');
      return this.authToken;
    }
    
    // Update the last token refresh time
    this.lastTokenRefresh = now;
    
    try {
      // Get the Supabase session
      const { data, error } = await supabase.auth.getSession();
      
      if (error) {
        console.error('Error getting Supabase session:', error);
        this.recordAuthFailure();
        return null;
      }
      
      if (!data.session?.access_token) {
        console.debug('No Supabase session available');
        return null;
      }
      
      // Try to get a backend-specific token with retry logic
      let retryCount = 0;
      const maxRetries = 3;
      
      while (retryCount < maxRetries) {
        try {
          console.debug(`Token exchange attempt ${retryCount + 1}/${maxRetries}`);
          
          const response = await fetch(`${API_BASE_URL}/auth/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${data.session.access_token}`
            },
            body: JSON.stringify({ token: data.session.access_token })
          });
          
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to get backend token: ${response.status} - ${errorText}`);
          }
          
          const tokenData = await response.json();
          
          if (tokenData.access_token) {
            console.debug('Using backend-specific token');
            
            // Calculate expiry time (default to 1 hour if not provided)
            const expirySeconds = tokenData.expires_in || 3600;
            const expiryTime = now + (expirySeconds * 1000);
            
            // Save the token
            this.authToken = tokenData.access_token;
            this.tokenExpiryTime = expiryTime;
            
            // Save to localStorage
            if (this.authToken) {
              this.saveTokenToStorage(this.authToken, this.tokenExpiryTime);
            }
            
            // Reset auth failure count
            this.resetAuthFailureCount();
            
            return this.authToken;
          }
          
          // If we get here, something went wrong but didn't throw an error
          throw new Error('Token response did not contain access_token');
        } catch (tokenError) {
          retryCount++;
          
          if (retryCount >= maxRetries) {
            console.error(`Error getting backend token after ${maxRetries} attempts:`, tokenError);
            this.recordAuthFailure();
            
            // Fallback to using Supabase token directly
            console.debug('Falling back to Supabase token');
            this.authToken = data.session.access_token;
            
            // Calculate expiry time from the Supabase session
            if (data.session.expires_at) {
              const expiryTime = new Date(data.session.expires_at).getTime();
              this.tokenExpiryTime = expiryTime;
              
              // Save to localStorage
              this.saveTokenToStorage(this.authToken, this.tokenExpiryTime);
            }
            
            return this.authToken;
          }
          
          // Wait before retrying (exponential backoff)
          const waitTime = Math.pow(2, retryCount) * 1000;
          console.log(`Retrying token exchange in ${waitTime}ms (attempt ${retryCount}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error in auth token acquisition:', error);
      this.recordAuthFailure();
      return null;
    }
  }
  
  /**
   * Clear the auth token (e.g., on logout)
   */
  clearAuthToken(): void {
    this.clearTokenStorage();
    
    // Also clear credits cache
    try {
      localStorage.removeItem(CREDITS_STORAGE_KEY);
      localStorage.removeItem(CREDITS_EXPIRY_KEY);
    } catch (error) {
      console.error('Error clearing credits cache:', error);
    }
    
    // Reset circuit breaker and auth failure count
    this.authFailureCount = 0;
    this.circuitBreakerTripped = false;
    if (this.circuitBreakerResetTimeout) {
      clearTimeout(this.circuitBreakerResetTimeout);
      this.circuitBreakerResetTimeout = null;
    }
  }
  
  /**
   * Get user credits with caching
   */
  async getUserCredits(): Promise<number> {
    try {
      // Check if we have cached credits
      const cachedCredits = localStorage.getItem(CREDITS_STORAGE_KEY);
      const cachedExpiry = localStorage.getItem(CREDITS_EXPIRY_KEY);
      
      if (cachedCredits && cachedExpiry) {
        const expiryTime = parseInt(cachedExpiry, 10);
        
        // Use cached credits if not expired
        if (expiryTime > Date.now()) {
          console.debug('Using cached user credits');
          return parseInt(cachedCredits, 10);
        }
      }
      
      // Get auth token
      const token = await this.getAuthToken();
      
      if (!token) {
        console.error('No access token available to fetch credits');
        return 0;
      }
      
      // Fetch credits from the backend API
      const response = await fetch(`${API_BASE_URL}/api/users/me/credits`, {
        headers: {
          'Authorization': `Bearer ${token || ''}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const credits = data.credits || 0;
        
        // Cache the credits
        try {
          const expiryTime = Date.now() + CREDITS_CACHE_DURATION_MS;
          localStorage.setItem(CREDITS_STORAGE_KEY, credits.toString());
          localStorage.setItem(CREDITS_EXPIRY_KEY, expiryTime.toString());
        } catch (cacheError) {
          console.error('Error caching credits:', cacheError);
        }
        
        return credits;
      }
      
      return 0;
    } catch (error) {
      console.error('Error fetching credits:', error);
      return 0;
    }
  }
}

// Create and export the auth client instance
export const authClient = new AuthClient();
