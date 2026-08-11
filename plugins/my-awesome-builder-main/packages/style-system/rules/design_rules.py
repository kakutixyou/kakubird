"""
design_rules.py
Design decision dictionary based on mood + domain
"""

MOOD_TYPES = ["futuristic", "elegant", "academic", "historical", "playful", "corporate", "minimal"]
DOMAIN_TYPES = ["engineering", "history", "medical", "business", "language", "science", "general"]
DENSITY_TYPES = ["light", "balanced", "heavy"]
AUTHORITY_TYPES = ["formal", "semi-formal", "casual"]
ENGAGEMENT_TYPES = ["static", "soft", "interactive"]

BASE_MOOD_RULES = {
    "futuristic": {
        "preferred_themes": ["future-purple"],
        "preferred_surfaces": ["glass", "glow"],
        "animation_tendency": "high",
        "spacing_trend": "balanced"
    },
    "elegant": {
        "preferred_themes": ["default"],
        "preferred_surfaces": ["paper", "elevated"],
        "animation_tendency": "soft",
        "spacing_trend": "luxury"
    },
    "academic": {
        "preferred_themes": ["default"],
        "preferred_surfaces": ["flat", "bordered"],
        "animation_tendency": "low",
        "spacing_trend": "balanced"
    },
    "historical": {
        "preferred_themes": ["default"],
        "preferred_surfaces": ["paper"],
        "animation_tendency": "none",
        "spacing_trend": "airy"
    },
    "playful": {
        "preferred_themes": ["alexandros"],
        "preferred_surfaces": ["neumorphism", "glass"],
        "animation_tendency": "high",
        "spacing_trend": "airy"
    },
    "corporate": {
        "preferred_themes": ["default"],
        "preferred_surfaces": ["flat", "elevated"],
        "animation_tendency": "soft",
        "spacing_trend": "balanced"
    },
    "minimal": {
        "preferred_themes": ["default"],
        "preferred_surfaces": ["flat"],
        "animation_tendency": "none",
        "spacing_trend": "balanced"
    }
}

BASE_DOMAIN_RULES = {
    "engineering": {
        "color_intensity": "high",
        "information_density": "balanced",
        "emphasis_elements": ["diagram", "code", "chart"]
    },
    "history": {
        "color_intensity": "low",
        "information_density": "medium",
        "emphasis_elements": ["timeline", "image", "quote"]
    },
    "medical": {
        "color_intensity": "medium",
        "information_density": "high",
        "emphasis_elements": ["diagram", "definition", "checklist"]
    },
    "business": {
        "color_intensity": "medium",
        "information_density": "high",
        "emphasis_elements": ["statistic", "chart", "quote"]
    },
    "language": {
        "color_intensity": "high",
        "information_density": "medium",
        "emphasis_elements": ["example", "quiz", "accordion"]
    },
    "science": {
        "color_intensity": "low",
        "information_density": "high",
        "emphasis_elements": ["code", "diagram", "table"]
    },
    "general": {
        "color_intensity": "medium",
        "information_density": "medium",
        "emphasis_elements": ["card", "banner", "image"]
    }
}

COMBINATION_OVERRIDES = {
    ("futuristic", "engineering"): {
        "theme": "future-purple",
        "recommended_surfaces": ["glass", "glow", "bordered", "frosted-dark"],
        "recommended_animations": ["soft-fade", "hover-lift"],
        "section_balance": "visual-tech"
    },
    ("academic", "engineering"): {
        "theme": "default",
        "recommended_surfaces": ["flat", "bordered", "elevated"],
        "recommended_animations": ["none", "soft-fade"],
        "section_balance": "data-heavy"
    },
    ("historical", "history"): {
        "theme": "default",
        "recommended_surfaces": ["paper", "bordered"],
        "recommended_animations": ["none"],
        "section_balance": "narrative"
    },
    ("playful", "language"): {
        "theme": "alexandros",
        "recommended_surfaces": ["neumorphism", "glass"],
        "recommended_animations": ["hover-lift", "soft-fade"],
        "section_balance": "interactive-learning"
    },
    ("academic", "general"): {
        "theme": "default",
        "recommended_surfaces": ["flat", "bordered", "elevated"],
        "recommended_animations": ["none", "soft-fade"],
        "section_balance": "structured-info"
    }
}

DENSITY_RULES = {
    "light": {
        "spacing_override": "airy",
        "max_blocks": 5,
        "text_length": "short"
    },
    "balanced": {
        "spacing_override": "balanced",
        "max_blocks": 8,
        "text_length": "medium"
    },
    "heavy": {
        "spacing_override": "compact",
        "max_blocks": 12,
        "text_length": "long"
    }
}

AUTHORITY_RULES = {
    "formal": {
        "surface_penalty": ["glass", "glow"],
        "typography_bias": "academic",
        "animation_bias": ["none"]
    },
    "semi-formal": {
        "surface_penalty": [],
        "typography_bias": None,
        "animation_bias": ["soft-fade"]
    },
    "casual": {
        "surface_penalty": [],
        "typography_bias": "rounded",
        "animation_bias": ["hover-lift", "soft-fade"]
    }
}

ENGAGEMENT_RULES = {
    "static": {
        "animation_force": ["none"],
        "interactive_bonus": False
    },
    "soft": {
        "animation_force": ["soft-fade"],
        "interactive_bonus": True
    },
    "interactive": {
        "animation_force": ["hover-lift", "soft-fade"],
        "interactive_bonus": True
    }
}

USAGE_LIMITS = {
    "glass": 0.35,
    "glow": 0.15,
    "neumorphism": 0.30,
    "hover-lift": 0.30,
    "soft-fade": 0.50
}

DEFAULT_DESIGN = {
    "theme": "default",
    "recommended_surfaces": ["flat", "bordered"],
    "recommended_animations": ["none"],
    "section_balance": "structured-info"
}
