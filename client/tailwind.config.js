const defaultTheme = require("tailwindcss/defaultTheme");
const {
  default: flattenColorPalette,
} = require("tailwindcss/lib/util/flattenColorPalette");

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  fontFamily: {
    sans: ['"Space Grotesk"', '"Geist Variable"', ...defaultTheme.fontFamily.sans],
  },
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      animation: {
        "slow-spin": "slow-spin 25s linear infinite",
        "gradient-x": "gradient-x 15s ease infinite",
        "gradient-y": "gradient-y 15s ease infinite",
        "gradient-xy": "gradient-xy 15s ease infinite",
        "border-flow": "border-flow 3s ease infinite",
        "loader-icons-1": "loader-icons-1 6s infinite linear",
        "loader-icons-2": "loader-icons-2 6s infinite linear",
        "loader-icons": "loader-icons-1 6s infinite linear, loader-icons-2 6s infinite linear",
      },
      keyframes: {
        "slow-spin": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "gradient-y": {
          "0%, 100%": {
            "background-size": "400% 400%",
            "background-position": "center top",
          },
          "50%": {
            "background-size": "200% 200%",
            "background-position": "center center",
          },
        },
        "gradient-x": {
          "0%, 100%": {
            "background-size": "200% 200%",
            "background-position": "left center",
          },
          "50%": {
            "background-size": "200% 200%",
            "background-position": "right center",
          },
        },
        "gradient-xy": {
          "0%, 100%": {
            "background-size": "400% 400%",
            "background-position": "left top",
          },
          "50%": {
            "background-size": "200% 200%",
            "background-position": "right bottom",
          },
        },
        "border-flow": {
          "0%, 100%": {
            "background-position": "0% 50%",
          },
          "50%": {
            "background-position": "100% 50%",
          },
        },
        "loader-icons-1": {
          "0%, 100%": { backgroundPosition: "0 -70px, 100% -70px, 0 -70px, 100% -70px" },
          "17.5%": { backgroundPosition: "0 100%, 100% -70px, 0 -70px, 100% -70px" },
          "35%": { backgroundPosition: "0 100%, 100% 100%, 0 -70px, 100% -70px" },
          "52.5%": { backgroundPosition: "0 100%, 100% 100%, 0 calc(100% - 24px), 100% -70px" },
          "70%, 98%": { backgroundPosition: "0 100%, 100% 100%, 0 calc(100% - 24px), 100% calc(100% - 24px)" }
        },
        "loader-icons-2": {
          "0%, 70%": { transform: "translate(0)" },
          "100%": { transform: "translate(200%)" }
        },
      },
      backdropBlur: {
        xs: "2px",
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        scene: {
          DEFAULT: "hsl(var(--scene))",
          foreground: "hsl(var(--scene-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
    },
  },
  plugins: [addVariablesForColors, require("tailwindcss-animate")],
};

function addVariablesForColors({ addBase, theme }) {
  let allColors = flattenColorPalette(theme("colors"));
  let newVars = Object.fromEntries(
    Object.entries(allColors).map(([key, val]) => [`--${key}`, val]),
  );

  addBase({
    ":root": newVars,
  });
}
