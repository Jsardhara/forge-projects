import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        ink: {
          950: "#07080b",
          900: "#0d1015",
          800: "#151a21",
          700: "#1e242d",
          600: "#2a323d",
          500: "#3a4453",
        },
        bone: {
          50: "#f6f3ec",
          100: "#ece7da",
          200: "#d5ccb6",
        },
        risk: {
          green: "#16a34a",
          amber: "#d97706",
          red: "#dc2626",
          black: "#0a0a0a",
        },
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.04) inset, 0 0 0 1px rgba(255,255,255,0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
