#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/base_tool.py
すべての *_tool.py（calculator_tool.py, blender_tool.py 等）の共通基底クラス。
- IntentInspector 用の高速判定 (can_fast_route)
- ToolRegistry / LLM 用のスキーマ定義 (get_schema)
- ToolRouter 用の実行処理 (execute)
を1ファイルで完結できるように統一します。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseTool(ABC):
    """全ツール共通の基底クラス"""

    # --- メタデータ（サブクラスでオーバーライド） ---
    name: str = ""
    aliases: List[str] = []
    category: str = "general"
    description: str = ""

    # --- IntentInspector（第一関門：強制ルーティング）用設定 ---
    fast_route_enabled: bool = False
    priority: int = 100
    mode: str = "unknown"
    forced_handler: Optional[str] = None
    fast_route_score: int = 100

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        IntentInspector から呼ばれる高速判定メソッド。
        LLMを介さずに即座にこのツール（Handler）へ直行させる場合は
        (True, "理由文字列") を返す。
        """
        return False, ""

    def get_schema(self) -> Dict[str, Any]:
        """ToolRegistry / PromptBuilder が LLM に渡す JSON Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema(),
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        """引数スキーマ（サブクラスで必要に応じてオーバーライド）"""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """ToolRouter から呼ばれる実処理"""
        raise NotImplementedError