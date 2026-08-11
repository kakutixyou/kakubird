import type { Config } from 'tailwindcss';
import plugin from 'tailwindcss/plugin';

/**
 * Root-level Tailwind CSS configuration.
 *
 * This mirrors the render-engine config at `packages/render-engine/config/tailwind.config.ts`
 * and is used for top-level tooling (e.g. Storybook, documentation site) that
 * needs the same design tokens without depending on the package.
 */
const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './packages/render-engine/src/**/*.{js,ts,jsx,tsx}',
  ],

  darkMode: 'class',

  theme: {
    extend: {
      colors: {
        'theme-primary':    'var(--color-primary)',
        'theme-secondary':  'var(--color-secondary)',
        'theme-accent':     'var(--color-accent)',
        'theme-bg':         'var(--color-bg)',
        'theme-surface':    'var(--color-surface)',
        'theme-text':       'var(--color-text)',
        'theme-text-muted': 'var(--color-text-muted)',
        'theme-border':     'var(--color-border)',
        'theme-glow':       'var(--color-glow)',

        default: {
          primary:        '#2563eb',
          'primary-light':'#3b82f6',
          'primary-dark': '#1d4ed8',
          secondary:      '#7c3aed',
          accent:         '#0ea5e9',
          bg:             '#f8fafc',
          'bg-dark':      '#0f172a',
          surface:        '#ffffff',
          'surface-dark': '#1e293b',
          text:           '#1e293b',
          'text-dark':    '#f1f5f9',
          'text-muted':   '#64748b',
          border:         '#e2e8f0',
          'border-dark':  '#334155',
        },

        'future-purple': {
          primary:         '#7c3aed',
          'primary-light': '#8b5cf6',
          secondary:       '#a855f7',
          accent:          '#06b6d4',
          bg:              '#0f0a1e',
          surface:         '#1a1035',
          text:            '#f0e6ff',
          'text-muted':    '#a78bfa',
          border:          '#3b1f6e',
          glow:            '#c084fc',
        },

        alexandros: {
          primary:        '#ff9f1c',
          'primary-light':'#ffb347',
          secondary:      '#2563eb',
          accent:         '#ffffff',
          bg:             '#fef9f0',
          surface:        '#ffffff',
          'surface-alt':  '#fff3e0',
          text:           '#1a1a2e',
          'text-muted':   '#6b5a3e',
          border:         '#f0c080',
          highlight:      '#ffd166',
        },
      },

      fontSize: {
        'fs-xs':   ['0.6875rem',  { lineHeight: '1rem' }],
        'fs-sm':   ['0.8125rem',  { lineHeight: '1.25rem' }],
        'fs-base': ['0.9375rem',  { lineHeight: '1.5rem' }],
        'fs-lg':   ['1.0625rem',  { lineHeight: '1.75rem' }],
        'fs-xl':   ['1.1875rem',  { lineHeight: '1.75rem' }],
        'fs-2xl':  ['1.4375rem',  { lineHeight: '2rem' }],
        'fs-3xl':  ['1.8125rem',  { lineHeight: '2.25rem' }],
        'fs-4xl':  ['2.1875rem',  { lineHeight: '2.5rem' }],
        'fs-5xl':  ['2.9375rem',  { lineHeight: '1' }],
        'fl-xs':   ['0.875rem',   { lineHeight: '1.25rem' }],
        'fl-sm':   ['1rem',       { lineHeight: '1.5rem' }],
        'fl-base': ['1.125rem',   { lineHeight: '1.75rem' }],
        'fl-lg':   ['1.25rem',    { lineHeight: '1.75rem' }],
        'fl-xl':   ['1.5rem',     { lineHeight: '2rem' }],
        'fl-2xl':  ['1.875rem',   { lineHeight: '2.25rem' }],
        'fl-3xl':  ['2.25rem',    { lineHeight: '2.5rem' }],
        'fl-4xl':  ['3rem',       { lineHeight: '1' }],
        'fl-5xl':  ['3.75rem',    { lineHeight: '1' }],
      },

      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Lexend', 'Inter', 'sans-serif'],
      },

      maxWidth: {
        page:    '1440px',
        content: '800px',
        wide:    '1200px',
        narrow:  '640px',
      },

      boxShadow: {
        'glow-sm': '0 0 8px 2px var(--color-glow, #c084fc)',
        'glow-md': '0 0 16px 4px var(--color-glow, #c084fc)',
        'glow-lg': '0 0 32px 8px var(--color-glow, #c084fc)',
        card:       '0 4px 24px -4px rgba(0,0,0,0.12)',
        'card-hover':'0 8px 32px -4px rgba(0,0,0,0.18)',
      },

      animation: {
        'fade-in-low':   'fadeIn 300ms ease-out both',
        'slide-up-low':  'slideUp 300ms ease-out both',
        'scale-in-low':  'scaleIn 300ms ease-out both',
        'fade-in':       'fadeIn 500ms ease-out both',
        'slide-up':      'slideUp 500ms ease-out both',
        'slide-down':    'slideDown 500ms ease-out both',
        'scale-in':      'scaleIn 500ms ease-out both',
        'fade-in-high':  'fadeIn 700ms cubic-bezier(0.16,1,0.3,1) both',
        'slide-up-high': 'slideUp 700ms cubic-bezier(0.16,1,0.3,1) both',
        glow:            'glow 2s ease-in-out infinite alternate',
        float:           'float 3s ease-in-out infinite',
        'pulse-glow':    'pulseGlow 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },

      keyframes: {
        fadeIn:   { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp:  { from: { opacity: '0', transform: 'translateY(24px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideDown:{ from: { opacity: '0', transform: 'translateY(-24px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        scaleIn:  { from: { opacity: '0', transform: 'scale(0.9)' }, to: { opacity: '1', transform: 'scale(1)' } },
        glow:     { from: { boxShadow: '0 0 8px 2px var(--color-glow,#c084fc)' }, to: { boxShadow: '0 0 24px 8px var(--color-glow,#c084fc)' } },
        float:    { '0%,100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-10px)' } },
        pulseGlow:{ '0%,100%': { opacity: '1' }, '50%': { opacity: '0.5', boxShadow: '0 0 32px 8px var(--color-glow,#c084fc)' } },
      },

      transitionTimingFunction: {
        spring:     'cubic-bezier(0.16, 1, 0.3, 1)',
        'bounce-in':'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },
    },
  },

  plugins: [
    plugin(({ addUtilities }) => {
      addUtilities({
        '.glass': {
          background: 'rgba(255,255,255,0.08)',
          'backdrop-filter': 'blur(12px)',
          '-webkit-backdrop-filter': 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.15)',
        },
        '.glass-dark': {
          background: 'rgba(0,0,0,0.25)',
          'backdrop-filter': 'blur(12px)',
          '-webkit-backdrop-filter': 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.08)',
        },
        '.neumorphism': {
          background: 'var(--surface-color, #f0f0f0)',
          border: 'none',
          'border-radius': '20px',
          'box-shadow': '8px 8px 16px rgba(0,0,0,0.1), -8px -8px 16px rgba(255,255,255,0.7)',
        },
        '.bordered': {
          background: 'transparent',
          border: '2px solid currentColor',
          'border-radius': '12px',
          'box-shadow': 'none',
        },
        '.elevated': {
          background: 'white',
          border: 'none',
          'border-radius': '12px',
          'box-shadow': '0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1)',
          transition: 'box-shadow 0.3s ease',
        },
        '.paper': {
          background: '#fafaf8',
          border: '1px solid #e5e5dc',
          'box-shadow': '0 2px 8px rgba(0,0,0,0.05)',
          'border-radius': '8px',
        },
        '.glow': {
          background: 'rgba(124,58,237,0.08)',
          border: '2px solid rgba(124,58,237,0.4)',
          'box-shadow': '0 0 20px rgba(124,58,237,0.3), inset 0 0 20px rgba(124,58,237,0.08)',
          'border-radius': '12px',
        },
        '.flat': {
          background: 'var(--flat-bg, #f5f5f5)',
          border: 'none',
          'box-shadow': 'none',
          'border-radius': '8px',
        },
        '.frosted-dark': {
          'backdrop-filter': 'blur(8px)',
          '-webkit-backdrop-filter': 'blur(8px)',
          background: 'rgba(0,0,0,0.6)',
          border: '1px solid rgba(255,255,255,0.1)',
          'box-shadow': '0 8px 32px rgba(0,0,0,0.4)',
          'border-radius': '12px',
          color: 'white',
        },
      });
    }),
    plugin(({ addUtilities }) => {
      addUtilities({
        '.text-balance': { 'text-wrap': 'balance' },
        '.text-pretty':  { 'text-wrap': 'pretty' },
        '.bg-grid-pattern': {
          'background-image':
            'linear-gradient(rgba(99,102,241,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.08) 1px, transparent 1px)',
          'background-size': '40px 40px',
        },
        '.bg-dot-pattern': {
          'background-image': 'radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px)',
          'background-size': '24px 24px',
        },
      });
    }),
  ],
};

export default config;
