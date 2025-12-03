/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        page: {
          bg: 'var(--page-bg)',
          container: 'var(--page-container)',
          content: 'var(--page-content)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
        border: {
          input: 'var(--border-input)',
          option: 'var(--border-option)',
          divider: 'var(--border-divider)',
        },
        step: {
          bg: 'var(--step-bg)',
          control: 'var(--step-control)',
          progress: 'var(--step-progress)',
        }
      },
      fontFamily: {
        'alibaba': ['Alibaba PuHuiTi 2.0', 'sans-serif'],
        'pingfang': ['PingFang SC', 'sans-serif'],
      },
      boxShadow: {
        'input': '0px 12px 24px -16px rgba(54, 54, 73, 0.04), 0px 12px 40px 0px rgba(51, 51, 71, 0.08), 0px 0px 1px 0px rgba(44, 44, 54, 0.02)',
      },
      keyframes: {
        fadeIn: {
          'from': { opacity: '0', transform: 'translateY(10px)' },
          'to': { opacity: '1', transform: 'translateY(0)' }
        }
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-out forwards'
      }
    },
  },
  plugins: [
    require('tailwind-scrollbar-hide'),
    require('tailwind-scrollbar')
  ],
}