import animate from "tailwindcss-animate";

/** Colors come from CSS variables in src/styles/tokens.css (light + dark). */
const v = (name) => `hsl(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
        display: ["Manrope", "system-ui", "sans-serif"],
      },
      colors: {
        background: v("background"),
        foreground: v("foreground"),
        card: { DEFAULT: v("card"), foreground: v("card-foreground") },
        muted: { DEFAULT: v("muted"), foreground: v("muted-foreground") },
        primary: { DEFAULT: v("primary"), foreground: v("primary-foreground") },
        accent: { DEFAULT: v("accent"), foreground: v("accent-foreground") },
        border: v("border"),
        input: v("input"),
        ring: v("ring"),
        destructive: { DEFAULT: v("blocker"), foreground: v("primary-foreground") },
        dream: { DEFAULT: v("dream"), soft: v("dream-soft") },
        target: { DEFAULT: v("target"), soft: v("target-soft") },
        safety: { DEFAULT: v("safety"), soft: v("safety-soft") },
        plus: { DEFAULT: v("plus"), soft: v("plus-soft") },
        risk: { DEFAULT: v("risk"), soft: v("risk-soft") },
        blocker: { DEFAULT: v("blocker"), soft: v("blocker-soft") },
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
        xl: "var(--radius-xl)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: { "fade-up": "fade-up .35s ease-out both" },
    },
  },
  plugins: [animate],
};
