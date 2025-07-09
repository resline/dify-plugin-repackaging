import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for better error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Log 404 errors specifically
      if (error.response.status === 404) {
        console.warn(`API endpoint not found: ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
      } else if (error.response.status >= 500) {
        console.error(`Server error (${error.response.status}): ${error.config?.url}`, error.response.data);
      }
    } else if (error.request) {
      console.error('Network error - no response received:', error.config?.url);
    } else {
      console.error('Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

export const taskService = {
  createTask: async (url, platform = '', suffix = 'offline') => {
    const response = await api.post('/tasks', {
      url,
      platform,
      suffix,
    });
    return response.data;
  },

  createMarketplaceTask: async (author, name, version, platform = '', suffix = 'offline') => {
    const response = await api.post('/tasks/marketplace', {
      author,
      name,
      version,
      platform,
      suffix,
    });
    return response.data;
  },

  uploadFile: async (file, platform = '', suffix = 'offline') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('platform', platform);
    formData.append('suffix', suffix);
    
    const response = await api.post('/tasks/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getTaskStatus: async (taskId) => {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  },

  downloadFile: (taskId) => {
    return `${API_BASE_URL}/tasks/${taskId}/download`;
  },

  listRecentTasks: async (limit = 10) => {
    const response = await api.get('/tasks', { params: { limit } });
    return response.data;
  },
};

// Re-export marketplaceService from marketplace.js for backward compatibility
export { marketplaceService } from './marketplace';

// Import fileService from files.ts
export { fileService } from './files';

export const createWebSocket = (taskId) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/tasks/${taskId}`);
};

export default api;