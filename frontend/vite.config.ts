import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          components: ['src/components'],
          utils: ['src/utils', 'src/api']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
