import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite configuration for E2E tests with mock backend
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // Points to local mock server instead of backend:8000
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',    // WebSocket connection to local mock server
        ws: true,
      },
    },
  },
})