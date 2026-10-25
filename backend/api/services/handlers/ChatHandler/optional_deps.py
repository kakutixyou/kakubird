
# api/services/handlers/ChatHandler/optional_deps.py
# -*- coding: utf-8 -*-
"""
任意依存（LocalLLM / PromptBuilder / ProjectBuildService）の読み込み。

方針:
1. 現在の実フォルダー構成に合う import パスを優先する。
2. 旧構成の import パスも互換性のために試す。
3. 依存関係が見つからない場合は warning を出し、None を返す。
4. import 中の例外も記録し、原因を追跡しやすくする。
5. クラスの読み込みと、LLMモデルのロードを分離する。
6. ChatPromptBuilder / PromptBuilder の両方のクラス名に対応する。

注意:
- このファイルは LocalLLMEngine のクラスを読み込むだけ。
- GGUFモデルの実際のロードは LocalLLMEngine 側に任せる。
- import パスは実際のプロジェクト構成に応じて調整する。
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Iterable, Optional, Sequence

logger = logging.getLogger(__name__)


# ============================================================
# Optional import
# ============================================================

def import_optional(
    module_paths: Iterable[str],
    attr: str,
) -> Optional[Any]:
    """
    複数の候補パスから属性を読み込む。

    Args:
        module_paths:
            import を試すモジュールパスの候補。
        attr:
            モジュールから取得するクラス名・関数名。

    Returns:
        読み込んだ属性。すべて失敗した場合は None。
    """
    errors: list[str] = []

    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            # モジュール内部の依存関係エラーなども記録する。
            errors.append(
                f"{module_path}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        try:
            value = getattr(module, attr)
        except AttributeError as exc:
            errors.append(
                f"{module_path}.{attr}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        logger.debug(
            "Optional dependency loaded: %s.%s",
            module_path,
            attr,
        )
        return value

    logger.warning(
        "Optional dependency '%s' is unavailable. Tried: %s",
        attr,
        " | ".join(errors) if errors else "(no paths provided)",
    )
    return None


def import_optional_attrs(
    module_paths: Iterable[str],
    attrs: Sequence[str],
) -> Optional[Any]:
    """
    モジュール候補と属性名候補を組み合わせて読み込む。

    例えば、ChatPromptBuilder.py 内のクラス名が
    PromptBuilder または ChatPromptBuilder のどちらでも対応する。
    """
    errors: list[str] = []

    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            errors.append(
                f"{module_path}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        for attr in attrs:
            try:
                value = getattr(module, attr)
            except AttributeError:
                continue

            logger.debug(
                "Optional dependency loaded: %s.%s",
                module_path,
                attr,
            )
            return value

        errors.append(
            f"{module_path}: "
            f"none of the attributes found: {', '.join(attrs)}"
        )

    logger.warning(
        "Optional dependency with attributes %s is unavailable. Tried: %s",
        ", ".join(attrs),
        " | ".join(errors) if errors else "(no paths provided)",
    )
    return None


# ============================================================
# LocalLLMEngine
# ============================================================

LocalLLMEngine = import_optional(
    (
        # 現在の実ファイル配置を優先
        "api.services.llm.LocalLLMEngine",

        # 旧構成・移動後の構成との互換性
        "api.services.project_generation.llm.LocalLLMEngine",
        "project_generation.llm.LocalLLMEngine",
    ),
    "LocalLLMEngine",
)


# ============================================================
# PromptBuilder
# ============================================================

PromptBuilder = import_optional_attrs(
    (
        # 現在のLLMフォルダーを優先
        "api.services.llm.ChatPromptBuilder",

        # 旧構成との互換性
        "api.services.project_generation.llm.ChatPromptBuilder",
        "project_generation.llm.ChatPromptBuilder",
    ),
    (
        # モジュール内の実際のクラス名に対応
        "PromptBuilder",
        "ChatPromptBuilder",
    ),
)


# ============================================================
# ProjectBuildService
# ============================================================

ProjectBuildService = import_optional(
    (
        "api.services.project_generation.ProjectBuildService",
        "api.services.project_generation.project_build_service",
        "project_generation.ProjectBuildService",
    ),
    "ProjectBuildService",
)


# ============================================================
# Diagnostics
# ============================================================

def get_optional_deps_status() -> dict[str, bool]:
    """
    任意依存がクラス・関数として読み込めたかを確認する。

    注意:
        True は import に成功したことを意味する。
        GGUFモデルが存在するか、実際に推論できるかまでは保証しない。
    """
    return {
        "LocalLLMEngine": LocalLLMEngine is not None,
        "PromptBuilder": PromptBuilder is not None,
        "ProjectBuildService": ProjectBuildService is not None,
    }


def log_optional_deps_status() -> dict[str, bool]:
    """
    依存関係の読み込み状況をログに出力して返す。
    """
    status = get_optional_deps_status()

    for name, loaded in status.items():
        if loaded:
            logger.info(
                "Optional dependency available: %s",
                name,
            )
        else:
            logger.warning(
                "Optional dependency unavailable: %s",
                name,
            )

    return status
