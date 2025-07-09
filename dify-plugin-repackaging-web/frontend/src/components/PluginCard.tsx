import React, { useState } from 'react';
import { Package, User, Tag, ChevronDown, Loader } from 'lucide-react';
import { marketplaceService } from '../services/api';

interface Plugin {
  author: string;
  name: string;
  description?: string;
  latest_version: string;
  category?: string;
  icon_url?: string;
}

interface Version {
  version: string;
  release_date?: string;
}

interface PluginCardProps {
  plugin: Plugin;
  onRepackage: (pluginData: {
    author: string;
    name: string;
    version: string;
    description?: string;
  }) => void;
  isSelected: boolean;
  onClick: () => void;
}

const PluginCard: React.FC<PluginCardProps> = ({ 
  plugin, 
  onRepackage, 
  isSelected, 
  onClick 
}) => {
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedVersion, setSelectedVersion] = useState(plugin.latest_version || '');
  const [showVersionDropdown, setShowVersionDropdown] = useState(false);
  const [error, setError] = useState('');

  const handleVersionClick = async (e: React.MouseEvent) => {
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

  const handleVersionSelect = (version: string) => {
    setSelectedVersion(version);
    setShowVersionDropdown(false);
  };

  const handleRepackage = (e: React.MouseEvent) => {
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
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm bg-white dark:bg-gray-800'
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
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const sibling = target.nextSibling as HTMLElement;
                if (sibling) sibling.style.display = 'flex';
              }}
            />
          ) : null}
          <div 
            className={`w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center ${pluginIcon ? 'hidden' : ''}`}
            style={pluginIcon ? { display: 'none' } : {}}
          >
            <Package className="h-5 w-5 text-gray-400 dark:text-gray-500" />
          </div>
        </div>
        {plugin.category && (
          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded">
            {plugin.category}
          </span>
        )}
      </div>
      
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {plugin.name}
      </h3>
      
      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
        {plugin.description || 'No description available'}
      </p>
      
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
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
            className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-between text-gray-900 dark:text-gray-100 transition-colors"
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
            <div className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg max-h-48 overflow-auto">
              {versions.map((v) => (
                <button
                  key={v.version}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleVersionSelect(v.version);
                  }}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-50 dark:focus:bg-gray-700 focus:outline-none text-gray-900 dark:text-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className={selectedVersion === v.version ? 'font-medium' : ''}>
                      {v.version}
                    </span>
                    {v.release_date && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
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
            <div className="absolute z-10 mt-1 w-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-2">
              <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
        </div>
        
        <button
          onClick={handleRepackage}
          disabled={!selectedVersion}
          className="px-3 py-1.5 text-sm bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Repackage
        </button>
      </div>
    </div>
  );
};

export default PluginCard;