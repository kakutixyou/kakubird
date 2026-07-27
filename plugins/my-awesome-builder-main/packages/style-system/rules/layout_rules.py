"""
layout_rules.py
Define layout patterns based on section_balance
"""

LAYOUT_SECTION_BALANCE = {
    "visual-tech": {
        "layout_pattern": "alternating-image-text",
        "recommended_blocks": [
            "hero", "split_hero", "statistic_circle",
            "feature_banner", "diagram_cards"
        ],
        "max_text_blocks": 3
    },
    "data-heavy": {
        "layout_pattern": "structured-columns",
        "recommended_blocks": [
            "table_section", "definition_box", "checklist_summary",
            "step_flow", "code_panel"
        ],
        "max_text_blocks": 8
    },
    "narrative": {
        "layout_pattern": "flowing-text",
        "recommended_blocks": [
            "timeline", "quote_panel", "section_header",
            "accordion_faq", "image_gallery"
        ],
        "max_text_blocks": 5
    },
    "interactive-learning": {
        "layout_pattern": "engaging-blocks",
        "recommended_blocks": [
            "quiz", "accordion_faq", "next_lesson",
            "mini_test", "checklist_summary"
        ],
        "max_text_blocks": 4
    },
    "structured-info": {
        "layout_pattern": "balanced",
        "recommended_blocks": [
            "info_cards", "profile_cards", "feature_banner",
            "progress_meter", "statistic_circle"
        ],
        "max_text_blocks": 6
    },
    "conversion": {
        "layout_pattern": "cta-focused",
        "recommended_blocks": [
            "feature_banner", "download_cta", "contact_box",
            "spotlight_panel", "next_lesson"
        ],
        "max_text_blocks": 3
    }
}
