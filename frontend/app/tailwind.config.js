/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        guardian: {
          bg: '#0F172A', // Slate 900
          card: '#1E293B', // Slate 800
          text: '#F8FAFC', // Slate 50
          muted: '#94A3B8', // Slate 400
          danger: '#EF4444', // Red 500
          warning: '#F59E0B', // Amber 500
          success: '#10B981', // Emerald 500
          accent: '#3B82F6', // Blue 500
        }
      }
    },
  },
  plugins: [],
}
