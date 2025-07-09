import axios, { AxiosError } from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Handle API errors consistently
const handleApiError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string; error?: string }>;
    if (axiosError.response) {
      // Server responded with error status
      const errorMessage = 
        axiosError.response.data?.detail || 
        axiosError.response.data?.message || 
        axiosError.response.data?.error ||
        `API request failed (${axiosError.response.status})`;
      
      // Add more context for specific status codes
      if (axiosError.response.status === 502) {
        throw new Error('Marketplace service is temporarily unavailable. Please try again later.');
      } else if (axiosError.response.status === 503) {
        throw new Error('Service overloaded. Please wait a moment and try again.');
      }
      
      throw new Error(errorMessage);
    } else if (axiosError.request) {
      // Request was made but no response
      throw new Error('Cannot connect to the service. Please check your connection.');
    }
  }
  // Something else happened
  throw new Error(error instanceof Error ? error.message : 'An unexpected error occurred');
};

interface SearchParams {
  q?: string;
  category?: string;
  author?: string;
  page?: number;
  per_page?: number;
}

interface Plugin {
  author: string;
  name: string;
  description?: string;
  latest_version: string;
  category?: string;
  icon_url?: string;
}

interface SearchResult {
  plugins: Plugin[];
  total: number;
  page: number;
  per_page: number;
}

interface Version {
  version: string;
  release_date?: string;
}

interface VersionsResult {
  versions: Version[];
}

interface CategoriesResult {
  categories: string[];
}

interface AuthorsResult {
  authors: string[];
}

export const marketplaceService = {
  /**
   * Check the status of the marketplace API
   */
  checkStatus: async (): Promise<{
    marketplace_api: { status: string; error?: string };
    circuit_breaker: { state: string; failure_count: number };
    recommendations?: any;
  }> => {
    try {
      const response = await api.get('/marketplace/status', { timeout: 5000 });
      return response.data;
    } catch (error) {
      // If status check fails, return a default error state
      return {
        marketplace_api: { status: 'error', error: 'Status check failed' },
        circuit_breaker: { state: 'unknown', failure_count: 0 }
      };
    }
  },

  /**
   * Search for plugins in the marketplace
   */
  searchPlugins: async (params: SearchParams = {}): Promise<SearchResult> => {
    try {
      const response = await api.get<SearchResult>('/marketplace/plugins', { 
        params,
        timeout: 30000  // 30 second timeout
      });
      
      // Validate response structure
      const data = response.data;
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response from server');
      }
      
      // Ensure required fields exist with defaults
      return {
        plugins: Array.isArray(data.plugins) ? data.plugins : [],
        total: data.total || 0,
        page: data.page || params.page || 1,
        per_page: data.per_page || params.per_page || 20,
        ...data  // Include any additional fields like error, fallback_used, etc.
      };
    } catch (error) {
      return handleApiError(error);
    }
  },

  /**
   * Get detailed information about a specific plugin
   */
  getPluginDetails: async (author: string, name: string): Promise<Plugin> => {
    try {
      const response = await api.get<Plugin>(`/marketplace/plugins/${author}/${name}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  /**
   * Get all available versions for a plugin
   */
  getPluginVersions: async (author: string, name: string): Promise<VersionsResult> => {
    try {
      const response = await api.get<VersionsResult>(
        `/marketplace/plugins/${author}/${name}/versions`
      );
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  /**
   * Get all available categories
   */
  getCategories: async (): Promise<CategoriesResult> => {
    try {
      const response = await api.get<CategoriesResult>('/marketplace/categories');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  /**
   * Get all unique authors
   */
  getAuthors: async (): Promise<AuthorsResult> => {
    try {
      const response = await api.get<AuthorsResult>('/marketplace/authors');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },

  /**
   * Get featured or recommended plugins
   */
  getFeaturedPlugins: async (limit = 6): Promise<SearchResult> => {
    try {
      const response = await api.get<SearchResult>('/marketplace/plugins/featured', { 
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