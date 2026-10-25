# api/services/handlers/ChatHandler/project_flow/context.py
"""Project Context の取得・更新・判定。"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from api.services.conversation.ConversationState import ConversationState

from ..constants import PROJECT_WORDS

logger = logging.getLogger(__name__)

_MEANINGFUL_FIELDS = (
    "project_name", "framework", "purpose", "description",
    "target_user", "features", "pages", "database", "backend",
    "design_preferences", "constraints", "raw_requirements",
)


def get_project_context(state: ConversationState) -> Dict[str, Any]:

    getter = getattr(state, "get_project_context", None)

    if callable(getter):
        try:
            result = getter()

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    raw = getattr(state, "project_context", {})

    if isinstance(raw, dict):
        return dict(raw)

    return {}


def has_project_context(context: Dict[str, Any]) -> bool:

    if not isinstance(context, dict):
        return False

    for key in _MEANINGFUL_FIELDS:
        value = context.get(key)

        if value not in (None, "", [], {}, False):
            return True

    return False


def looks_like_project_message(message: str) -> bool:

    lowered = str(message or "").lower()

    return any(word in lowered for word in PROJECT_WORDS)


def update_project_context(
    requirement_analyzer,
    message: str,
    state: ConversationState,
    debug: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """RequirementAnalyzerで発言からProject Contextを更新する。"""

    current_context = get_project_context(state)

    # Projectに無関係で、既存Contextも無ければ解析しない
    if (
        not looks_like_project_message(message)
        and not has_project_context(current_context)
    ):
        return current_context

    try:
        result = requirement_analyzer.analyze(
            message=message,
            current_context=current_context,
        )

    except Exception as exc:
        logger.exception("RequirementAnalyzer failed")

        if debug:
            debug(f"RequirementAnalyzer failed: {exc}")

        return current_context

    if not isinstance(result, dict):
        return current_context

    updater = getattr(state, "update_project_context", None)

    if callable(updater):
        try:
            updater(result)

        except Exception as exc:
            if debug:
                debug(f"state.update_project_context failed: {exc}")

    else:
        # 古いConversationState互換
        try:
            state.project_context = dict(result)
        except Exception:
            pass

    return result
