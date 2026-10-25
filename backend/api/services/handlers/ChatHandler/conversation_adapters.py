# api/services/handlers/ChatHandler/conversation_adapters.py
"""services/conversation/ の各部品を「失敗しても止まらない」形で呼ぶ。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from api.services.conversation.ConversationState import ConversationState

from .project_flow.context import get_project_context

DebugFn = Callable[[str], None]


def _noop(_: str) -> None:
    return None


def resolve_context(
    context_resolver,
    message: str,
    state: ConversationState,
    debug: Optional[DebugFn] = None,
) -> Dict[str, Any]:

    debug = debug or _noop

    try:
        result = context_resolver.resolve(
            user_input=message,
            topic=state.current_topic,
            state=state,
        )

        if isinstance(result, dict):
            return result

        if isinstance(result, str):
            return {
                "original": message,
                "resolved": result,
                "changed": result != message,
                "reference": None,
                "source": None,
            }

    except Exception as exc:
        debug(f"ContextResolver failed: {exc}")

    return {
        "original": message,
        "resolved": message,
        "changed": False,
        "reference": None,
        "source": None,
    }


def track_topic(
    topic_tracker,
    message: str,
    state: ConversationState,
    analysis: Dict[str, Any],
    knowledge_paths: List[str],
    debug: Optional[DebugFn] = None,
) -> Dict[str, Any]:

    debug = debug or _noop

    try:
        result = topic_tracker.track(
            user_input=message,
            state=state,
            analysis=analysis,
            knowledge_paths=knowledge_paths,
        )

        if isinstance(result, dict):
            return result

        if isinstance(result, str):
            return {
                "topic": result,
                "previous_topic": state.current_topic,
                "changed": result != state.current_topic,
                "source": "tracker",
            }

    except Exception as exc:
        debug(f"TopicTracker failed: {exc}")

    return {
        "topic": state.current_topic,
        "previous_topic": state.previous_topic,
        "changed": False,
        "source": "previous",
    }


def build_summary(
    conversation_summary,
    state: ConversationState,
    debug: Optional[DebugFn] = None,
) -> Dict[str, Any]:

    debug = debug or _noop

    try:
        result = conversation_summary.summarize(
            history=state.history,
            state=state,
        )

        if isinstance(result, dict):
            return result

        return {"text": str(result)}

    except Exception as exc:
        debug(f"ConversationSummary failed: {exc}")

    return {
        "current_topic": state.current_topic,
        "previous_topic": state.previous_topic,
        "current_intent": state.current_intent,
        "active_knowledge": list(state.active_knowledge),
        "turn_count": state.turn_count,
        "project_context": get_project_context(state),
    }
