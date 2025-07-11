import React, { useState, useEffect } from 'react';
import { Download, Package, Clock, RefreshCw, FileCheck, ChevronDown, ChevronUp } from 'lucide-react';
import { taskService } from '../services/api';

interface CompletedTask {
  task_id: string;
  status: string;
  created_at: string;
  completed_at: string;
  output_filename: string;
  download_url: string;
  plugin_metadata?: {
    name: string;
    author: string;
    version: string;
    description?: string;
  };
  marketplace_metadata?: {
    name: string;
    author: string;
    version: string;
    description?: string;
  };
  plugin_info?: {
    name: string;
    author: string;
    version: string;
    description?: string;
  };
}

interface CompletedFilesProps {
  className?: string;
  refreshInterval?: number;
  showCompact?: boolean;
}

const CompletedFiles: React.FC<CompletedFilesProps> = ({ className = '', refreshInterval, showCompact = false }) => {
  const [tasks, setTasks] = useState<CompletedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    let isMounted = true;
    let intervalId: NodeJS.Timeout | null = null;
    
    const loadTasksWithDelay = () => {
      if (isMounted) {
        loadCompletedTasks();
      }
    };
    
    // Delay initial load to prevent race conditions during testing
    const timeoutId = setTimeout(loadTasksWithDelay, 100);
    
    // Set up refresh interval if specified
    if (refreshInterval && refreshInterval > 0) {
      intervalId = setInterval(() => {
        if (isMounted) {
          loadCompletedTasks();
        }
      }, refreshInterval * 1000);
    }
    
    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [refreshInterval]);

  const loadCompletedTasks = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await taskService.listCompletedFiles(10);
      setTasks(response.tasks || []);
    } catch (err: any) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Error loading completed tasks:', err);
      }
      setError('Failed to load completed files');
      // If the endpoint doesn't exist yet, fall back to listing recent tasks
      try {
        const fallbackResponse = await taskService.listRecentTasks(10);
        const completedTasks = (fallbackResponse.tasks || []).filter(
          (task: CompletedTask) => task.status === 'completed' && task.download_url
        );
        setTasks(completedTasks);
        setError('');
      } catch (fallbackErr) {
        if (process.env.NODE_ENV !== 'test') {
          console.error('Fallback also failed:', fallbackErr);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const getPluginInfo = (task: CompletedTask) => {
    return task.plugin_metadata || task.marketplace_metadata || task.plugin_info;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
    
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-green-500" />
            Completed Files
          </h3>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (showCompact) {
    // Compact mode for sidebar
    return (
      <div className={className}>
        {loading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={loadCompletedTasks}
              className="mt-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
            >
              Try again
            </button>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8">
            <Package className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-xs text-gray-500 dark:text-gray-400">No completed files</p>
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => {
              const pluginInfo = getPluginInfo(task);
              return (
                <div
                  key={task.task_id}
                  className="p-2 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0 mr-2">
                      <p className="text-xs font-medium text-gray-900 dark:text-gray-100 truncate">
                        {pluginInfo?.name || task.output_filename || 'Plugin'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(task.completed_at)}
                      </p>
                    </div>
                    <a
                      href={task.download_url}
                      download
                      className="p-1.5 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 rounded transition-all"
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Regular mode
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <FileCheck className="h-5 w-5 text-green-500" />
          Completed Files
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={loadCompletedTasks}
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <>
          {error ? (
            <div className="text-center py-8">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              <button
                onClick={loadCompletedTasks}
                className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
              >
                Try again
              </button>
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8">
              <Package className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">No completed files yet</p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Completed repackaging tasks will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {tasks.map((task) => {
                const pluginInfo = getPluginInfo(task);
                return (
                  <div
                    key={task.task_id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Package className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {task.output_filename || `${pluginInfo?.name || 'Plugin'}-offline.difypkg`}
                        </p>
                      </div>
                      {pluginInfo && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {pluginInfo.name} v{pluginInfo.version} by {pluginInfo.author}
                        </p>
                      )}
                      <div className="flex items-center gap-1 mt-1">
                        <Clock className="h-3 w-3 text-gray-400" />
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(task.completed_at)}
                        </p>
                      </div>
                    </div>
                    <a
                      href={task.download_url}
                      download
                      className="ml-3 p-2 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all opacity-70 group-hover:opacity-100"
                      title="Download"
                    >
                      <Download className="h-5 w-5" />
                    </a>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default CompletedFiles;