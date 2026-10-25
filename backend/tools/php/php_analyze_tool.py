#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/php/php_analyze_tool.py
フォルダー構成の tools/php/ に対応する PHP コード解析・変換ツール（PhpHandler 連携）。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from tools.base_tool import BaseTool


class PhpAnalyzeTool(BaseTool):
    name = "php_analyze"
    aliases = ["php", "php_handler", "laravel_analyze"]
    category = "php"
    description = "PHPコードやLaravelプロジェクトの構文解析・リファクタリング・変換を行います。"

    fast_route_enabled = True
    priority = 38
    mode = "php_code"
    forced_handler = "PhpHandler"
    fast_route_score = 95

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if msg_lower.startswith("/php"):
            return True, "php_command"
        if "<?php" in msg_lower:
            return True, "php_opening_tag_detected"
        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "解析または変換したいPHPコード",
                },
                "task": {
                    "type": "string",
                    "description": "実行したい操作（'analyze', 'refactor', 'convert' など）",
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str = "", task: str = "analyze", **kwargs: Any) -> Dict[str, Any]:
        from api.services.handlers.code.PHPHandler import PhpHandler

        handler = PhpHandler()
        return await handler.handle(code or kwargs.get("message", ""))