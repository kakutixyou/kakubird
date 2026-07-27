# backend/engines/html/structure_analyzer.py
from typing import Dict, Any, List, Set
from bs4.element import Tag

class StructureAnalyzer:
    """
    DOM構造の深度、コンポーネントツリーの構築、セマンティック推測を専門に行うクラス
    """
    def __init__(self):
        pass

    def calculate_dom_depth(self, node: Tag, depth: int = 0) -> int:
        if node is None:
            return depth
        max_depth = depth
        for child in node.children:
            if isinstance(child, Tag):
                max_depth = max(max_depth, self.calculate_dom_depth(child, depth + 1))
        return max_depth

    def build_component_tree(self, node: Tag) -> Dict[str, Any]:
        tree = {
            "tag": node.name,
            "id": node.get("id"),
            "classes": node.get("class", []),
            "children": []
        }
        for child in node.children:
            if isinstance(child, Tag):
                tree["children"].append(self.build_component_tree(child))
        return tree

    def detect_semantic_components(self, tags: Set[str], classes: Set[str], ids: Set[str], images_len: int, forms_len: int, tables_len: int) -> List[str]:
        detected = []
        
        # Hero
        if "section" in tags and "button" in tags and ("h1" in tags or "h2" in tags):
            detected.append("hero")
        # Navbar
        if "nav" in tags or "navbar" in classes or "navbar" in ids:
            detected.append("navbar")
        # Footer
        if "footer" in tags or "footer" in classes:
            detected.append("footer")
        # Card
        if "card" in classes or "card" in ids:
            detected.append("card")
        # Sidebar
        if "sidebar" in classes or "aside" in tags:
            detected.append("sidebar")
        # Modal
        if "modal" in classes or "dialog" in tags:
            detected.append("modal")
        # Gallery
        if images_len >= 3:
            detected.append("gallery")
        # Pricing
        if "pricing" in classes or "price" in classes:
            detected.append("pricing")
        # Contact Form
        if forms_len > 0:
            detected.append("contact_form")
        # Table Layout
        if tables_len > 0:
            detected.append("table_layout")

        return sorted(list(set(detected)))