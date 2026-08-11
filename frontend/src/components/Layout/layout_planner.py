# layout/layout_planner.py
import json
from typing import Any, Dict, List

class LayoutPlanner:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def plan(self) -> Dict[str, Any]:
        # レイアウトを計画する
        layout = {
            'blocks': []
        }

        # ブロックを追加する
        for block in self.data['blocks']:
            layout['blocks'].append({
                'type': block['type'],
                'props': block['props']
            })

        # レイアウトを整理する
        layout = self._sort_blocks(layout)

        return layout

    def _sort_blocks(self, layout: Dict[str, Any]) -> Dict[str, Any]:
        # ブロックをソートする
        layout['blocks'] = sorted(layout['blocks'], key=lambda x: x['type'])

        return layout

    def _get_block_type(self, block: Dict[str, Any]) -> str:
        # ブロックのタイプを取得する
        return block['type']

    def _get_block_props(self, block: Dict[str, Any]) -> Dict[str, Any]:
        # ブロックのプロパティを取得する
        return block['props']

def main():
    # データを読み込む
    with open('.ai_memory/data.json', 'r') as f:
        data = json.load(f)

    # レイアウトを計画する
    layout_planner = LayoutPlanner(data)
    layout = layout_planner.plan()

    # レイアウトを出力する
    print(json.dumps(layout, indent=4))

if __name__ == '__main__':
    main()
