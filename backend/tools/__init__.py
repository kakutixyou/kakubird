from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """AIやシステムがツールを特定するための一意の名前"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """LLMのプロンプトに渡すためのツールの説明"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """実際の処理（API通信など）を行うメソッド"""
        pass