// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  base: './',

  plugins: [react()],

  server: {
    port: 5173,
    strictPort: true,

    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },

  resolve: {
    alias: {
      // 変更点: '../' を使って一つ上の階層(To)に戻り、pluginsフォルダを指定する
      '@tokyo': path.resolve(
        __dirname,
        '../plugins/Tokyo_hackson_23/renderer/src'
      ),
    },
  },
});