/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    
    // 🚨 修正ポイント: `**` でフォルダ全体を指定するのをやめ、
    // 実際に画面のコードが入っているフォルダだけを狙い撃ちします。
    // （※もし他のフォルダにも画面コードがあれば、行を追加してください）
    '../plugins/Tokyo_hackson_23/renderer/src/**/*.{js,ts,jsx,tsx}',
    '../plugins/Tokyo_hackson_23/src/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
};