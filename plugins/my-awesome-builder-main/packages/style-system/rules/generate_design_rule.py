"""
generate_design_rule.py
Generate design rules from mood + domain using BASE rules + OVERRIDES
"""

from .design_rules import (
    BASE_MOOD_RULES,
    BASE_DOMAIN_RULES,
    COMBINATION_OVERRIDES,
    DEFAULT_DESIGN
)


def merge_rules(mood_base, domain_base):
    """Merge mood and domain base rules"""
    merged = {}
    merged.update(mood_base)

    # Domain rules supplement mood rules
    for key, value in domain_base.items():
        if key not in merged:
            merged[key] = value

    return merged


def apply_override(merged, override):
    """Apply specific override for mood+domain combination"""
    merged.update(override)
    return merged


def generate_design_rule(mood, domain):
    """
    Generate complete design rule from mood + domain

    Args:
        mood: str - One of MOOD_TYPES
        domain: str - One of DOMAIN_TYPES

    Returns:
        dict - Complete design specification
    """
    mood_base = BASE_MOOD_RULES.get(mood, {})
    domain_base = BASE_DOMAIN_RULES.get(domain, {})

    if not mood_base and not domain_base:
        return DEFAULT_DESIGN

    merged = merge_rules(mood_base, domain_base)

    # Apply specific override if exists
    if (mood, domain) in COMBINATION_OVERRIDES:
        merged = apply_override(merged, COMBINATION_OVERRIDES[(mood, domain)])

    return merged
