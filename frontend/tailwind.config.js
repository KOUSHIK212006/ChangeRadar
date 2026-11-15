/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#191918',
          secondary: '#242321',
          elevated: '#2B2926',
        },
        accent: {
          DEFAULT: '#E45B3F',
          hover: '#F06A4D',
          muted: 'rgba(228, 91, 63, 0.15)',
        },
        text: {
          primary: '#F1EDE5',
          secondary: '#A6A096',
          muted: '#77736B',
        },
        border: {
          DEFAULT: '#393632',
          subtle: '#2E2B27',
          active: '#524E48',
        },
        status: {
          success: '#65B891',
          warning: '#E5B45C',
          danger: '#E45B3F',
          info: '#83A9D1',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        heading: ['"Space Grotesk"', '"DM Sans"', 'Inter', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        card: '12px',
      },
      transitionDuration: {
        standard: '200ms',
      }
    },
  },
  plugins: [],
}

