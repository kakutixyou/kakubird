#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/registry/ToolLoader.py
importlib.import_module を用いた遅延読み込み（Lazy Load）および
tools.json からの動的ターゲット解決を担当するローダー。
一部のハンドラーや外部ライブラリが未インストールでもシステム全体の起動を止めません。
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LazyToolProxy:
    """
    ツールが実際に呼び出される瞬間まで import とインスタンス化を遅延させるプロキシ。
    プライマリモジュールが失敗した場合は fallback_module へ自動で切り替える。
    """

    def __init__(
        self,
        module_path: str,
        class_name: str,
        method_name: str = "execute",
        *,
        fallback_module: Optional[str] = None,
        fallback_class: Optional[str] = None,
        fallback_method: Optional[str] = None,
        init_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.module_path = module_path
        self.class_name = class_name
        self.method_name = method_name
        self.fallback_module = fallback_module
        self.fallback_class = fallback_class or class_name
        self.fallback_method = fallback_method or method_name
        self.init_kwargs = dict(init_kwargs or {})

        self._instance: Any = None
        self._resolved_method_name: str = method_name

    def _resolve_instance(self) -> Any:
        if self._instance is not None:
            return self._instance

        # 1. プライマリモジュールのロード試行
        try:
            mod = importlib.import_module(self.module_path)
            cls = getattr(mod, self.class_name)
            self._instance = cls(**self.init_kwargs)
            self._resolved_method_name = self.method_name
            return self._instance
        except Exception as primary_exc:
            if not self.fallback_module:
                raise primary_exc
            logger.debug(
                f"[ToolLoader] Primary load failed ({self.module_path}.{self.class_name}): {primary_exc}. "
                f"Trying fallback ({self.fallback_module}.{self.fallback_class})..."
            )

        # 2. フォールバックモジュールのロード試行
        mod = importlib.import_module(self.fallback_module)
        cls = getattr(mod, self.fallback_class)
        self._instance = cls(**self.init_kwargs)
        self._resolved_method_name = self.fallback_method
        return self._instance

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        instance = self._resolve_instance()
        target_fn = getattr(instance, self._resolved_method_name)
        result = target_fn(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


class ToolLoader:
    """モジュールパスや tools.json からツールインスタンスを安全にロードするクラス"""

    @staticmethod
    def load_class_instance(
        module_path: str,
        class_name: str,
        *,
        fallback_module: Optional[str] = None,
        fallback_class: Optional[str] = None,
        init_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """即座にクラスをimportしてインスタンス化する（失敗時はNoneを返す）"""
        kwargs = dict(init_kwargs or {})
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            return cls(**kwargs)
        except Exception as exc:
            if fallback_module:
                try:
                    mod = importlib.import_module(fallback_module)
                    cls = getattr(mod, fallback_class or class_name)
                    return cls(**kwargs)
                except Exception as fb_exc:
                    logger.warning(f"⚠️ [ToolLoader] フォールバック読込失敗 ({fallback_module}): {fb_exc}")
            else:
                logger.warning(f"⚠️ [ToolLoader] モジュール読込失敗 ({module_path}.{class_name}): {exc}")
        return None

    @staticmethod
    def create_lazy_proxy(target_cfg: Dict[str, Any]) -> LazyToolProxy:
        """tools.json の target ブロックから LazyToolProxy を生成する"""
        return LazyToolProxy(
            module_path=target_cfg["module"],
            class_name=target_cfg["class"],
            method_name=target_cfg.get("method", "execute"),
            fallback_module=target_cfg.get("fallback_module"),
            fallback_class=target_cfg.get("fallback_class"),
            fallback_method=target_cfg.get("fallback_method"),
            init_kwargs=target_cfg.get("init_kwargs"),
        )

    @staticmethod
    def load_tools_json(json_path: str | Path) -> List[Dict[str, Any]]:
        """tools.json を読み込んでツール定義リストを返す"""
        path = Path(json_path)
        if not path.is_file():
            logger.warning(f"⚠️ [ToolLoader] tools.json が見つかりません: {path}")
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return list(data.get("tools", []))
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.error(f"❌ [ToolLoader] tools.json の解析に失敗 ({path}): {exc}")
        return []


__all__ = ["LazyToolProxy", "ToolLoader"]