import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef8f5',
          100: '#d6efe8',
          200: '#aee0d2',
          300: '#7dcbb7',
          400: '#4bad97',
          500: '#2f917d',
          600: '#237462',
          700: '#1e5d50',
          800: '#1b4b42',
          900: '#183f38',
        },
        ink: {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d5dae3',
          300: '#b2bbc9',
          400: '#8995a8',
          500: '#6b788d',
          600: '#566175',
          700: '#464f60',
          800: '#3c4351',
          900: '#353a45',
          950: '#22262e',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'PingFang SC',
          'Microsoft YaHei',
          'Noto Sans SC',
          'system-ui',
          'sans-serif',
        ],
      },
      boxShadow: {
        panel: '0 20px 60px -30px rgba(34, 38, 46, 0.35)',
        float: '0 12px 35px -18px rgba(34, 38, 46, 0.25)',
      },
    },
  },
  plugins: [],
} satisfies Config