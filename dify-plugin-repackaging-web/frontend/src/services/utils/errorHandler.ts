import axios, { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

/**
 * Extract error message from various error response formats
 */
function extractErrorMessage(error: AxiosError<any>): string {
  if (!error.response) {
    return 'Network error: Unable to connect to the server';
  }

  const { data, status } = error.response;

  // Try different possible error message fields
  const errorMessage = 
    data?.detail ||
    data?.message ||
    data?.error ||
    data?.error_message ||
    data?.msg ||
    (typeof data === 'string' ? data : null);

  if (errorMessage) {
    return errorMessage;
  }

  // Fallback to status-based messages
  switch (status) {
    case 400:
      return 'Bad request: Invalid data provided';
    case 401:
      return 'Unauthorized: Please log in';
    case 403:
      return 'Forbidden: You do not have permission';
    case 404:
      return 'Not found: The requested resource does not exist';
    case 408:
      return 'Request timeout: The server took too long to respond';
    case 409:
      return 'Conflict: The request conflicts with current state';
    case 429:
      return 'Too many requests: Please slow down';
    case 500:
      return 'Internal server error: Something went wrong on our end';
    case 502:
      return 'Bad gateway: Service temporarily unavailable';
    case 503:
      return 'Service unavailable: Please try again later';
    case 504:
      return 'Gateway timeout: The server is not responding';
    default:
      return `Server error (${status}): Please try again`;
  }
}

/**
 * Convert any error to a standardized ApiError object
 */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    return {
      message: extractErrorMessage(axiosError),
      status: axiosError.response?.status,
      code: axiosError.code,
      details: axiosError.response?.data
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      code: error.name
    };
  }

  return {
    message: String(error) || 'An unknown error occurred'
  };
}

/**
 * Log error with appropriate level based on severity
 */
export function logError(error: unknown, context?: string): void {
  // Skip logging in test environment
  if (process.env.NODE_ENV === 'test') {
    return;
  }
  
  const apiError = toApiError(error);
  const logMessage = context ? `[${context}] ${apiError.message}` : apiError.message;

  if (apiError.status && apiError.status >= 500) {
    console.error(logMessage, apiError);
  } else if (apiError.status && apiError.status >= 400) {
    console.warn(logMessage, apiError);
  } else {
    console.log(logMessage, apiError);
  }
}

/**
 * Create a safe wrapper for async functions that handles errors gracefully
 */
export function createSafeWrapper<T>(
  defaultValue: T,
  context?: string
): <Args extends any[]>(
  fn: (...args: Args) => Promise<T>
) => (...args: Args) => Promise<T> {
  return (fn) => {
    return async (...args) => {
      try {
        return await fn(...args);
      } catch (error) {
        logError(error, context);
        return defaultValue;
      }
    };
  };
}

/**
 * Higher-order function to wrap async functions with error handling
 */
export function withErrorHandling<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options?: {
    defaultValue?: any;
    context?: string;
    rethrow?: boolean;
    onError?: (error: ApiError) => void;
  }
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (error) {
      const apiError = toApiError(error);
      logError(error, options?.context);
      
      if (options?.onError) {
        options.onError(apiError);
      }

      if (options?.rethrow) {
        throw apiError;
      }

      return options?.defaultValue;
    }
  }) as T;
}

/**
 * Check if error is retryable (network errors or 5xx status codes)
 */
export function isRetryableError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }

  // Network errors are retryable
  if (!error.response) {
    return true;
  }

  // 5xx errors are retryable
  const status = error.response.status;
  return status >= 500 && status < 600;
}

/**
 * Create a user-friendly error message
 */
export function getUserFriendlyErrorMessage(error: unknown): string {
  const apiError = toApiError(error);
  
  // Add retry suggestion for retryable errors
  if (isRetryableError(error)) {
    return `${apiError.message}. Please try again in a few moments.`;
  }

  return apiError.message;
}