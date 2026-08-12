import axios from 'axios';

/**
 * Configure default axios settings for better error handling
 */
export function configureAxiosDefaults(): void {
  // Set default timeout for all requests
  axios.defaults.timeout = 30000; // 30 seconds
  axios.defaults.withCredentials = true;

  // Add request timestamps used for slow-request diagnostics.
  axios.interceptors.request.use(
    (config) => {
      // Add timestamp to track request duration
      (config as any)._requestStartTime = Date.now();

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Add response interceptor for logging and auth errors
  axios.interceptors.response.use(
    (response) => {
      // Log slow requests in development (but not in tests)
      if (process.env.NODE_ENV === 'development') {
        const duration = Date.now() - ((response.config as any)._requestStartTime || 0);
        if (duration > 5000) {
          console.warn(`Slow request detected: ${response.config.method?.toUpperCase()} ${response.config.url} took ${duration}ms`);
        }
      }
      return response;
    },
    (error) => {
      // Don't log cancelled requests
      if (axios.isCancel(error)) {
        return Promise.reject(error);
      }

      // Handle 401 Unauthorized by triggering re-login.
      if (error.response && error.response.status === 401) {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }

      // Log request duration for failed requests (but not in tests)
      if (process.env.NODE_ENV !== 'test' && error.config && (error.config as any)._requestStartTime) {
        const duration = Date.now() - (error.config as any)._requestStartTime;
        if (duration > 5000) {
          console.warn(`Failed slow request: ${error.config.method?.toUpperCase()} ${error.config.url} took ${duration}ms`);
        }
      }

      return Promise.reject(error);
    }
  );
}

/**
 * Create a cancel token source for cancellable requests
 */
export function createCancelToken() {
  return axios.CancelToken.source();
}

/**
 * Check if an error is a cancellation error
 */
export function isCancelError(error: any): boolean {
  return axios.isCancel(error);
}
