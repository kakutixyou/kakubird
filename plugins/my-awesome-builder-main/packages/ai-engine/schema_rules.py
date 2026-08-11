"""
schema_rules.py
===============
Centralised block library and schema validation rules for the AI engine.

The AI uses BLOCK_LIBRARY to validate that generated page schemas only
reference known block types with valid variants.

Page-level configuration is validated against PAGE_SCHEMA.
"""

from __future__ import annotations

from typing import Literal, TypedDict, get_args


# ─────────────────────────────────────────────────────────────────────────────
# Block library — 30 block types × 3 variants each
# ─────────────────────────────────────────────────────────────────────────────

BLOCK_LIBRARY: dict[str, list[str]] = {
    "hero":               ["center-title", "left-image", "full-background"],
    "split_hero":         ["image-right", "image-left", "alternate"],
    "info_cards":         ["flat", "glass", "bordered"],
    "timeline":           ["vertical", "horizontal", "minimal"],
    "quiz":               ["choice", "flashcard", "instant-check"],
    "section_header":     ["simple", "decorated", "full-width"],
    "anchor_nav":         ["horizontal", "vertical", "floating"],
    "sidebar_index":      ["simple", "numbered", "collapsible"],
    "two_column_layout":  ["equal", "sidebar-right", "sidebar-left"],
    "footer":             ["minimal", "rich", "centered"],
    "profile_cards":      ["portrait", "horizontal", "featured"],
    "step_flow":          ["numbered", "arrow", "circular"],
    "table_section":      ["simple", "striped", "comparison"],
    "definition_box":     ["simple", "highlighted", "card"],
    "quote_panel":        ["simple", "large", "attributed"],
    "code_panel":         ["simple", "terminal", "highlighted"],
    "diagram_cards":      ["grid", "flow", "feature"],
    "accordion_faq":      ["simple", "bordered", "colored"],
    "checklist_summary":  ["simple", "detailed", "progress"],
    "image_gallery":      ["grid", "masonry", "carousel"],
    "feature_banner":     ["simple", "gradient", "pattern"],
    "progress_meter":     ["bar", "circle", "steps"],
    "statistic_circle":   ["simple", "animated", "comparison"],
    "comparison_split":   ["side-by-side", "overlay", "table"],
    "spotlight_panel":    ["centered", "split", "hero"],
    "mini_test":          ["text", "fill-blank", "matching"],
    "download_cta":       ["button", "card", "banner"],
    "next_lesson":        ["simple", "preview", "progress"],
    "contact_box":        ["simple", "card", "sidebar"],
    "final_message":      ["simple", "celebration", "summary"],
}

# Convenient sets for O(1) look-ups
BLOCK_TYPES: frozenset[str] = frozenset(BLOCK_LIBRARY.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Surface system — 8 surface types for visual texture
# ─────────────────────────────────────────────────────────────────────────────

SURFACE_TYPES: list[str] = [
    "flat",
    "glass",
    "neumorphism",
    "bordered",
    "elevated",
    "paper",
    "glow",
    "frosted-dark",
]

# Default surface recommendations per block type
BLOCK_SURFACE_DEFAULTS: dict[str, str] = {
    "hero":              "glass",
    "split_hero":        "elevated",
    "section_header":    "flat",
    "anchor_nav":        "flat",
    "sidebar_index":     "flat",
    "two_column_layout": "flat",
    "footer":            "flat",
    "info_cards":        "elevated",
    "profile_cards":     "elevated",
    "timeline":          "paper",
    "step_flow":         "elevated",
    "table_section":     "bordered",
    "definition_box":    "paper",
    "quote_panel":       "paper",
    "code_panel":        "bordered",
    "diagram_cards":     "flat",
    "accordion_faq":     "flat",
    "checklist_summary": "bordered",
    "image_gallery":     "flat",
    "feature_banner":    "glow",
    "progress_meter":    "flat",
    "statistic_circle":  "neumorphism",
    "comparison_split":  "elevated",
    "spotlight_panel":   "glass",
    "quiz":              "neumorphism",
    "mini_test":         "bordered",
    "download_cta":      "glow",
    "next_lesson":       "elevated",
    "contact_box":       "glass",
    "final_message":     "flat",
}


# ─────────────────────────────────────────────────────────────────────────────
# Page-level configuration schema
# ─────────────────────────────────────────────────────────────────────────────

ThemeType          = Literal["default", "future-purple", "alexandros"]
AnimationLevelType = Literal["none", "low", "medium", "high"]
FontScaleType      = Literal["small", "medium", "large"]
BackgroundStyleType = Literal["gradient-grid", "solid", "pattern"]

VALID_THEMES:            tuple[str, ...] = get_args(ThemeType)
VALID_ANIMATION_LEVELS:  tuple[str, ...] = get_args(AnimationLevelType)
VALID_FONT_SCALES:       tuple[str, ...] = get_args(FontScaleType)
VALID_BACKGROUND_STYLES: tuple[str, ...] = get_args(BackgroundStyleType)


class PageConfig(TypedDict):
    theme:            ThemeType
    animation_level:  AnimationLevelType
    font_scale:       FontScaleType
    background_style: BackgroundStyleType
    max_width:        str


PAGE_SCHEMA_DEFAULTS: PageConfig = {
    "theme":            "default",
    "animation_level":  "medium",
    "font_scale":       "medium",
    "background_style": "gradient-grid",
    "max_width":        "1440px",
}


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

class SchemaValidationError(ValueError):
    """Raised when a generated schema violates the block or page rules."""


def validate_block(block_type: str, variant: str, surface: str | None = None) -> None:
    """
    Validate that *block_type* exists, *variant* is one of its allowed values,
    and (optionally) *surface* is a recognised surface type.

    Raises
    ------
    SchemaValidationError
        If the block type is unknown, the variant is not supported, or the
        surface is not a valid SURFACE_TYPES entry.
    """
    if block_type not in BLOCK_LIBRARY:
        known = ", ".join(sorted(BLOCK_LIBRARY))
        raise SchemaValidationError(
            f"Unknown block type '{block_type}'. "
            f"Known types: {known}"
        )

    allowed_variants = BLOCK_LIBRARY[block_type]
    if variant not in allowed_variants:
        raise SchemaValidationError(
            f"Invalid variant '{variant}' for block '{block_type}'. "
            f"Allowed variants: {', '.join(allowed_variants)}"
        )

    if surface is not None and surface not in SURFACE_TYPES:
        raise SchemaValidationError(
            f"Invalid surface '{surface}' for block '{block_type}'. "
            f"Allowed surfaces: {', '.join(SURFACE_TYPES)}"
        )


def validate_page_config(config: dict) -> PageConfig:
    """
    Validate and normalise a page-level configuration dict.

    Missing keys fall back to ``PAGE_SCHEMA_DEFAULTS``.

    Parameters
    ----------
    config:
        Raw dict from an AI-generated schema.

    Returns
    -------
    PageConfig
        Validated and normalised page configuration.

    Raises
    ------
    SchemaValidationError
        If any field contains an unrecognised value.
    """
    merged: dict = {**PAGE_SCHEMA_DEFAULTS, **config}

    if merged["theme"] not in VALID_THEMES:
        raise SchemaValidationError(
            f"Invalid theme '{merged['theme']}'. "
            f"Allowed: {', '.join(VALID_THEMES)}"
        )

    if merged["animation_level"] not in VALID_ANIMATION_LEVELS:
        raise SchemaValidationError(
            f"Invalid animation_level '{merged['animation_level']}'. "
            f"Allowed: {', '.join(VALID_ANIMATION_LEVELS)}"
        )

    if merged["font_scale"] not in VALID_FONT_SCALES:
        raise SchemaValidationError(
            f"Invalid font_scale '{merged['font_scale']}'. "
            f"Allowed: {', '.join(VALID_FONT_SCALES)}"
        )

    if merged["background_style"] not in VALID_BACKGROUND_STYLES:
        raise SchemaValidationError(
            f"Invalid background_style '{merged['background_style']}'. "
            f"Allowed: {', '.join(VALID_BACKGROUND_STYLES)}"
        )

    return merged  # type: ignore[return-value]


def validate_page_schema(schema: dict) -> list[str]:
    """
    Validate an entire page schema dict (``page`` key + ``blocks`` list).

    Parameters
    ----------
    schema:
        Full page schema, e.g.::

            {
                "page": {"theme": "future-purple", ...},
                "blocks": [
                    {"type": "hero", "variant": "center-title", "content": {...}},
                    ...
                ]
            }

    Returns
    -------
    list[str]
        A list of validation error messages.  Empty list means the schema is valid.
    """
    errors: list[str] = []

    # Validate page config
    try:
        validate_page_config(schema.get("page", {}))
    except SchemaValidationError as exc:
        errors.append(f"[page] {exc}")

    # Validate each block
    blocks = schema.get("blocks", [])
    if not isinstance(blocks, list):
        errors.append("[blocks] 'blocks' must be a list")
        return errors

    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            errors.append(f"[blocks[{i}]] Block must be a dict, got {type(block).__name__}")
            continue

        block_type = block.get("type", "")
        variant    = block.get("variant", "")
        surface    = block.get("surface")

        try:
            validate_block(block_type, variant, surface)
        except SchemaValidationError as exc:
            errors.append(f"[blocks[{i}]] {exc}")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# AI prompt helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_block_library_prompt_fragment() -> str:
    """
    Returns a compact text representation of the block library suitable for
    inclusion in an AI system prompt.
    """
    lines = ["Available blocks and their variants:"]
    for block_type, variants in BLOCK_LIBRARY.items():
        default_surface = BLOCK_SURFACE_DEFAULTS.get(block_type, "flat")
        lines.append(f"  - {block_type}: {', '.join(variants)} (default surface: {default_surface})")
    return "\n".join(lines)


def get_surface_types_prompt_fragment() -> str:
    """
    Returns surface type options for AI prompts.
    """
    return (
        "Surface types (optional per-block 'surface' field):\n"
        f"  {' | '.join(SURFACE_TYPES)}"
    )


def get_page_config_prompt_fragment() -> str:
    """
    Returns page-level configuration options for AI prompts.
    """
    return (
        "Page configuration options:\n"
        f"  theme: {' | '.join(VALID_THEMES)}\n"
        f"  animation_level: {' | '.join(VALID_ANIMATION_LEVELS)}\n"
        f"  font_scale: {' | '.join(VALID_FONT_SCALES)}\n"
        f"  background_style: {' | '.join(VALID_BACKGROUND_STYLES)}\n"
        "  max_width: e.g. '1440px'"
    )
