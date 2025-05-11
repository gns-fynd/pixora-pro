/**
 * User interface representing a user in the application
 */
export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  role: 'user' | 'admin';
  credits: number;
}

/**
 * User settings interface for user preferences
 */
export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  notifications: boolean;
  emailNotifications: boolean;
}

/**
 * Session interface for auth session
 */
export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
  user: {
    id: string;
    email?: string;
  };
}

/**
 * Auth response interface for authentication responses
 */
export interface AuthResponse {
  user: User | null;
  session: Session | null;
  error: string | null;
}

/**
 * Error type for handling errors
 */
export type AuthError = {
  message: string;
  status?: number;
};
