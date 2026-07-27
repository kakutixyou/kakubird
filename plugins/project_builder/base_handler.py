# api/services/handlers/base_handler.py
from typing import Any, Tuple

class BaseHandler:
    """すべてのチャットハンドラーの親クラス"""
    
    async def can_handle(self, message: str) -> bool:
        """このメッセージを自分が処理すべきか判定する（True/False）"""
        raise NotImplementedError()

    async def handle(self, message: str) -> Tuple[str, Any]:
        """実際の処理を行い、(response_type, content) を返す"""
        raise NotImplementedError()