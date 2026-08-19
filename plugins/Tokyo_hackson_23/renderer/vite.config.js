import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  base: './',

  plugins: [react()],

  server: {
    port: 5173,
    strictPort: true,

    allowedHosts: [
      'k022c0001y.com',
    ],

    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },

  resolve: {
    alias: {
      '@tokyo': path.resolve(__dirname, './src'),
    },
  },
});