# api/services/handlers/ChatHandler/request_utils.py
"""request / signals から値を取り出すだけの関数群。"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

DebugFn = Callable[[str], None]


def _noop(_: str) -> None:
    return None


def compact_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


def extract_message(request) -> str:

    if isinstance(request, str):
        return request

    value = getattr(request, "message", "")

    if isinstance(value, str):
        return value

    return str(
        getattr(
            value,
            "text",
            getattr(value, "content", value),
        )
    )


def extract_signals(request) -> Dict[str, Any]:

    signals = getattr(request, "current_signals", None)

    if isinstance(signals, dict):
        return dict(signals)

    return {}


def extract_preloaded_knowledge(request) -> List[Any]:
    """ChatOrchestratorがロード済みのKnowledgeを再利用する。"""

    raw = getattr(request, "loaded_knowledge", None)

    if raw is None:
        return []

    if isinstance(raw, list):
        return list(raw)

    if isinstance(raw, dict):
        values = list(raw.values())

        if values and all(isinstance(item, dict) for item in values):
            return values

        return [raw]

    return []


def extract_existing_analysis(
    current_signals: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(current_signals, dict):
        return {}

    raw = current_signals.get("intent_analysis")

    if isinstance(raw, dict):
        return raw

    return {}


def analysis_from_request_or_signals(
    request,
    current_signals: Dict[str, Any],
    fallback_message: str,
    debug: Optional[DebugFn] = None,
) -> Dict[str, Any]:

    debug = debug or _noop

    # 1. Orchestrator Signal
    analysis = extract_existing_analysis(current_signals)

    if analysis:
        debug("reusing orchestrator intent_analysis")
        return analysis

    # 2. request.intent_analysis
    request_analysis = getattr(request, "intent_analysis", None)

    if isinstance(request_analysis, dict):
        return request_analysis

    # 3. Fallback（IntentInspectorはOrchestratorで1回だけ実行する方針）
    debug(
        "intent_analysis was not supplied by orchestrator; "
        "using safe fallback"
    )

    return {
        "mode": "unknown",
        "intent": "unknown",
        "score": 0,
        "routing_reason": "missing_orchestrator_intent_analysis",
        "fallback_message": fallback_message,
    }
