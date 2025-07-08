import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle, XCircle, Loader, Download, AlertCircle, Package, User, Tag, Plus, RefreshCw } from 'lucide-react';
import { taskService, createWebSocket } from '../services/api';
import LogViewer from './LogViewer';

const TaskStatus = ({ taskId, onComplete, onError, onNewTask }) => {
  const [task, setTask] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');
  const [logs, setLogs] = useState([]);
  const logIdCounter = useRef(0);
  const [logHeight, setLogHeight] = useState(350);

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

    // Initial fetch
    fetchTaskStatus();

    // Setup WebSocket
    const ws = createWebSocket(taskId);

    ws.onopen = () => {
      setWsStatus('connected');
      addLogEntry('info', 'Connected to task status updates');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'heartbeat') {
        setTask(data);
        
        // Add log entry for status changes and messages
        if (data.message || data.status) {
          const logLevel = data.status === 'failed' ? 'error' : 
                          data.status === 'completed' ? 'success' :
                          data.status === 'processing' || data.status === 'downloading' ? 'processing' : 'info';
          
          addLogEntry(logLevel, data.message || getStatusText(data.status), data.error);
        }
        
        if (data.status === 'completed') {
          onComplete(data);
        } else if (data.status === 'failed') {
          onError(data.error || 'Task failed');
        }
      }
    };

    ws.onerror = () => {
      setWsStatus('error');
      addLogEntry('error', 'WebSocket connection error', 'Failed to receive real-time updates');
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
      if (task?.status !== 'completed' && task?.status !== 'failed') {
        addLogEntry('warning', 'Disconnected from real-time updates', 'Click refresh to check status');
      }
    };

    return () => {
      ws.close();
    };
  }, [taskId, onComplete, onError]);

  const addLogEntry = (level, message, details) => {
    setLogs(prev => [...prev, {
      id: `log-${logIdCounter.current++}`,
      timestamp: new Date(),
      level,
      message,
      details
    }]);
  };

  const getStatusText = (status) => {
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

  const fetchTaskStatus = async () => {
    try {
      const data = await taskService.getTaskStatus(taskId);
      setTask(data);
      
      // Add initial log entry if this is the first fetch
      if (logs.length === 0) {
        addLogEntry('info', `Task ${taskId} started`, `Status: ${data.status}`);
        if (data.message) {
          const logLevel = data.status === 'failed' ? 'error' : 
                          data.status === 'completed' ? 'success' :
                          data.status === 'processing' || data.status === 'downloading' ? 'processing' : 'info';
          addLogEntry(logLevel, data.message);
        }
      }
      
      if (data.status === 'completed') {
        onComplete(data);
      } else if (data.status === 'failed') {
        onError(data.error || 'Task failed');
      }
    } catch (error) {
      console.error('Error fetching task status:', error);
      addLogEntry('error', 'Failed to fetch task status', error.message);
    }
  };

  if (!task) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-500" />;
      case 'pending':
      case 'downloading':
      case 'processing':
        return <Loader className="h-6 w-6 animate-spin text-indigo-600" />;
      default:
        return <AlertCircle className="h-6 w-6 text-gray-500" />;
    }
  };


  const getStatusColor = () => {
    switch (task.status) {
      case 'completed':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-700 bg-red-50 border-red-200';
      default:
        return 'text-indigo-700 bg-indigo-50 border-indigo-200';
    }
  };

  return (
    <div className="space-y-4">
      {/* Status card with improved visual feedback */}
      <div className={`rounded-lg border-2 p-6 transition-all duration-300 ${getStatusColor()}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <div>
              <h3 className="text-lg font-medium">{getStatusText(task.status)}</h3>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {wsStatus === 'disconnected' && task.status !== 'completed' && task.status !== 'failed' && (
              <button
                onClick={fetchTaskStatus}
                className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-500 transition-colors"
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
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className="bg-indigo-600 h-3 rounded-full transition-all duration-300 relative overflow-hidden"
                style={{ width: `${task.progress}%` }}
              >
                {/* Animated stripes for active progress */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Log Viewer */}
      <div className="mt-4">
        <LogViewer
          logs={logs}
          height={logHeight}
          darkMode={true}
          autoScroll={true}
          showTimestamps={true}
          showCopyButton={true}
          className="shadow-lg"
        />
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        {/* Download button */}
        {task.status === 'completed' && task.download_url && (
          <a
            href={task.download_url}
            download
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all shadow-sm hover:shadow-md"
          >
            <Download className="mr-2 h-4 w-4" />
            Download {task.output_filename || 'Repackaged Plugin'}
          </a>
        )}
        
        {/* New Task button - visible during processing and after completion */}
        <button
          onClick={onNewTask}
          className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all shadow-sm hover:shadow-md"
        >
          <Plus className="mr-2 h-4 w-4" />
          New Task
        </button>
      </div>

      {/* Plugin metadata if from marketplace */}
      {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info) && (
        <div className="mt-4 p-3 bg-gray-50 rounded-md">
          <div className="flex items-center gap-2 mb-2">
            <Package className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Plugin Information</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Name:</span>
              <span className="font-medium">{(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).name}</span>
            </div>
            <div className="flex items-center gap-1">
              <User className="h-3 w-3 text-gray-400" />
              <span className="text-gray-500">Author:</span>
              <span className="font-medium">{(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).author}</span>
            </div>
            <div className="flex items-center gap-1">
              <Tag className="h-3 w-3 text-gray-400" />
              <span className="text-gray-500">Version:</span>
              <span className="font-medium">v{(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).version}</span>
            </div>
          </div>
          {(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).description && (
            <p className="mt-2 text-sm text-gray-600">{(task.plugin_metadata || task.marketplace_metadata || task.plugin_info).description}</p>
          )}
        </div>
      )}

      {/* Task details */}
      <div className="text-xs space-y-1 opacity-50 bg-gray-50 rounded p-3">
        <p>Task ID: {taskId}</p>
        {task.created_at && (
          <p>Started: {new Date(task.created_at).toLocaleString()}</p>
        )}
        {task.completed_at && (
          <p>Completed: {new Date(task.completed_at).toLocaleString()}</p>
        )}
      </div>
    </div>
  );
};

export default TaskStatus;