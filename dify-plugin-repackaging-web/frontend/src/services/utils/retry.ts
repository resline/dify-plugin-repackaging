import axios, { AxiosError, AxiosRequestConfig } from 'axios';

interface RetryConfig {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  retryCondition?: (error: AxiosError) => boolean;
}

const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 10000, // 10 seconds
  backoffMultiplier: 2,
  retryCondition: (error: AxiosError) => {
    // Retry on network errors or 5xx status codes
    if (!error.response) return true; // Network error
    return error.response.status >= 500 && error.response.status < 600;
  }
};

/**
 * Calculate delay with exponential backoff
 */
function calculateDelay(
  retryCount: number, 
  initialDelay: number, 
  maxDelay: number, 
  backoffMultiplier: number
): number {
  const delay = initialDelay * Math.pow(backoffMultiplier, retryCount);
  return Math.min(delay, maxDelay);
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry an axios request with exponential backoff
 */
export async function retryRequest<T>(
  requestFn: () => Promise<T>,
  config?: RetryConfig
): Promise<T> {
  const retryConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error | null = null;

  for (let i = 0; i <= retryConfig.maxRetries; i++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error as Error;
      
      // Check if we should retry
      if (i === retryConfig.maxRetries) {
        break; // No more retries
      }

      if (axios.isAxiosError(error) && !retryConfig.retryCondition(error)) {
        throw error; // Don't retry this error
      }

      // Calculate delay and wait
      const delay = calculateDelay(
        i,
        retryConfig.initialDelay,
        retryConfig.maxDelay,
        retryConfig.backoffMultiplier
      );

      if (process.env.NODE_ENV !== 'test') {
        console.warn(`Request failed, retrying in ${delay}ms (attempt ${i + 1}/${retryConfig.maxRetries})...`);
      }
      await sleep(delay);
    }
  }

  // All retries exhausted
  throw lastError;
}

/**
 * Wrap an API method with retry logic
 */
export function withRetry<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  config?: RetryConfig
): T {
  return (async (...args: Parameters<T>) => {
    return retryRequest(() => fn(...args), config);
  }) as T;
}

/**
 * Create an axios instance with built-in retry logic
 */
export function createAxiosWithRetry(
  axiosConfig?: AxiosRequestConfig,
  retryConfig?: RetryConfig
) {
  const instance = axios.create(axiosConfig);
  const mergedRetryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };

  // Add retry interceptor
  instance.interceptors.response.use(
    response => response,
    async error => {
      const config = error.config;
      
      // Initialize retry count
      if (!config._retryCount) {
        config._retryCount = 0;
      }

      // Check if we should retry
      if (
        config._retryCount >= mergedRetryConfig.maxRetries ||
        (axios.isAxiosError(error) && !mergedRetryConfig.retryCondition(error))
      ) {
        return Promise.reject(error);
      }

      // Increment retry count
      config._retryCount++;

      // Calculate delay
      const delay = calculateDelay(
        config._retryCount - 1,
        mergedRetryConfig.initialDelay,
        mergedRetryConfig.maxDelay,
        mergedRetryConfig.backoffMultiplier
      );

      if (process.env.NODE_ENV !== 'test') {
        console.warn(
          `Request failed, retrying in ${delay}ms (attempt ${config._retryCount}/${mergedRetryConfig.maxRetries})...`,
          {
            url: config.url,
            method: config.method,
            status: error.response?.status
          }
        );
      }

      // Wait and retry
      await sleep(delay);
      return instance(config);
    }
  );

  return instance;
}