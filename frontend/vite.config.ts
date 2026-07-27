// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';


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
});