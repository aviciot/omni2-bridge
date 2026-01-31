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
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "#6366F1",
          foreground: "#FFFFFF",
          50: "#EEF2FF",
          100: "#E0E7FF",
          500: "#6366F1",
          600: "#4F46E5",
          700: "#4338CA",
        },
        secondary: {
          DEFAULT: "#8B5CF6",
          foreground: "#FFFFFF",
        },
        accent: {
          DEFAULT: "#EC4899",
          foreground: "#FFFFFF",
        },
        success: "#10B981",
        warning: "#F59E0B",
        error: "#EF4444",
        dark: {
          bg: "#0F172A",
          card: "#1E293B",
          hover: "#334155",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
