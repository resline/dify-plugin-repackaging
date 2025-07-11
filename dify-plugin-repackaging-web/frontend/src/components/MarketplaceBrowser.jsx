import React, { useState, useEffect } from 'react';
import { Search, Filter, AlertCircle, Loader2 } from 'lucide-react';
import { marketplaceService } from '../services/marketplace';
import PluginCard from './PluginCard';

const MarketplaceBrowser = ({ onSelectPlugin, platform, suffix }) => {
  const [plugins, setPlugins] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedAuthor, setSelectedAuthor] = useState('');
  const [categories, setCategories] = useState([]);
  const [authors, setAuthors] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedPlugin, setSelectedPlugin] = useState(null);
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
      
      setCategories(categoriesResult.categories || []);
      setAuthors(authorsResult.authors || []);
      
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
      };
      
      if (searchQuery) params.q = searchQuery;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedAuthor) params.author = selectedAuthor;
      
      const result = await marketplaceService.searchPlugins(params);
      
      setPlugins(result.plugins || []);
      setTotalPages(Math.ceil((result.total || 0) / (result.per_page || 12)));
      
      // Check for API status issues
      if (result.api_status === 'incompatible' || result.api_status === 'changed') {
        setError('Dify Marketplace API has been updated. Please use GitHub or local file options for plugin repackaging.');
      } else if (result.error && typeof result.error === 'string') {
        setError(result.error);
      } else if (result.plugins && result.plugins.length === 0) {
        setError('No plugins found matching your criteria');
      }
      
    } catch (error) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error searching plugins:', error);
      }
      setError(error.message || 'Failed to search plugins');
      setPlugins([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    searchPlugins(true);
  };

  const handlePluginSelect = (plugin) => {
    setSelectedPlugin(plugin);
  };

  const handleRepackage = (pluginData) => {
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
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search plugins by name..."
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Search
        </button>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <Filter className="h-5 w-5 text-gray-600" />
        </button>
      </form>

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Category filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1).replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            {/* Author filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Author
              </label>
              <select
                value={selectedAuthor}
                onChange={(e) => setSelectedAuthor(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Authors</option>
                {authors.map((author) => (
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
              className="text-sm text-indigo-600 hover:text-indigo-500"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Error message */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Plugin grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-12 space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-sm text-gray-500">Loading plugins...</p>
        </div>
      ) : !error && plugins.length === 0 ? (
        <div className="text-center py-12 space-y-3">
          <div className="mx-auto h-12 w-12 text-gray-400">
            <Search className="h-full w-full" />
          </div>
          <p className="text-gray-500">No plugins found</p>
          <p className="text-sm text-gray-400">Try adjusting your search criteria</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {plugins.map((plugin) => (
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
            className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          <div className="flex items-center gap-1">
            {/* Show page numbers */}
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
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
                  className={`px-3 py-1.5 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    pageNum === page
                      ? 'bg-indigo-600 text-white'
                      : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                  } disabled:cursor-not-allowed`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || loading}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default MarketplaceBrowser;