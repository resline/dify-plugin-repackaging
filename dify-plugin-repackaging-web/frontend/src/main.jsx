import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Import and configure axios defaults synchronously to ensure auth interceptors are ready
import { configureAxiosDefaults } from './services/utils/axiosDefaults';
import { installGlobalErrorHandlers } from './utils/globalErrorHandler';

configureAxiosDefaults();
installGlobalErrorHandlers();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)