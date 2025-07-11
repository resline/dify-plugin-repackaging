import axios, { AxiosError } from 'axios';
import { createAxiosWithRetry } from './utils/retry';
import { withErrorHandling, toApiError, logError, getUserFriendlyErrorMessage } from './utils/errorHandler';

const API_BASE_URL = '/api/v1';

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
    retryCondition: (error) => {
      // Don't retry client errors (4xx) except for 408 (timeout) and 429 (rate limit)
      if (error.response) {
        const status = error.response.status;
        if (status === 408 || status === 429) return true;
        if (status >= 400 && status < 500) return false;
      }
      // Retry network errors and 5xx errors
      return !error.response || (error.response.status >= 500);
    }
  }
);


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
  checkStatus: withErrorHandling(
    async (): Promise<{
      marketplace_api: { status: string; error?: string };
      circuit_breaker: { state: string; failure_count: number };
      recommendations?: any;
    }> => {
      const response = await api.get('/marketplace/status', { timeout: 5000 });
      return response.data;
    },
    {
      context: 'checkStatus',
      defaultValue: {
        marketplace_api: { status: 'error', error: 'Status check failed' },
        circuit_breaker: { state: 'unknown', failure_count: 0 }
      },
      rethrow: false
    }
  ),

  /**
   * Search for plugins in the marketplace
   */
  searchPlugins: withErrorHandling(
    async (params: SearchParams = {}): Promise<SearchResult> => {
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
    },
    {
      context: 'searchPlugins',
      defaultValue: {
        plugins: [],
        total: 0,
        page: 1,
        per_page: 20
      },
      rethrow: false
    }
  ),

  /**
   * Get detailed information about a specific plugin
   */
  getPluginDetails: withErrorHandling(
    async (author: string, name: string): Promise<Plugin> => {
      const response = await api.get<Plugin>(`/marketplace/plugins/${author}/${name}`);
      return response.data;
    },
    {
      context: 'getPluginDetails',
      rethrow: true // Re-throw as this is likely a user action
    }
  ),

  /**
   * Get all available versions for a plugin
   */
  getPluginVersions: withErrorHandling(
    async (author: string, name: string): Promise<VersionsResult> => {
      const response = await api.get<VersionsResult>(
        `/marketplace/plugins/${author}/${name}/versions`
      );
      return response.data;
    },
    {
      context: 'getPluginVersions',
      defaultValue: { versions: [] },
      rethrow: false
    }
  ),

  /**
   * Get all available categories
   */
  getCategories: withErrorHandling(
    async (): Promise<CategoriesResult> => {
      const response = await api.get<CategoriesResult>('/marketplace/categories');
      return response.data;
    },
    {
      context: 'getCategories',
      defaultValue: { categories: [] },
      rethrow: false
    }
  ),

  /**
   * Get all unique authors
   */
  getAuthors: withErrorHandling(
    async (): Promise<AuthorsResult> => {
      const response = await api.get<AuthorsResult>('/marketplace/authors');
      return response.data;
    },
    {
      context: 'getAuthors',
      defaultValue: { authors: [] },
      rethrow: false
    }
  ),

  /**
   * Get featured or recommended plugins
   */
  getFeaturedPlugins: withErrorHandling(
    async (limit = 6): Promise<SearchResult> => {
      try {
        const response = await api.get<SearchResult>('/marketplace/plugins/featured', { 
          params: { limit } 
        });
        return response.data;
      } catch (error) {
        // If featured endpoint doesn't exist, fallback to regular search
        const apiError = toApiError(error);
        if (apiError.status === 404) {
          return marketplaceService.searchPlugins({ per_page: limit });
        }
        throw error;
      }
    },
    {
      context: 'getFeaturedPlugins',
      defaultValue: {
        plugins: [],
        total: 0,
        page: 1,
        per_page: 6
      },
      rethrow: false
    }
  ),
};

export default marketplaceService;