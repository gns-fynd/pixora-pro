import { supabase } from './supabase';
import { getCookie, deleteCookie } from '@/utils/cookie-utils';

// API base URL - will be different in development vs production
const API_BASE_URL = import.meta.env.VITE_API_URL;

// Constants for token management
const TOKEN_EXPIRY_KEY = 'pixora_auth_expiry';
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
  private refreshTimer: NodeJS.Timeout | null = null;
  
  constructor() {
    // Try to load token expiry from cookie on initialization
    this.loadTokenExpiryFromCookie();
    
    // Set up token refresh timer
    this.setupTokenRefreshTimer();
  }
  
  /**
   * Load token expiry from cookie
   */
  private loadTokenExpiryFromCookie(): void {
    try {
      const storedExpiry = getCookie(TOKEN_EXPIRY_KEY);
      
      if (storedExpiry) {
        const expiryTime = parseInt(storedExpiry, 10);
        
        // Only use the stored expiry if it's not expired
        if (expiryTime > Date.now()) {
          console.debug('Using stored auth token expiry from cookie');
          this.tokenExpiryTime = expiryTime;
        } else {
          console.debug('Stored auth token is expired, will refresh');
        }
      }
    } catch (error) {
      console.error('Error loading token expiry from cookie:', error);
    }
  }
  
  /**
   * Set up token refresh timer
   */
  private setupTokenRefreshTimer(): void {
    // Clear any existing timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    
    // If we have a valid expiry time, set up a timer to refresh the token
    if (this.tokenExpiryTime > Date.now()) {
      // Refresh when 75% of the token's lifetime has passed
      const tokenLifetime = this.tokenExpiryTime - Date.now();
      const refreshTime = Math.max(tokenLifetime * 0.75, 60000); // At least 1 minute before expiry
      
      this.refreshTimer = setTimeout(() => {
        console.log('Token refresh timer triggered');
        this.refreshTokenIfNeeded().catch(err => {
          console.error('Error in scheduled token refresh:', err);
        });
      }, refreshTime);
      
      console.log(`Token refresh scheduled in ${refreshTime/1000} seconds`);
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
   * Refresh the token if needed
   */
  private async refreshTokenIfNeeded(): Promise<string | null> {
    // If we have a valid token that's not expired, return it
    if (this.tokenExpiryTime > Date.now() + 60000) { // 1 minute buffer
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
    
    // Add retry logic for token refresh
    let retries = 3;
    let lastError = null;
    
    while (retries > 0) {
      try {
        console.debug(`Attempting to refresh token (attempts remaining: ${retries})`);
        
        // Try to refresh the session first
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
        
        if (!refreshError && refreshData.session?.access_token) {
          console.debug('Successfully refreshed Supabase session');
          
          // Now exchange the refreshed token for a backend token
          const success = await this.exchangeSupabaseToken(refreshData.session.access_token);
          
          if (success) {
            console.debug('Successfully exchanged token');
            
            // Set up token refresh timer
            this.setupTokenRefreshTimer();
            
            return this.authToken;
          }
          
          // If token exchange failed, try again
          throw new Error('Token exchange failed');
        } else {
          console.debug('Failed to refresh Supabase session, falling back to getSession');
          
          // Fall back to getting the current session
          const { data, error } = await supabase.auth.getSession();
          
          if (error) {
            console.error('Error getting Supabase session:', error);
            throw error;
          }
          
          if (!data.session?.access_token) {
            console.debug('No Supabase session available');
            throw new Error('No Supabase session available');
          }
          
          // Exchange the token
          const success = await this.exchangeSupabaseToken(data.session.access_token);
          
          if (success) {
            console.debug('Successfully got token from current session');
            
            // Set up token refresh timer
            this.setupTokenRefreshTimer();
            
            return this.authToken;
          }
          
          // If getting token from current session failed, try again
          throw new Error('Failed to get token from current session');
        }
      } catch (error) {
        console.error(`Error refreshing token (attempt ${4 - retries}/3):`, error);
        lastError = error;
        retries--;
        
        if (retries > 0) {
          // Wait before retrying (exponential backoff)
          const waitTime = Math.pow(2, 3 - retries) * 1000;
          console.debug(`Waiting ${waitTime}ms before retrying...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }
      }
    }
    
    // If all retries failed, record the failure and return null
    console.error('All token refresh attempts failed:', lastError);
    this.recordAuthFailure();
    
    return null;
  }
  
  /**
   * Exchange a Supabase token for a backend token
   */
  private async exchangeSupabaseToken(supabaseToken: string): Promise<boolean> {
    let retryCount = 0;
    const maxRetries = 3;
    
    while (retryCount < maxRetries) {
      try {
        console.debug(`Token exchange attempt ${retryCount + 1}/${maxRetries}`);
        
        // Adjust the URL path to match the backend API structure
        const apiUrl = API_BASE_URL;
        // Remove '/api/v1' if it's included in the URL to avoid path duplication
        const baseUrl = apiUrl.endsWith('/api/v1') 
          ? apiUrl.replace('/api/v1', '') 
          : apiUrl;
        
        console.debug(`Making token exchange request to ${baseUrl}/api/auth/token`);
        
        const response = await fetch(`${baseUrl}/api/auth/token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${supabaseToken}`
          },
          body: JSON.stringify({ token: supabaseToken }),
          credentials: 'include' // Important: This enables sending/receiving cookies
        });
        
        console.debug(`Token exchange response status: ${response.status}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to get backend token: ${response.status} - ${errorText}`);
        }
        
        const tokenData = await response.json();
        
        if (tokenData.success && tokenData.expires_at) {
          console.debug('Successfully exchanged token');
          
          // Store the expiry time
          this.tokenExpiryTime = tokenData.expires_at * 1000; // Convert to milliseconds if needed
          
          // Reset auth failure count
          this.resetAuthFailureCount();
          
          return true;
        }
        
        throw new Error('Token exchange response did not contain expected data');
      } catch (tokenError) {
        retryCount++;
        
        if (retryCount >= maxRetries) {
          console.error(`Error getting backend token after ${maxRetries} attempts:`, tokenError);
          this.recordAuthFailure();
          return false;
        }
        
        // Wait before retrying (exponential backoff)
        const waitTime = Math.pow(2, retryCount) * 1000;
        console.log(`Retrying token exchange in ${waitTime}ms (attempt ${retryCount}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
    
    return false;
  }
  
  /**
   * Get the auth token expiry time
   */
  getTokenExpiryTime(): number {
    return this.tokenExpiryTime;
  }
  
  /**
   * Check if the user is authenticated
   */
  isAuthenticated(): boolean {
    return this.tokenExpiryTime > Date.now();
  }
  
  /**
   * Get the auth token, refreshing if necessary
   */
  async getAuthToken(): Promise<string | null> {
    // If circuit breaker is tripped, block the request
    if (this.checkCircuitBreaker()) {
      return null;
    }
    
    // Try to refresh the token if needed
    return await this.refreshTokenIfNeeded();
  }
  
  /**
   * Clear the auth token (e.g., on logout)
   */
  clearAuthToken(): void {
    // Clear the token expiry cookie
    deleteCookie(TOKEN_EXPIRY_KEY);
    
    // Clear the auth token cookie (will be done by the server)
    // We'll make a request to the logout endpoint which will clear the cookie
    
    // Clear the token expiry time
    this.tokenExpiryTime = 0;
    this.authToken = null;
    
    // Clear the refresh timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    
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
      
      // Check if authenticated
      if (!this.isAuthenticated()) {
        console.error('Not authenticated, cannot fetch credits');
        return 0;
      }
      
      // Fetch credits from the backend API
      // Adjust the URL path to match the backend API structure
      const apiUrl = API_BASE_URL;
      // Remove '/api/v1' if it's included in the URL to avoid path duplication
      const baseUrl = apiUrl.endsWith('/api/v1') 
        ? apiUrl.replace('/api/v1', '') 
        : apiUrl;
      
      const response = await fetch(`${baseUrl}/api/users/me/credits`, {
        credentials: 'include' // Important: This enables sending cookies
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
