import React, { useState, useEffect } from 'react';
import { Search, Filter, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { marketplaceService } from '../services/marketplace';
import PluginCard from './PluginCard';
import { CardSkeleton } from './LoadingSkeleton';

interface Plugin {
  author: string;
  name: string;
  description?: string;
  latest_version: string;
  category?: string;
  icon_url?: string;
}

interface MarketplaceBrowserProps {
  onSelectPlugin: (pluginData: {
    author: string;
    name: string;
    version: string;
    platform?: string;
    suffix?: string;
    description?: string;
  }) => void;
  platform?: string;
  suffix?: string;
}

const MarketplaceBrowser: React.FC<MarketplaceBrowserProps> = ({ 
  onSelectPlugin, 
  platform = '', 
  suffix = 'offline' 
}) => {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedAuthor, setSelectedAuthor] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [authors, setAuthors] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [error, setError] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Load initial data on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  // Search when filters change
  useEffect(() => {
    searchPlugins(true);
  }, [selectedCategory, selectedAuthor]);

  // Search when page changes
  useEffect(() => {
    if (page > 1) {
      searchPlugins(false);
    }
  }, [page]);

  const loadInitialData = async () => {
    try {
      // Load categories and authors in parallel
      const [categoriesResult, authorsResult] = await Promise.all([
        marketplaceService.getCategories().catch(() => ({ categories: [] })),
        marketplaceService.getAuthors().catch(() => ({ authors: [] }))
      ]);
      
      setCategories(Array.isArray(categoriesResult.categories) ? categoriesResult.categories : []);
      setAuthors(Array.isArray(authorsResult.authors) ? authorsResult.authors : []);
      
      // Initial search
      searchPlugins();
    } catch (error) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error loading initial data:', error);
      }
      setError('Failed to load marketplace data');
    }
  };

  const searchPlugins = async (resetPage = true) => {
    if (resetPage) {
      setPage(1);
    }
    
    setLoading(true);
    setError('');
    
    try {
      const params = {
        page: resetPage ? 1 : page,
        per_page: 12,
        ...(searchQuery && { q: searchQuery }),
        ...(selectedCategory && { category: selectedCategory }),
        ...(selectedAuthor && { author: selectedAuthor }),
      };
      
      const result = await marketplaceService.searchPlugins(params);
      
      // Ensure plugins is always an array
      const plugins = Array.isArray(result.plugins) ? result.plugins : [];
      
      setPlugins(plugins);
      setTotalPages(Math.ceil((result.total || 0) / (result.per_page || 12)));
      
      if (plugins.length === 0 && !result.error) {
        setError('No plugins found matching your criteria');
      } else if (result.error) {
        setError(result.error);
      }
      
      // Check if we're using fallback
      if (result.fallback_used) {
        if (process.env.NODE_ENV !== 'test') {
          console.warn('Using fallback data source:', result.fallback_reason);
        }
      }
      
    } catch (error: any) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error searching plugins:', error);
      }
      setError(error.message || 'Failed to search plugins. Please try again later.');
      setPlugins([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchPlugins(true);
  };

  const handlePluginSelect = (plugin: Plugin) => {
    setSelectedPlugin(plugin);
  };

  const handleRepackage = (pluginData: {
    author: string;
    name: string;
    version: string;
    description?: string;
  }) => {
    onSelectPlugin({
      ...pluginData,
      platform,
      suffix,
    });
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
    setSelectedAuthor('');
    searchPlugins(true);
  };

  return (
    <div className="space-y-6">
      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-500" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search plugins by name..."
            className="block w-full pl-10 pr-3 py-2 border rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors placeholder:text-gray-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Search
        </button>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors"
        >
          <Filter className="h-5 w-5 text-gray-600" />
        </button>
      </form>

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Category filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="block w-full px-3 py-2 border rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              >
                <option value="">All Categories</option>
                {Array.isArray(categories) && categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1).replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            {/* Author filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Author
              </label>
              <select
                value={selectedAuthor}
                onChange={(e) => setSelectedAuthor(e.target.value)}
                className="block w-full px-3 py-2 border rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              >
                <option value="">All Authors</option>
                {Array.isArray(authors) && authors.map((author) => (
                  <option key={author} value={author}>
                    {author}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Clear filters button */}
          {(selectedCategory || selectedAuthor || searchQuery) && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Error message */}
      {error && !loading && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">{error}</p>
              <button
                onClick={() => loadInitialData()}
                className="mt-2 inline-flex items-center gap-1 text-sm text-red-700 dark:text-red-300 hover:text-red-800 dark:hover:text-red-200 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Plugin grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton count={6} />
        </div>
      ) : !error && plugins.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <div className="mx-auto h-12 w-12 text-gray-500">
            <Search className="h-full w-full" />
          </div>
          <p className="text-gray-500">No plugins found</p>
          <p className="text-sm text-gray-500">Try adjusting your search criteria</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.isArray(plugins) && plugins.map((plugin) => (
            <PluginCard
              key={`${plugin.author}/${plugin.name}`}
              plugin={plugin}
              onRepackage={handleRepackage}
              isSelected={selectedPlugin?.name === plugin.name && selectedPlugin?.author === plugin.author}
              onClick={() => handlePluginSelect(plugin)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || loading}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          
          <div className="flex items-center gap-1">
            {/* Show page numbers */}
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }
              
              return (
                <button
                  key={i}
                  onClick={() => setPage(pageNum)}
                  disabled={loading}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    pageNum === page
                      ? 'bg-blue-600 dark:bg-blue-500 text-white'
                      : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                  } disabled:cursor-not-allowed transition-colors`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || loading}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default MarketplaceBrowser;