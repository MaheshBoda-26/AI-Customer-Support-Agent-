import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors (from Design.md)
        primary: {
          DEFAULT: "#E8722C",
          hover: "#D4611F",
          light: "#FBD9BD",
        },
        accent: {
          DEFAULT: "#F2A65A",
          soft: "#FFF1E0",
        },
        // Semantic colors - Light mode (CSS variables will override)
        surface: "var(--bg-surface)",
        background: "var(--bg-base)",
        muted: "var(--bg-muted)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
        },
        border: "var(--border)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      fontFamily: {
        sans: ["var(--font-family-base)", "system-ui", "sans-serif"],
      },
      fontSize: {
        xs: ["12px", { lineHeight: "1.5" }],
        sm: ["14px", { lineHeight: "1.5" }],
        base: ["16px", { lineHeight: "1.5" }],
        lg: ["18px", { lineHeight: "1.25", fontWeight: "500" }],
        xl: ["22px", { lineHeight: "1.25", fontWeight: "600" }],
        "2xl": ["28px", { lineHeight: "1.25", fontWeight: "700" }],
      },
      borderRadius: {
        DEFAULT: "8px",
        lg: "12px",
      },
      boxShadow: {
        soft: "0 2px 8px rgba(0,0,0,0.06)",
        "soft-dark": "0 2px 8px rgba(0,0,0,0.2)",
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;