# Themes Reference

Three themes are available in the educational website builder. Each theme is activated by setting `data-theme` on the root element and is fully described by CSS custom properties in `styles/themes.css`.

---

## Applying a Theme

```html
<!-- Default theme (light) -->
<html data-theme="default">

<!-- Default theme (dark) -->
<html data-theme="default" class="dark">

<!-- Future Purple (always dark) -->
<html data-theme="future-purple">

<!-- Alexandros (light) -->
<html data-theme="alexandros">
```

In React, pass the `theme` and `animationLevel` props to a block component. The render engine wraps the page with the correct `data-theme` and `data-animation` attributes automatically.

---

## Theme: `default`

**Character:** Professional, clean, blue/gray palette. Supports both light and dark modes.

| Token | Light value | Dark value |
|-------|------------|------------|
| `--color-primary` | `#2563eb` (blue-600) | `#3b82f6` (blue-500) |
| `--color-secondary` | `#7c3aed` (violet-700) | `#8b5cf6` (violet-500) |
| `--color-accent` | `#0ea5e9` (sky-500) | `#38bdf8` (sky-400) |
| `--color-bg` | `#f8fafc` (slate-50) | `#0f172a` (slate-900) |
| `--color-surface` | `#ffffff` | `#1e293b` (slate-800) |
| `--color-text` | `#1e293b` (slate-800) | `#f1f5f9` (slate-100) |
| `--color-text-muted` | `#64748b` (slate-500) | `#94a3b8` (slate-400) |
| `--color-border` | `#e2e8f0` (slate-200) | `#334155` (slate-700) |
| `--color-glow` | `rgba(37,99,235,0.4)` | `rgba(59,130,246,0.5)` |

**Best for:** General-purpose educational content, professional courses, documentation pages.

---

## Theme: `future-purple`

**Character:** Dark, immersive, sci-fi aesthetic. Purple primary with cyan glow accents.

> ⚠️ This theme is always dark — there is no light variant.

| Token | Value |
|-------|-------|
| `--color-primary` | `#7c3aed` (violet-700) |
| `--color-secondary` | `#a855f7` (purple-500) |
| `--color-accent` | `#06b6d4` (cyan-500) |
| `--color-bg` | `#0f0a1e` |
| `--color-surface` | `#1a1035` |
| `--color-text` | `#f0e6ff` |
| `--color-text-muted` | `#a78bfa` (violet-400) |
| `--color-border` | `#3b1f6e` |
| `--color-glow` | `rgba(192,132,252,0.5)` (purple-400) |
| `--color-glow-cyan` | `rgba(6,182,212,0.5)` |

**Gradient presets:**
- `--gradient-primary`: `linear-gradient(135deg, #7c3aed, #a855f7)`
- `--gradient-accent`: `linear-gradient(135deg, #06b6d4, #7c3aed)`
- `--gradient-hero`: `linear-gradient(135deg, #0f0a1e 0%, #1a0a2e 50%, #0a0a1e 100%)`

**Best for:** Tech courses, coding bootcamps, AI/ML content, night-mode first experiences.

---

## Theme: `alexandros`

**Character:** Vibrant, geometric, energetic. Orange squares and blue diamonds on warm pastel backgrounds.

| Token | Light value | Dark value |
|-------|------------|------------|
| `--color-primary` | `#ff9f1c` (orange) | `#ffb347` |
| `--color-secondary` | `#2563eb` (blue-600) | `#3b82f6` (blue-500) |
| `--color-accent` | `#ffffff` | `#f0f9ff` |
| `--color-bg` | `#fef9f0` | `#1a1205` |
| `--color-surface` | `#ffffff` | `#2a1e08` |
| `--color-text` | `#1a1a2e` | `#fef9f0` |
| `--color-text-muted` | `#6b5a3e` | `#c8ab7e` |
| `--color-border` | `#f0c080` | `#7a5a20` |
| `--color-glow` | `rgba(255,159,28,0.4)` | `rgba(255,179,71,0.5)` |

**Geometric pattern:**  
Available via `--pattern-geometric` CSS variable or `.bg-alexandros-pattern` utility. Contains orange squares, rotated squares (diamonds), and blue triangles.

**Best for:** Creative courses, art & design education, kids/youth learning, language learning.

---

## Background Styles

Each theme can use one of three background styles, set via `data-bg`:

| Value | Description |
|-------|-------------|
| `gradient-grid` | Subtle grid lines over a gradient background |
| `solid` | Flat `--color-bg` fill |
| `pattern` | Repeating geometric pattern from `--pattern-geometric` |

---

## Font Scales

| `data-font-scale` | Base font size |
|-------------------|---------------|
| `small` | `14px` |
| `medium` | `16px` (default) |
| `large` | `18px` |
