import React, { useState } from 'react';
import { Upload, Link, Store } from 'lucide-react';
import { Listbox } from '@headlessui/react';
import MarketplaceBrowser from './MarketplaceBrowser';

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

interface UploadFormProps {
  onSubmit: (data: FormData) => void;
  onSubmitMarketplace: (data: MarketplaceData) => void;
  isLoading: boolean;
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

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, onSubmitMarketplace, isLoading }) => {
  const [mode, setMode] = useState<'url' | 'marketplace'>('url');
  const [url, setUrl] = useState('');
  const [platform, setPlatform] = useState(platforms[0]);
  const [suffix, setSuffix] = useState('offline');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!url) {
      newErrors.url = 'URL is required';
    } else if (!url.endsWith('.difypkg')) {
      newErrors.url = 'URL must point to a .difypkg file';
    } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
      newErrors.url = 'URL must start with http:// or https://';
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

  return (
    <div className="space-y-6">
      {/* Mode selector */}
      <div className="flex rounded-lg shadow-sm" role="group">
        <button
          type="button"
          onClick={() => setMode('url')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-l-lg border ${
            mode === 'url'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          <Link className="inline-block w-4 h-4 mr-2" />
          Direct URL
        </button>
        <button
          type="button"
          onClick={() => setMode('marketplace')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-r-lg border ${
            mode === 'marketplace'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          <Store className="inline-block w-4 h-4 mr-2" />
          Browse Marketplace
        </button>
      </div>

      {mode === 'url' ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700">
              Plugin URL
            </label>
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
                placeholder="https://marketplace.dify.ai/plugins/example.difypkg"
                disabled={isLoading}
              />
            </div>
            {errors.url && (
              <p className="mt-2 text-sm text-red-600">{errors.url}</p>
            )}
            <p className="mt-2 text-sm text-gray-500">
              Enter the URL of a .difypkg file from Dify Marketplace or GitHub
            </p>
          </div>

          <div>
            <label htmlFor="platform" className="block text-sm font-medium text-gray-700">
              Target Platform
            </label>
            <Listbox value={platform} onChange={setPlatform} disabled={isLoading}>
              <div className="relative mt-1">
                <Listbox.Button className="relative w-full cursor-pointer rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-left shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:text-sm">
                  <span className="block truncate">{platform.label}</span>
                  <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                    <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3zm-3.707 9.293a1 1 0 011.414 0L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </span>
                </Listbox.Button>
                <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                  {platforms.map((plat) => (
                    <Listbox.Option
                      key={plat.value}
                      value={plat}
                      className={({ active }) =>
                        `relative cursor-pointer select-none py-2 pl-3 pr-9 ${
                          active ? 'bg-indigo-600 text-white' : 'text-gray-900'
                        }`
                      }
                    >
                      {({ selected, active }) => (
                        <>
                          <span className={`block truncate ${selected ? 'font-semibold' : 'font-normal'}`}>
                            {plat.label}
                          </span>
                          {selected && (
                            <span className={`absolute inset-y-0 right-0 flex items-center pr-4 ${
                              active ? 'text-white' : 'text-indigo-600'
                            }`}>
                              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            </span>
                          )}
                        </>
                      )}
                    </Listbox.Option>
                  ))}
                </Listbox.Options>
              </div>
            </Listbox>
            <p className="mt-2 text-sm text-gray-500">
              Select the target platform for the repackaged plugin
            </p>
          </div>

          <div>
            <label htmlFor="suffix" className="block text-sm font-medium text-gray-700">
              Output Suffix
            </label>
            <input
              type="text"
              id="suffix"
              value={suffix}
              onChange={(e) => setSuffix(e.target.value)}
              className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.suffix ? 'border-red-300' : 'border-gray-300'
              }`}
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
      ) : (
        <MarketplaceBrowser
          onSelectPlugin={handleMarketplaceSelect}
          platform={platform.value}
          suffix={suffix}
        />
      )}
    </div>
  );
};

export default UploadForm;