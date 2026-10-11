import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/meta': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/scenarios': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/audit': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/investigate': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/hitl': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/report': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
