import React, { useEffect, useRef, useState } from 'react';
import { Copy, Check, Terminal, Info, AlertCircle, XCircle, Loader, CheckCircle, Clock, Zap } from 'lucide-react';
import type { LogEntry, LogViewerProps } from '../types/logger';

// Track command execution states
interface CommandState {
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed' | 'queued';
}

const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  height = 400,
  darkMode = true,
  autoScroll = true,
  showTimestamps = true,
  showCopyButton = true,
  className = '',
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [commandStates, setCommandStates] = useState<Record<string, CommandState>>({});

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && !isUserScrolling && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll, isUserScrolling]);

  // Handle user scroll to detect if they're scrolling
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;
    
    setIsUserScrolling(!isAtBottom);
    setShowScrollToBottom(!isAtBottom);
  };

  // Scroll to bottom button handler
  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
      setIsUserScrolling(false);
      setShowScrollToBottom(false);
    }
  };

  // Copy logs to clipboard
  const copyToClipboard = async () => {
    const logText = logs
      .map(log => {
        const timestamp = showTimestamps
          ? `[${log.timestamp.toLocaleTimeString()}] `
          : '';
        const level = `[${log.level.toUpperCase()}] `;
        return `${timestamp}${level}${log.message}${log.details ? '\n' + log.details : ''}`;
      })
      .join('\n');

    try {
      await navigator.clipboard.writeText(logText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy logs:', err);
    }
  };

  // Update command states based on log entries
  useEffect(() => {
    const newCommandStates = { ...commandStates };
    let hasChanges = false;

    logs.forEach((log) => {
      // Detect command start
      if (log.message.includes('Running command:') || log.message.includes('Executing:')) {
        const commandId = log.id;
        if (!newCommandStates[commandId]) {
          newCommandStates[commandId] = {
            startTime: log.timestamp,
            status: 'running'
          };
          hasChanges = true;
        }
      }
      
      // Detect command completion
      if (log.message.includes('Command completed') || log.message.includes('✓') || log.level === 'success') {
        const commandId = findRelatedCommandId(log, logs);
        if (commandId && newCommandStates[commandId]) {
          newCommandStates[commandId].endTime = log.timestamp;
          newCommandStates[commandId].status = 'completed';
          hasChanges = true;
        }
      }
      
      // Detect command failure
      if (log.level === 'error' || log.message.includes('failed') || log.message.includes('✗')) {
        const commandId = findRelatedCommandId(log, logs);
        if (commandId && newCommandStates[commandId]) {
          newCommandStates[commandId].endTime = log.timestamp;
          newCommandStates[commandId].status = 'failed';
          hasChanges = true;
        }
      }
    });

    if (hasChanges) {
      setCommandStates(newCommandStates);
    }
  }, [logs]);

  // Helper to find related command ID
  const findRelatedCommandId = (log: LogEntry, allLogs: LogEntry[]): string | null => {
    const index = allLogs.findIndex(l => l.id === log.id);
    // Look backwards for the most recent command
    for (let i = index - 1; i >= 0; i--) {
      if (allLogs[i].message.includes('Running command:') || allLogs[i].message.includes('Executing:')) {
        return allLogs[i].id;
      }
    }
    return null;
  };

  // Get icon for log level with command state awareness
  const getLogIcon = (log: LogEntry) => {
    const commandState = commandStates[log.id];
    
    // If this is a command, show status-based icon
    if (commandState) {
      switch (commandState.status) {
        case 'running':
          return <Zap className="h-4 w-4 text-yellow-400 animate-pulse" />;
        case 'completed':
          return <CheckCircle className="h-4 w-4 text-green-400" />;
        case 'failed':
          return <XCircle className="h-4 w-4 text-red-400" />;
        case 'queued':
          return <Clock className="h-4 w-4 text-gray-400" />;
      }
    }
    
    // Otherwise, use standard icons
    switch (log.level) {
      case 'info':
        return <Info className="h-4 w-4 text-blue-400" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-400" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-400" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'processing':
        return <Loader className="h-4 w-4 text-indigo-400 animate-spin" />;
      default:
        return <Terminal className="h-4 w-4 text-gray-400" />;
    }
  };

  // Get text color for log level
  const getLogColor = (level: LogEntry['level']) => {
    if (!darkMode) {
      switch (level) {
        case 'info':
          return 'text-blue-700';
        case 'warning':
          return 'text-yellow-700';
        case 'error':
          return 'text-red-700';
        case 'success':
          return 'text-green-700';
        case 'processing':
          return 'text-indigo-700';
        default:
          return 'text-gray-700';
      }
    }

    switch (level) {
      case 'info':
        return 'text-blue-300';
      case 'warning':
        return 'text-yellow-300';
      case 'error':
        return 'text-red-300';
      case 'success':
        return 'text-green-300';
      case 'processing':
        return 'text-indigo-300';
      default:
        return 'text-gray-300';
    }
  };

  const containerClasses = darkMode
    ? 'bg-gray-900 text-gray-100 border-gray-700'
    : 'bg-white text-gray-900 border-gray-200';

  const headerClasses = darkMode
    ? 'bg-gray-800 border-gray-700'
    : 'bg-gray-50 border-gray-200';

  return (
    <div className={`rounded-lg border overflow-hidden ${containerClasses} ${className}`}>
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-2 border-b ${headerClasses}`}>
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 opacity-50" />
          <span className="text-sm font-medium">Process Log</span>
          <span className="text-xs opacity-50">({logs.length} entries)</span>
        </div>
        {showCopyButton && (
          <button
            onClick={copyToClipboard}
            className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-all ${
              darkMode
                ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-200'
                : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
            }`}
            title="Copy all logs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                Copy
              </>
            )}
          </button>
        )}
      </div>

      {/* Log container */}
      <div className="relative">
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className={`overflow-y-auto overflow-x-hidden font-mono text-sm ${
            darkMode ? 'log-viewer-scroll' : 'log-viewer-scroll-light'
          }`}
          style={{ height: `${height}px` }}
        >
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full opacity-50">
              <p className="text-sm">No logs yet...</p>
            </div>
          ) : (
            <div className="p-4 space-y-1">
              {logs.map((log, index) => (
                <div
                  key={log.id}
                  className={`flex items-start gap-2 py-1 animate-fadeIn ${
                    index === logs.length - 1 ? 'animate-pulse-once' : ''
                  }`}
                >
                  {getLogIcon(log)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2">
                      {showTimestamps && (
                        <span className="text-xs opacity-50 whitespace-nowrap">
                          [{log.timestamp.toLocaleTimeString()}]
                        </span>
                      )}
                      <div className="flex-1">
                        <p className={`break-words whitespace-pre-wrap ${getLogColor(log.level)}`}>
                          {log.message}
                        </p>
                        {/* Show execution time for completed commands */}
                        {commandStates[log.id]?.endTime && (
                          <p className="text-xs opacity-50 mt-1">
                            Execution time: {getExecutionTime(commandStates[log.id])}
                          </p>
                        )}
                      </div>
                    </div>
                    {log.details && (
                      <pre className="mt-1 text-xs opacity-75 whitespace-pre-wrap break-words pl-6">
                        {log.details}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scroll to bottom button */}
        {showScrollToBottom && (
          <button
            onClick={scrollToBottom}
            className={`absolute bottom-4 right-4 px-3 py-2 rounded-full shadow-lg transition-all ${
              darkMode
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                : 'bg-white hover:bg-gray-100 text-gray-700'
            }`}
            title="Scroll to bottom"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

// Helper to format execution time
const getExecutionTime = (commandState: CommandState): string => {
  if (!commandState.endTime) return '';
  const duration = commandState.endTime.getTime() - commandState.startTime.getTime();
  if (duration < 1000) return `${duration}ms`;
  if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`;
  return `${Math.floor(duration / 60000)}m ${Math.floor((duration % 60000) / 1000)}s`;
};

export default LogViewer;
export type { LogEntry } from '../types/logger';