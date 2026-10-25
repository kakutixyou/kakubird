#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/repomix/repomix_app_tool.py

BaseTool（IntentInspector 高速ルーティング・LLM スキーマ定義）と
handlers/Repomixhandler/Repomixhandler.py（実処理ハンドラー）をつなぐシンプルなラッパー。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from tools.base_tool import BaseTool
except ImportError:
    from abc import ABC
    class BaseTool(ABC):  # type: ignore
        pass

try:
    from handlers.Repomixhandler.Repomixhandler import RepomixHandler
except ModuleNotFoundError:
    try:
        from handlers.Repomix_Handler.Repomixhandler import RepomixHandler
    except ModuleNotFoundError:
        from Repomixhandler import RepomixHandler


class RepomixAppTool(BaseTool):
    """BaseTool 準拠の軽量ラッパー（実処理は RepomixHandler に委譲）"""

    name: str = "repomix"
    aliases: List[str] = ["repomix_app", "app_template", "restaurant_app"]
    category: str = "repomix"
    description: str = (
        "チャット欄に送られたRepomix出力を自動加工してpluginsに保存（ingest）、"
        "または保存済み記録からアプリZIPを生成（export）します。"
    )

    fast_route_enabled: bool = True
    priority: int = 15
    mode: str = "tool"
    forced_handler: Optional[str] = "repomix"
    fast_route_score: int = 95

    def __init__(self) -> None:
        super().__init__()
        self.handler = RepomixHandler()

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if RepomixHandler.is_repomix_output(message):
            cache["repomix_action"] = "ingest"
            return True, "Repomix出力を検知したため自動加工を実行します。"

        if (
            any(k in msg_lower for k in ("レストラン", "飲食店", "メニューアプリ"))
            and any(k in msg_lower for k in ("アプリ", "テンプレート", "zip"))
            and any(k in msg_lower for k in ("作りたい", "作成", "引き出", "ダウンロード"))
        ):
            cache["repomix_action"] = "export"
            cache["template_id"] = "restaurant-app-v2"
            return True, "レストランアプリのRepomix記録からの引き出し要求を検知しました。"

        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["ingest", "export", "list"]},
                "message": {"type": "string", "description": "Repomix出力テキスト"},
                "template_id": {"type": "string", "default": "restaurant-app-v2"},
                "store_name": {"type": "string", "description": "変更後の店舗名（任意）"},
                "store_description": {"type": "string", "description": "変更後の店舗説明文（任意）"},
            },
            "required": ["action"],
        }

    async def execute(self, payload: Any = None, **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        return await self.handler.execute(payload, **kwargs)