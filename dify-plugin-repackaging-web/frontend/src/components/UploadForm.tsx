import React, { useState } from 'react';
import { Upload, Link, Store, File, Info } from 'lucide-react';
import { Listbox } from '@headlessui/react';
import MarketplaceBrowser from './MarketplaceBrowser';
import FileUpload from './FileUpload';
import PlatformSelector from './PlatformSelector';

interface Platform {
  value: string;
  label: string;
}

interface FormData {
  url: string;
  platform: string;
  suffix: string;
}

interface MarketplaceData {
  author: string;
  name: string;
  version: string;
  platform?: string;
  suffix?: string;
}

interface FileData {
  file: File;
  platform: string;
  suffix: string;
}

interface UploadFormProps {
  onSubmit: (data: FormData) => void;
  onSubmitMarketplace: (data: MarketplaceData) => void;
  onSubmitFile: (data: FileData) => void;
  isLoading: boolean;
  currentTab: string;
  onTabChange: (tabId: string) => void;
}

const platforms: Platform[] = [
  { value: '', label: 'Auto-detect (Default)' },
  { value: 'manylinux2014_x86_64', label: 'Linux x86_64 (manylinux2014)' },
  { value: 'manylinux2014_aarch64', label: 'Linux ARM64 (manylinux2014)' },
  { value: 'manylinux_2_17_x86_64', label: 'Linux x86_64 (manylinux 2.17)' },
  { value: 'manylinux_2_17_aarch64', label: 'Linux ARM64 (manylinux 2.17)' },
  { value: 'macosx_10_9_x86_64', label: 'macOS x86_64' },
  { value: 'macosx_11_0_arm64', label: 'macOS ARM64' },
];

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, onSubmitMarketplace, onSubmitFile, isLoading, currentTab, onTabChange }) => {
  const [url, setUrl] = useState('');
  const [platform, setPlatform] = useState(platforms[0]);
  const [suffix, setSuffix] = useState('offline');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!url) {
      newErrors.url = 'URL is required';
    } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
      newErrors.url = 'URL must start with http:// or https://';
    } else {
      // Check if it's a valid URL type
      const isMarketplaceUrl = url.includes('marketplace.dify.ai/plugins/');
      const isDifypkgUrl = url.endsWith('.difypkg');
      
      if (!isMarketplaceUrl && !isDifypkgUrl) {
        newErrors.url = 'URL must point to a .difypkg file or be a Dify Marketplace plugin URL';
      }
    }
    
    if (!suffix) {
      newErrors.suffix = 'Suffix is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      onSubmit({
        url,
        platform: platform.value,
        suffix,
      });
    }
  };

  const handleMarketplaceSelect = (pluginData: MarketplaceData) => {
    onSubmitMarketplace(pluginData);
  };

  const handleFileUpload = (fileData: { file: File } | null) => {
    if (!fileData || !fileData.file) {
      setSelectedFile(null);
      return;
    }
    
    setSelectedFile(fileData.file);
  };
  
  const handleFileSubmit = () => {
    if (!selectedFile) {
      return;
    }
    
    onSubmitFile({
      file: selectedFile,
      platform: platform.value,
      suffix,
    });
  };

  return (
    <div className="space-y-6">
      {currentTab === 'url' ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <div className="flex items-center space-x-2">
              <label htmlFor="url" className="block text-sm font-medium text-gray-700">
                Plugin URL
              </label>
              <div className="group relative">
                <Info className="h-3.5 w-3.5 text-gray-400 cursor-help" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                  <div className="text-left">
                    <p className="font-semibold mb-1">Download Limits:</p>
                    <p>• Maximum file size: 500MB</p>
                    <p>• Timeout: 10 minutes</p>
                  </div>
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                    <div className="border-4 border-transparent border-t-gray-900 dark:border-t-gray-700"></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Link className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="url"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className={`block w-full pl-10 pr-3 py-2 border rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  errors.url ? 'border-red-300' : 'border-gray-300'
                }`}
                placeholder="https://marketplace.dify.ai/plugins/langgenius/agent"
                disabled={isLoading}
              />
            </div>
            {errors.url && (
              <p className="mt-2 text-sm text-red-600">{errors.url}</p>
            )}
            <p className="mt-2 text-sm text-gray-500">
              Enter a Dify Marketplace plugin URL (e.g. https://marketplace.dify.ai/plugins/langgenius/agent) or direct .difypkg file URL
            </p>
          </div>

          <PlatformSelector 
            value={platform.value} 
            onChange={(value) => setPlatform(platforms.find(p => p.value === value) || platforms[0])}
            className="mt-1"
          />

          <div>
            <label htmlFor="suffix" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Output Suffix
            </label>
            <input
              type="text"
              id="suffix"
              value={suffix}
              onChange={(e) => setSuffix(e.target.value)}
              className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors ${
                errors.suffix ? 'border-red-300 dark:border-red-600' : 'border-gray-300 dark:border-gray-600'
              } bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100`}
              placeholder="offline"
              disabled={isLoading}
            />
            {errors.suffix && (
              <p className="mt-2 text-sm text-red-600">{errors.suffix}</p>
            )}
            <p className="mt-2 text-sm text-gray-500">
              The suffix will be added to the output filename (e.g., plugin-offline.difypkg)
            </p>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
            }`}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-5 w-5" />
                Start Repackaging
              </>
            )}
          </button>
        </form>
      ) : currentTab === 'marketplace' ? (
        <MarketplaceBrowser
          onSelectPlugin={handleMarketplaceSelect}
          platform={platform.value}
          suffix={suffix}
        />
      ) : (
        <div className="space-y-6">
          <FileUpload
            onFileSelect={handleFileUpload}
            isLoading={isLoading}
          />
          
          <PlatformSelector 
            value={platform.value} 
            onChange={(value) => setPlatform(platforms.find(p => p.value === value) || platforms[0])}
            className="mt-1"
          />

          <div>
            <label htmlFor="suffix" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Output Suffix
            </label>
            <input
              type="text"
              id="suffix"
              value={suffix}
              onChange={(e) => setSuffix(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="offline"
              disabled={isLoading}
            />
            <p className="mt-2 text-sm text-gray-500">
              The suffix will be added to the output filename (e.g., plugin-offline.difypkg)
            </p>
          </div>

          {selectedFile && (
            <button
              type="button"
              onClick={handleFileSubmit}
              disabled={isLoading}
              className={`w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                isLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
              }`}
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-5 w-5" />
                  Start Repackaging
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default UploadForm;