import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://backend:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.VITE_BACKEND_URL || 'ws://backend:8000',
        ws: true,
      },
    },
  },

  preview: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: [
      'adsmind.online',
      'www.adsmind.online',
      'localhost'
    ],
  },

  build: {
    outDir: 'dist',
    sourcemap: false,
    emptyOutDir: true,
  },
});