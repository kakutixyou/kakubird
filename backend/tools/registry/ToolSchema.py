#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/registry/ToolSchema.py
BaseTool インスタンスや Python 関数の型ヒント（typing / inspect）から、
LLM（PromptBuilder / Ollama / OpenAI Function Calling）向けの JSON Schema を生成・整形する。
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints

_PYTHON_TYPE_TO_JSON: Dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    List: "array",
    Dict: "object",
}


class ToolSchemaGenerator:
    """ツール定義からLLM用スキーマを生成・変換するユーティリティ"""

    @classmethod
    def from_base_tool(cls, tool: Any) -> Dict[str, Any]:
        """BaseTool インスタンスから標準スキーマ辞書を生成する"""
        if hasattr(tool, "get_schema") and callable(tool.get_schema):
            raw = tool.get_schema()
            # 既に OpenAI 形式 {"type": "function", "function": {...}} の場合は中身を取り出す
            if isinstance(raw, dict) and "function" in raw and isinstance(raw["function"], dict):
                fn = raw["function"]
                return {
                    "name": fn.get("name", getattr(tool, "name", "")),
                    "description": fn.get("description", getattr(tool, "description", "")),
                    "parameters": cls.normalize_parameters(fn.get("parameters", {})),
                }
            if isinstance(raw, dict):
                return {
                    "name": raw.get("name", getattr(tool, "name", "")),
                    "description": raw.get("description", getattr(tool, "description", "")),
                    "parameters": cls.normalize_parameters(raw.get("parameters", {})),
                }

        execute_fn = getattr(tool, "execute", None)
        params = cls.from_callable(execute_fn) if callable(execute_fn) else cls.normalize_parameters({})
        return {
            "name": getattr(tool, "name", tool.__class__.__name__.lower()),
            "description": getattr(tool, "description", inspect.getdoc(tool) or ""),
            "parameters": params,
        }

    @classmethod
    def from_callable(cls, func: Callable[..., Any]) -> Dict[str, Any]:
        """関数のシグネチャと型アノテーションから JSON Schema の parameters を自動生成する"""
        sig = inspect.signature(func)
        try:
            type_hints = get_type_hints(func)
        except Exception:
            type_hints = {}

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls", "kwargs", "args"):
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            annotated_type = type_hints.get(param_name, str)
            json_type = _PYTHON_TYPE_TO_JSON.get(annotated_type, "string")

            prop_entry: Dict[str, Any] = {
                "type": json_type,
                "description": f"Parameter '{param_name}'",
            }
            if param.default is not inspect.Parameter.empty and param.default is not None:
                prop_entry["default"] = param.default
            elif param.default is inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = prop_entry

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @classmethod
    def normalize_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        簡易形式 {"formula": "説明文"} で渡された parameters も
        正式な JSON Schema {"type": "object", "properties": {...}, "required": [...]} に正規化する。
        """
        if not isinstance(params, dict):
            return {"type": "object", "properties": {}, "required": []}

        if params.get("type") == "object" and "properties" in params:
            return {
                "type": "object",
                "properties": dict(params.get("properties") or {}),
                "required": list(params.get("required") or []),
            }

        # 簡易キー・バリュー形式の自動変換（旧 ToolRegistry.setup_default_tools 互換）
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for key, val in params.items():
            if isinstance(val, str):
                properties[key] = {"type": "string", "description": val}
                required.append(key)
            elif isinstance(val, dict):
                properties[key] = dict(val)
                if val.get("required", True):
                    required.append(key)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @staticmethod
    def to_openai_tool(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Ollama / OpenAI Function Calling 互換の {"type": "function", "function": ...} 形式へ変換"""
        return {
            "type": "function",
            "function": {
                "name": schema.get("name", ""),
                "description": schema.get("description", ""),
                "parameters": schema.get(
                    "parameters",
                    {"type": "object", "properties": {}, "required": []},
                ),
            },
        }


__all__ = ["ToolSchemaGenerator"]