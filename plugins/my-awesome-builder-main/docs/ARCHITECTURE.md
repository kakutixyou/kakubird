# Architecture

High-level architecture of the **my-awesome-builder** educational website builder.

---

## Overview

```
my-awesome-builder/
├── packages/
│   ├── render-engine/   ← React components + Tailwind theme system
│   ├── ai-engine/       ← Schema validation rules for AI-generated pages
│   └── block-library/   ← Block/variant catalogue (JSON + docs)
├── config/              ← Root-level Tailwind config
└── docs/                ← Architecture, CSS framework, implementation guides
```

---

## Core Concepts

### 1. Blocks

A **block** is the fundamental building unit. Each block maps to a React component that accepts a `variant`, `theme`, `animationLevel`, and `content` prop.

There are **30 block types**, each with **3 variants** = **90 distinct visual layouts**.

### 2. Themes

Three themes control the visual language of a page:

| Theme | Character |
|-------|-----------|
| `default` | Professional blue/gray, light + dark mode |
| `future-purple` | Immersive dark sci-fi with purple/cyan glow |
| `alexandros` | Vibrant geometric orange + blue on warm pastels |

Themes are implemented as CSS custom property sets in `styles/themes.css` and activated via `data-theme` HTML attributes.

### 3. Animation Levels

Four animation levels (`none` / `low` / `medium` / `high`) gate progressively richer motion, implemented via CSS classes and `data-animation` attributes.

### 4. Page Schema

The AI engine produces a **page schema** — a JSON document describing the page configuration and an ordered array of blocks:

```json
{
  "page": {
    "theme": "future-purple",
    "animation_level": "high",
    "font_scale": "medium",
    "background_style": "gradient-grid",
    "max_width": "1440px"
  },
  "blocks": [
    { "type": "hero", "variant": "center-title", "content": { ... } },
    { "type": "info_cards", "variant": "glass", "content": { ... } }
  ]
}
```

The schema is validated by `packages/ai-engine/schema_rules.py` before being passed to the render engine.

---

## Package Responsibilities

### `@my-awesome-builder/render-engine`

- **Tailwind config** (`config/tailwind.config.ts`) — design tokens, animations, plugins
- **Theme definitions** (`config/theme-definitions.ts`) — TypeScript types + theme objects
- **CSS framework** (`styles/`) — themes.css, animations.css, components.css, globals.css
- **Block components** (`src/components/blocks/`) — React components for each block type

### `packages/ai-engine`

- **Schema rules** (`schema_rules.py`) — BLOCK_LIBRARY dict, validation functions, AI prompt helpers

### `packages/block-library`

- **Variants catalogue** (`variants.json`) — machine-readable block/variant definitions with Tailwind class hints
- **README** — human-readable block reference

---

## Data Flow

```
User intent
    │
    ▼
AI Engine  →  schema_rules.validate_page_schema()
    │
    ▼ validated JSON schema
Render Engine
    │
    ├─ Reads page.theme        → sets data-theme on root
    ├─ Reads page.animation    → sets data-animation on root
    ├─ Reads page.font_scale   → sets data-font-scale on root
    ├─ Reads page.background   → sets data-bg on root
    │
    └─ For each block:
         BlockComponent({ variant, theme, animationLevel, content })
              │
              ▼
         React + Tailwind CSS → rendered HTML
```

---

## Theme Token Flow

```
theme-definitions.ts  →  CSS custom properties (themes.css)
                                │
                                ▼
                     Tailwind utilities (tailwind.config.ts)
                     'theme-primary' = var(--color-primary)
                                │
                                ▼
                     Block components use:
                     className="bg-theme-primary text-theme"
                     style={{ color: 'var(--color-primary)' }}
```

---

## Adding a New Block

1. **Define in schema_rules.py** — add to `BLOCK_LIBRARY` dict.
2. **Add to variants.json** — include description and Tailwind class hints.
3. **Create React component** — in `packages/render-engine/src/components/blocks/`.
4. **Document in BLOCK_STYLES.md** — record Tailwind classes per variant.
5. **Export from index** — add to the package barrel export.
