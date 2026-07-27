import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // ★重要: Electron環境（file://プロトコル）でアセットを正しく読み込むために必須
  base: './',

  plugins: [react()],

  server: {
    // main.js の await mainWindow.loadURL("http://localhost:3000"); に合わせる
    port: 3000,
    
    // Electronアプリのウィンドウで画面を確認するため、
    // Vite起動時にOSの標準ブラウザが勝手に開かないようにする
    open: false,
  },

  build: {
    // main.js の path.join(__dirname, "../dist/index.html") に合わせる
    outDir: 'dist',
    
    // ビルド時に古いdistフォルダの中身を空にする
    emptyOutDir: true,
  }
});