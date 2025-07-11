import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { installGlobalErrorHandlers } from './utils/globalErrorHandler'
import { configureAxiosDefaults } from './services/utils/axiosDefaults'

// Configure axios defaults
configureAxiosDefaults();

// Install global error handlers
installGlobalErrorHandlers();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)