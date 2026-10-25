# api/services/handlers/ChatHandler/result_builder.py
"""ChatHandler の戻り値（("text", {...}) など）を組み立てる。"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from api.services.conversation.ConversationState import ConversationState

from .constants import ERROR_CLEARING_SOURCES
from .project_flow.context import get_project_context


class ResultBuilder:

    def __init__(
        self,
        debug: Callable[[str], None],
        enable_debug: bool = True,
    ) -> None:
        self._debug = debug
        self._enable_debug = enable_debug

    # --------------------------------------------------------
    # 通常応答
    # --------------------------------------------------------

    def finalize(
        self,
        message: str,
        source: str,
        state: ConversationState,
        current_signals: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:

        if source in ERROR_CLEARING_SOURCES:
            state.clear_error()

        updated_signals = dict(current_signals)
        updated_signals["conversation_state"] = state.to_dict()
        updated_signals["active_context"] = state.current_topic
        updated_signals["chat_mode"] = state.mode
        updated_signals["project_context"] = get_project_context(state)

        result: Dict[str, Any] = {
            "message": message,
            "source": source,
            "mode": state.mode,
            "ai_enabled": state.ai_enabled,
            "conversation_state": state.to_dict(),
            "project_context": get_project_context(state),
            "update_signals": updated_signals,
            "blocks": [],
        }

        if extra:
            result.update(extra)

        self._debug(
            "response "
            f"source={source}, "
            f"mode={state.mode}, "
            f"topic={state.current_topic}, "
            f"turn={state.turn_count}"
        )

        if self._enable_debug:
            try:
                state.debug_print()
            except Exception:
                pass

        return ("text", result)

    # --------------------------------------------------------
    # 簡易応答（空メッセージ等）
    # --------------------------------------------------------

    def simple(
        self,
        message: str,
        source: str,
        state: ConversationState,
    ) -> Tuple[str, Dict[str, Any]]:

        return (
            "text",
            {
                "message": message,
                "source": source,
                "mode": state.mode,
                "ai_enabled": state.ai_enabled,
                "conversation_state": state.to_dict(),
                "project_context": get_project_context(state),
                "blocks": [],
            },
        )

    # --------------------------------------------------------
    # Build 応答
    # --------------------------------------------------------

    def finalize_project_build(
        self,
        message: str,
        build_data: Dict[str, Any],
        state: ConversationState,
        current_signals: Dict[str, Any],
        analysis: Dict[str, Any],
        requirement_result: Dict[str, Any],
        context_result: Dict[str, Any],
        topic_result: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:

        updated_signals = dict(current_signals)
        updated_signals["conversation_state"] = state.to_dict()
        updated_signals["active_context"] = state.current_topic
        updated_signals["chat_mode"] = state.mode
        updated_signals["project_context"] = get_project_context(state)
        updated_signals["last_project_build"] = {
            "project_name": build_data.get("project_name"),
            "status": build_data.get("status"),
            "zip_download_url": build_data.get("zip_download_url"),
        }

        result = {
            "message": message,
            "source": "project_build",
            "mode": state.mode,
            "ai_enabled": state.ai_enabled,
            "intent": "project_build",
            "analysis": analysis,
            "project_context": get_project_context(state),
            "requirements": requirement_result,
            "context_resolution": context_result,
            "topic_tracking": topic_result,
            "conversation_state": state.to_dict(),
            "project_build": build_data,
            "update_signals": updated_signals,
            "blocks": [
                {"type": "project_build", "data": build_data}
            ],
        }

        self._debug(
            "project build response "
            f"status={build_data.get('status')}"
        )

        return ("project_build", result)
