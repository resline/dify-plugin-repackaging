import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const taskService = {
  createTask: async (url, platform = '', suffix = 'offline') => {
    const response = await api.post('/tasks', {
      url,
      platform,
      suffix,
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

export const createWebSocket = (taskId) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/tasks/${taskId}`);
};

export default api;