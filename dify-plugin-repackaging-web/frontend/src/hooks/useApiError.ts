import { useState, useCallback } from 'react';
import { ApiError, getUserFriendlyErrorMessage } from '../services/utils/errorHandler';

interface UseApiErrorResult {
  error: string | null;
  setError: (error: string | null) => void;
  clearError: () => void;
  handleError: (error: unknown) => void;
  isError: boolean;
}

/**
 * Hook for handling API errors in components
 */
export function useApiError(): UseApiErrorResult {
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleError = useCallback((error: unknown) => {
    const errorMessage = getUserFriendlyErrorMessage(error);
    setError(errorMessage);
  }, []);

  return {
    error,
    setError,
    clearError,
    handleError,
    isError: error !== null,
  };
}

interface UseApiCallOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
  defaultValue?: T;
}

/**
 * Hook for making API calls with loading and error states
 */
export function useApiCall<T = any>() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const { error, handleError, clearError } = useApiError();

  const execute = useCallback(
    async (
      apiCall: () => Promise<T>,
      options?: UseApiCallOptions<T>
    ): Promise<T | null> => {
      setLoading(true);
      clearError();

      try {
        const result = await apiCall();
        setData(result);
        
        if (options?.onSuccess) {
          options.onSuccess(result);
        }
        
        return result;
      } catch (err) {
        handleError(err);
        
        if (options?.onError) {
          options.onError(err as ApiError);
        }
        
        // Return default value if provided
        if (options?.defaultValue !== undefined) {
          return options.defaultValue;
        }
        
        return null;
      } finally {
        setLoading(false);
      }
    },
    [handleError, clearError]
  );

  return {
    loading,
    data,
    error,
    execute,
    clearError,
  };
}