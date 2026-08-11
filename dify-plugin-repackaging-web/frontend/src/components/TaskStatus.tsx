import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle, XCircle, Loader, Download, AlertCircle, Package, User, Tag, Plus, RefreshCw, Sparkles, PartyPopper } from 'lucide-react';
import { taskService } from '../services/api';
import { createReconnectingWebSocket, ReconnectingWebSocket } from '../services/websocket';
import { WebSocketConnectionState } from '../types/websocket';
import WebSocketStatus from './WebSocketStatus';
import LogViewer from './LogViewer';
import Confetti from './Confetti';
import { useToast } from './Toast';

interface TaskStatusProps {
  taskId: string;
  onComplete: (task: any) => void;
  onError: (error: string) => void;
  onNewTask: () => void;
}

const TaskStatus: React.FC<TaskStatusProps> = ({ taskId, onComplete, onError, onNewTask }) => {
  const [task, setTask] = useState<any>(null);
  const [wsStatus, setWsStatus] = useState<WebSocketConnectionState>('connecting');
  const wsRef = useRef<ReconnectingWebSocket | null>(null);
  const taskRef = useRef<any>(null);
  const wsStatusRef = useRef<WebSocketConnectionState>('connecting');
  const hasLoggedConnectionErrorRef = useRef(false);
  const [logs, setLogs] = useState<any[]>([]);
  const logIdCounter = useRef(0);
  const [logHeight, setLogHeight] = useState(350);
  const [showConfetti, setShowConfetti] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const { success, error: showError } = useToast();
  const hasShownCompletionRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const successRef = useRef(success);
  const showErrorRef = useRef(showError);

  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;
  successRef.current = success;
  showErrorRef.current = showError;

  // Handle responsive log height
  useEffect(() => {
    const handleResize = () => {
      setLogHeight(window.innerWidth < 640 ? 250 : 350);
    };
    
    handleResize(); // Set initial height
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    taskRef.current = null;
    wsStatusRef.current = 'connecting';
    hasLoggedConnectionErrorRef.current = false;
    hasShownCompletionRef.current = false;
    setTask(null);
    setLogs([]);
    setWsStatus('connecting');

    // Initial fetch
    fetchTaskStatus(true);

    // Setup WebSocket with auto-reconnect
    const ws = createReconnectingWebSocket(taskId, {
      onOpen: () => {
        wsStatusRef.current = 'connected';
        setWsStatus('connected');
        hasLoggedConnectionErrorRef.current = false;
        addLogEntry('info', 'Connected to task status updates');
      },
      onMessage: (data) => {
        if (data.type !== 'heartbeat' && data.type !== 'ping' && data.type !== 'pong') {
          taskRef.current = data;
          setTask(data);
          
          // Add log entry for status changes and messages
          if (data.message || data.status) {
            const logLevel = data.status === 'failed' ? 'error' : 
                            data.status === 'completed' ? 'success' :
                            data.status === 'processing' || data.status === 'downloading' ? 'processing' : 'info';
            
            addLogEntry(logLevel, data.message || getStatusText(data.status), data.error);
          }
          
          if (data.status === 'completed' && !hasShownCompletionRef.current) {
            hasShownCompletionRef.current = true;
            setShowConfetti(true);
            successRef.current('Plugin repackaged successfully! 🎉');
            setTimeout(() => setShowConfetti(false), 5000);
            onCompleteRef.current(data);
          } else if (data.status === 'failed') {
            showErrorRef.current(data.error || 'Task failed');
            onErrorRef.current(data.error || 'Task failed');
          }
        }
      },
      onError: () => {
        wsStatusRef.current = 'error';
        setWsStatus('error');
        // Log once per outage. Reconnect attempts can emit both error and close events.
        if (!hasLoggedConnectionErrorRef.current) {
          hasLoggedConnectionErrorRef.current = true;
          addLogEntry('error', 'WebSocket connection error', 'Attempting to reconnect...');
        }
      },
      onClose: () => {
        const previousStatus = wsStatusRef.current;
        wsStatusRef.current = 'disconnected';
        setWsStatus('disconnected');
        const currentTask = taskRef.current;
        if (currentTask?.status !== 'completed' && currentTask?.status !== 'failed' && previousStatus === 'connected') {
          addLogEntry('warning', 'Connection lost', 'Attempting to reconnect automatically...');
        }
      },
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10
    });
    
    wsRef.current = ws;

    return () => {
      ws.close();
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
    };
    // The connection lifecycle belongs to the task id. Callback identities from the
    // parent and useToast change during ordinary renders and must not recreate it.
  }, [taskId]);

  const addLogEntry = (level: string, message: string, details?: string) => {
    setLogs(prev => [...prev, {
      id: `log-${logIdCounter.current++}`,
      timestamp: new Date(),
      level,
      message,
      details
    }]);
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Waiting to start...';
      case 'downloading':
        return 'Downloading plugin...';
      case 'processing':
        return 'Repackaging plugin...';
      case 'completed':
        return 'Repackaging completed!';
      case 'failed':
        return 'Repackaging failed';
      default:
        return 'Unknown status';
    }
  };

  const fetchTaskStatus = async (forceInitialLog = false) => {
    try {
      const data = await taskService.getTaskStatus(taskId);
      
      // Handle null response (task not found or error)
      if (!data) {
        addLogEntry('warning', 'Task not found or server error', 'The task may have expired or the server is temporarily unavailable');
        // Don't set task to null to avoid losing UI state
        return;
      }
      
      taskRef.current = data;
      setTask(data);
      
      // Add initial log entry if this is the first fetch
      if (forceInitialLog || logs.length === 0) {
        addLogEntry('info', `Task ${taskId} started`, `Status: ${data.status}`);
        if (data.message) {
          const logLevel = data.status === 'failed' ? 'error' : 
                          data.status === 'completed' ? 'success' :
                          data.status === 'processing' || data.status === 'downloading' ? 'processing' : 'info';
          addLogEntry(logLevel, data.message);
        }
      }
      
      if (data.status === 'completed' && !hasShownCompletionRef.current) {
        hasShownCompletionRef.current = true;
        setShowConfetti(true);
        successRef.current('Plugin repackaged successfully! 🎉');
        setTimeout(() => setShowConfetti(false), 5000);
        onCompleteRef.current(data);
      } else if (data.status === 'failed') {
        showErrorRef.current(data.error || 'Task failed');
        onErrorRef.current(data.error || 'Task failed');
      }
    } catch (error: any) {
      console.error('Error fetching task status:', error);
      addLogEntry('error', 'Failed to fetch task status', error.message || 'Network error');
      // Don't throw - gracefully handle the error
    }
  };

  const handleDownload = async () => {
    if (!task || isDownloading) return;

    try {
      setIsDownloading(true);
      await taskService.downloadTaskFile(taskId, task.output_filename);
    } catch (error: any) {
      console.error('Error downloading task result:', error);
      showErrorRef.current(error?.message || 'Failed to download plugin');
    } finally {
      setIsDownloading(false);
    }
  };

  if (!task) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500 animate-bounce-in" />;
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-500 animate-shake" />;
      case 'pending':
      case 'downloading':
      case 'processing':
        return <Loader className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />;
      default:
        return <AlertCircle className="h-6 w-6 text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    switch (task.status) {
      case 'completed':
        return 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'failed':
        return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      default:
        return 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
    }
  };

  return (
    <div className="space-y-4">
      <Confetti active={showConfetti} />
      
      {/* Status card with improved visual feedback */}
      <div className={`rounded-lg border-2 p-6 transition-all duration-300 ${getStatusColor()}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <div>
              <h3 className="text-lg font-medium">{getStatusText(task.status)}</h3>
              {task.status === 'completed' && (
                <p className="text-sm opacity-75 flex items-center gap-1 mt-1">
                  <Sparkles className="h-3 w-3" />
                  Your plugin is ready for offline installation!
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <WebSocketStatus 
              status={wsStatus} 
              onReconnect={() => {
                if (wsRef.current) {
                  wsRef.current.reconnect();
                }
              }}
            />
            {(wsStatus === 'disconnected' || wsStatus === 'error') && task.status !== 'completed' && task.status !== 'failed' && (
              <button
                onClick={() => fetchTaskStatus()}
                className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                title="Refresh status"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Progress bar with animated stripes */}
        {task.progress > 0 && task.progress < 100 && (
          <div className="">
            <div className="flex justify-between text-sm mb-1">
              <span>Progress</span>
              <span className="font-medium">{task.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-blue-600 dark:bg-blue-400 h-3 rounded-full transition-all duration-300 relative overflow-hidden"
                style={{ width: `${task.progress}%` }}
              >
                {/* Animated stripes for active progress */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-progress-shine" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Success celebration card */}
      {task.status === 'completed' && (
        <div className="bg-gradient-to-r from-green-400 via-blue-500 to-purple-600 p-1 rounded-lg animate-gradient-xy">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <PartyPopper className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  Success! Your plugin is ready
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  All dependencies have been bundled for offline installation
                </p>
              </div>
              {task.download_url && (
                <button
                  type="button"
                  onClick={handleDownload}
                  disabled={isDownloading}
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <Download className="mr-2 h-5 w-5" />
                  {isDownloading ? 'Downloading...' : 'Download Plugin'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Log Viewer */}
      <div className="mt-4">
        <LogViewer
          logs={logs}
          height={logHeight}
          darkMode={false}
          autoScroll={true}
          showTimestamps={true}
          showCopyButton={true}
          className="shadow-lg"
        />
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        {/* Download button (secondary location) */}
        {task.status === 'completed' && task.download_url && (
          <button
            type="button"
            onClick={handleDownload}
            disabled={isDownloading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all shadow-sm hover:shadow-md"
          >
            <Download className="mr-2 h-4 w-4" />
            {isDownloading ? 'Downloading...' : `Download ${task.output_filename || 'Repackaged Plugin'}`}
          </button>
        )}
        
        {/* New Task button */}
        <button
          type="button"
          onClick={onNewTask}
          className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all shadow-sm hover:shadow-md"
        >
          <Plus className="mr-2 h-4 w-4" />
          New Task
        </button>
      </div>

      {/* Plugin metadata */}
      {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info) && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Package className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Plugin Information</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-500 dark:text-gray-400">Name:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).name}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <User className="h-3 w-3 text-gray-400" />
              <span className="text-gray-500 dark:text-gray-400">Author:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).author}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Tag className="h-3 w-3 text-gray-400" />
              <span className="text-gray-500 dark:text-gray-400">Version:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                v{(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).version}
              </span>
            </div>
          </div>
          {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).description && (
            <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
              {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).description}
            </p>
          )}
        </div>
      )}

      {/* Task details */}
      <details className="text-xs opacity-60">
        <summary className="cursor-pointer hover:opacity-80 transition-opacity">Task Details</summary>
        <div className="mt-2 space-y-1 bg-gray-50 dark:bg-gray-800 rounded p-3">
          <p>Task ID: {taskId}</p>
          {task.created_at && (
            <p>Started: {new Date(task.created_at).toLocaleString()}</p>
          )}
          {task.completed_at && (
            <p>Completed: {new Date(task.completed_at).toLocaleString()}</p>
          )}
        </div>
      </details>

      <style jsx>{`
        @keyframes bounce-in {
          0% {
            transform: scale(0.3);
            opacity: 0;
          }
          50% {
            transform: scale(1.05);
          }
          70% {
            transform: scale(0.9);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
          20%, 40%, 60%, 80% { transform: translateX(2px); }
        }

        @keyframes progress-shine {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        @keyframes gradient-xy {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }

        .animate-bounce-in {
          animation: bounce-in 0.6s ease-out;
        }

        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }

        .animate-progress-shine {
          animation: progress-shine 1.5s ease-in-out infinite;
        }

        .animate-gradient-xy {
          background-size: 200% 200%;
          animation: gradient-xy 3s ease infinite;
        }
      `}</style>
    </div>
  );
};

export default TaskStatus;
