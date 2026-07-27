# patch_planner.py
from typing import Any, Dict, List
import yaml

class PatchPlanner:
    def __init__(self, template: str, patches: List[Dict[str, Any]]):
        self.template = template
        self.patches = patches

    def plan(self) -> str:
        """
        パッチを適用してHTMLを生成する。

        Returns:
            str: 生成されたHTML。
        """
        html = self.template
        for patch in self.patches:
            html = self._apply_patch(html, patch)
        return html

    def _apply_patch(self, html: str, patch: Dict[str, Any]) -> str:
        """
        パッチを適用してHTMLを更新する。

        Args:
            html (str): 現在のHTML。
            patch (Dict[str, Any]): パッチ。

        Returns:
            str: 更新されたHTML。
        """
        if patch['type'] == 'replace':
            html = html.replace(patch['old'], patch['new'])
        elif patch['type'] == 'insert':
            html = html[:patch['index']] + patch['new'] + html[patch['index']:]
        elif patch['type'] == 'delete':
            html = html[:patch['index']] + html[patch['index'] + patch['length']:]
        return html

    @classmethod
    def from_yaml(cls, yaml_file: str) -> 'PatchPlanner':
        """
        YAMLファイルからPatchPlannerを生成する。

        Args:
            yaml_file (str): YAMLファイルのパス。

        Returns:
            PatchPlanner: 生成されたPatchPlanner。
        """
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        return cls(data['template'], data['patches'])

# 例
template = '<html><body>{content}</body></html>'
patches = [
    {'type': 'replace', 'old': '{content}', 'new': '<h1>Hello World!</h1>'},
    {'type': 'insert', 'index': 10, 'new': '<p>This is a paragraph.</p>'},
]

planner = PatchPlanner(template, patches)
html = planner.plan()
print(html)
# <html><body><h1>Hello World!</h1><p>This is a paragraph.</p></body></html>

# YAMLファイルから生成
with open('patch.yaml', 'w') as f:
    yaml.dump({
        'template': template,
        'patches': patches,
    }, f)

planner = PatchPlanner.from_yaml('patch.yaml')
html = planner.plan()
print(html)
# <html><body><h1>Hello World!</h1><p>This is a paragraph.</p></body></html>
