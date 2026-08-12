import React, { useEffect, useRef, useState } from 'react';
import { Minimize2, Maximize2, X } from 'lucide-react';
import TaskStatus from './TaskStatus';
import useAppStore from '../stores/appStore';
import type { Task } from '../types/app';

interface ProcessingPanelProps {
  taskId: string;
  onComplete: (task: Task) => void;
  onError: (error: string) => void;
  onClose: () => void;
}

const ProcessingPanel: React.FC<ProcessingPanelProps> = ({
  taskId,
  onComplete,
  onError,
  onClose
}) => {
  const { isProcessingPanelMinimized, toggleProcessingPanel } = useAppStore();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [taskSnapshot, setTaskSnapshot] = useState<Task | null>(null);

  useEffect(() => {
    setTaskSnapshot(null);
  }, [taskId]);

  useEffect(() => {
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleBackdropMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget && !isProcessingPanelMinimized) {
      onClose();
    }
  };

  const status = taskSnapshot?.status;
  const compactStatus = (() => {
    switch (status) {
      case 'completed':
        return {
          title: 'Completed Task',
          message: 'Task completed successfully',
          details: 'Click maximize to download or see details',
          messageClassName: 'text-green-700 dark:text-green-300'
        };
      case 'failed':
        return {
          title: 'Failed Task',
          message: 'Task failed',
          details: 'Click maximize to see the error details',
          messageClassName: 'text-red-700 dark:text-red-300'
        };
      case 'downloading':
        return {
          title: 'Processing Task',
          message: 'Downloading plugin...',
          details: 'Click maximize to see details',
          messageClassName: 'text-blue-700 dark:text-blue-300'
        };
      case 'processing':
        return {
          title: 'Processing Task',
          message: 'Repackaging plugin...',
          details: 'Click maximize to see details',
          messageClassName: 'text-blue-700 dark:text-blue-300'
        };
      case 'pending':
        return {
          title: 'Processing Task',
          message: 'Waiting to start...',
          details: 'Click maximize to see details',
          messageClassName: 'text-blue-700 dark:text-blue-300'
        };
      default:
        return {
          title: 'Processing Task',
          message: 'Loading task status...',
          details: 'Click maximize to see details',
          messageClassName: 'text-gray-600 dark:text-gray-400'
        };
    }
  })();

  return (
    <div
      className={`fixed inset-0 z-[60] flex p-4 transition-colors duration-300 ${
        isProcessingPanelMinimized
          ? 'pointer-events-none items-end justify-end'
          : 'items-center justify-center bg-black/50 dark:bg-black/70'
      }`}
      onMouseDown={handleBackdropMouseDown}
      data-testid="processing-panel-backdrop"
    >
      <section
        role="dialog"
        aria-modal={!isProcessingPanelMinimized}
        aria-labelledby="processing-panel-title"
        className={`pointer-events-auto w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-2xl transition-all duration-300 dark:border-gray-700 dark:bg-gray-800 ${
          isProcessingPanelMinimized ? 'max-w-80' : 'max-w-2xl max-h-[90vh]'
        }`}
      >
        {/* The sticky header keeps the close action available after a long task log. */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <h3 id="processing-panel-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {compactStatus.title}
          </h3>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleProcessingPanel}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              title={isProcessingPanelMinimized ? 'Maximize' : 'Minimize'}
              aria-label={isProcessingPanelMinimized ? 'Maximize task result' : 'Minimize task result'}
            >
              {isProcessingPanelMinimized ? (
                <Maximize2 className="h-4 w-4" />
              ) : (
                <Minimize2 className="h-4 w-4" />
              )}
            </button>
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              title="Close task result"
              aria-label="Close task result"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={`${isProcessingPanelMinimized ? 'p-4' : 'p-6'}`}>
          {isProcessingPanelMinimized && (
            <div className="text-sm">
              <p className={compactStatus.messageClassName}>{compactStatus.message}</p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                {compactStatus.details}
              </p>
            </div>
          )}
          <div className={isProcessingPanelMinimized ? 'hidden' : ''}>
            <TaskStatus
              taskId={taskId}
              onComplete={onComplete}
              onError={onError}
              onNewTask={onClose}
              onStatusChange={setTaskSnapshot}
            />
          </div>
        </div>
      </section>
    </div>
  );
};

export default ProcessingPanel;
