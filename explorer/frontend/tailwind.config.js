/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        xai: {
          primary: '#00d4aa',
          secondary: '#00b894',
          dark: '#0a0f1c',
          darker: '#060a14',
          card: '#111827',
          border: '#1f2937',
          text: '#e5e7eb',
          muted: '#9ca3af',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
