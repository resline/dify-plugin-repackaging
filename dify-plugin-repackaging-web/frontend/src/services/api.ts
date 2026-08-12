import { createAxiosWithRetry } from './utils/retry';
import { withErrorHandling, toApiError, logError } from './utils/errorHandler';
import type { AxiosError } from 'axios';
import type { CompletedTask, Task, TaskListResponse, TaskStartResponse } from '../types/app';

const API_BASE_URL = '/api/v1';

const getDownloadFilename = (
  contentDisposition: string | undefined,
  fallbackFilename?: string
): string => {
  const encodedMatch = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i);
  const plainMatch = contentDisposition?.match(/filename="?([^";]+)"?/i);
  const headerFilename = encodedMatch?.[1]
    ? decodeURIComponent(encodedMatch[1])
    : plainMatch?.[1];
  const filename = headerFilename || fallbackFilename || 'plugin-offline.difypkg';

  // The download attribute must never contain path components supplied by a server.
  return filename.split(/[\\/]/).pop() || 'plugin-offline.difypkg';
};

const saveBlob = (blob: Blob, filename: string): void => {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();

  // Give the browser time to start consuming the object URL before releasing it.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
};

// Create axios instance with built-in retry logic
const api = createAxiosWithRetry(
  {
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
  },
  {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
    retryCondition: (error: AxiosError) => {
      // Don't retry client errors (4xx) except for 408 (timeout) and 429 (rate limit)
      if (error.response) {
        const status = error.response.status;

        // Special handling for 429: don't retry if it's an authentication failure
        if (status === 429) {
          const detail = (error.response.data as { detail?: string } | undefined)?.detail || '';
          // Don't retry authentication-related rate limits
          if (typeof detail === 'string' && detail.toLowerCase().includes('authentication')) {
            return false;
          }
          return true; // Retry other 429 errors (regular API rate limits)
        }

        if (status === 408) return true;
        if (status >= 400 && status < 500) return false;
      }
      // Retry network errors and 5xx errors
      return !error.response || (error.response.status >= 500);
    }
  }
);

// Add response interceptor for better error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError = toApiError(error);
    logError(error, 'API Request');
    return Promise.reject(apiError);
  }
);

export const taskService = {
  createTask: withErrorHandling(
    async (url: string, platform = '', suffix = 'offline'): Promise<TaskStartResponse> => {
      const response = await api.post<TaskStartResponse>('/tasks', {
        url,
        platform,
        suffix,
      });
      return response.data;
    },
    { context: 'createTask', rethrow: true }
  ),

  createMarketplaceTask: withErrorHandling(
    async (
      author: string,
      name: string,
      version?: string,
      platform = '',
      suffix = 'offline'
    ): Promise<TaskStartResponse> => {
      const response = await api.post<TaskStartResponse>('/tasks/marketplace', {
        author,
        name,
        version,
        platform,
        suffix,
      });
      return response.data;
    },
    { context: 'createMarketplaceTask', rethrow: true }
  ),

  uploadFile: withErrorHandling(
    async (file: File, platform = '', suffix = 'offline'): Promise<TaskStartResponse> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('platform', platform);
      formData.append('suffix', suffix);

      const response = await api.post<TaskStartResponse>('/tasks/upload', formData);
      return response.data;
    },
    { context: 'uploadFile', rethrow: true }
  ),

  getTaskStatus: withErrorHandling(
    async (taskId: string): Promise<Task | null> => {
      const response = await api.get<Task>(`/tasks/${taskId}`);
      return response.data;
    },
    { 
      context: 'getTaskStatus',
      defaultValue: null, // Return null if task not found
      rethrow: false
    }
  ),

  downloadFile: (taskId: string): string => {
    return `${API_BASE_URL}/tasks/${taskId}/download`;
  },

  downloadTaskFile: async (taskId: string, fallbackFilename?: string): Promise<string> => {
    const response = await api.get(`/tasks/${taskId}/download`, {
      responseType: 'blob',
    });
    const filename = getDownloadFilename(
      response.headers['content-disposition'],
      fallbackFilename
    );
    const blob = response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: 'application/octet-stream' });

    saveBlob(blob, filename);
    return filename;
  },

  listRecentTasks: withErrorHandling(
    async (limit = 10): Promise<TaskListResponse> => {
      const response = await api.get<TaskListResponse>('/tasks', { params: { limit } });
      return response.data;
    },
    { 
      context: 'listRecentTasks',
      defaultValue: { tasks: [], total: 0 }, // Return empty array on error
      rethrow: false
    }
  ),

  listCompletedFiles: withErrorHandling(
    async (limit = 10): Promise<{ tasks: CompletedTask[]; total: number }> => {
      const response = await api.get<{ tasks: CompletedTask[]; total: number }>('/tasks/completed', { params: { limit } });
      return response.data;
    },
    { 
      context: 'listCompletedFiles',
      defaultValue: { tasks: [], total: 0 }, // Return empty array on error
      rethrow: false
    }
  ),
};

// Re-export marketplaceService from marketplace.js for backward compatibility
export { marketplaceService } from './marketplace';

// Import fileService from files.ts
export { fileService } from './files';

export const createWebSocket = (taskId: string): WebSocket => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/tasks/${taskId}`);
};

export default api;
