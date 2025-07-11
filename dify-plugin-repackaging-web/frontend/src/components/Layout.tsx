import React, { useState, useEffect } from 'react';
import { Package, Link, Store, File, ChevronLeft, Plus, Command, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface Tab {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  shortcut: string;
}

interface LayoutProps {
  children: React.ReactNode;
  currentTab: string;
  onTabChange: (tabId: string) => void;
  isProcessing: boolean;
  onNewTask: () => void;
  showBackButton?: boolean;
}

const Layout: React.FC<LayoutProps> = ({ 
  children, 
  currentTab, 
  onTabChange, 
  isProcessing,
  onNewTask,
  showBackButton = false
}) => {
  const { isDark, toggleTheme } = useTheme();
  const [showKeyboardHint, setShowKeyboardHint] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only handle keyboard shortcuts when not typing in an input
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      
      switch(e.key) {
        case '1':
          onTabChange('url');
          break;
        case '2':
          onTabChange('marketplace');
          break;
        case '3':
          onTabChange('file');
          break;
        case 'n':
        case 'N':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            onNewTask();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [onTabChange, onNewTask]);

  const tabs: Tab[] = [
    { id: 'url', label: 'Direct URL', icon: Link, shortcut: '1' },
    { id: 'marketplace', label: 'Browse Marketplace', icon: Store, shortcut: '2' },
    { id: 'file', label: 'Upload File', icon: File, shortcut: '3' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Package className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  Dify Plugin Repackaging Service
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Repackage Dify plugins with offline dependencies
                </p>
              </div>
            </div>
            
            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {/* Dark mode toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                aria-label="Toggle theme"
              >
                {isDark ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </button>
              
              {/* Keyboard shortcuts hint */}
              <button
                onClick={() => setShowKeyboardHint(!showKeyboardHint)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                title="Keyboard shortcuts"
              >
                <Command className="h-4 w-4" />
              </button>
              
              {/* New Task button - always visible */}
              <button
                onClick={onNewTask}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 border border-blue-600 hover:border-blue-700 dark:border-blue-400 dark:hover:border-blue-300 rounded-md transition-all"
                title="New Task (Ctrl/Cmd + N)"
              >
                <Plus className="h-4 w-4" />
                New Task
              </button>
            </div>
          </div>
        </div>

        {/* Tab navigation - always visible */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-1" aria-label="Tabs" role="tablist">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`${tab.id}-tabpanel`}
                  id={`${tab.id}-tab`}
                  tabIndex={isActive ? 0 : -1}
                  className={`
                    group relative flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg
                    transition-all duration-200 ease-in-out
                    ${isActive 
                      ? 'bg-blue-600 dark:bg-blue-500 text-white shadow-sm' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 hover:text-gray-900 dark:hover:text-gray-100'
                    }
                  `}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300'}`} />
                  <span>{tab.label}</span>
                  
                  {/* Keyboard shortcut indicator */}
                  <span className={`
                    ml-1 text-xs px-1.5 py-0.5 rounded
                    ${isActive 
                      ? 'bg-blue-500 dark:bg-blue-600 text-blue-100' 
                      : 'bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400 group-hover:bg-gray-300 dark:group-hover:bg-gray-500'
                    }
                  `}>
                    {tab.shortcut}
                  </span>
                  
                  {/* Active tab indicator */}
                  {isActive && (
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-white rounded-t-sm" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Keyboard shortcuts modal */}
      {showKeyboardHint && (
        <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Keyboard Shortcuts</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Switch to Direct URL</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300">1</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Switch to Marketplace</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300">2</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Switch to Upload File</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300">3</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">New Task</span>
                <div>
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300">Ctrl</kbd>
                  <span className="mx-1 text-gray-600 dark:text-gray-400">+</span>
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300">N</kbd>
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowKeyboardHint(false)}
              className="mt-6 w-full px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Breadcrumb / Status bar */}
      {isProcessing && (
        <div className="bg-white border-b">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <div className="flex items-center gap-2 text-sm">
              <button
                onClick={onNewTask}
                className="flex items-center gap-1 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
                Back to Form
              </button>
              <span className="text-gray-400">/</span>
              <span className="text-gray-700">Processing Task</span>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main 
        className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
        role="tabpanel"
        id={`${currentTab}-tabpanel`}
        aria-labelledby={`${currentTab}-tab`}
        tabIndex={0}
      >
        {children}
      </main>

      {/* Footer */}
      <footer className="mt-12 text-center text-sm text-gray-500 pb-8">
        <p>
          This service repackages Dify plugins with all Python dependencies for offline installation.
        </p>
        <p className="mt-2">
          Files are automatically deleted after 24 hours.
        </p>
      </footer>
    </div>
  );
};

export default Layout;