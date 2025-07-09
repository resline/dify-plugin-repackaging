import React from 'react';
import { Wifi, WifiOff, AlertCircle, RefreshCw, Loader } from 'lucide-react';
import { WebSocketConnectionState } from '../types/websocket';

interface WebSocketStatusProps {
  status: WebSocketConnectionState;
  onReconnect?: () => void;
  className?: string;
}

const WebSocketStatus: React.FC<WebSocketStatusProps> = ({ 
  status, 
  onReconnect, 
  className = '' 
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'connecting':
      case 'reconnecting':
        return <Loader className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin" />;
      case 'disconnected':
        return <WifiOff className="h-4 w-4 text-gray-500 dark:text-gray-400" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'reconnecting':
        return 'Reconnecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'connecting':
      case 'reconnecting':
        return 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      case 'disconnected':
        return 'text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
      case 'error':
        return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      default:
        return 'text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor()} ${className}`}>
      {getStatusIcon()}
      <span>{getStatusText()}</span>
      {status === 'error' && onReconnect && (
        <button
          onClick={onReconnect}
          className="ml-1 hover:opacity-70 transition-opacity"
          title="Retry connection"
        >
          <RefreshCw className="h-3 w-3" />
        </button>
      )}
    </div>
  );
};

export default WebSocketStatus;