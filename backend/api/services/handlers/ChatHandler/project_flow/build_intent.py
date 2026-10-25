# api/services/handlers/ChatHandler/project_flow/build_intent.py
"""「今Buildを始めるべきか」の判定（外部依存なし）。

判定の優先順位:
    1. IntentInspector の明示Intent（PROJECT_BUILD_INTENTS）
    2. 文字列フォールバック（下記3段階）

文字列フォールバック:
    STRONG        単独でBuild命令        例「じゃあ作って」「アプリを作って」
    NEED_CONTEXT  要件が溜まっている時のみ  例「ビルドして」
    BARE          その一言だけの時のみ（要件も必要）
                                          例「生成して」/ ×「要約を生成して」
    ※ 説明・質問（「〜とは」「どうやって〜」等）は命令として扱わない
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ..constants import (
    BUILD_PHRASES_BARE,
    BUILD_PHRASES_NEED_CONTEXT,
    BUILD_PHRASES_STRONG,
    INFORMATIONAL_MARKERS,
    PROJECT_BUILD_INTENTS,
)
from ..intent_view import IntentView
from .context import has_project_context

_TRAILING_PUNCT = re.compile(r"[\s。．.!！?？〜~、,]+$")
_POLITE_SUFFIXES = (
    "お願いします", "お願い", "ください", "ほしい", "欲しい", "ね", "よ",
)


def _normalize_bare(text: str) -> str:
    """「生成して！」「実装してください」→「生成して」「実装して」"""

    text = _TRAILING_PUNCT.sub("", text)

    for suffix in _POLITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break

    return _TRAILING_PUNCT.sub("", text)


def _intent_matches(analysis: Dict[str, Any]) -> bool:

    return any(
        name in PROJECT_BUILD_INTENTS
        for name in IntentView.from_dict(analysis).candidates()
    )


def is_build_intent(
    message: str,
    analysis: Optional[Dict[str, Any]] = None,
    project_context: Optional[Dict[str, Any]] = None,
) -> bool:

    analysis = analysis if isinstance(analysis, dict) else {}

    # 1. IntentInspectorの明示Intent
    if _intent_matches(analysis):
        return True

    # 2. 文字列フォールバック
    lowered = str(message or "").lower().strip()

    if not lowered:
        return False

    if any(marker in lowered for marker in INFORMATIONAL_MARKERS):
        return False

    if any(phrase in lowered for phrase in BUILD_PHRASES_STRONG):
        return True

    has_context = has_project_context(project_context or {})

    if not has_context:
        return False

    if any(phrase in lowered for phrase in BUILD_PHRASES_NEED_CONTEXT):
        return True

    return _normalize_bare(lowered) in BUILD_PHRASES_BARE
