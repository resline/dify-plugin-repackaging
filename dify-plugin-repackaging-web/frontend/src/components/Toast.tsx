import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X, Copy } from 'lucide-react';

export interface ToastType {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning' | 'copy';
  message: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastType;
  onClose: (id: string) => void;
}

const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    const duration = toast.duration || 5000;
    const interval = 10; // Update every 10ms for smooth animation
    const step = (100 / duration) * interval;

    const timer = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev - step;
        if (newProgress <= 0) {
          handleClose();
          return 0;
        }
        return newProgress;
      });
    }, interval);

    const autoCloseTimer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => {
      clearInterval(timer);
      clearTimeout(autoCloseTimer);
    };
  }, [toast]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose(toast.id);
    }, 300);
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'copy':
        return <Copy className="w-5 h-5 text-blue-500" />;
      case 'info':
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getStyles = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'error':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
      case 'copy':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      case 'info':
      default:
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
    }
  };

  return (
    <div
      className={`
        relative overflow-hidden
        min-w-[300px] max-w-md
        p-4 pr-10
        rounded-lg border shadow-lg
        transform transition-all duration-300 ease-out
        ${getStyles()}
        ${isExiting 
          ? 'translate-x-full opacity-0' 
          : 'translate-x-0 opacity-100 animate-slide-in'
        }
      `}
      role="alert"
    >
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 animate-bounce-in">
          {getIcon()}
        </div>
        <p className="text-sm text-gray-800 dark:text-gray-200">
          {toast.message}
        </p>
      </div>
      
      <button
        onClick={handleClose}
        className="absolute top-2 right-2 p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
      </button>

      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full bg-current opacity-30 transition-all duration-100 ease-linear"
          style={{
            width: `${progress}%`,
            color: toast.type === 'error' ? '#ef4444' : 
                   toast.type === 'success' ? '#10b981' :
                   toast.type === 'warning' ? '#f59e0b' : '#3b82f6'
          }}
        />
      </div>
    </div>
  );
};

interface ToastContainerProps {
  toasts: ToastType[];
  onClose: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onClose }) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <Toast key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
};

// Custom hook for managing toasts
export const useToast = () => {
  const [toasts, setToasts] = useState<ToastType[]>([]);

  const showToast = (type: ToastType['type'], message: string, duration?: number) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const newToast: ToastType = { id, type, message, duration };
    
    setToasts(prev => [...prev, newToast]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return {
    toasts,
    showToast,
    removeToast,
    success: (message: string, duration?: number) => showToast('success', message, duration),
    error: (message: string, duration?: number) => showToast('error', message, duration),
    info: (message: string, duration?: number) => showToast('info', message, duration),
    warning: (message: string, duration?: number) => showToast('warning', message, duration),
    copy: (message: string = 'Copied to clipboard!', duration?: number) => showToast('copy', message, duration || 2000),
  };
};