# api/services/handlers/offline_handler.py
from typing import Any, Tuple

from .base_handler import BaseHandler
from core.memory_manager import save_chat_message

class OfflineFallbackHandler(BaseHandler):
    """
    どのハンドラーも処理できず、メインのAI（Ollama）もダウンしている場合の
    最終的なフォールバック（最後の砦）を担当するハンドラー
    """
    
    async def can_handle(self, message: str) -> bool:
        """
        オーケストレーターのリストの一番最後に配置されるため、
        ここまで処理が流れてきたら無条件で引き受けます（常にTrue）。
        """
        return True

    async def handle(self, message: str) -> Tuple[str, Any]:
        """
        AIが応答できない旨を伝える安全なメッセージを返す
        """
        print("🛑 Offline Fallback Handler 発動: 最終フォールバック応答を返します")
        
        fallback_msg = (
            f"【システムAI】\n"
            f"「{message}」を受け付けました。\n"
            f"（現在、メインAIシステムがオフライン、または処理できない状態です）"
        )

        # 会話履歴には「オフライン時のシステム応答」として保存
        save_chat_message(
            "assistant",
            fallback_msg,
            metadata={"source": "offline_fallback"}
        )

        return "text", fallback_msg
    
    
    async def calculate_score(self, message: str) -> int:
        """
        どのハンドラーも処理できない場合の最終的なフォールバックなので、
        常に最低スコア（0点）を返します。
        """ 
        return 1