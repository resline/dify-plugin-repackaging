import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Defer utility imports to avoid initialization issues
setTimeout(() => {
  import('./services/utils/axiosDefaults').then(({ configureAxiosDefaults }) => {
    configureAxiosDefaults();
  });
  
  import('./utils/globalErrorHandler').then(({ installGlobalErrorHandlers }) => {
    installGlobalErrorHandlers();
  });
}, 0);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)