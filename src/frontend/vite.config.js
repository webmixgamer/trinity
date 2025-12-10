import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Use localhost for local dev, backend for Docker
const backendHost = process.env.DOCKER_ENV ? 'backend' : 'localhost'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: `http://${backendHost}:8000`,
        changeOrigin: true,
      },
      '/token': {
        target: `http://${backendHost}:8000`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://${backendHost}:8000`,
        ws: true,
      },
    }
  }
})
