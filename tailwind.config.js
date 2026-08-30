/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./frontend/index.html",
    "./frontend/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#000000',
        brand: {
          blue: '#3054ff',
          deep: '#0a1a5c',
          glow: '#4d7cff',
          dark: '#030712',
          light: '#e2e8f0',
        },
      },
      fontFamily: {
        sans: ['Instrument Sans', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
