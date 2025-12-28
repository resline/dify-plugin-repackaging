import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  token: string | null;
  login: (password: string) => void;
  logout: () => void;
  authError: string | null;
  setAuthError: (error: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

const AUTH_TOKEN_KEY = 'auth_token';

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    // Check localStorage for existing token
    return localStorage.getItem(AUTH_TOKEN_KEY);
  });
  const [authError, setAuthError] = useState<string | null>(null);

  const isAuthenticated = !!token;

  const login = (password: string) => {
    // Store the password as token in localStorage
    localStorage.setItem(AUTH_TOKEN_KEY, password);
    setToken(password);
    setAuthError(null);
  };

  const logout = () => {
    // Clear token from localStorage and state
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setToken(null);
    setAuthError(null);
  };

  // Listen for unauthorized events from axios interceptor
  useEffect(() => {
    const handleUnauthorized = (event?: CustomEvent) => {
      setToken(null);
      // Ensure authError is always a string
      const message = typeof event?.detail === 'string'
        ? event.detail
        : 'Invalid password. Please try again.';
      setAuthError(message);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized as EventListener);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized as EventListener);
    };
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout, authError, setAuthError }}>
      {children}
    </AuthContext.Provider>
  );
};
