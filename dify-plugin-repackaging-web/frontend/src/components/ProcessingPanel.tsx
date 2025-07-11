import React from 'react';
import { Minimize2, Maximize2, X } from 'lucide-react';
import TaskStatus from './TaskStatus';
import useAppStore from '../stores/appStore';

interface ProcessingPanelProps {
  taskId: string;
  onComplete: (task: any) => void;
  onError: (error: string) => void;
  onNewTask: () => void;
}

const ProcessingPanel: React.FC<ProcessingPanelProps> = ({
  taskId,
  onComplete,
  onError,
  onNewTask
}) => {
  const { isProcessingPanelMinimized, toggleProcessingPanel } = useAppStore();

  return (
    <div
      className={`fixed bottom-4 right-4 z-40 bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 transition-all duration-300 ${
        isProcessingPanelMinimized ? 'w-80' : 'w-full max-w-2xl'
      }`}
      style={{ 
        right: isProcessingPanelMinimized ? '1rem' : '50%',
        transform: isProcessingPanelMinimized ? 'none' : 'translateX(50%)'
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Processing Task
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleProcessingPanel}
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            title={isProcessingPanelMinimized ? 'Maximize' : 'Minimize'}
          >
            {isProcessingPanelMinimized ? (
              <Maximize2 className="h-4 w-4" />
            ) : (
              <Minimize2 className="h-4 w-4" />
            )}
          </button>
          <button
            onClick={onNewTask}
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            title="Close and start new task"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className={`${isProcessingPanelMinimized ? 'p-4' : 'p-6'}`}>
        {isProcessingPanelMinimized ? (
          <div className="text-sm">
            <p className="text-gray-600 dark:text-gray-400">Task in progress...</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Click maximize to see details
            </p>
          </div>
        ) : (
          <TaskStatus
            taskId={taskId}
            onComplete={onComplete}
            onError={onError}
            onNewTask={onNewTask}
          />
        )}
      </div>
    </div>
  );
};

export default ProcessingPanel;