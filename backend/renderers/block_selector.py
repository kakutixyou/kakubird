# block_selector.py
from typing import Any, Dict, List

class BlockSelector:
    def __init__(self, blocks: List[Dict[str, Any]]):
        self.blocks = blocks

    def select(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        指定された条件に基づいてブロックを選択する。

        Args:
            conditions (Dict[str, Any]): 選択条件。

        Returns:
            List[Dict[str, Any]]: 選択されたブロック。
        """
        selected_blocks = []
        for block in self.blocks:
            if self._match_conditions(block, conditions):
                selected_blocks.append(block)
        return selected_blocks

    def _match_conditions(self, block: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """
        ブロックが指定された条件に一致するかどうかを判断する。

        Args:
            block (Dict[str, Any]): ブロック。
            conditions (Dict[str, Any]): 選択条件。

        Returns:
            bool: ブロックが条件に一致する場合に True。
        """
        for key, value in conditions.items():
            if key not in block or block[key] != value:
                return False
        return True

    def select_by_type(self, block_type: str) -> List[Dict[str, Any]]:
        """
        指定されたタイプのブロックを選択する。

        Args:
            block_type (str): ブロックタイプ。

        Returns:
            List[Dict[str, Any]]: 選択されたブロック。
        """
        return self.select({'type': block_type})

    def select_by_priority(self, priority: int) -> List[Dict[str, Any]]:
        """
        指定された優先度のブロックを選択する。

        Args:
            priority (int): 優先度。

        Returns:
            List[Dict[str, Any]]: 選択されたブロック。
        """
        return self.select({'priority': priority})

# 例
blocks = [
    {'type': 'hero', 'priority': 1},
    {'type': 'card', 'priority': 2},
    {'type': 'gallery', 'priority': 3},
    {'type': 'hero', 'priority': 4},
]

selector = BlockSelector(blocks)
selected_blocks = selector.select_by_type('hero')
print(selected_blocks)  # [{'type': 'hero', 'priority': 1}, {'type': 'hero', 'priority': 4}]

selected_blocks = selector.select_by_priority(2)
print(selected_blocks)  # [{'type': 'card', 'priority': 2}]
