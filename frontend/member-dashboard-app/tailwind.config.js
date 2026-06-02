/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#020713",
          900: "#061426",
          800: "#0b2036"
        },
        cyanAccent: "#29d8ff",
        blueAccent: "#2388ff",
        purpleAccent: "#8d5dff"
      },
      boxShadow: {
        glow: "0 0 42px rgba(41, 216, 255, 0.18)",
        card: "0 22px 70px rgba(0, 0, 0, 0.28)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
