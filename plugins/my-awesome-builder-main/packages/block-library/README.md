# Block Library

A catalogue of all **30 block types** available in the educational website builder, each offered in **3 variants**. Blocks are the fundamental building units composed by the AI engine into complete learning pages.

---

## Quick Reference

| Block | Variants |
|-------|----------|
| `hero` | center-title · left-image · full-background |
| `split_hero` | image-right · image-left · alternate |
| `info_cards` | flat · glass · bordered |
| `timeline` | vertical · horizontal · minimal |
| `quiz` | choice · flashcard · instant-check |
| `section_header` | simple · decorated · full-width |
| `anchor_nav` | horizontal · vertical · floating |
| `sidebar_index` | simple · numbered · collapsible |
| `two_column_layout` | equal · sidebar-right · sidebar-left |
| `footer` | minimal · rich · centered |
| `profile_cards` | portrait · horizontal · featured |
| `step_flow` | numbered · arrow · circular |
| `table_section` | simple · striped · comparison |
| `definition_box` | simple · highlighted · card |
| `quote_panel` | simple · large · attributed |
| `code_panel` | simple · terminal · highlighted |
| `diagram_cards` | grid · flow · feature |
| `accordion_faq` | simple · bordered · colored |
| `checklist_summary` | simple · detailed · progress |
| `image_gallery` | grid · masonry · carousel |
| `feature_banner` | simple · gradient · pattern |
| `progress_meter` | bar · circle · steps |
| `statistic_circle` | simple · animated · comparison |
| `comparison_split` | side-by-side · overlay · table |
| `spotlight_panel` | centered · split · hero |
| `mini_test` | text · fill-blank · matching |
| `download_cta` | button · card · banner |
| `next_lesson` | simple · preview · progress |
| `contact_box` | simple · card · sidebar |
| `final_message` | simple · celebration · summary |

---

## Schema Usage

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
    {
      "type": "hero",
      "variant": "center-title",
      "content": {
        "title": "Master React in 30 Days",
        "ctaLabel": "Start Learning",
        "ctaHref": "/start"
      }
    },
    {
      "type": "info_cards",
      "variant": "glass",
      "content": {
        "heading": "What You'll Learn",
        "cards": [
          { "title": "Hooks", "description": "useState, useEffect, and more.", "icon": "⚛️" }
        ]
      }
    }
  ]
}
```

---

## Adding a New Block

1. Add the block type and its 3 variants to `packages/ai-engine/schema_rules.py → BLOCK_LIBRARY`.
2. Add the entry to `packages/block-library/variants.json`.
3. Create the React component in `packages/render-engine/src/components/blocks/`.
4. Document the Tailwind classes in `packages/render-engine/docs/BLOCK_STYLES.md`.

---

## File Structure

```
packages/block-library/
├── variants.json   ← Machine-readable block + variant definitions
└── README.md       ← This file
```
