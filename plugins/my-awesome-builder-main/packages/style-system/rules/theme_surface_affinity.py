"""
theme_surface_affinity.py
Define theme and surface compatibility rules
"""

THEME_SURFACE_AFFINITY = {
    "default": {
        "best": ["flat", "elevated", "bordered"],
        "ok": ["glass", "neumorphism", "paper"],
        "avoid": []
    },
    "future-purple": {
        "best": ["glass", "glow", "frosted-dark"],
        "ok": ["elevated", "bordered"],
        "avoid": ["paper"]
    },
    "alexandros": {
        "best": ["bordered", "elevated", "flat"],
        "ok": ["glass", "neumorphism"],
        "avoid": ["frosted-dark"]
    }
}


def validate_surface_affinity(theme, surfaces):
    """
    Validate and correct surface/theme incompatibilities

    Args:
        theme: str - Theme name
        surfaces: list - List of surface types

    Returns:
        list - Corrected surface list
    """
    if theme not in THEME_SURFACE_AFFINITY:
        return surfaces

    affinity = THEME_SURFACE_AFFINITY[theme]
    corrected = []

    for surface in surfaces:
        if surface in affinity.get('avoid', []):
            # Replace with best alternative
            best = affinity.get('best', ['flat'])
            corrected.append(best[0])
        else:
            corrected.append(surface)

    return corrected
