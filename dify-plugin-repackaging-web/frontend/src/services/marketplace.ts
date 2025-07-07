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
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    if (axiosError.response) {
      // Server responded with error status
      throw new Error(
        axiosError.response.data?.detail || 
        axiosError.response.data?.message || 
        'API request failed'
      );
    } else if (axiosError.request) {
      // Request was made but no response
      throw new Error('No response from server');
    }
  }
  // Something else happened
  throw new Error(error instanceof Error ? error.message : 'Request failed');
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
   * Search for plugins in the marketplace
   */
  searchPlugins: async (params: SearchParams = {}): Promise<SearchResult> => {
    try {
      const response = await api.get<SearchResult>('/marketplace/plugins', { params });
      return response.data;
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