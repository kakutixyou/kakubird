# CSS Framework Guide

Complete reference for the Tailwind CSS styling framework used in the educational website builder.

---

## File Structure

```
packages/render-engine/
├── config/
│   ├── tailwind.config.ts     ← Design tokens, animations, plugins
│   └── theme-definitions.ts   ← TypeScript theme objects + interfaces
└── styles/
    ├── globals.css             ← Entry point; imports all other files
    ├── themes.css              ← CSS custom properties per theme
    ├── animations.css          ← Keyframes + animation-level presets
    └── components.css          ← Reusable @apply component classes
```

---

## Setup

### 1. Install dependencies

```bash
pnpm install
```

### 2. Import global styles

In your app entry point (e.g. `app/layout.tsx` or `pages/_app.tsx`):

```ts
import '@my-awesome-builder/render-engine/styles';
```

### 3. Configure PostCSS

```js
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

### 4. Configure Tailwind

Point your app's `tailwind.config.ts` at the render-engine config:

```ts
// tailwind.config.ts (app level)
export { default } from '@my-awesome-builder/render-engine/config/tailwind.config';
```

Or extend it:

```ts
import baseConfig from '@my-awesome-builder/render-engine/config/tailwind.config';
const config = { ...baseConfig, content: ['./src/**/*.{ts,tsx}', ...baseConfig.content] };
export default config;
```

---

## Theme System

### Activating a Theme

Set `data-theme` on the root element:

```html
<html data-theme="future-purple" data-animation="high" data-font-scale="medium" data-bg="gradient-grid">
```

Or in React:

```tsx
<div
  data-theme={pageConfig.theme}
  data-animation={pageConfig.animationLevel}
  data-font-scale={pageConfig.fontScale}
  data-bg={pageConfig.backgroundStyle}
>
  {blocks}
</div>
```

### CSS Custom Properties

All theme values are available as CSS variables:

```css
.my-element {
  background-color: var(--color-primary);
  color: var(--color-text);
  border-color: var(--color-border);
  box-shadow: var(--shadow-card);
}
```

### Tailwind Theme Utilities

Theme-aware utility classes map to CSS variables:

```html
<div class="bg-theme-surface text-theme border border-theme rounded-xl p-6">
  Card content
</div>
```

---

## Component Classes

Defined in `styles/components.css` using `@apply`:

### Buttons

```html
<button class="btn-primary">Primary action</button>
<button class="btn-secondary">Secondary action</button>
<button class="btn-outline">Outline</button>
<button class="btn-ghost">Ghost</button>

<!-- Sizes -->
<button class="btn-primary btn-sm">Small</button>
<button class="btn-primary btn-lg">Large</button>
```

### Cards

```html
<!-- Standard card -->
<div class="card">Content</div>

<!-- Interactive card (hover lift) -->
<div class="card-interactive">Clickable card</div>

<!-- Glass effect (ideal for future-purple theme) -->
<div class="glass-card">Frosted glass card</div>

<!-- Bordered accent card -->
<div class="bordered-card">Accent border card</div>
```

### Typography

```html
<h1 class="heading-xl">Page title</h1>
<h2 class="heading-lg">Section title</h2>
<h3 class="heading-md">Subsection</h3>
<h4 class="heading-sm">Card title</h4>

<p class="body-lg">Lead paragraph</p>
<p class="body-base">Body text</p>
<p class="body-sm">Small text / caption</p>

<!-- Gradient text -->
<span class="gradient-text">Highlighted term</span>
```

### Badges

```html
<span class="badge-primary">New</span>
<span class="badge-secondary">Pro</span>
<span class="badge-success">Complete</span>
<span class="badge-warning">Review</span>
<span class="badge-error">Failed</span>
```

### Layout

```html
<!-- Full-width section -->
<section class="block-wrapper">
  <div class="page-container">
    <!-- max-width 1440px, centred, responsive padding -->
  </div>
</section>

<!-- Grid of cards -->
<div class="grid-cards">
  <!-- auto-fill 280px min-width columns -->
</div>
```

### Forms

```html
<label class="label-base" for="email">Email</label>
<input class="input-base" id="email" type="email" />
```

---

## Animation System

### Applying Animation Level

```html
<div data-animation="medium">
  <h1 class="animate-entrance">Fades in</h1>
  <p class="animate-slide-up">Slides up</p>
  <div class="animate-glow card">Glows continuously</div>
</div>
```

### Stagger Children

```html
<ul data-animation="high" class="stagger-children">
  <li class="animate-slide-up">Item 1</li>
  <li class="animate-slide-up">Item 2 (+100ms)</li>
  <li class="animate-slide-up">Item 3 (+200ms)</li>
</ul>
```

### CSS Variable Access

```css
.custom-animation {
  animation-duration: var(--anim-duration);
  animation-timing-function: var(--anim-easing);
  animation-delay: var(--anim-stagger);
}
```

---

## Glass Effect

The `.glass` and `.glass-dark` utilities are registered via the Tailwind plugin:

```html
<!-- Light glass -->
<div class="glass rounded-xl p-6">…</div>

<!-- Dark glass -->
<div class="glass-dark rounded-xl p-6">…</div>

<!-- Strong glass -->
<div class="glass-strong rounded-xl p-6">…</div>
```

---

## Geometric Patterns

```html
<!-- Grid pattern (default/future-purple) -->
<div class="bg-grid-pattern">…</div>

<!-- Dot pattern -->
<div class="bg-dot-pattern">…</div>

<!-- Alexandros squares + diamonds -->
<div class="bg-alexandros-pattern">…</div>
```

---

## Dark Mode

Dark mode uses the `.dark` class on an ancestor element in combination with `data-theme`:

```html
<!-- Dark default theme -->
<html data-theme="default" class="dark">

<!-- Toggle in JavaScript -->
document.documentElement.classList.toggle('dark');
```

---

## Custom Properties Reference

| Variable | Purpose |
|----------|---------|
| `--color-primary` | Main brand color |
| `--color-secondary` | Secondary brand color |
| `--color-accent` | Accent / highlight color |
| `--color-bg` | Page background |
| `--color-surface` | Card/panel background |
| `--color-text` | Primary text color |
| `--color-text-muted` | Muted / secondary text |
| `--color-border` | Default border color |
| `--color-glow` | Glow effect color |
| `--shadow-card` | Card box shadow |
| `--shadow-hover` | Hovered card shadow |
| `--shadow-glow` | Glow box shadow |
| `--anim-duration` | Primary animation duration |
| `--anim-micro-duration` | Micro-interaction duration |
| `--anim-stagger` | Stagger delay per child |
| `--anim-easing` | Primary easing function |
| `--space-block-y` | Vertical section padding |
| `--space-block-x` | Horizontal section padding |
| `--space-card-p` | Card padding |
| `--max-width-page` | Page max-width |
