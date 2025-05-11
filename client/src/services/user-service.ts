import { User } from '@/interfaces/user';
import { apiClient } from './api-client';

/**
 * Service for user-related operations
 */
export const userService = {
  /**
   * Get the current user's profile
   */
  getCurrentUser: async (): Promise<User> => {
    return apiClient.get<User>('/users/me');
  },

  /**
   * Get a user by ID
   */
  getUser: async (userId: string): Promise<User> => {
    return apiClient.get<User>(`/users/${userId}`);
  },

  /**
   * Update a user's profile
   */
  updateUser: async (userId: string, userData: Partial<User>): Promise<User> => {
    return apiClient.put<User>(`/users/${userId}`, userData);
  },

  /**
   * Get the current user's credit balance
   */
  getCredits: async (): Promise<number> => {
    const user = await apiClient.get<User>('/users/me');
    return user.credits;
  },

  /**
   * Get credit transaction history
   */
  getCreditTransactions: async (): Promise<CreditTransaction[]> => {
    return apiClient.get<CreditTransaction[]>('/users/credits/transactions');
  },
};

/**
 * Credit transaction interface
 */
export interface CreditTransaction {
  id: string;
  user_id: string;
  amount: number;
  description: string;
  created_at: string;
}
