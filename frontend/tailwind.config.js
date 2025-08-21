/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)']
      },
      colors: {
        ink: '#0b0b0b',
        fog: '#f5f5f5',
        steel: '#d3d3d3'
      },
      letterSpacing: {
        wideish: '.15em'
      },
      boxShadow: {
        card: '0 10px 25px rgba(0,0,0,0.08)'
      },
      backgroundImage: {
        "studio-gradient": "linear-gradient(180deg, #222 0%, #f2f2f2 60%)"
      }
    },
  },
  plugins: [],
}
