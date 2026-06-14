import type { Config } from "tailwindcss";

/**
 * "Ledger" design system — a light, editorial, institutional aesthetic for a
 * regulatory compliance workspace. Warm paper canvas, ink text, a confident
 * emerald accent (the colour of "compliant"), and gold / clay / claret for
 * escalating severity. Serif display (Fraunces) over a grotesque body (Archivo)
 * with a mono (IBM Plex Mono) for data, IDs, and verbatim citations.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F4F1E8",
        "paper-2": "#EDE9DC",
        surface: "#FCFAF4",
        raised: "#FFFFFF",
        line: "#E4DECF",
        "line-strong": "#D3CAB5",
        ink: "#211F1A",
        "ink-soft": "#3C392F",
        muted: "#6C6557",
        subtle: "#9A937F",
        emerald: "#0F6E50",
        "emerald-deep": "#0B5640",
        "emerald-soft": "rgba(15,110,80,0.10)",
        gold: "#B5882E",
        clay: "#B05A35",
        claret: "#A8324A",
        // agent role colours (warm, cohesive)
        ingestor: "#3F6E8C",
        mapper: "#6E5A93",
        validator: "#B5882E",
        assigner: "#2C7E84",
        evidence: "#0F6E50",
        auditor: "#A8324A",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        body: ["var(--font-body)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(33,31,26,0.04), 0 10px 26px rgba(33,31,26,0.055)",
        raised: "0 2px 6px rgba(33,31,26,0.06), 0 18px 44px rgba(33,31,26,0.10)",
        ring: "0 0 0 3px rgba(15,110,80,0.16)",
        inset: "inset 0 1px 0 rgba(255,255,255,0.6)",
      },
      borderRadius: {
        xl: "10px",
        "2xl": "14px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "draw-in": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        breathe: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.55s cubic-bezier(0.16,1,0.3,1) both",
        "draw-in": "draw-in 0.5s cubic-bezier(0.16,1,0.3,1) both",
        breathe: "breathe 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
