import axios from 'axios';
import React, { createContext, useContext, useEffect, useState } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  isCheckingAuth: boolean;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
  authError: string | null;
  setAuthError: (error: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    axios.get('/api/v1/auth/session', { withCredentials: true })
      .then(({ data }) => {
        if (active) setIsAuthenticated(Boolean(data.authenticated));
      })
      .catch(() => {
        if (active) setIsAuthenticated(false);
      })
      .finally(() => {
        if (active) setIsCheckingAuth(false);
      });

    const handleUnauthorized = (event?: CustomEvent) => {
      setIsAuthenticated(false);
      setAuthError(
        typeof event?.detail === 'string'
          ? event.detail
          : 'Your session expired. Please sign in again.'
      );
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized as EventListener);

    return () => {
      active = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized as EventListener);
    };
  }, []);

  const login = async (password: string) => {
    setAuthError(null);
    try {
      await axios.post('/api/v1/auth/login', { password }, { withCredentials: true });
      setIsAuthenticated(true);
    } catch (requestError: any) {
      const message = requestError?.response?.data?.detail
        || 'Unable to sign in. Please check the password.';
      setAuthError(message);
      throw requestError;
    }
  };

  const logout = async () => {
    try {
      await axios.post('/api/v1/auth/logout', {}, { withCredentials: true });
    } finally {
      setIsAuthenticated(false);
      setAuthError(null);
    }
  };

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      isCheckingAuth,
      login,
      logout,
      authError,
      setAuthError,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
