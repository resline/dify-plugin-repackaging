import React, { useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Package } from 'lucide-react';
import UploadForm from './components/UploadForm';
import TaskStatus from './components/TaskStatus';
import { taskService } from './services/api';

function App() {
  const [currentTask, setCurrentTask] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (formData) => {
    setIsLoading(true);
    
    try {
      const task = await taskService.createTask(
        formData.url,
        formData.platform,
        formData.suffix
      );
      
      setCurrentTask(task);
      toast.success('Task created successfully!');
    } catch (error) {
      console.error('Error creating task:', error);
      toast.error(
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
      toast.success('Marketplace task created successfully!');
    } catch (error) {
      console.error('Error creating marketplace task:', error);
      toast.error(
        error.response?.data?.detail || 'Failed to create task. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleTaskComplete = (task) => {
    toast.success('Plugin repackaged successfully! You can now download it.');
  };

  const handleTaskError = (error) => {
    toast.error(error || 'Task failed. Please try again.');
  };

  const handleNewTask = () => {
    setCurrentTask(null);
  };

  return (
    <>
      <Toaster position="top-right" />
      
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm">
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
              {currentTask && currentTask.status === 'completed' && (
                <button
                  onClick={handleNewTask}
                  className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
                >
                  New Task
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
            {!currentTask ? (
              <>
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Repackage a Dify Plugin
                </h2>
                <UploadForm 
                  onSubmit={handleSubmit} 
                  onSubmitMarketplace={handleMarketplaceSubmit}
                  isLoading={isLoading} 
                />
                
                <div className="mt-8 pt-8 border-t border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    How it works
                  </h3>
                  <ol className="space-y-2 text-sm text-gray-600">
                    <li className="flex">
                      <span className="font-semibold mr-2">1.</span>
                      Enter the URL of a .difypkg file from Dify Marketplace or GitHub
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
                />
              </>
            )}
          </div>

          {/* Footer */}
          <footer className="mt-12 text-center text-sm text-gray-500">
            <p>
              This service repackages Dify plugins with all Python dependencies for offline installation.
            </p>
            <p className="mt-2">
              Files are automatically deleted after 24 hours.
            </p>
          </footer>
        </main>
      </div>
    </>
  );
}

export default App;