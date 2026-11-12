import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#050914",
          900: "#0a1124",
          850: "#0f172a",
          800: "#131f3a",
          700: "#1e2e52",
        },
        electric: {
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#2563eb",
        },
      },
      backgroundImage: {
        "xray-grid":
          "radial-gradient(circle at 1px 1px, rgba(56, 189, 248, 0.08) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};

export default config;
