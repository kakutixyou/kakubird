// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

<<<<<<< HEAD
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
      '@tokyo': path.resolve(
        __dirname,
        './Tokyo_hackson_23/renderer/src'
      ),
    },
  },
=======

  // ...
  export default defineConfig({
  base: './', // ← この1行を追加！
  plugins: [react()],

server: {
  port: 5173,
  strictPort: true,  // ← これを追加。5173が使えなければエラーにする
  proxy: {
    '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true },
  },
},
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
});