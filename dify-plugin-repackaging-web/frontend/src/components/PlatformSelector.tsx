import React, { useState } from 'react';
import { ChevronDown, Monitor, Cpu, HelpCircle } from 'lucide-react';

interface Platform {
  value: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  group: string;
}

interface PlatformSelectorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const platforms: Platform[] = [
  {
    value: '',
    label: 'Auto-detect',
    description: 'Automatically detect platform',
    icon: <Monitor className="w-5 h-5" />,
    group: 'Default'
  },
  {
    value: 'manylinux2014_x86_64',
    label: 'Linux x86_64 (2014)',
    description: 'Compatible with most modern Linux distributions',
    icon: <Cpu className="w-5 h-5" />,
    group: 'Linux'
  },
  {
    value: 'manylinux_2_17_x86_64',
    label: 'Linux x86_64 (2017)',
    description: 'For newer Linux distributions',
    icon: <Cpu className="w-5 h-5" />,
    group: 'Linux'
  },
  {
    value: 'manylinux2014_aarch64',
    label: 'Linux ARM64 (2014)',
    description: 'For ARM-based Linux systems',
    icon: <Cpu className="w-5 h-5" />,
    group: 'Linux'
  },
  {
    value: 'manylinux_2_17_aarch64',
    label: 'Linux ARM64 (2017)',
    description: 'For newer ARM-based Linux systems',
    icon: <Cpu className="w-5 h-5" />,
    group: 'Linux'
  },
  {
    value: 'macosx_10_9_x86_64',
    label: 'macOS x86_64',
    description: 'For Intel-based Macs',
    icon: <Monitor className="w-5 h-5" />,
    group: 'macOS'
  },
  {
    value: 'macosx_11_0_arm64',
    label: 'macOS ARM64',
    description: 'For Apple Silicon Macs (M1/M2)',
    icon: <Monitor className="w-5 h-5" />,
    group: 'macOS'
  },
  {
    value: 'win_amd64',
    label: 'Windows x86_64',
    description: 'For 64-bit Windows systems',
    icon: <Monitor className="w-5 h-5" />,
    group: 'Windows'
  }
];

const PlatformSelector: React.FC<PlatformSelectorProps> = ({ value, onChange, className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const selectedPlatform = platforms.find(p => p.value === value) || platforms[0];

  const groupedPlatforms = platforms.reduce((acc, platform) => {
    if (!acc[platform.group]) {
      acc[platform.group] = [];
    }
    acc[platform.group].push(platform);
    return acc;
  }, {} as Record<string, Platform[]>);

  return (
    <div className={`relative ${className}`}>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        <span className="flex items-center gap-2">
          Target Platform
          <div className="relative inline-block">
            <button
              type="button"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              aria-label="Platform information"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
            {showTooltip && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg z-50">
                <div className="relative">
                  <p>Select the target platform for the repackaged plugin. This ensures compatibility with the intended system.</p>
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            )}
          </div>
        </span>
      </label>

      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-4 py-3 text-left bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:border-gray-400 dark:hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-gray-600 dark:text-gray-400">
                {selectedPlatform.icon}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedPlatform.label}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {selectedPlatform.description}
                </p>
              </div>
            </div>
            <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${isOpen ? 'transform rotate-180' : ''}`} />
          </div>
        </button>

        {isOpen && (
          <div className="absolute z-10 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-96 overflow-auto">
            {Object.entries(groupedPlatforms).map(([group, items]) => (
              <div key={group}>
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-900">
                  {group}
                </div>
                {items.map((platform) => (
                  <button
                    key={platform.value}
                    type="button"
                    onClick={() => {
                      onChange(platform.value);
                      setIsOpen(false);
                    }}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                      platform.value === value ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`${platform.value === value ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'}`}>
                        {platform.icon}
                      </div>
                      <div>
                        <p className={`text-sm font-medium ${
                          platform.value === value ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-gray-100'
                        }`}>
                          {platform.label}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {platform.description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlatformSelector;