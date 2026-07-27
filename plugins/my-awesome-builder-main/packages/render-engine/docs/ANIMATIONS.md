# Animations Reference

The animation system is controlled by the `data-animation` attribute applied to a container element (usually the page root). Four levels are available, each activating progressively more complex motion.

---

## Levels

| Level | Duration | Micro-duration | Continuous effects | Stagger |
|-------|----------|----------------|--------------------|---------|
| `none` | 0 ms | 0 ms | ✗ | 0 ms |
| `low` | 300 ms | 150 ms | ✗ | 50 ms |
| `medium` | 500 ms | 200 ms | ✓ | 75 ms |
| `high` | 700 ms | 250 ms | ✓ | 100 ms |

---

## Usage

### HTML attribute
```html
<div data-animation="high">
  <div class="animate-entrance">Fades in</div>
  <div class="animate-slide-up">Slides up</div>
</div>
```

### React block prop
```tsx
<HeroBlock
  variant="center-title"
  theme="future-purple"
  animationLevel="high"
  content={{ title: "Learn Anything" }}
/>
```

---

## Entrance Classes

Apply these to any element inside a `[data-animation]` container:

| Class | `none` | `low` | `medium` | `high` |
|-------|--------|-------|----------|--------|
| `.animate-entrance` | — | fadeIn 300ms | fadeIn 500ms | fadeIn 700ms spring |
| `.animate-slide-up` | — | slideUp 300ms | slideUp 500ms | slideUp 700ms spring |
| `.animate-slide-down` | — | — | slideDown 500ms | slideDown 700ms spring |
| `.animate-slide-left` | — | — | — | slideLeft 700ms spring |
| `.animate-slide-right` | — | — | — | slideRight 700ms spring |
| `.animate-scale-in` | — | scaleIn 300ms | scaleIn 500ms | scaleIn 700ms spring |
| `.animate-bounce-in` | — | — | — | bounceIn 800ms bounce |
| `.animate-rotate-in` | — | — | — | rotateIn 700ms spring |

---

## Continuous Effect Classes

These run indefinitely and are only enabled at `medium` and `high` levels:

| Class | Effect | Period |
|-------|--------|--------|
| `.animate-glow` | Pulsing box-shadow glow | 2 s |
| `.animate-float` | Gentle vertical float | 3 s |
| `.animate-pulse-glow` | Opacity + glow pulse | 2 s |
| `.animate-shimmer` | Moving shimmer highlight (`high` only) | 2.5 s |

---

## Hover Lift

```html
<div class="animate-hover-lift card">Lifts on hover</div>
```

| Level | Behaviour |
|-------|-----------|
| `none` | No effect |
| `low` | `translateY(-2px)` |
| `medium` | `translateY(-4px)` |
| `high` | `translateY(-6px) scale(1.01)` |

---

## Stagger Children

Apply `.stagger-children` to a parent to stagger entrance animations across up to 8 children:

```html
<ul class="stagger-children">
  <li class="animate-slide-up">Item 1 — no delay</li>
  <li class="animate-slide-up">Item 2 — 1× stagger</li>
  <li class="animate-slide-up">Item 3 — 2× stagger</li>
</ul>
```

Only active at `medium` and `high` levels. Delay = `n × --anim-stagger`.

---

## Keyframe Definitions

All keyframes are defined in `styles/animations.css`:

| Keyframe | Transform |
|----------|-----------|
| `fadeIn` | `opacity: 0 → 1` |
| `slideUp` | `translateY(24px), opacity:0 → 0` |
| `slideDown` | `translateY(-24px), opacity:0 → 0` |
| `slideLeft` | `translateX(24px), opacity:0 → 0` |
| `slideRight` | `translateX(-24px), opacity:0 → 0` |
| `scaleIn` | `scale(0.9), opacity:0 → 1` |
| `bounceIn` | Overshoot bounce: 0.3 → 1.05 → 0.9 → 1 |
| `rotateIn` | `rotate(-15deg) scale(0.9), opacity:0 → 1` |
| `glow` | box-shadow 8px → 24px |
| `float` | `translateY(0) → -10px → 0` |
| `pulseGlow` | opacity 1 → 0.6 + glow |
| `shimmer` | background-position sweep |

---

## Accessibility

`prefers-reduced-motion: reduce` is respected globally:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:        0.01ms !important;
    animation-iteration-count: 1     !important;
    transition-duration:       0.01ms !important;
  }
}
```

Always test with reduced motion enabled in your OS accessibility settings.

---

## CSS Custom Properties

Each level sets the following variables, available for programmatic use:

| Property | Purpose |
|----------|---------|
| `--anim-duration` | Primary entrance/exit duration |
| `--anim-micro-duration` | Hover / interactive micro-animation duration |
| `--anim-stagger` | Per-child delay for staggered lists |
| `--anim-easing` | Primary easing function |
