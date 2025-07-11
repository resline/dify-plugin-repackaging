import React, { useState, useEffect, useCallback } from 'react';
import Layout from './components/Layout';
import UploadForm from './components/UploadForm';
import TaskStatus from './components/TaskStatus';
import CompletedFiles from './components/CompletedFiles';
import { taskService } from './services/api';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastContainer, useToast } from './components/Toast';
import useDeepLink from './hooks/useDeepLink';
import { ErrorBoundary } from './components/ErrorBoundary';

function AppContent() {
  const { toasts, success, error, removeToast } = useToast();
  const deepLinkData = useDeepLink();
  const [currentTask, setCurrentTask] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [initialUrl, setInitialUrl] = useState('');
  const [currentTab, setCurrentTab] = useState(() => {
    // Check for deep link data first
    if (deepLinkData?.type === 'marketplace') {
      return 'marketplace';
    }
    // Otherwise restore last selected tab from localStorage
    const savedTab = localStorage.getItem('lastSelectedTab');
    // Ensure saved tab is valid
    const validTabs = ['url', 'marketplace', 'file', 'completed'];
    return (savedTab && validTabs.includes(savedTab)) ? savedTab : 'url';
  });

  // Save tab selection to localStorage
  useEffect(() => {
    localStorage.setItem('lastSelectedTab', currentTab);
  }, [currentTab]);

  const handleSubmit = useCallback(async (formData) => {
    setIsLoading(true);
    
    try {
      const task = await taskService.createTask(
        formData.url,
        formData.platform,
        formData.suffix
      );
      
      setCurrentTask(task);
      success('Task created successfully!');
    } catch (err) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error creating task:', err);
      }
      error(
        err.response?.data?.detail || 'Failed to create task. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [success, error]);

  const handleMarketplaceSubmit = useCallback(async (pluginData) => {
    setIsLoading(true);
    
    try {
      const task = await taskService.createMarketplaceTask(
        pluginData.author,
        pluginData.name,
        pluginData.version,
        pluginData.platform,
        pluginData.suffix
      );
      
      setCurrentTask(task);
      success('Marketplace task created successfully!');
    } catch (err) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error creating marketplace task:', err);
      }
      error(
        err.response?.data?.detail || 'Failed to create task. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [success, error]);

  // Handle deep link data
  useEffect(() => {
    // Prevent execution if component is unmounting or during initial render
    let isMounted = true;
    const timeoutId = setTimeout(() => {
      if (!isMounted) return;
      
      if (deepLinkData && !currentTask) {
        if (deepLinkData.type === 'url') {
          setCurrentTab('url');
          setInitialUrl(deepLinkData.url);
          // Auto-submit if it's a valid marketplace URL or .difypkg file
          if (deepLinkData.url.endsWith('.difypkg') || deepLinkData.url.includes('marketplace.dify.ai/plugins/')) {
            handleSubmit({
              url: deepLinkData.url,
              platform: '',
              suffix: 'offline'
            });
          }
        } else if (deepLinkData.type === 'marketplace') {
          setCurrentTab('marketplace');
          // Auto-submit marketplace plugin
          handleMarketplaceSubmit({
            author: deepLinkData.author,
            name: deepLinkData.name,
            version: deepLinkData.version === 'latest' ? undefined : deepLinkData.version,
            platform: '',
            suffix: 'offline'
          });
        }
      }
    }, 100); // Small delay to ensure component is fully mounted
    
    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
  }, [deepLinkData, currentTask, handleSubmit, handleMarketplaceSubmit]);

  const handleFileSubmit = async (fileData) => {
    // Validate fileData
    if (!fileData || !fileData.file) {
      error('No file selected. Please select a .difypkg file to upload.');
      return;
    }
    
    // Additional file validation
    if (!fileData.file.name.endsWith('.difypkg')) {
      error('Invalid file type. Please select a .difypkg file.');
      return;
    }
    
    // Check file size (100MB limit)
    const maxSize = 100 * 1024 * 1024; // 100MB in bytes
    if (fileData.file.size > maxSize) {
      error('File size exceeds 100MB limit. Please select a smaller file.');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const task = await taskService.uploadFile(
        fileData.file,
        fileData.platform || '',
        fileData.suffix || 'offline'
      );
      
      setCurrentTask(task);
      success('File upload task created successfully!');
    } catch (err) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error creating file upload task:', err);
      }
      const errorMessage = err.response?.data?.detail || 
                          err.message || 
                          'Failed to upload file. Please try again.';
      error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTaskComplete = (task) => {
    // Success is handled in TaskStatus component with confetti
  };

  const handleTaskError = (errorMsg) => {
    error(errorMsg || 'Task failed. Please try again.');
  };

  const handleNewTask = () => {
    setCurrentTask(null);
  };

  const handleTabChange = (tabId) => {
    setCurrentTab(tabId);
  };

  return (
    <>
      <ToastContainer toasts={toasts} onClose={removeToast} />
      
      <Layout
        currentTab={currentTab}
        onTabChange={handleTabChange}
        isProcessing={!!currentTask}
        onNewTask={handleNewTask}
        showBackButton={!!currentTask}
      >
        <div className="space-y-6">
          {!currentTask && currentTab !== 'completed' && (
            <CompletedFiles />
          )}
          
          {currentTab === 'completed' && !currentTask ? (
            <CompletedFiles refreshInterval={30} />
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 md:p-8">
              {!currentTask ? (
            <>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                Repackage a Dify Plugin
              </h2>
              <UploadForm 
                onSubmit={handleSubmit} 
                onSubmitMarketplace={handleMarketplaceSubmit}
                onSubmitFile={handleFileSubmit}
                isLoading={isLoading}
                currentTab={currentTab}
                onTabChange={handleTabChange}
                initialUrl={initialUrl}
                deepLinkData={deepLinkData}
              />
              
              <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                  How it works
                </h3>
                <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex">
                    <span className="font-semibold mr-2">1.</span>
                    Choose your source: Enter URL, browse Marketplace, or upload a .difypkg file
                  </li>
                  <li className="flex">
                    <span className="font-semibold mr-2">2.</span>
                    Select the target platform (optional)
                  </li>
                  <li className="flex">
                    <span className="font-semibold mr-2">3.</span>
                    Click "Start Repackaging" to begin processing
                  </li>
                  <li className="flex">
                    <span className="font-semibold mr-2">4.</span>
                    Download the repackaged plugin with all dependencies included
                  </li>
                </ol>
              </div>

              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                  Supported Sources
                </h4>
                <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                  <li>• Dify Marketplace (marketplace.dify.ai)</li>
                  <li>• GitHub Releases (github.com)</li>
                  <li>• Direct URLs to .difypkg files</li>
                  <li>• Local .difypkg files (upload from your computer)</li>
                </ul>
              </div>
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                Processing Task
              </h2>
              <TaskStatus
                taskId={currentTask.task_id}
                onComplete={handleTaskComplete}
                onError={handleTaskError}
                onNewTask={handleNewTask}
              />
            </>
          )}
            </div>
          )}
        </div>
      </Layout>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;