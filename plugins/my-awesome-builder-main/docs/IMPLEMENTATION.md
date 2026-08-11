# Implementation Guide

Step-by-step instructions for integrating the educational website builder into a Next.js or Vite/React application.

---

## Prerequisites

- Node.js ≥ 18
- pnpm ≥ 8
- Basic familiarity with React and Tailwind CSS

---

## Quick Start

### 1. Install dependencies

```bash
pnpm install
```

### 2. Set up Tailwind CSS

```bash
# Inside your app package
pnpm add -D tailwindcss postcss autoprefixer
```

Create `postcss.config.js`:

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

Create or extend `tailwind.config.ts`:

```ts
import type { Config } from 'tailwindcss';
// Re-export the render-engine config (or import and extend it)
export { default } from '../packages/render-engine/config/tailwind.config';
```

### 3. Import global styles

In your app entry point:

```ts
// app/layout.tsx (Next.js App Router)
import '../packages/render-engine/styles/globals.css';
```

---

## Rendering a Page

### Page schema structure

```ts
import type { PageConfig } from './packages/render-engine/config/theme-definitions';

const page: PageConfig = {
  theme: 'future-purple',
  animationLevel: 'high',
  fontScale: 'medium',
  backgroundStyle: 'gradient-grid',
  maxWidth: '1440px',
};
```

### Page wrapper component

```tsx
import React from 'react';
import type { PageConfig } from '@my-awesome-builder/render-engine/config/theme-definitions';

interface PageWrapperProps {
  config: PageConfig;
  children: React.ReactNode;
}

export function PageWrapper({ config, children }: PageWrapperProps) {
  return (
    <div
      data-theme={config.theme}
      data-animation={config.animationLevel}
      data-font-scale={config.fontScale}
      data-bg={config.backgroundStyle}
      style={{ maxWidth: config.maxWidth, margin: '0 auto' }}
    >
      {children}
    </div>
  );
}
```

### Rendering blocks

```tsx
import { HeroBlock }      from '@my-awesome-builder/render-engine/src/components/blocks/HeroBlock';
import { InfoCardsBlock } from '@my-awesome-builder/render-engine/src/components/blocks/InfoCardsBlock';
import { TimelineBlock }  from '@my-awesome-builder/render-engine/src/components/blocks/TimelineBlock';
import { QuizBlock }      from '@my-awesome-builder/render-engine/src/components/blocks/QuizBlock';

export function CoursePage() {
  return (
    <PageWrapper config={{ theme: 'default', animationLevel: 'medium', fontScale: 'medium', backgroundStyle: 'gradient-grid', maxWidth: '1440px' }}>
      <HeroBlock
        variant="center-title"
        theme="default"
        animationLevel="medium"
        content={{
          title: "Master TypeScript",
          subtitle: "From beginner to expert",
          description: "A structured, hands-on curriculum with real-world projects.",
          ctaLabel: "Start for free",
          ctaHref: "/enrol",
          badge: "New course",
        }}
      />

      <InfoCardsBlock
        variant="flat"
        theme="default"
        animationLevel="medium"
        content={{
          heading: "What you'll learn",
          cards: [
            { title: "Type System", description: "Interfaces, generics, and utility types.", icon: "🔷" },
            { title: "React + TS", description: "Type-safe hooks and component props.", icon: "⚛️" },
            { title: "Testing", description: "Vitest and Testing Library with types.", icon: "✅" },
          ],
        }}
      />

      <TimelineBlock
        variant="vertical"
        theme="default"
        animationLevel="medium"
        content={{
          heading: "Course Roadmap",
          entries: [
            { marker: "1", title: "Foundations", description: "Types, interfaces, and type narrowing." },
            { marker: "2", title: "Advanced Types", description: "Conditional types, mapped types.", featured: true },
            { marker: "3", title: "Real-World Projects", description: "Build a typed REST client." },
          ],
        }}
      />

      <QuizBlock
        variant="choice"
        theme="default"
        animationLevel="medium"
        content={{
          heading: "Knowledge Check",
          questions: [{
            question: "Which utility type makes all properties optional?",
            options: [
              { id: "a", label: "Required<T>" },
              { id: "b", label: "Partial<T>", correct: true },
              { id: "c", label: "Readonly<T>" },
              { id: "d", label: "Record<K,V>" },
            ],
            explanation: "Partial<T> constructs a type with all properties of T set to optional.",
          }],
        }}
      />
    </PageWrapper>
  );
}
```

---

## Rendering from AI-Generated Schema

```ts
import { validate_page_schema } from './packages/ai-engine/schema_rules';

// Validate schema first (Python — call via API or subprocess)
// const errors = validate_page_schema(schema);
// if (errors.length) throw new Error(errors.join('\n'));

// Then map schema.blocks → React components
function renderBlock(block: { type: string; variant: string; content: unknown }, pageConfig: PageConfig) {
  const commonProps = {
    variant: block.variant,
    theme: pageConfig.theme,
    animationLevel: pageConfig.animationLevel,
    content: block.content as Record<string, unknown>,
  };

  switch (block.type) {
    case 'hero':       return <HeroBlock      {...commonProps} />;
    case 'info_cards': return <InfoCardsBlock {...commonProps} />;
    case 'timeline':   return <TimelineBlock  {...commonProps} />;
    case 'quiz':       return <QuizBlock      {...commonProps} />;
    default:           return null;
  }
}
```

---

## Dark Mode Toggle

```tsx
'use client';
import { useState } from 'react';

export function DarkModeToggle() {
  const [dark, setDark] = useState(false);

  const toggle = () => {
    setDark((d) => {
      document.documentElement.classList.toggle('dark', !d);
      return !d;
    });
  };

  return (
    <button onClick={toggle} className="btn-outline btn-sm">
      {dark ? '☀️ Light' : '🌙 Dark'}
    </button>
  );
}
```

---

## Theme Switcher

```tsx
'use client';
import { useState } from 'react';
import type { Theme } from './packages/render-engine/config/theme-definitions';

const THEMES: Theme[] = ['default', 'future-purple', 'alexandros'];

export function ThemeSwitcher() {
  const [theme, setTheme] = useState<Theme>('default');

  const switchTheme = (t: Theme) => {
    setTheme(t);
    document.documentElement.setAttribute('data-theme', t);
  };

  return (
    <div className="flex gap-2">
      {THEMES.map((t) => (
        <button
          key={t}
          onClick={() => switchTheme(t)}
          className={theme === t ? 'btn-primary btn-sm' : 'btn-outline btn-sm'}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
```

---

## Using Python Schema Validation

```python
from packages.ai_engine.schema_rules import validate_page_schema, SchemaValidationError

schema = {
    "page": { "theme": "alexandros", "animation_level": "low" },
    "blocks": [
        { "type": "hero", "variant": "center-title", "content": { "title": "Hello" } },
        { "type": "quiz", "variant": "choice",       "content": { "questions": [] } },
    ]
}

errors = validate_page_schema(schema)
if errors:
    for err in errors:
        print(f"Validation error: {err}")
else:
    print("Schema is valid ✓")
```

---

## TypeScript Interfaces Quick Reference

```ts
import type {
  Theme,
  AnimationLevel,
  FontScale,
  BackgroundStyle,
  BlockProps,
  PageConfig,
  ThemeDefinition,
} from './packages/render-engine/config/theme-definitions';

// Theme: 'default' | 'future-purple' | 'alexandros'
// AnimationLevel: 'none' | 'low' | 'medium' | 'high'
// FontScale: 'small' | 'medium' | 'large'
// BackgroundStyle: 'gradient-grid' | 'solid' | 'pattern'
```

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Classes not applied | Ensure content paths in `tailwind.config.ts` cover your component files |
| Custom properties missing | Confirm `globals.css` (which imports `themes.css`) is imported in your entry point |
| Animations not running | Check `data-animation` attribute is set on an ancestor; verify `prefers-reduced-motion` is not forcing `0ms` |
| Glass effect not visible | Requires a non-opaque background behind the element; works best on dark themes |
| TypeScript errors on content | The `content` prop is typed as `Record<string, unknown>`; cast to your specific interface inside the component |
