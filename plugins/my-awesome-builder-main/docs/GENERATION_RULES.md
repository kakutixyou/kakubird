# Design Rules Generation

## generate_design_rule(mood, domain)

Automatically generate optimal design rules from mood + domain.

### Example
```python
import sys
sys.path.insert(0, "packages/style-system")

from rules.generate_design_rule import generate_design_rule

rules = generate_design_rule("futuristic", "engineering")
# Returns: {
#   "theme": "future-purple",
#   "recommended_surfaces": ["glass", "glow", "bordered", "frosted-dark"],
#   "recommended_animations": ["soft-fade", "hover-lift"],
#   "section_balance": "visual-tech",
#   ...
# }
```

## Base Rules + Overrides Pattern

1. `BASE_MOOD_RULES` — General mood preferences
2. `BASE_DOMAIN_RULES` — Domain-specific settings
3. `COMBINATION_OVERRIDES` — Specific mood+domain rules (highest priority)
4. `DEFAULT_DESIGN` — Fallback when mood and domain are both unknown

## Supported Moods
`futuristic` | `elegant` | `academic` | `historical` | `playful` | `corporate` | `minimal`

## Supported Domains
`engineering` | `history` | `medical` | `business` | `language` | `science` | `general`

## Density Control
Pass `density` to `apply_design_rules()` in `design_engine.py`:
- `light` — airy spacing, max 5 blocks
- `balanced` — balanced spacing, max 8 blocks
- `heavy` — compact spacing, max 12 blocks

## Extending with New Combinations
Add entries to `COMBINATION_OVERRIDES` in `packages/style-system/rules/design_rules.py`:

```python
("minimal", "science"): {
    "theme": "default",
    "recommended_surfaces": ["flat", "bordered"],
    "recommended_animations": ["none"],
    "section_balance": "data-heavy"
}
```
