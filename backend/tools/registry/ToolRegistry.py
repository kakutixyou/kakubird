#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/registry/ToolRegistry.py
LLM向けのツール定義（Schema）、実行環境（ToolRouter）、遅延読込（ToolLoader）、
自動スキャン（ToolDiscovery）を統合管理するレジストリ。
"""
from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tools.ToolRouter import ToolRouter
except ModuleNotFoundError:
    try:
        from api.services.tools.ToolRouter import ToolRouter
    except ModuleNotFoundError:
        from ToolRouter import ToolRouter

try:
    from tools.base_tool import BaseTool
except ModuleNotFoundError:
    from base_tool import BaseTool

try:
    from tools.registry.ToolSchema import ToolSchemaGenerator
    from tools.registry.ToolLoader import ToolLoader
    from tools.registry.ToolDiscovery import ToolDiscovery
except ModuleNotFoundError:
    from ToolSchema import ToolSchemaGenerator
    from ToolLoader import ToolLoader
    from ToolDiscovery import ToolDiscovery

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    PromptBuilder には get_all_schemas() で LLM 用ツール仕様を渡し、
    Orchestrator / ActionPlanner には router.execute() で実行環境を提供する。
    """

    def __init__(self, router: Optional[ToolRouter] = None) -> None:
        self.router = router or ToolRouter()
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        target: Any,
        method: Optional[str] = "execute",
        aliases: Optional[List[str]] = None,
        run_in_thread: bool = False,
        category: str = "general",
        replace: bool = True,
    ) -> None:
        """ツールを LLM 用スキーマと ToolRouter の両方に一括登録する"""
        normalized_params = ToolSchemaGenerator.normalize_parameters(parameters)
        schema_entry = {
            "name": name,
            "description": description,
            "parameters": normalized_params,
        }
        self._schemas[name] = schema_entry

        if callable(target) and method is None:
            self.router.register_callable(
                name=name,
                function=target,
                aliases=aliases or [],
                run_in_thread=run_in_thread,
                metadata={"schema": schema_entry, "category": category},
                replace=replace,
            )
        else:
            self.router.register(
                name=name,
                target=target,
                method=method,
                aliases=aliases or [],
                run_in_thread=run_in_thread,
                metadata={"schema": schema_entry, "category": category},
                replace=replace,
            )
        logger.debug(f"🔧 [ToolRegistry] ツール登録完了: {name}")

    def register_base_tool(self, tool_obj: BaseTool, *, replace: bool = True) -> None:
        """BaseTool サブクラス（calculator_tool.py, blender_tool.py 等）をそのまま登録する"""
        schema = ToolSchemaGenerator.from_base_tool(tool_obj)
        self._tool_instances[tool_obj.name] = tool_obj
        self.register_tool(
            name=tool_obj.name,
            description=schema["description"],
            parameters=schema["parameters"],
            target=tool_obj,
            method="execute",
            aliases=list(getattr(tool_obj, "aliases", []) or []),
            run_in_thread=False,
            category=getattr(tool_obj, "category", "general"),
            replace=replace,
        )

    def load_from_tools_json(self, json_path: str | Path) -> int:
        """
        tools.json を読み込み、LazyToolProxy 経由で全ツールを一括登録する。
        setup_default_tools() に try/except を並べる必要がなくなります。
        """
        tools_list = ToolLoader.load_tools_json(json_path)
        registered_count = 0

        for item in tools_list:
            if not item.get("enabled", True):
                continue

            name = item.get("name")
            target_cfg = item.get("target")
            schema_cfg = item.get("schema", {})
            if not name or not isinstance(target_cfg, dict):
                continue

            lazy_proxy = ToolLoader.create_lazy_proxy(target_cfg)
            self.register_tool(
                name=name,
                description=schema_cfg.get("description", ""),
                parameters=schema_cfg.get("parameters", {}),
                target=lazy_proxy,
                method="execute",
                aliases=item.get("aliases", []),
                run_in_thread=bool(target_cfg.get("run_in_thread", False)),
                category=item.get("category", "general"),
                replace=True,
            )
            registered_count += 1

        logger.info(f"📦 [ToolRegistry] tools.json から {registered_count} 件のツールを登録しました")
        return registered_count

    def auto_discover(self, tools_dir: str | Path, package_prefix: str = "tools") -> int:
        """
        tools/ フォルダー配下の *_tool.py を自動スキャンして一括登録する。
        """
        instances = ToolDiscovery.discover_in_directory(tools_dir, package_prefix=package_prefix)
        for inst in instances:
            self.register_base_tool(inst, replace=True)
        logger.info(f"🔍 [ToolRegistry] 自動スキャンで {len(instances)} 件のツールを登録しました")
        return len(instances)

    def get_all_schemas(self, *, openai_format: bool = False) -> List[Dict[str, Any]]:
        """PromptBuilder や Ollama に渡すための全ツール仕様を取得する"""
        schemas = [copy.deepcopy(s) for s in self._schemas.values()]
        if openai_format:
            return [ToolSchemaGenerator.to_openai_tool(s) for s in schemas]
        return schemas

    def get_schemas_by_names(
        self,
        names: List[str],
        *,
        openai_format: bool = False,
    ) -> List[Dict[str, Any]]:
        """特定のモードで許可されたツール群のみの仕様を取得する"""
        selected = [copy.deepcopy(self._schemas[n]) for n in names if n in self._schemas]
        if openai_format:
            return [ToolSchemaGenerator.to_openai_tool(s) for s in selected]
        return selected

    def get_all_descriptions_text(self) -> str:
        """ChatPromptBuilder のシステムプロンプトへそのまま埋め込めるテキスト一覧"""
        lines = []
        for idx, (name, schema) in enumerate(self._schemas.items(), start=1):
            desc = schema.get("description", "")
            lines.append(f'{idx}. "{name}": {desc}')
        return "\n".join(lines)


__all__ = ["ToolRegistry"]