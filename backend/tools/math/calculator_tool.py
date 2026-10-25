#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/math/calculator_tool.py
旧 IntentInspector._detect_math_request() のロジックを切り出した数式計算ツール。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from tools.base_tool import BaseTool


class CalculatorTool(BaseTool):
    name = "math_calculator"
    aliases = ["math", "calculate", "calculation"]
    category = "math"
    description = "複雑な数式や日本語単位混じりの計算要求（例: '220億+34000'）を安全かつ正確に計算します。"

    # IntentInspector 高速ルーティング設定
    fast_route_enabled = True
    priority = 30
    mode = "math_calculation"
    forced_handler = "MathHandler"
    fast_route_score = 100

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """SafeMathEngine を使って計算可能か直接テストする"""
        try:
            from engine.MathEngine import SafeMathEngine

            engine = SafeMathEngine()
            if engine.can_evaluate(message):
                return True, "mathengine_evaluable"
        except ImportError:
            pass
        except Exception as exc:
            print(f"⚠️ [CalculatorTool] MathEngine Check Error: {exc}", flush=True)

        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "description": "計算したい数式または計算要求テキスト（例: '220億+34000'）",
                }
            },
            "required": ["formula"],
        }

    async def execute(self, formula: str = "", **kwargs: Any) -> Dict[str, Any]:
        from api.services.handlers.Math_Handler import MathHandler

        handler = MathHandler()
        return await handler.handle(formula or kwargs.get("message", ""))