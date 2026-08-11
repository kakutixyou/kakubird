git push -f origin mainimport { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // '/tokyo-api' から始まるリクエストを東京都のサーバーに横流しする設定
      '/tokyo-api': {
        target: 'https://catalog.data.metro.tokyo.lg.jp',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tokyo-api/, '')
      }
    }
  }
})