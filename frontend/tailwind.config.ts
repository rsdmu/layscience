import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#000000',
        accent: '#00BFFF',
        surface: '#0a0a0a',
        border: '#1a1a1a'
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(0,191,255,.4), 0 0 30px rgba(0,191,255,.08)'
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0,191,255, .6)' },
          '50%': { boxShadow: '0 0 0 8px rgba(0,191,255, 0)' }
        }
      },
      animation: { pulseGlow: 'pulseGlow 2s infinite' }
    }
  },
  darkMode: 'class',
  plugins: []
}
export default config
