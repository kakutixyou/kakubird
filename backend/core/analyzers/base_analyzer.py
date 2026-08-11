# base_analyzer.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAnalyzer(ABC):
    """すべてのアナライザーの雛形となる抽象基底クラス"""
    
    @abstractmethod
    def can_handle(self, file_path: str, ext: str) -> bool:
        """このファイルをご自身（アナライザー）が処理可能か判定する"""
        pass

    @abstractmethod
    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        """実際の解析処理を行い、内部状態に蓄積する"""
        pass

    @abstractmethod
    def get_export_data(self) -> Optional[Dict[str, Any]]:
        """KnowledgeManagerに渡すための保存データを返す
        戻り値の形式: {"filename": "出力ファイル名.json", "content": {出力する辞書データ}}
        """
        pass