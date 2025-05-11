import { apiClient } from './api-client';

// Types for task-related data
export interface Task {
  task_id: string;
  user_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  created_at: number;
  updated_at: number;
  result?: {
    video_url?: string;
    thumbnail_url?: string;
    [key: string]: unknown;
  };
}

export interface TaskSummary {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: number;
  updated_at: number;
}

/**
 * Service for task-related operations
 */
export const taskService = {
  /**
   * Get a specific task by ID
   */
  getTask: async (taskId: string): Promise<Task> => {
    return apiClient.get<Task>(`/tasks/${taskId}`);
  },

  /**
   * Get all tasks for the current user
   */
  getUserTasks: async (): Promise<TaskSummary[]> => {
    return apiClient.get<TaskSummary[]>('/tasks/user');
  },

  /**
   * Resume a task (navigate to the appropriate page based on task type)
   */
  resumeTask: (task: Task | TaskSummary): string => {
    // Extract task type from task ID
    const taskType = task.task_id.split('_')[0];
    
    // Return the appropriate route based on task type
    switch (taskType) {
      case 'video':
        return `/generation?taskId=${task.task_id}`;
      case 'script':
        return `/scene-breakdown?taskId=${task.task_id}`;
      case 'edit':
        return `/editor?taskId=${task.task_id}`;
      default:
        return `/generation?taskId=${task.task_id}`;
    }
  }
};
