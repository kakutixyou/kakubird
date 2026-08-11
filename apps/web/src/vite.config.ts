// apps/web/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true, // 先ほどの外部ブラウザで開く設定
    proxy: {
      // /api で始まるリクエストを Pythonサーバー(8765) に転送する
      '/api': {
        target: 'http://127.0.0.1:8765', // ← ここを 8765 に修正
        changeOrigin: true,
        // 必要に応じてパスの書き換え設定（現状の構成に合わせてください）
        // rewrite: (path) => path.replace(/^\/api/, ''), 
      },
    },
  },
});