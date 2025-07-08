import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';
import UploadForm from './components/UploadForm';
import TaskStatus from './components/TaskStatus';
import { taskService } from './services/api';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastContainer, useToast } from './components/Toast';

function AppContent() {
  const { toasts, success, error, removeToast } = useToast();
  const [currentTask, setCurrentTask] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTab, setCurrentTab] = useState(() => {
    // Restore last selected tab from localStorage
    return localStorage.getItem('lastSelectedTab') || 'url';
  });

  // Save tab selection to localStorage
  useEffect(() => {
    localStorage.setItem('lastSelectedTab', currentTab);
  }, [currentTab]);

  const handleSubmit = async (formData) => {
    setIsLoading(true);
    
    try {
      const task = await taskService.createTask(
        formData.url,
        formData.platform,
        formData.suffix
      );
      
      setCurrentTask(task);
      success('Task created successfully!');
    } catch (error) {
      console.error('Error creating task:', error);
      error(
        error.response?.data?.detail || 'Failed to create task. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarketplaceSubmit = async (pluginData) => {
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
      console.error('Error creating marketplace task:', err);
      error(
        err.response?.data?.detail || 'Failed to create task. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSubmit = async (fileData) => {
    setIsLoading(true);
    
    try {
      const task = await taskService.uploadFile(
        fileData.file,
        fileData.platform,
        fileData.suffix
      );
      
      setCurrentTask(task);
      success('File upload task created successfully!');
    } catch (err) {
      console.error('Error creating file upload task:', err);
      error(
        err.response?.data?.detail || 'Failed to upload file. Please try again.'
      );
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
        <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
          {!currentTask ? (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Repackage a Dify Plugin
              </h2>
              <UploadForm 
                onSubmit={handleSubmit} 
                onSubmitMarketplace={handleMarketplaceSubmit}
                onSubmitFile={handleFileSubmit}
                isLoading={isLoading}
                currentTab={currentTab}
                onTabChange={handleTabChange}
              />
              
              <div className="mt-8 pt-8 border-t border-gray-200">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  How it works
                </h3>
                <ol className="space-y-2 text-sm text-gray-600">
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

              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="text-sm font-medium text-blue-900 mb-2">
                  Supported Sources
                </h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Dify Marketplace (marketplace.dify.ai)</li>
                  <li>• GitHub Releases (github.com)</li>
                  <li>• Direct URLs to .difypkg files</li>
                  <li>• Local .difypkg files (upload from your computer)</li>
                </ul>
              </div>
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
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
      </Layout>
    </>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;