/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F8FAFC",
        card: "#FFFFFF",
        primary: "#2563EB",
        primaryLight: "#EFF6FF",
        ink: "#0F172A",
        muted: "#64748B",
        line: "#E2E8F0",
        success: "#16A34A",
        warning: "#F59E0B",
        danger: "#DC2626"
      },
      borderRadius: { xl2: "1rem" }
    }
  },
  plugins: []
};
