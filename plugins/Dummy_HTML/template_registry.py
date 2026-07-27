# plugins/Dummy_HTML/template_registry.py

from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "templates"

def get_templates():
    templates = []

    for file in TEMPLATE_DIR.glob("*.html"):
        templates.append({
            "id": file.stem,
            "name": file.stem.replace("_", " ").title(),
            "path": str(file)
        })

    return templates