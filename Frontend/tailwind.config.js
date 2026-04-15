// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  // 必须确保 content 包含这行，告诉 Tailwind 去哪里找 class
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}", 
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        academic: {
          blue: { dark: '#003366', DEFAULT: '#004a99', light: '#4A90E2', bg: '#e6f0ff' },
          gray: { bg: '#F5F7FA', text: '#4A5568', border: '#E2E8F0' },
          accent: { orange: '#ED8936', green: '#48BB78' }
        }
      },
      animation: { 'fade-in': 'fadeIn 0.5s ease-out' },
      keyframes: { fadeIn: { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } } }
    }
  },
  plugins: [],
}