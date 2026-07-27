from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HTMLElement:
    tag_name: str
    attributes: Dict[str, str] = field(default_factory=dict)
    content: Optional[str] = None
    children: List['HTMLElement'] = field(default_factory=list)

    def add_child(self, child: 'HTMLElement'):
        self.children.append(child)

    def set_attribute(self, key: str, value: str):
        self.attributes[key] = value