/**
 * Input validation utilities
 * 
 * This module provides utilities for validating user inputs to prevent security issues
 * and ensure data integrity.
 */

/**
 * Interface for the prompt object
 */
export interface PromptValidation {
  prompt: string;
  duration?: number;
  aspectRatio?: string;
  style?: string;
  [key: string]: unknown;
}

/**
 * Validate a prompt object for the scene breakdown
 * @param prompt The prompt object to validate
 * @returns True if the prompt is valid, false otherwise
 */
export const validatePrompt = (prompt: PromptValidation | null | undefined): boolean => {
  if (!prompt) return false;
  if (typeof prompt.prompt !== 'string' || prompt.prompt.trim() === '') return false;
  if (prompt.duration && (isNaN(Number(prompt.duration)) || Number(prompt.duration) < 5 || Number(prompt.duration) > 300)) return false;
  if (prompt.aspectRatio && !['16:9', '9:16', '1:1', '4:3', '3:4'].includes(prompt.aspectRatio)) return false;
  if (prompt.style && typeof prompt.style !== 'string') return false;
  return true;
};

/**
 * Validate a URL string
 * @param url The URL to validate
 * @returns True if the URL is valid, false otherwise
 */
export const validateUrl = (url: string): boolean => {
  try {
    const parsedUrl = new URL(url);
    return ['http:', 'https:'].includes(parsedUrl.protocol);
  } catch {
    // URL parsing failed, return false
    return false;
  }
};

/**
 * Validate a file type based on its extension
 * @param filename The filename to validate
 * @param allowedExtensions Array of allowed file extensions (without the dot)
 * @returns True if the file type is allowed, false otherwise
 */
export const validateFileType = (filename: string, allowedExtensions: string[]): boolean => {
  if (!filename) return false;
  const extension = filename.split('.').pop()?.toLowerCase();
  if (!extension) return false;
  return allowedExtensions.includes(extension);
};

/**
 * Validate a file size
 * @param fileSize The file size in bytes
 * @param maxSizeInBytes The maximum allowed file size in bytes
 * @returns True if the file size is within the limit, false otherwise
 */
export const validateFileSize = (fileSize: number, maxSizeInBytes: number): boolean => {
  return fileSize > 0 && fileSize <= maxSizeInBytes;
};

/**
 * Sanitize a string to prevent XSS attacks
 * @param input The string to sanitize
 * @returns The sanitized string
 */
export const sanitizeString = (input: string): string => {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

/**
 * Validate an email address
 * @param email The email address to validate
 * @returns True if the email is valid, false otherwise
 */
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(email);
};

/**
 * Validate a password strength
 * @param password The password to validate
 * @returns True if the password meets the strength requirements, false otherwise
 */
export const validatePasswordStrength = (password: string): boolean => {
  // At least 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
  return passwordRegex.test(password);
};

/**
 * Validate a username
 * @param username The username to validate
 * @returns True if the username is valid, false otherwise
 */
export const validateUsername = (username: string): boolean => {
  // Alphanumeric characters, underscores, and hyphens, 3-20 characters
  const usernameRegex = /^[a-zA-Z0-9_-]{3,20}$/;
  return usernameRegex.test(username);
};
