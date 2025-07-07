import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader, Download, AlertCircle, Package, User, Tag } from 'lucide-react';
import { taskService, createWebSocket } from '../services/api';

const TaskStatus = ({ taskId, onComplete, onError }) => {
  const [task, setTask] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');

  useEffect(() => {
    if (!taskId) return;

    // Initial fetch
    fetchTaskStatus();

    // Setup WebSocket
    const ws = createWebSocket(taskId);

    ws.onopen = () => {
      setWsStatus('connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'heartbeat') {
        setTask(data);
        
        if (data.status === 'completed') {
          onComplete(data);
        } else if (data.status === 'failed') {
          onError(data.error || 'Task failed');
        }
      }
    };

    ws.onerror = () => {
      setWsStatus('error');
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
    };

    return () => {
      ws.close();
    };
  }, [taskId, onComplete, onError]);

  const fetchTaskStatus = async () => {
    try {
      const data = await taskService.getTaskStatus(taskId);
      setTask(data);
      
      if (data.status === 'completed') {
        onComplete(data);
      } else if (data.status === 'failed') {
        onError(data.error || 'Task failed');
      }
    } catch (error) {
      console.error('Error fetching task status:', error);
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

  const getStatusText = () => {
    switch (task.status) {
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
    <div className={`rounded-lg border p-6 ${getStatusColor()}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-lg font-medium">{getStatusText()}</h3>
            {task.message && (
              <p className="text-sm mt-1 opacity-75">{task.message}</p>
            )}
          </div>
        </div>
        {wsStatus === 'disconnected' && task.status !== 'completed' && task.status !== 'failed' && (
          <button
            onClick={fetchTaskStatus}
            className="text-sm text-indigo-600 hover:text-indigo-500"
          >
            Refresh
          </button>
        )}
      </div>

      {/* Progress bar */}
      {task.progress > 0 && task.progress < 100 && (
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span>Progress</span>
            <span>{task.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {task.error && (
        <div className="mt-4 p-3 bg-red-100 rounded-md">
          <p className="text-sm text-red-700">{task.error}</p>
        </div>
      )}

      {/* Download button */}
      {task.status === 'completed' && task.download_url && (
        <div className="mt-4">
          <a
            href={task.download_url}
            download
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <Download className="mr-2 h-4 w-4" />
            Download {task.output_filename || 'Repackaged Plugin'}
          </a>
        </div>
      )}

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
      <div className="mt-4 text-xs space-y-1 opacity-50">
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