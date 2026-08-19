/** @type {import('tailwindcss').Config} */
export default {
  // 👇 contentを1つにまとめ、正しい相対パス（../plugins/...）を指定します
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    '../plugins/Tokyo_hackson_23/**/*.{js,ts,jsx,tsx}' // ⬅️ frontendから1つ上の階層に上がり、pluginsを見に行く
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