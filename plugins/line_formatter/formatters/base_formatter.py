# plugins/line_formatter/formatters/base_formatter.py
from abc import ABC, abstractmethod


class BaseFormatter(ABC):
    """各言語別フォーマッターの共通インターフェース"""

    name = "base"

    @abstractmethod
    async def calculate_score(self, message: str) -> int:
        """この言語のフォーマッターがどれだけ確信を持って処理できるか (0-100)"""
        raise NotImplementedError

    @abstractmethod
    async def format(self, message: str) -> str:
        """1行の文字列を要素分解して改行整形したコードを返す"""
        raise NotImplementedError