import type { Config } from 'tailwindcss';
import plugin from 'tailwindcss/plugin';

/**
 * Tailwind CSS configuration for the educational website builder.
 *
 * Supports three themes (default, future-purple, alexandros), four animation
 * levels, three font scales, and class-based dark mode.
 */
const config: Config = {
  // Scan all source files for class names
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],

  // Class-based dark mode so themes can control it via data attributes
  darkMode: 'class',

  theme: {
    extend: {
      // ─────────────────────────────────────────────
      // Color palettes for all three themes
      // ─────────────────────────────────────────────
      colors: {
        // ── Default theme ──────────────────────────
        'theme-primary': 'var(--color-primary)',
        'theme-secondary': 'var(--color-secondary)',
        'theme-accent': 'var(--color-accent)',
        'theme-bg': 'var(--color-bg)',
        'theme-surface': 'var(--color-surface)',
        'theme-text': 'var(--color-text)',
        'theme-text-muted': 'var(--color-text-muted)',
        'theme-border': 'var(--color-border)',
        'theme-glow': 'var(--color-glow)',

        // ── Default static colors ──────────────────
        default: {
          primary: '#2563eb',
          'primary-light': '#3b82f6',
          'primary-dark': '#1d4ed8',
          secondary: '#7c3aed',
          'secondary-light': '#8b5cf6',
          accent: '#0ea5e9',
          'accent-light': '#38bdf8',
          bg: '#f8fafc',
          'bg-dark': '#0f172a',
          surface: '#ffffff',
          'surface-dark': '#1e293b',
          text: '#1e293b',
          'text-dark': '#f1f5f9',
          'text-muted': '#64748b',
          'text-muted-dark': '#94a3b8',
          border: '#e2e8f0',
          'border-dark': '#334155',
        },

        // ── Future-Purple static colors ────────────
        'future-purple': {
          primary: '#7c3aed',
          'primary-light': '#8b5cf6',
          'primary-dark': '#6d28d9',
          secondary: '#a855f7',
          'secondary-light': '#c084fc',
          accent: '#06b6d4',
          'accent-light': '#22d3ee',
          bg: '#0f0a1e',
          surface: '#1a1035',
          text: '#f0e6ff',
          'text-muted': '#a78bfa',
          border: '#3b1f6e',
          glow: '#c084fc',
          'glow-cyan': '#06b6d4',
        },

        // ── Alexandros static colors ───────────────
        alexandros: {
          primary: '#ff9f1c',
          'primary-light': '#ffb347',
          'primary-dark': '#e8890a',
          secondary: '#2563eb',
          'secondary-light': '#3b82f6',
          accent: '#ffffff',
          bg: '#fef9f0',
          surface: '#ffffff',
          'surface-alt': '#fff3e0',
          text: '#1a1a2e',
          'text-muted': '#6b5a3e',
          border: '#f0c080',
          highlight: '#ffd166',
          diamond: '#2563eb',
          square: '#ff9f1c',
        },
      },

      // ─────────────────────────────────────────────
      // Typography — three scales driven by CSS vars
      // ─────────────────────────────────────────────
      fontSize: {
        // Font-scale: small
        'fs-xs': ['0.6875rem', { lineHeight: '1rem' }],     // 11px
        'fs-sm': ['0.8125rem', { lineHeight: '1.25rem' }],  // 13px
        'fs-base': ['0.9375rem', { lineHeight: '1.5rem' }], // 15px
        'fs-lg': ['1.0625rem', { lineHeight: '1.75rem' }],  // 17px
        'fs-xl': ['1.1875rem', { lineHeight: '1.75rem' }],  // 19px
        'fs-2xl': ['1.4375rem', { lineHeight: '2rem' }],    // 23px
        'fs-3xl': ['1.8125rem', { lineHeight: '2.25rem' }], // 29px
        'fs-4xl': ['2.1875rem', { lineHeight: '2.5rem' }],  // 35px
        'fs-5xl': ['2.9375rem', { lineHeight: '1' }],       // 47px

        // Font-scale: medium (default Tailwind baseline)
        'fm-xs': ['0.75rem', { lineHeight: '1rem' }],
        'fm-sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'fm-base': ['1rem', { lineHeight: '1.5rem' }],
        'fm-lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'fm-xl': ['1.25rem', { lineHeight: '1.75rem' }],
        'fm-2xl': ['1.5rem', { lineHeight: '2rem' }],
        'fm-3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        'fm-4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        'fm-5xl': ['3rem', { lineHeight: '1' }],

        // Font-scale: large
        'fl-xs': ['0.875rem', { lineHeight: '1.25rem' }],
        'fl-sm': ['1rem', { lineHeight: '1.5rem' }],
        'fl-base': ['1.125rem', { lineHeight: '1.75rem' }],
        'fl-lg': ['1.25rem', { lineHeight: '1.75rem' }],
        'fl-xl': ['1.5rem', { lineHeight: '2rem' }],
        'fl-2xl': ['1.875rem', { lineHeight: '2.25rem' }],
        'fl-3xl': ['2.25rem', { lineHeight: '2.5rem' }],
        'fl-4xl': ['3rem', { lineHeight: '1' }],
        'fl-5xl': ['3.75rem', { lineHeight: '1' }],
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Lexend', 'Inter', 'sans-serif'],
      },

      // ─────────────────────────────────────────────
      // Spacing — standardised scale
      // ─────────────────────────────────────────────
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
        '22': '5.5rem',
        '30': '7.5rem',
        '100': '25rem',
        '112': '28rem',
        '128': '32rem',
        '144': '36rem',
      },

      // ─────────────────────────────────────────────
      // Max widths
      // ─────────────────────────────────────────────
      maxWidth: {
        'page': '1440px',
        'content': '800px',
        'wide': '1200px',
        'narrow': '640px',
      },

      // ─────────────────────────────────────────────
      // Border radius
      // ─────────────────────────────────────────────
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },

      // ─────────────────────────────────────────────
      // Box shadows
      // ─────────────────────────────────────────────
      boxShadow: {
        'glow-sm': '0 0 8px 2px var(--color-glow, #c084fc)',
        'glow-md': '0 0 16px 4px var(--color-glow, #c084fc)',
        'glow-lg': '0 0 32px 8px var(--color-glow, #c084fc)',
        'card': '0 4px 24px -4px rgba(0,0,0,0.12)',
        'card-hover': '0 8px 32px -4px rgba(0,0,0,0.18)',
      },

      // ─────────────────────────────────────────────
      // Backdrop blur
      // ─────────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
      },

      // ─────────────────────────────────────────────
      // Animations — 4 levels
      // ─────────────────────────────────────────────
      animation: {
        // Level: low (subtle, 300 ms)
        'fade-in-low': 'fadeIn 300ms ease-out both',
        'slide-up-low': 'slideUp 300ms ease-out both',
        'scale-in-low': 'scaleIn 300ms ease-out both',

        // Level: medium (standard, 500 ms)
        'fade-in': 'fadeIn 500ms ease-out both',
        'slide-up': 'slideUp 500ms ease-out both',
        'slide-down': 'slideDown 500ms ease-out both',
        'scale-in': 'scaleIn 500ms ease-out both',

        // Level: high (complex, 700 ms+)
        'fade-in-high': 'fadeIn 700ms cubic-bezier(0.16,1,0.3,1) both',
        'slide-up-high': 'slideUp 700ms cubic-bezier(0.16,1,0.3,1) both',
        'slide-down-high': 'slideDown 700ms cubic-bezier(0.16,1,0.3,1) both',
        'scale-in-high': 'scaleIn 700ms cubic-bezier(0.16,1,0.3,1) both',

        // Continuous effects
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'spin-slow': 'spin 8s linear infinite',
      },

      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(24px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-24px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.9)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        glow: {
          from: { boxShadow: '0 0 8px 2px var(--color-glow, #c084fc)' },
          to: { boxShadow: '0 0 24px 8px var(--color-glow, #c084fc)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5', boxShadow: '0 0 32px 8px var(--color-glow, #c084fc)' },
        },
      },

      // ─────────────────────────────────────────────
      // Transition timing
      // ─────────────────────────────────────────────
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
        '400': '400ms',
        '600': '600ms',
        '800': '800ms',
        '900': '900ms',
      },

      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'bounce-in': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },

      // ─────────────────────────────────────────────
      // Grid utilities
      // ─────────────────────────────────────────────
      gridTemplateColumns: {
        'auto-fill-xs': 'repeat(auto-fill, minmax(160px, 1fr))',
        'auto-fill-sm': 'repeat(auto-fill, minmax(200px, 1fr))',
        'auto-fill-md': 'repeat(auto-fill, minmax(280px, 1fr))',
        'auto-fill-lg': 'repeat(auto-fill, minmax(360px, 1fr))',
      },

      // ─────────────────────────────────────────────
      // Z-index scale
      // ─────────────────────────────────────────────
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },

  plugins: [
    // ────────────────────────────────────────────
    // Plugin: glass-card utility
    // ────────────────────────────────────────────
    plugin(({ addUtilities }) => {
      addUtilities({
        '.glass': {
          background: 'rgba(255, 255, 255, 0.08)',
          'backdrop-filter': 'blur(12px)',
          '-webkit-backdrop-filter': 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
        },
        '.glass-dark': {
          background: 'rgba(0, 0, 0, 0.25)',
          'backdrop-filter': 'blur(12px)',
          '-webkit-backdrop-filter': 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        },
        '.glass-strong': {
          background: 'rgba(255, 255, 255, 0.15)',
          'backdrop-filter': 'blur(20px)',
          '-webkit-backdrop-filter': 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.25)',
        },
      });
    }),

    // ────────────────────────────────────────────
    // Plugin: text-balance and text-pretty
    // ────────────────────────────────────────────
    plugin(({ addUtilities }) => {
      addUtilities({
        '.text-balance': { 'text-wrap': 'balance' },
        '.text-pretty': { 'text-wrap': 'pretty' },
      });
    }),

    // ────────────────────────────────────────────
    // Plugin: animation-delay utilities
    // ────────────────────────────────────────────
    plugin(({ matchUtilities, theme }) => {
      matchUtilities(
        { 'animation-delay': (value) => ({ 'animation-delay': value }) },
        { values: theme('transitionDelay') },
      );
    }),

    // ────────────────────────────────────────────
    // Plugin: geometric pattern backgrounds
    // ────────────────────────────────────────────
    plugin(({ addUtilities }) => {
      addUtilities({
        '.bg-grid-pattern': {
          'background-image':
            'linear-gradient(rgba(99,102,241,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.08) 1px, transparent 1px)',
          'background-size': '40px 40px',
        },
        '.bg-dot-pattern': {
          'background-image': 'radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px)',
          'background-size': '24px 24px',
        },
        '.bg-alexandros-pattern': {
          'background-image':
            "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Crect x='5' y='5' width='12' height='12' fill='%23ff9f1c' opacity='0.15' rx='1'/%3E%3Cpolygon points='43,2 50,15 36,15' fill='%232563eb' opacity='0.12'/%3E%3Crect x='35' y='35' width='12' height='12' fill='%23ff9f1c' opacity='0.10' rx='1' transform='rotate(45 41 41)'/%3E%3C/g%3E%3C/svg%3E\")",
          'background-size': '60px 60px',
        },
      });
    }),
  ],
};

export default config;
