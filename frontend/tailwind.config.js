/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["var(--font-heading)"],
        body: ["var(--font-body)"],
      },
      backgroundImage: {
        "hero-gradient": "linear-gradient(180deg, #1a1b1e 0%, #101114 100%)",
      },
    },
  },
  plugins: [],
};
