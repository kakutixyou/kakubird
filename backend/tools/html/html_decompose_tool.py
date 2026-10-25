#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/html/html_decompose_tool.py
旧 IntentInspector._detect_decomposition_request() を切り出した <script> 抽出ツール。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple
from tools.base_tool import BaseTool


class HtmlDecomposeTool(BaseTool):
    name = "script_decomposition"
    aliases = ["decomposition", "extract_script"]
    category = "html"
    description = "HTML内の<script>タグや埋め込みスクリプトを検出・抽出・分解します。"

    # IntentInspector 高速ルーティング設定
    fast_route_enabled = True
    priority = 10
    mode = "script_extraction"
    forced_handler = "DecompositionHandler"
    fast_route_score = 100

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        has_script_tag = bool(
            re.search(r"<script\b[^>]*>", message, flags=re.IGNORECASE)
        )
        if not has_script_tag:
            return False, ""

        pk = cache.get("parser_keywords", {})
        decomp_kws = pk.get("DECOMPOSITION_KEYWORDS", [])
        if any(kw in msg_lower for kw in decomp_kws):
            return True, "script_tag_extraction"

        return True, "script_tag_detected"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "抽出対象のHTMLまたはスクリプトを含むテキスト",
                }
            },
            "required": ["html_content"],
        }

    async def execute(self, html_content: str = "", **kwargs: Any) -> Dict[str, Any]:
        from api.services.handlers.code.Decompositionhandler import DecompositionHandler

        handler = DecompositionHandler()
        return await handler.handle(html_content or kwargs.get("message", ""))