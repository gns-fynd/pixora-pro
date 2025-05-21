/**
 * Universal error handler utility
 * 
 * This utility provides a consistent way to handle errors across the application.
 * It logs the error to the console and optionally calls a callback function with
 * a user-friendly error message.
 * 
 * It also includes utilities for sanitizing error messages to prevent sensitive
 * information from being exposed to users.
 */

/**
 * Custom error class for application-specific errors
 */
export class AppError extends Error {
  public readonly code: string;
  public readonly userMessage: string;
  
  constructor(message: string, code: string = 'UNKNOWN_ERROR', userMessage?: string) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.userMessage = userMessage || message;
  }
}

/**
 * Sanitize an error message to remove sensitive information
 * @param error The error to sanitize
 * @returns A sanitized error message
 */
export const sanitizeErrorMessage = (error: unknown): string => {
  let message = '';
  
  if (error instanceof AppError) {
    message = error.userMessage;
  } else if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'string') {
    message = error;
  } else {
    message = 'An unknown error occurred';
  }
  
  // Remove sensitive information
  return message
    .replace(/token=[\w\d\-_.]+/g, 'token=[REDACTED]')
    .replace(/key=[\w\d\-_.]+/g, 'key=[REDACTED]')
    .replace(/password=[\w\d\-_.]+/g, 'password=[REDACTED]')
    .replace(/Bearer\s+[\w\d\-_.]+/g, 'Bearer [REDACTED]')
    .replace(/apikey\s*:\s*[\w\d\-_.]+/gi, 'apikey: [REDACTED]')
    .replace(/Authorization\s*:\s*Bearer\s+[\w\d\-_.]+/gi, 'Authorization: Bearer [REDACTED]');
}

/**
 * Handle an error and return a user-friendly error message
 * @param error The error to handle
 * @param callback Optional callback function to call with the error message
 * @returns A user-friendly error message
 */
export const handleError = (error: unknown, callback?: (message: string) => void): string => {
  // Log the original error to console for debugging
  console.error('Error:', error);
  
  // Get a sanitized user-friendly message
  const message = sanitizeErrorMessage(error);
  
  // Call callback if provided
  if (callback) callback(message);
  
  // Return sanitized error message
  return message;
};

/**
 * Create a function that handles errors for a specific component
 * @param componentName The name of the component
 * @param callback Optional callback function to call with the error message
 * @returns A function that handles errors for the component
 */
export const createErrorHandler = (
  componentName: string,
  callback?: (message: string) => void
) => {
  return (error: unknown): string => {
    // Log error with component name
    console.error(`Error in ${componentName}:`, error);
    
    // Get a sanitized user-friendly message
    const message = sanitizeErrorMessage(error);
    
    // Call callback if provided
    if (callback) callback(message);
    
    // Return sanitized error message
    return message;
  };
};

/**
 * Async handler utility for handling async operations
 * @param operation The async operation to execute
 * @param onSuccess Optional callback for successful operations
 * @param onError Optional callback for failed operations
 * @returns Promise that resolves with the result or undefined if an error occurred
 */
export const asyncHandler = async <T>(
  operation: () => Promise<T>,
  onSuccess?: (result: T) => void,
  onError?: (error: unknown) => void
): Promise<T | undefined> => {
  try {
    const result = await operation();
    
    if (onSuccess) {
      onSuccess(result);
    }
    
    return result;
  } catch (error) {
    if (onError) {
      onError(error);
    } else {
      handleError(error);
    }
    
    return undefined;
  }
};
