/**
 * Global error handler for unhandled promise rejections and errors
 */

import { getUserFriendlyErrorMessage } from '../services/utils/errorHandler';

// Track if handlers are already installed
let handlersInstalled = false;

// Store original console methods
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

/**
 * Install global error handlers
 */
export function installGlobalErrorHandlers(): void {
  if (handlersInstalled) return;
  
  // Skip installing handlers in test environment
  if (process.env.NODE_ENV === 'test') {
    handlersInstalled = true;
    return;
  }
  
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    // Prevent the default handling (which would log to console)
    event.preventDefault();
    
    // Get user-friendly error message
    const message = getUserFriendlyErrorMessage(event.reason);
    
    // Show error notification if possible
    if (window.__showGlobalError) {
      window.__showGlobalError(message);
    }
  });

  // Handle global errors
  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    
    // Prevent default error handling for known API errors
    if (event.error?.isApiError) {
      event.preventDefault();
    }
  });

  // Wrap console.error to catch and format errors
  console.error = (...args) => {
    // Filter out noisy errors
    const errorString = args.join(' ');
    
    // Skip certain known non-critical errors
    const ignoredPatterns = [
      'ResizeObserver loop limit exceeded',
      'ResizeObserver loop completed with undelivered notifications',
      'Non-Error promise rejection captured',
      'Network request failed',
      'WebSocket is already in CLOSING or CLOSED state',
      'Failed to fetch',
      'NetworkError',
      'ERR_NETWORK',
    ];
    
    if (ignoredPatterns.some(pattern => errorString.includes(pattern))) {
      return;
    }
    
    // Call original console.error
    originalConsoleError.apply(console, args);
  };

  // Wrap console.warn to filter warnings
  console.warn = (...args) => {
    const warnString = args.join(' ');
    
    // Skip certain known warnings
    const ignoredPatterns = [
      'React Hook useEffect has missing dependencies',
      'findDOMNode is deprecated',
    ];
    
    if (ignoredPatterns.some(pattern => warnString.includes(pattern))) {
      return;
    }
    
    // Call original console.warn
    originalConsoleWarn.apply(console, args);
  };

  handlersInstalled = true;
}

/**
 * Set global error display function
 */
export function setGlobalErrorDisplay(showError: (message: string) => void): void {
  (window as any).__showGlobalError = showError;
}

// Declare global type
declare global {
  interface Window {
    __showGlobalError?: (message: string) => void;
  }
}