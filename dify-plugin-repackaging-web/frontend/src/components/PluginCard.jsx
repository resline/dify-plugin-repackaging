import React, { useState } from 'react';
import { Package, User, Tag, ChevronDown, Loader } from 'lucide-react';
import { marketplaceService } from '../services/api';

const PluginCard = ({ plugin, onRepackage, isSelected, onClick }) => {
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(plugin.latest_version || '');
  const [showVersionDropdown, setShowVersionDropdown] = useState(false);
  const [error, setError] = useState('');

  const handleVersionClick = async (e) => {
    e.stopPropagation();
    
    if (versions.length === 0 && !isLoadingVersions) {
      // Load versions if not already loaded
      setIsLoadingVersions(true);
      setError('');
      
      try {
        const result = await marketplaceService.getPluginVersions(plugin.author, plugin.name);
        const versionList = result.versions || [];
        setVersions(versionList);
        
        // Select latest version by default
        if (versionList.length > 0 && !selectedVersion) {
          setSelectedVersion(versionList[0].version || plugin.latest_version);
        }
      } catch (err) {
        console.error('Error loading plugin versions:', err);
        setError('Failed to load versions');
        setVersions([]);
      } finally {
        setIsLoadingVersions(false);
      }
    }
    
    setShowVersionDropdown(!showVersionDropdown);
  };

  const handleVersionSelect = (version) => {
    setSelectedVersion(version);
    setShowVersionDropdown(false);
  };

  const handleRepackage = (e) => {
    e.stopPropagation();
    
    if (selectedVersion) {
      onRepackage({
        author: plugin.author,
        name: plugin.name,
        version: selectedVersion,
        description: plugin.description,
      });
    }
  };

  // Get plugin icon URL or use default
  const getPluginIcon = () => {
    if (plugin.icon_url) {
      return plugin.icon_url;
    }
    return null;
  };

  const pluginIcon = getPluginIcon();

  return (
    <div
      className={`border rounded-lg p-4 cursor-pointer transition-all ${
        isSelected
          ? 'border-indigo-500 bg-indigo-50 shadow-md'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          {pluginIcon ? (
            <img 
              src={pluginIcon} 
              alt={`${plugin.name} icon`}
              className="w-10 h-10 rounded-lg object-cover"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
          ) : null}
          <div 
            className={`w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center ${pluginIcon ? 'hidden' : ''}`}
            style={pluginIcon ? { display: 'none' } : {}}
          >
            <Package className="h-5 w-5 text-gray-400" />
          </div>
        </div>
        {plugin.category && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
            {plugin.category}
          </span>
        )}
      </div>
      
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        {plugin.name}
      </h3>
      
      <p className="text-sm text-gray-600 line-clamp-2 mb-3">
        {plugin.description || 'No description available'}
      </p>
      
      <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
        <span className="flex items-center gap-1">
          <User className="h-3 w-3" />
          {plugin.author}
        </span>
        <span className="flex items-center gap-1">
          <Tag className="h-3 w-3" />
          v{plugin.latest_version}
        </span>
      </div>

      {/* Version selector and repackage button */}
      <div className="flex items-center gap-2 mt-auto">
        <div className="relative flex-1">
          <button
            onClick={handleVersionClick}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 flex items-center justify-between"
            disabled={isLoadingVersions}
          >
            <span className="truncate">
              {isLoadingVersions ? 'Loading...' : selectedVersion || 'Select version'}
            </span>
            {isLoadingVersions ? (
              <Loader className="h-4 w-4 animate-spin text-gray-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            )}
          </button>
          
          {/* Version dropdown */}
          {showVersionDropdown && versions.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-auto">
              {versions.map((v) => (
                <button
                  key={v.version}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleVersionSelect(v.version);
                  }}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
                >
                  <div className="flex items-center justify-between">
                    <span className={selectedVersion === v.version ? 'font-medium' : ''}>
                      {v.version}
                    </span>
                    {v.release_date && (
                      <span className="text-xs text-gray-500">
                        {new Date(v.release_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
          
          {/* Error message */}
          {error && (
            <div className="absolute z-10 mt-1 w-full bg-red-50 border border-red-200 rounded-md p-2">
              <p className="text-xs text-red-600">{error}</p>
            </div>
          )}
        </div>
        
        <button
          onClick={handleRepackage}
          disabled={!selectedVersion}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Repackage
        </button>
      </div>
    </div>
  );
};

export default PluginCard;