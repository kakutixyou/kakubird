# Design System Documentation

## Overview
Complete design system supporting 30 blocks × 3 variants with 8 surface types.

## Surface Types
- **flat**: Minimalist, educational
- **glass**: Modern, transparent
- **neumorphism**: Soft, friendly
- **bordered**: Technical, defined
- **elevated**: Professional, dimensional
- **paper**: Historical, traditional
- **glow**: Futuristic, energetic
- **frosted-dark**: Premium, dark

## Theme Integration
Each surface works with all 3 themes:
- Default (professional)
- Future Purple (futuristic)
- Alexandros (playful)

## Adding Surface to a Block Schema
Each block in the page schema accepts an optional `surface` field:

```json
{
  "type": "hero",
  "variant": "center-title",
  "surface": "glass",
  "content": { "title": "Hello World" }
}
```

If omitted, the render engine applies the `BLOCK_SURFACE_DEFAULTS` from `schema_rules.py`.

## Using Design Rules
See [GENERATION_RULES.md](./GENERATION_RULES.md) for automatic design rule generation.
