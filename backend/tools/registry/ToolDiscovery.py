#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/registry/ToolDiscovery.py
tools/ フォルダー配下の各カテゴリ（math/, weather/, github/, blender/, unity/ 等）を自動スキャンし、
BaseTool を継承したクラスや @tool デコレータ付き関数を自動検出する。
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

try:
    from tools.base_tool import BaseTool
except ModuleNotFoundError:
    from base_tool import BaseTool

logger = logging.getLogger(__name__)


def tool(
    name: Optional[str] = None,
    description: str = "",
    aliases: Optional[List[str]] = None,
    category: str = "general",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """関数をシンプルなツールとして登録するための @tool デコレータ"""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_is_registered_tool", True)
        setattr(func, "_tool_meta", {
            "name": name or func.__name__.lower(),
            "description": description or (inspect.getdoc(func) or ""),
            "aliases": list(aliases or []),
            "category": category,
        })
        return func
    return decorator


class ToolDiscovery:
    """tools/ ディレクトリツリーを走査してツールクラスを自動発見するクラス"""

    IGNORE_DIRS = {"__pycache__", "registry", ".git", ".pytest_cache"}
    IGNORE_FILES = {"__init__.py", "base.py", "base_tool.py", "registry.py", "ToolResult.py", "ToolRouter.py"}

    @classmethod
    def discover_in_directory(
        cls,
        tools_root: str | Path,
        package_prefix: str = "tools",
    ) -> List[BaseTool]:
        """
        指定された tools/ ディレクトリ配下の *_tool.py 等をスキャンし、
        BaseTool サブクラスのインスタンス一覧を返す。
        """
        root_path = Path(tools_root).resolve()
        if not root_path.is_dir():
            logger.warning(f"⚠️ [ToolDiscovery] ディレクトリが存在しません: {root_path}")
            return []

        discovered: List[BaseTool] = []
        seen_names: set[str] = set()

        for py_file in sorted(root_path.rglob("*.py")):
            if any(part in cls.IGNORE_DIRS for part in py_file.parts):
                continue
            if py_file.name in cls.IGNORE_FILES:
                continue

            module = cls._load_module_from_path(py_file, root_path, package_prefix)
            if module is None:
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if not cls._is_concrete_base_tool(obj):
                    continue
                try:
                    instance: BaseTool = obj()
                    tool_name = getattr(instance, "name", "").strip()
                    if not tool_name or tool_name in seen_names:
                        continue
                    seen_names.add(tool_name)
                    discovered.append(instance)
                    logger.debug(f"🔍 [ToolDiscovery] 検出成功: {tool_name} ({py_file.name})")
                except Exception as exc:
                    logger.warning(f"⚠️ [ToolDiscovery] {obj.__name__} の初期化失敗: {exc}")

        return discovered

    @staticmethod
    def _is_concrete_base_tool(candidate: Type[Any]) -> bool:
        """抽象クラスではない BaseTool のサブクラスかどうかを判定"""
        if inspect.isabstract(candidate):
            return False
        if candidate is BaseTool or candidate.__name__ == "BaseTool":
            return False
        return issubclass(candidate, BaseTool) or (
            hasattr(candidate, "can_fast_route")
            and hasattr(candidate, "get_schema")
            and hasattr(candidate, "execute")
        )

    @staticmethod
    def _load_module_from_path(
        py_file: Path,
        root_path: Path,
        package_prefix: str,
    ) -> Optional[Any]:
        rel_parts = py_file.relative_to(root_path).with_suffix("").parts
        dotted_name = ".".join([package_prefix, *rel_parts]) if package_prefix else ".".join(rel_parts)

        try:
            return importlib.import_module(dotted_name)
        except Exception:
            try:
                spec = importlib.util.spec_from_file_location(dotted_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return mod
            except Exception as exc:
                logger.warning(f"⚠️ [ToolDiscovery] ファイル読込スキップ ({py_file.name}): {exc}")
        return None


__all__ = ["ToolDiscovery", "tool"]