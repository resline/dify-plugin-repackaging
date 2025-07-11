import React, { useState, useEffect } from 'react';
import { Package, Link, Store, File, ChevronLeft, Plus, Command, FolderOpen } from 'lucide-react';
import useAppStore from '../stores/appStore';

const Layout = ({ 
  children, 
  currentTab, 
  onTabChange, 
  isProcessing,
  onNewTask,
  showBackButton = false
}) => {
  const [showKeyboardHint, setShowKeyboardHint] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Only handle keyboard shortcuts when not typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      
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
        case '4':
          onTabChange('completed');
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

  const tabs = [
    { id: 'url', label: 'Direct URL', icon: Link, shortcut: '1' },
    { id: 'marketplace', label: 'Browse Marketplace', icon: Store, shortcut: '2' },
    { id: 'file', label: 'Upload File', icon: File, shortcut: '3' },
    { id: 'completed', label: 'Completed Files', icon: FolderOpen, shortcut: '4' }
  ];

  const { isSidebarOpen } = useAppStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Package className="h-8 w-8 text-indigo-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Dify Plugin Repackaging Service
                </h1>
                <p className="text-sm text-gray-500">
                  Repackage Dify plugins with offline dependencies
                </p>
              </div>
            </div>
            
            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {/* Keyboard shortcuts hint */}
              <button
                onClick={() => setShowKeyboardHint(!showKeyboardHint)}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Keyboard shortcuts"
              >
                <Command className="h-4 w-4" />
              </button>
              
              {/* New Task button - always visible */}
              <button
                onClick={onNewTask}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 border border-indigo-600 hover:border-indigo-500 rounded-md transition-all"
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
                      ? 'bg-indigo-600 text-white shadow-sm' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-900'
                    }
                  `}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'}`} />
                  <span>{tab.label}</span>
                  
                  {/* Keyboard shortcut indicator */}
                  <span className={`
                    ml-1 text-xs px-1.5 py-0.5 rounded
                    ${isActive 
                      ? 'bg-indigo-500 text-indigo-100' 
                      : 'bg-gray-200 text-gray-500 group-hover:bg-gray-300'
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
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">Keyboard Shortcuts</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Switch to Direct URL</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">1</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Switch to Marketplace</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">2</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Switch to Upload File</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">3</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Switch to Completed Files</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">4</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">New Task</span>
                <div>
                  <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">Ctrl</kbd>
                  <span className="mx-1">+</span>
                  <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">N</kbd>
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowKeyboardHint(false)}
              className="mt-6 w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
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

      {/* Main content with sidebar padding */}
      <main 
        className={`transition-all duration-300 ${isSidebarOpen ? 'lg:mr-80' : ''}`}
      >
        <div
          className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
          role="tabpanel"
          id={`${currentTab}-tabpanel`}
          aria-labelledby={`${currentTab}-tab`}
          tabIndex={0}
        >
          {children}
        </div>
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