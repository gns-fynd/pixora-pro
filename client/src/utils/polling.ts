/**
 * Utility functions for polling API endpoints
 */
import { apiClient } from '@/services/api-client';

/**
 * Poll a task status endpoint until completion or failure
 * 
 * @param taskId The ID of the task to poll
 * @param controller AbortController to cancel the request
 * @param messageCallback Callback function to update progress messages
 * @returns The task result or null if polling failed
 */
export async function pollTaskStatus<T>(
  taskId: string,
  controller: AbortController,
  messageCallback: (message: { role: 'user' | 'assistant'; content: string; timestamp: Date }) => void
): Promise<T | null> {
  let pollAttempt = 0;
  let pollDelay = 1000; // Start with 1 second delay
  const maxAttempts = 10;
  
  // Define the expected response type
  interface TaskStatusResponse {
    status: string;
    progress: number;
    message: string;
    task_id: string;
    user_id: string;
    updated_at: string;
    result: T;
    data?: Record<string, unknown>;
  }
  
  // Use a proper polling mechanism with clear exit conditions
  while (pollAttempt < maxAttempts) {
    // Wait before polling (first iteration will wait 1 second)
    await new Promise(resolve => setTimeout(resolve, pollDelay));
    
    try {
      // Check if the request has been aborted
      if (controller.signal.aborted) {
        console.log('Polling aborted due to component unmount or navigation');
        return null;
      }
      
      // Make the API request with the abort signal
      const taskResponse = await apiClient.get<TaskStatusResponse>(
        `/ai/generate/status/${taskId}`, 
        { signal: controller.signal }
      );
      
      console.log(`Poll attempt ${pollAttempt + 1}, task status:`, taskResponse);
      
      // Validate the response data
      const taskData = taskResponse.data;
      if (!taskData) {
        console.error('Task response data is undefined');
        throw new Error('Invalid task response data');
      }
      
      // Check for task completion - this is our primary exit condition
      if (taskData.status === 'completed' && taskData.result) {
        console.log('Task completed successfully, result:', taskData.result);
        return taskData.result as T;
      }
      
      // Check for task failure - this is another exit condition
      if (taskData.status === 'error' || taskData.status === 'failed') {
        console.error('Task failed:', taskData.message);
        throw new Error(`Task failed: ${taskData.message}`);
      }
      
      // Update progress message every other attempt
      if (pollAttempt % 2 === 0) {
        const progress = typeof taskData.progress === 'number' ? Math.round(taskData.progress) : 0;
        messageCallback({
          role: 'assistant',
          content: `Still working on the task... (${progress}% complete)`,
          timestamp: new Date()
        });
      }
      
      // Increase delay with exponential backoff, capped at 5 seconds
      pollDelay = Math.min(pollDelay * 1.5, 5000);
      pollAttempt++;
    } catch (err) {
      // Log the error but continue polling unless we've reached max attempts
      console.error(`Error polling for task result (attempt ${pollAttempt + 1}):`, err);
      
      // Only increment attempt counter and increase delay for non-abort errors
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        pollDelay = Math.min(pollDelay * 2, 5000);
        pollAttempt++;
        
        // If we've reached max attempts, throw the error
        if (pollAttempt >= maxAttempts) {
          throw err;
        }
      } else {
        // If the request was aborted, exit the polling loop
        console.log('Polling aborted');
        return null;
      }
    }
  }
  
  // If we've reached max attempts without success or error, return null
  console.error('Max polling attempts reached without success');
  return null;
}
