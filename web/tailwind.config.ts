import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        canvas: "var(--canvas)",
        border: "var(--border)",
        divider: "var(--divider)",
        fg: "var(--fg)",
        "fg-2": "var(--fg-2)",
        "fg-3": "var(--fg-3)",
        disabled: "var(--disabled)",
        a: "var(--a)",
        b: "var(--b)",
        good: "var(--good)",
        bad: "var(--bad)",
        muted: "var(--muted)",
        wash: "var(--wash)",
        focus: "var(--focus)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "IBM Plex Sans Arabic", "sans-serif"],
        ar: ["IBM Plex Sans Arabic", "IBM Plex Sans", "sans-serif"],
      },
      fontSize: {
        display: ["32px", { lineHeight: "40px", fontWeight: "600" }],
        section: ["20px", { lineHeight: "28px", fontWeight: "600" }],
        card: ["15px", { lineHeight: "22px", fontWeight: "500" }],
        kpi: ["28px", { lineHeight: "34px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "22px", fontWeight: "400" }],
        small: ["13px", { lineHeight: "20px", fontWeight: "400" }],
        caption: ["12px", { lineHeight: "16px", fontWeight: "400" }],
      },
      borderRadius: {
        card: "8px",
        control: "6px",
        pill: "999px",
      },
      maxWidth: {
        page: "1440px",
      },
      spacing: {
        gutter: "32px",
        "gutter-md": "24px",
        "gutter-sm": "16px",
        section: "48px",
      },
    },
  },
  plugins: [],
};

export default config;
