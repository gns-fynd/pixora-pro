import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { authClient } from './auth-client';

// API base URL - must be set in environment variables for production
const API_BASE_URL = import.meta.env.VITE_API_URL;

// Warn if API URL is not set
if (!API_BASE_URL) {
  console.error('VITE_API_URL environment variable is not set. API requests will fail.');
}

// Type definitions
interface ApiErrorResponse {
  detail?: string;
  [key: string]: unknown;
}

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * API client for making requests to the backend
 */
class ApiClient {
  private client: AxiosInstance;
  private authToken: string | null = null;
  
  // Track ongoing requests to prevent duplicates
  private ongoingRequests = new Map<string, { promise: Promise<unknown>, controller: AbortController }>();
  
  // Track last request time by endpoint to prevent rapid successive calls
  private lastRequestTime: Record<string, number> = {};
  private REQUEST_THROTTLE_MS = 500; // 500ms minimum between identical requests

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Important: This enables sending cookies with requests
    });

    // Add request interceptor for authentication
    this.client.interceptors.request.use(
      async (config) => {
        // First try to use the token set directly on this client
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        } else {
          // Fall back to getting the token from the auth client
          // Note: With cookie-based auth, this might not be needed for most requests
          // but we keep it for backward compatibility and for APIs that still require token auth
          const token = await authClient.getAuthToken();
          
          // If we have a token, add it to the request
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        
        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiErrorResponse>) => {
        // Handle authentication errors (401)
        if (error.response?.status === 401) {
          // Try to refresh the token
          const refreshed = await this.handleAuthError();
          
          // If token was refreshed successfully, retry the request
          if (refreshed && error.config) {
            console.debug('Retrying request after token refresh');
            return this.client.request(error.config);
          }
        }
        
        // Handle API errors
        return this.handleApiError(error);
      }
    );
  }

  /**
   * Handle authentication errors by attempting to refresh the token
   */
  private async handleAuthError(): Promise<boolean> {
    try {
      // Try to refresh the token
      const token = await authClient.getAuthToken();
      return !!token;
    } catch (error) {
      console.error('Error refreshing token:', error);
      return false;
    }
  }

  /**
   * Handle API errors consistently
   */
  private handleApiError(error: AxiosError<ApiErrorResponse>): never {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    const status = error.response?.status || 500;
    const data = error.response?.data;
    
    // Enhanced error logging for validation errors (422)
    if (status === 422) {
      console.error(`Validation Error (${status}):`, message);
      
      // Log detailed validation errors if available
      if (Array.isArray(data) && data.length > 0) {
        console.error('Validation error details:', data);
      } else if (typeof data === 'object' && data !== null) {
        console.error('Validation error data:', data);
      }
    } else {
      console.error(`API Error (${status}):`, message, data);
    }
    
    throw new ApiError(message, status, data);
  }
  
  /**
   * Generate a request key for deduplication
   */
  private getRequestKey(method: string, url: string, data?: unknown): string {
    // For video generation endpoints, include a timestamp to ensure uniqueness
    if (url.includes('/scenes/video')) {
      return `${method}:${url}:${Date.now()}`;
    }
    
    // For auth endpoints, make sure we don't block legitimate requests
    if (url.includes('/auth/')) {
      return `${method}:${url}:${Date.now()}`;
    }
    
    return `${method}:${url}:${data ? JSON.stringify(data) : ''}`;
  }
  
  /**
   * Check if a request should be throttled
   */
  private shouldThrottleRequest(url: string): boolean {
    const now = Date.now();
    const lastTime = this.lastRequestTime[url] || 0;
    
    // If this is a critical endpoint that needs throttling
    if (url.includes('/scenes/video') || url.includes('/auth/')) {
      if (now - lastTime < this.REQUEST_THROTTLE_MS) {
        console.debug(`Throttling request to ${url} (too frequent)`);
        return true;
      }
    }
    
    // Update last request time
    this.lastRequestTime[url] = now;
    return false;
  }
  
  /**
   * Setup abort controller with signal from config
   */
  private setupAbortController(config?: AxiosRequestConfig): AbortController {
    const controller = new AbortController();
    
    if (config?.signal) {
      // TypeScript-safe way to handle the signal
      const configSignal = config.signal as AbortSignal;
      
      // Only add event listener if the signal exists and is not already aborted
      if (configSignal && !configSignal.aborted) {
        const abortHandler = () => {
          controller.abort();
        };
        
        configSignal.addEventListener('abort', abortHandler);
        
        // Remove the event listener when controller is aborted
        controller.signal.addEventListener('abort', () => {
          configSignal.removeEventListener('abort', abortHandler);
        });
      }
    }
    
    return controller;
  }
  
  /**
   * Make a GET request with deduplication and cancellation
   */
  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    // Check if we should throttle this request
    if (this.shouldThrottleRequest(url)) {
      // If we have an ongoing request for this URL, return it
      const existingRequests = Array.from(this.ongoingRequests.entries())
        .filter(([key]) => key.includes(url))
        .map(([, value]) => value);
      
      if (existingRequests.length > 0) {
        console.debug(`Reusing existing request for throttled endpoint: ${url}`);
        return existingRequests[0].promise as Promise<T>;
      }
    }
    
    // Generate a unique key for this request
    const requestKey = this.getRequestKey('GET', url);
    
    // Check if this exact request is already in progress
    if (this.ongoingRequests.has(requestKey)) {
      console.debug(`Duplicate GET request detected: ${requestKey}`);
      const request = this.ongoingRequests.get(requestKey);
      if (request) {
        return request.promise as Promise<T>;
      }
    }
    
    // Create an AbortController with proper signal handling
    const controller = this.setupAbortController(config);
    
    // Create the request promise
    const requestPromise = (async () => {
      try {
        const response: AxiosResponse<T> = await this.client.get(url, {
          ...config,
          signal: controller.signal
        });
        return response.data;
      } finally {
        // Remove from ongoing requests when done
        setTimeout(() => {
          this.ongoingRequests.delete(requestKey);
        }, 100);
      }
    })();
    
    // Store the promise and controller
    this.ongoingRequests.set(requestKey, { 
      promise: requestPromise,
      controller
    });
    
    return requestPromise;
  }
  
  /**
   * Make a POST request with deduplication and cancellation
   */
  async post<T = unknown, D = unknown>(
    url: string, 
    data?: D, 
    config?: AxiosRequestConfig
  ): Promise<T> {
    // Check if we should throttle this request
    if (this.shouldThrottleRequest(url)) {
      // If we have an ongoing request for this URL, return it
      const existingRequests = Array.from(this.ongoingRequests.entries())
        .filter(([key]) => key.includes(url))
        .map(([, value]) => value);
      
      if (existingRequests.length > 0) {
        console.debug(`Reusing existing request for throttled endpoint: ${url}`);
        return existingRequests[0].promise as Promise<T>;
      }
    }
    
    // Generate a unique key for this request
    const requestKey = this.getRequestKey('POST', url, data);
    
    // Check if this exact request is already in progress
    if (this.ongoingRequests.has(requestKey)) {
      console.debug(`Duplicate POST request detected: ${requestKey}`);
      const request = this.ongoingRequests.get(requestKey);
      if (request) {
        return request.promise as Promise<T>;
      }
    }
    
    // Create an AbortController with proper signal handling
    const controller = this.setupAbortController(config);
    
    // Create the request promise
    const requestPromise = (async () => {
      try {
        const response: AxiosResponse<T> = await this.client.post(url, data, {
          ...config,
          signal: controller.signal
        });
        return response.data;
      } finally {
        // Remove from ongoing requests when done
        setTimeout(() => {
          this.ongoingRequests.delete(requestKey);
        }, 100);
      }
    })();
    
    // Store the promise and controller
    this.ongoingRequests.set(requestKey, { 
      promise: requestPromise,
      controller
    });
    
    return requestPromise;
  }

  /**
   * Make a PUT request with deduplication and cancellation
   */
  async put<T = unknown, D = unknown>(
    url: string, 
    data?: D, 
    config?: AxiosRequestConfig
  ): Promise<T> {
    // Generate a unique key for this request
    const requestKey = this.getRequestKey('PUT', url, data);
    
    // Check if this exact request is already in progress
    if (this.ongoingRequests.has(requestKey)) {
      console.debug(`Duplicate PUT request detected: ${requestKey}`);
      const request = this.ongoingRequests.get(requestKey);
      if (request) {
        return request.promise as Promise<T>;
      }
    }
    
    // Create an AbortController with proper signal handling
    const controller = this.setupAbortController(config);
    
    // Create the request promise
    const requestPromise = (async () => {
      try {
        const response: AxiosResponse<T> = await this.client.put(url, data, {
          ...config,
          signal: controller.signal
        });
        return response.data;
      } finally {
        // Remove from ongoing requests when done
        setTimeout(() => {
          this.ongoingRequests.delete(requestKey);
        }, 100);
      }
    })();
    
    // Store the promise and controller
    this.ongoingRequests.set(requestKey, { 
      promise: requestPromise,
      controller
    });
    
    return requestPromise;
  }

  /**
   * Make a DELETE request with deduplication and cancellation
   */
  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    // Generate a unique key for this request
    const requestKey = this.getRequestKey('DELETE', url);
    
    // Check if this exact request is already in progress
    if (this.ongoingRequests.has(requestKey)) {
      console.debug(`Duplicate DELETE request detected: ${requestKey}`);
      const request = this.ongoingRequests.get(requestKey);
      if (request) {
        return request.promise as Promise<T>;
      }
    }
    
    // Create an AbortController with proper signal handling
    const controller = this.setupAbortController(config);
    
    // Create the request promise
    const requestPromise = (async () => {
      try {
        const response: AxiosResponse<T> = await this.client.delete(url, {
          ...config,
          signal: controller.signal
        });
        return response.data;
      } finally {
        // Remove from ongoing requests when done
        setTimeout(() => {
          this.ongoingRequests.delete(requestKey);
        }, 100);
      }
    })();
    
    // Store the promise and controller
    this.ongoingRequests.set(requestKey, { 
      promise: requestPromise,
      controller
    });
    
    return requestPromise;
  }

  /**
   * Make a PATCH request with deduplication and cancellation
   */
  async patch<T = unknown, D = unknown>(
    url: string, 
    data?: D, 
    config?: AxiosRequestConfig
  ): Promise<T> {
    // Generate a unique key for this request
    const requestKey = this.getRequestKey('PATCH', url, data);
    
    // Check if this exact request is already in progress
    if (this.ongoingRequests.has(requestKey)) {
      console.debug(`Duplicate PATCH request detected: ${requestKey}`);
      const request = this.ongoingRequests.get(requestKey);
      if (request) {
        return request.promise as Promise<T>;
      }
    }
    
    // Create an AbortController with proper signal handling
    const controller = this.setupAbortController(config);
    
    // Create the request promise
    const requestPromise = (async () => {
      try {
        const response: AxiosResponse<T> = await this.client.patch(url, data, {
          ...config,
          signal: controller.signal
        });
        return response.data;
      } finally {
        // Remove from ongoing requests when done
        setTimeout(() => {
          this.ongoingRequests.delete(requestKey);
        }, 100);
      }
    })();
    
    // Store the promise and controller
    this.ongoingRequests.set(requestKey, { 
      promise: requestPromise,
      controller
    });
    
    return requestPromise;
  }
  
  /**
   * Set the authentication token for API requests
   */
  setAuthToken(token: string | null): void {
    this.authToken = token;
  }
  
  /**
   * Clear all ongoing requests and reset the client state
   * This is useful when signing out or when we want to reset the client state
   */
  clearAllRequests(): void {
    console.debug('Clearing all ongoing requests');
    
    // Abort all ongoing requests
    this.ongoingRequests.forEach(({ controller }) => {
      try {
        controller.abort();
      } catch (error) {
        console.error('Error aborting request:', error);
      }
    });
    
    // Clear the ongoing requests map
    this.ongoingRequests.clear();
    
    // Clear the last request time record
    this.lastRequestTime = {};
    
    // Clear the auth token
    this.authToken = null;
    
    // Add a small delay to allow pending operations to complete
    setTimeout(() => {
      // This space intentionally left blank
    }, 500);
  }
  
  /**
   * Logout the user by making a request to the logout endpoint
   * This will clear the auth cookies on the server side
   */
  async logout(): Promise<void> {
    try {
      // Make a request to the logout endpoint
      const baseUrl = API_BASE_URL.endsWith('/api/v1') 
        ? API_BASE_URL.replace('/api/v1', '') 
        : API_BASE_URL;
      
      await this.post(`${baseUrl}/api/auth/logout`, {}, { withCredentials: true });
      
      // Clear the auth token
      this.authToken = null;
      
      // Clear all ongoing requests
      this.clearAllRequests();
    } catch (error) {
      console.error('Error logging out:', error);
      // Even if the logout request fails, clear the local state
      this.authToken = null;
      this.clearAllRequests();
    }
  }
}

// Create and export the API client instance
export const apiClient = new ApiClient(API_BASE_URL);
