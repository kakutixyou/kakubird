/**
 * Theme definitions for the educational website builder.
 *
 * Each theme exports a strongly-typed object consumed by the render engine to
 * inject CSS custom properties and derive Tailwind class names at runtime.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Core type aliases
// ─────────────────────────────────────────────────────────────────────────────

export type Theme = 'default' | 'future-purple' | 'alexandros';
export type AnimationLevel = 'none' | 'low' | 'medium' | 'high';
export type FontScale = 'small' | 'medium' | 'large';
export type BackgroundStyle = 'gradient-grid' | 'solid' | 'pattern';

// ─────────────────────────────────────────────────────────────────────────────
// Color token interfaces
// ─────────────────────────────────────────────────────────────────────────────

export interface ColorTokens {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  secondary: string;
  secondaryLight: string;
  accent: string;
  accentLight: string;
  background: string;
  backgroundDark?: string;
  surface: string;
  surfaceDark?: string;
  surfaceAlt?: string;
  text: string;
  textDark?: string;
  textMuted: string;
  textMutedDark?: string;
  border: string;
  borderDark?: string;
  glow?: string;
  glowCyan?: string;
  highlight?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Typography token interface
// ─────────────────────────────────────────────────────────────────────────────

export interface TypographyTokens {
  fontFamily: {
    sans: string[];
    mono: string[];
    display: string[];
  };
  /** Scale multiplier applied on top of the base Tailwind font sizes */
  scaleMultiplier: {
    small: number;
    medium: number;
    large: number;
  };
  baseSize: string;
  lineHeight: string;
  letterSpacing: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Animation configuration interface
// ─────────────────────────────────────────────────────────────────────────────

export interface AnimationConfig {
  /** Duration for entrance/exit animations */
  duration: string;
  /** Duration for hover/interactive micro-animations */
  microDuration: string;
  /** Easing function */
  easing: string;
  /** Whether complex continuous animations (glow, float) are enabled */
  enableContinuous: boolean;
  /** Stagger delay between sibling elements */
  staggerDelay: string;
}

export type AnimationPresets = Record<AnimationLevel, AnimationConfig>;

// ─────────────────────────────────────────────────────────────────────────────
// Background style configuration
// ─────────────────────────────────────────────────────────────────────────────

export interface BackgroundConfig {
  /** CSS value for background-image */
  backgroundImage?: string;
  /** CSS value for background-color */
  backgroundColor?: string;
  /** CSS value for background-size */
  backgroundSize?: string;
}

export type BackgroundPresets = Record<BackgroundStyle, BackgroundConfig>;

// ─────────────────────────────────────────────────────────────────────────────
// Full theme definition
// ─────────────────────────────────────────────────────────────────────────────

export interface ThemeDefinition {
  id: Theme;
  displayName: string;
  description: string;
  colors: ColorTokens;
  typography: TypographyTokens;
  animations: AnimationPresets;
  backgrounds: BackgroundPresets;
  /** Map of CSS custom property names → values for light mode */
  cssVarsLight: Record<string, string>;
  /** Map of CSS custom property names → values for dark mode */
  cssVarsDark: Record<string, string>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Block props interfaces
// ─────────────────────────────────────────────────────────────────────────────

export interface PageConfig {
  theme: Theme;
  animationLevel: AnimationLevel;
  fontScale: FontScale;
  backgroundStyle: BackgroundStyle;
  maxWidth: string;
}

export interface BlockProps {
  variant: string;
  theme: Theme;
  animationLevel: AnimationLevel;
  fontScale?: FontScale;
  content: Record<string, unknown>;
  className?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared animation presets (reused across themes)
// ─────────────────────────────────────────────────────────────────────────────

const SHARED_ANIMATION_PRESETS: AnimationPresets = {
  none: {
    duration: '0ms',
    microDuration: '0ms',
    easing: 'linear',
    enableContinuous: false,
    staggerDelay: '0ms',
  },
  low: {
    duration: '300ms',
    microDuration: '150ms',
    easing: 'ease-out',
    enableContinuous: false,
    staggerDelay: '50ms',
  },
  medium: {
    duration: '500ms',
    microDuration: '200ms',
    easing: 'ease-out',
    enableContinuous: true,
    staggerDelay: '75ms',
  },
  high: {
    duration: '700ms',
    microDuration: '250ms',
    easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
    enableContinuous: true,
    staggerDelay: '100ms',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// DEFAULT THEME
// ─────────────────────────────────────────────────────────────────────────────

export const defaultTheme: ThemeDefinition = {
  id: 'default',
  displayName: 'Default',
  description: 'Professional blue/gray palette with light and dark mode support.',

  colors: {
    primary: '#2563eb',
    primaryLight: '#3b82f6',
    primaryDark: '#1d4ed8',
    secondary: '#7c3aed',
    secondaryLight: '#8b5cf6',
    accent: '#0ea5e9',
    accentLight: '#38bdf8',
    background: '#f8fafc',
    backgroundDark: '#0f172a',
    surface: '#ffffff',
    surfaceDark: '#1e293b',
    text: '#1e293b',
    textDark: '#f1f5f9',
    textMuted: '#64748b',
    textMutedDark: '#94a3b8',
    border: '#e2e8f0',
    borderDark: '#334155',
  },

  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      display: ['Lexend', 'Inter', 'sans-serif'],
    },
    scaleMultiplier: { small: 0.875, medium: 1, large: 1.125 },
    baseSize: '1rem',
    lineHeight: '1.5',
    letterSpacing: '0em',
  },

  animations: SHARED_ANIMATION_PRESETS,

  backgrounds: {
    'gradient-grid': {
      backgroundImage:
        'linear-gradient(to bottom right, #f8fafc, #eff6ff), ' +
        'linear-gradient(rgba(37,99,235,0.06) 1px, transparent 1px), ' +
        'linear-gradient(90deg, rgba(37,99,235,0.06) 1px, transparent 1px)',
      backgroundSize: '100%, 40px 40px, 40px 40px',
    },
    solid: { backgroundColor: '#f8fafc' },
    pattern: {
      backgroundImage:
        'radial-gradient(circle, rgba(37,99,235,0.1) 1px, transparent 1px)',
      backgroundSize: '24px 24px',
      backgroundColor: '#f8fafc',
    },
  },

  cssVarsLight: {
    '--color-primary': '#2563eb',
    '--color-secondary': '#7c3aed',
    '--color-accent': '#0ea5e9',
    '--color-bg': '#f8fafc',
    '--color-surface': '#ffffff',
    '--color-text': '#1e293b',
    '--color-text-muted': '#64748b',
    '--color-border': '#e2e8f0',
    '--color-glow': '#3b82f6',
  },

  cssVarsDark: {
    '--color-primary': '#3b82f6',
    '--color-secondary': '#8b5cf6',
    '--color-accent': '#38bdf8',
    '--color-bg': '#0f172a',
    '--color-surface': '#1e293b',
    '--color-text': '#f1f5f9',
    '--color-text-muted': '#94a3b8',
    '--color-border': '#334155',
    '--color-glow': '#3b82f6',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// FUTURE-PURPLE THEME
// ─────────────────────────────────────────────────────────────────────────────

export const futurePurpleTheme: ThemeDefinition = {
  id: 'future-purple',
  displayName: 'Future Purple',
  description: 'Purple accents with cyan glow effects and dark gradient backgrounds.',

  colors: {
    primary: '#7c3aed',
    primaryLight: '#8b5cf6',
    primaryDark: '#6d28d9',
    secondary: '#a855f7',
    secondaryLight: '#c084fc',
    accent: '#06b6d4',
    accentLight: '#22d3ee',
    background: '#0f0a1e',
    surface: '#1a1035',
    text: '#f0e6ff',
    textMuted: '#a78bfa',
    border: '#3b1f6e',
    glow: '#c084fc',
    glowCyan: '#06b6d4',
  },

  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      display: ['Lexend', 'Orbitron', 'sans-serif'],
    },
    scaleMultiplier: { small: 0.875, medium: 1, large: 1.125 },
    baseSize: '1rem',
    lineHeight: '1.6',
    letterSpacing: '0.01em',
  },

  animations: SHARED_ANIMATION_PRESETS,

  backgrounds: {
    'gradient-grid': {
      backgroundImage:
        'linear-gradient(135deg, #0f0a1e 0%, #1a0a2e 50%, #0a0a1e 100%), ' +
        'linear-gradient(rgba(124,58,237,0.12) 1px, transparent 1px), ' +
        'linear-gradient(90deg, rgba(124,58,237,0.12) 1px, transparent 1px)',
      backgroundSize: '100%, 40px 40px, 40px 40px',
    },
    solid: { backgroundColor: '#0f0a1e' },
    pattern: {
      backgroundImage:
        'radial-gradient(circle, rgba(192,132,252,0.15) 1px, transparent 1px)',
      backgroundSize: '28px 28px',
      backgroundColor: '#0f0a1e',
    },
  },

  cssVarsLight: {
    '--color-primary': '#7c3aed',
    '--color-secondary': '#a855f7',
    '--color-accent': '#06b6d4',
    '--color-bg': '#0f0a1e',
    '--color-surface': '#1a1035',
    '--color-text': '#f0e6ff',
    '--color-text-muted': '#a78bfa',
    '--color-border': '#3b1f6e',
    '--color-glow': '#c084fc',
  },

  // Future-purple is always dark; dark vars mirror light vars
  cssVarsDark: {
    '--color-primary': '#8b5cf6',
    '--color-secondary': '#c084fc',
    '--color-accent': '#22d3ee',
    '--color-bg': '#070413',
    '--color-surface': '#120b28',
    '--color-text': '#f5f0ff',
    '--color-text-muted': '#c4b5fd',
    '--color-border': '#4c1d95',
    '--color-glow': '#d8b4fe',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// ALEXANDROS THEME
// ─────────────────────────────────────────────────────────────────────────────

export const alexandrosTheme: ThemeDefinition = {
  id: 'alexandros',
  displayName: 'Alexandros',
  description: 'Vibrant orange squares and blue diamonds with bright pastel backgrounds.',

  colors: {
    primary: '#ff9f1c',
    primaryLight: '#ffb347',
    primaryDark: '#e8890a',
    secondary: '#2563eb',
    secondaryLight: '#3b82f6',
    accent: '#ffffff',
    accentLight: '#f0f9ff',
    background: '#fef9f0',
    surface: '#ffffff',
    surfaceAlt: '#fff3e0',
    text: '#1a1a2e',
    textMuted: '#6b5a3e',
    border: '#f0c080',
    highlight: '#ffd166',
  },

  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      display: ['Lexend', 'Nunito', 'sans-serif'],
    },
    scaleMultiplier: { small: 0.875, medium: 1, large: 1.125 },
    baseSize: '1rem',
    lineHeight: '1.55',
    letterSpacing: '0em',
  },

  animations: SHARED_ANIMATION_PRESETS,

  backgrounds: {
    'gradient-grid': {
      backgroundImage:
        "linear-gradient(to bottom right, #fef9f0, #fff3e0), " +
        "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='5' y='5' width='12' height='12' fill='%23ff9f1c' opacity='0.12' rx='1'/%3E%3Crect x='35' y='35' width='12' height='12' fill='%23ff9f1c' opacity='0.10' rx='1' transform='rotate(45 41 41)'/%3E%3Cpolygon points='43,2 50,15 36,15' fill='%232563eb' opacity='0.10'/%3E%3C/svg%3E\")",
      backgroundSize: '100%, 60px 60px',
    },
    solid: { backgroundColor: '#fef9f0' },
    pattern: {
      backgroundImage:
        "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='5' y='5' width='12' height='12' fill='%23ff9f1c' opacity='0.12' rx='1'/%3E%3Crect x='35' y='35' width='12' height='12' fill='%23ff9f1c' opacity='0.10' rx='1' transform='rotate(45 41 41)'/%3E%3Cpolygon points='43,2 50,15 36,15' fill='%232563eb' opacity='0.10'/%3E%3C/svg%3E\")",
      backgroundSize: '60px 60px',
      backgroundColor: '#fef9f0',
    },
  },

  cssVarsLight: {
    '--color-primary': '#ff9f1c',
    '--color-secondary': '#2563eb',
    '--color-accent': '#ffffff',
    '--color-bg': '#fef9f0',
    '--color-surface': '#ffffff',
    '--color-text': '#1a1a2e',
    '--color-text-muted': '#6b5a3e',
    '--color-border': '#f0c080',
    '--color-glow': '#ff9f1c',
  },

  cssVarsDark: {
    '--color-primary': '#ffb347',
    '--color-secondary': '#3b82f6',
    '--color-accent': '#f0f9ff',
    '--color-bg': '#1a1205',
    '--color-surface': '#2a1e08',
    '--color-text': '#fef9f0',
    '--color-text-muted': '#c8ab7e',
    '--color-border': '#7a5a20',
    '--color-glow': '#ffb347',
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Theme registry
// ─────────────────────────────────────────────────────────────────────────────

export const THEMES: Record<Theme, ThemeDefinition> = {
  'default': defaultTheme,
  'future-purple': futurePurpleTheme,
  'alexandros': alexandrosTheme,
};

/**
 * Returns the theme definition for a given theme id.
 * Falls back to the default theme if the id is not recognised.
 */
export function getTheme(id: string): ThemeDefinition {
  return THEMES[id as Theme] ?? defaultTheme;
}

/**
 * Generates an inline style object from a theme's CSS variables,
 * suitable for use as a React `style` prop on the root element.
 */
export function getThemeCssVars(
  themeId: Theme,
  dark = false,
): React.CSSProperties {
  const theme = getTheme(themeId);
  const vars = dark ? theme.cssVarsDark : theme.cssVarsLight;
  return vars as unknown as React.CSSProperties;
}

/**
 * Returns the Tailwind data-attribute selector string for a theme, e.g.
 * `data-theme="future-purple"`.
 */
export function themeDataAttr(themeId: Theme): Record<string, string> {
  return { 'data-theme': themeId };
}
