# Color Palette Reference

Complete color tables for all three themes. Colors are expressed as both hex values and their nearest Tailwind CSS named equivalents.

---

## Default Theme

### Primary Palette

| Token | Hex | Tailwind | Usage |
|-------|-----|---------|-------|
| Primary | `#2563eb` | `blue-600` | Buttons, links, active states |
| Primary Light | `#3b82f6` | `blue-500` | Hover states, dark-mode primary |
| Primary Dark | `#1d4ed8` | `blue-700` | Pressed states |
| Secondary | `#7c3aed` | `violet-700` | Secondary actions, tags |
| Secondary Light | `#8b5cf6` | `violet-500` | Dark-mode secondary |
| Accent | `#0ea5e9` | `sky-500` | Highlights, gradients |
| Accent Light | `#38bdf8` | `sky-400` | Dark-mode accent |

### Neutral Palette (Light Mode)

| Token | Hex | Tailwind | Usage |
|-------|-----|---------|-------|
| Background | `#f8fafc` | `slate-50` | Page background |
| Surface | `#ffffff` | `white` | Card / panel backgrounds |
| Surface Alt | `#f1f5f9` | `slate-100` | Alternate rows, subtle panels |
| Text | `#1e293b` | `slate-800` | Body text, headings |
| Text Muted | `#64748b` | `slate-500` | Captions, secondary text |
| Border | `#e2e8f0` | `slate-200` | Dividers, input borders |
| Border Strong | `#cbd5e1` | `slate-300` | Stronger dividers |

### Neutral Palette (Dark Mode)

| Token | Hex | Tailwind | Usage |
|-------|-----|---------|-------|
| Background | `#0f172a` | `slate-900` | Page background |
| Surface | `#1e293b` | `slate-800` | Card / panel backgrounds |
| Text | `#f1f5f9` | `slate-100` | Body text, headings |
| Text Muted | `#94a3b8` | `slate-400` | Captions, secondary text |
| Border | `#334155` | `slate-700` | Dividers |
| Border Strong | `#475569` | `slate-600` | Stronger dividers |

### Semantic Colors

| Name | Hex | Tailwind |
|------|-----|---------|
| Success | `#16a34a` | `green-600` |
| Warning | `#d97706` | `amber-600` |
| Error | `#dc2626` | `red-600` |
| Info | `#0284c7` | `sky-600` |

---

## Future-Purple Theme

### Brand Palette

| Token | Hex | Description |
|-------|-----|------------|
| Primary | `#7c3aed` | Violet-700 — main purple |
| Primary Light | `#8b5cf6` | Violet-500 |
| Primary Dark | `#6d28d9` | Violet-800 |
| Secondary | `#a855f7` | Purple-500 |
| Secondary Light | `#c084fc` | Purple-400 |
| Accent | `#06b6d4` | Cyan-500 — electric accent |
| Accent Light | `#22d3ee` | Cyan-400 |
| Glow | `#c084fc` | Purple-400 — glow shadow colour |
| Glow Cyan | `#06b6d4` | Cyan-500 — alternate glow |

### Surface Palette

| Token | Hex | Description |
|-------|-----|------------|
| Background | `#0f0a1e` | Deep space background |
| Surface | `#1a1035` | Card background |
| Surface Alt | `#13092a` | Slightly darker panels |
| Text | `#f0e6ff` | Warm white with purple tint |
| Text Muted | `#a78bfa` | Violet-400 |
| Border | `#3b1f6e` | Dark purple border |
| Border Strong | `#5b2d9e` | Brighter purple border |

### Dark-Mode Overrides

| Token | Hex |
|-------|-----|
| Primary | `#8b5cf6` |
| Background | `#070413` |
| Surface | `#120b28` |
| Text | `#f5f0ff` |
| Text Muted | `#c4b5fd` |
| Glow | `rgba(216,180,254,0.6)` |

---

## Alexandros Theme

### Brand Palette

| Token | Hex | Description |
|-------|-----|------------|
| Primary (Square) | `#ff9f1c` | Orange — geometric squares motif |
| Primary Light | `#ffb347` | Lighter orange |
| Primary Dark | `#e8890a` | Deeper orange |
| Secondary (Diamond) | `#2563eb` | Blue-600 — diamond motif |
| Secondary Light | `#3b82f6` | Blue-500 |
| Accent | `#ffffff` | White — high contrast on orange |
| Highlight | `#ffd166` | Golden yellow |

### Surface Palette (Light)

| Token | Hex | Description |
|-------|-----|------------|
| Background | `#fef9f0` | Warm cream |
| Surface | `#ffffff` | White cards |
| Surface Alt | `#fff3e0` | Orange-tinted panels |
| Text | `#1a1a2e` | Near-black with blue tint |
| Text Muted | `#6b5a3e` | Warm brown |
| Border | `#f0c080` | Golden border |
| Border Strong | `#d4a017` | Deep gold |

### Surface Palette (Dark)

| Token | Hex | Description |
|-------|-----|------------|
| Background | `#1a1205` | Dark amber-brown |
| Surface | `#2a1e08` | Lighter dark surface |
| Text | `#fef9f0` | Cream text |
| Text Muted | `#c8ab7e` | Muted warm tan |
| Border | `#7a5a20` | Dark amber |

---

## Gradient Presets

These CSS variables are set per-theme and can be referenced directly:

| Variable | Theme | Value |
|----------|-------|-------|
| `--gradient-primary` | future-purple | `linear-gradient(135deg, #7c3aed, #a855f7)` |
| `--gradient-accent` | future-purple | `linear-gradient(135deg, #06b6d4, #7c3aed)` |
| `--gradient-hero` | future-purple | `linear-gradient(135deg, #0f0a1e 0%, #1a0a2e 50%, #0a0a1e 100%)` |
| `--gradient-primary` | alexandros | `linear-gradient(135deg, #ff9f1c, #ffd166)` |
| `--gradient-secondary` | alexandros | `linear-gradient(135deg, #2563eb, #38bdf8)` |
| `--gradient-hero` | alexandros | `linear-gradient(135deg, #fef9f0, #fff3e0)` |

---

## Using Colors in Tailwind

Theme colors are exposed as Tailwind utilities via CSS variable bridging in `tailwind.config.ts`:

```html
<!-- Uses current theme's primary color -->
<div class="bg-theme-primary text-theme-text border-theme">…</div>

<!-- Static theme colors (not affected by theme switching) -->
<div class="bg-default-primary text-future-purple-text">…</div>
```

### Key Tailwind color utilities

| Class | Value |
|-------|-------|
| `bg-theme-primary` | `var(--color-primary)` |
| `bg-theme-secondary` | `var(--color-secondary)` |
| `bg-theme-accent` | `var(--color-accent)` |
| `bg-theme-bg` | `var(--color-bg)` |
| `bg-theme-surface` | `var(--color-surface)` |
| `text-theme` | `var(--color-text)` |
| `text-theme-muted` | `var(--color-text-muted)` |
| `text-theme-primary` | `var(--color-primary)` |
| `border-theme` | `var(--color-border)` |
