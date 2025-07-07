import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Handle API errors consistently
const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    throw new Error(error.response.data.detail || error.response.data.message || 'API request failed');
  } else if (error.request) {
    // Request was made but no response
    throw new Error('No response from server');
  } else {
    // Something else happened
    throw new Error(error.message || 'Request failed');
  }
};

export const marketplaceService = {
  /**
   * Search for plugins in the marketplace
   * @param {Object} params - Search parameters
   * @param {string} params.q - Search query
   * @param {string} params.category - Filter by category
   * @param {string} params.author - Filter by author
   * @param {number} params.page - Page number
   * @param {number} params.per_page - Items per page
   * @returns {Promise<{plugins: Array, total: number, page: number, per_page: number}>}
   */
  searchPlugins: async (params = {}) => {
    try {
      const response = await api.get('/marketplace/plugins', { params });
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get detailed information about a specific plugin
   * @param {string} author - Plugin author
   * @param {string} name - Plugin name
   * @returns {Promise<Object>} Plugin details
   */
  getPluginDetails: async (author, name) => {
    try {
      const response = await api.get(`/marketplace/plugins/${author}/${name}`);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get all available versions for a plugin
   * @param {string} author - Plugin author
   * @param {string} name - Plugin name
   * @returns {Promise<{versions: Array}>} List of versions
   */
  getPluginVersions: async (author, name) => {
    try {
      const response = await api.get(`/marketplace/plugins/${author}/${name}/versions`);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get all available categories
   * @returns {Promise<{categories: Array}>} List of categories
   */
  getCategories: async () => {
    try {
      const response = await api.get('/marketplace/categories');
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get all unique authors
   * @returns {Promise<{authors: Array}>} List of authors
   */
  getAuthors: async () => {
    try {
      const response = await api.get('/marketplace/authors');
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },

  /**
   * Get featured or recommended plugins
   * @param {number} limit - Maximum number of plugins to return
   * @returns {Promise<{plugins: Array}>} List of featured plugins
   */
  getFeaturedPlugins: async (limit = 6) => {
    try {
      const response = await api.get('/marketplace/plugins/featured', { 
        params: { limit } 
      });
      return response.data;
    } catch (error) {
      // If featured endpoint doesn't exist, fallback to regular search
      return marketplaceService.searchPlugins({ per_page: limit });
    }
  },
};

export default marketplaceService;