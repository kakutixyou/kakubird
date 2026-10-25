#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/unity/unity_tool.py
フォルダー構成の tools/unity/ に対応する Unity C# (MonoBehaviour) スクリプト生成・支援ツール。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from tools.base_tool import BaseTool


class UnityTool(BaseTool):
    name = "unity_tool"
    aliases = ["unity", "monobehaviour", "unity_csharp"]
    category = "unity"
    description = "Unity用のC#スクリプト（MonoBehaviour、物理演算、UI、エディタ拡張）の生成・解析を行います。"

    fast_route_enabled = True
    priority = 46
    mode = "unity_development"
    forced_handler = None
    fast_route_score = 95

    UNITY_COMMANDS = ("/unity",)
    UNITY_STRONG_KEYWORDS = (
        "using unityengine",
        "monobehaviour",
        "serializefield",
        "unityスクリプト",
    )

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if any(msg_lower.startswith(cmd) for cmd in cls.UNITY_COMMANDS):
            return True, "unity_command"
        if any(kw in msg_lower for kw in cls.UNITY_STRONG_KEYWORDS):
            return True, "explicit_unity_script"
        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script_name": {
                    "type": "string",
                    "description": "生成するC#クラス名（例: 'PlayerController'）",
                },
                "instruction": {
                    "type": "string",
                    "description": "実装したい挙動やコンポーネントの説明",
                },
            },
            "required": ["instruction"],
        }

    async def execute(
        self,
        instruction: str = "",
        script_name: str = "NewBehaviourScript",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "tool": self.name,
            "message": f"Unity C#スクリプト ({script_name}.cs) の生成リクエストを受理しました: {instruction}",
            "data": {"script_name": script_name, "instruction": instruction, **kwargs},
        }