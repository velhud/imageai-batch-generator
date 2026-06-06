/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0f172a", // Slate-900
        surface: "#1e293b",    // Slate-800
        "surface-glass": "rgba(30, 41, 59, 0.7)", 
        primary: "#3b82f6",    // Blue-500
        "primary-glow": "#60a5fa",
        accent: "#f59e0b",     // Amber-500
        success: "#10b981",    // Emerald-500
        danger: "#ef4444",     // Red-500
        "text-main": "#f8fafc", // Slate-50
        "text-muted": "#94a3b8", // Slate-400
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.2s ease-out',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}