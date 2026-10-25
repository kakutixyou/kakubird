# api/services/handlers/ChatHandler/knowledge_access.py
"""KnowledgeRouter / KnowledgeLoader へのアクセスと、Knowledgeの整形。

※ api/services/knowledge_service.py とは別物。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from engine.KnowledgeLoader import KnowledgeLoader
from engine.KnowledgeRouter import KnowledgeRouter

from api.services.conversation.ConversationState import ConversationState

from .compat import accepts_kwarg
from .project_flow.context import get_project_context

logger = logging.getLogger(__name__)


class KnowledgeAccess:

    def __init__(
        self,
        knowledge_dir: Path,
        threshold: int,
        top_k: Optional[int],
        debug: Callable[[str], None],
    ) -> None:

        self._debug = debug

        self.router = KnowledgeRouter(
            knowledge_dir=str(knowledge_dir),
            threshold=threshold,
            top_k=top_k,
        )

        self.loader = KnowledgeLoader(
            knowledge_dirs=[knowledge_dir],
            cache_enabled=True,
        )

    # --------------------------------------------------------
    # Route
    # --------------------------------------------------------

    def route(
        self,
        message: str,
        state: ConversationState,
        analysis: Optional[Dict[str, Any]] = None,
    ):

        analysis = analysis or {}

        signals = {
            "active_context": state.current_topic,
            "current_topic": state.current_topic,
            "previous_topic": state.previous_topic,
            "active_knowledge": list(state.active_knowledge),
            "current_intent": state.current_intent,
            "project_context": get_project_context(state),
            "intent_analysis": dict(analysis),
            "mode": analysis.get("mode"),
            "intent": analysis.get("intent"),
            "actions": analysis.get("actions", []),
            "targets": analysis.get("targets", []),
            "target_categories": analysis.get("target_categories", []),
        }

        route = self.router.route

        # 旧KnowledgeRouter互換: signals を受け取れる時だけ渡す
        call_kwargs = (
            {"signals": signals} if accepts_kwarg(route, "signals") else {}
        )

        try:
            return route(message, **call_kwargs)

        except Exception as exc:
            logger.exception("KnowledgeRouter failed")
            self._debug(f"KnowledgeRouter failed: {exc}")
            return None

    @staticmethod
    def extract_route_paths(route_result) -> List[str]:

        if route_result is None:
            return []

        file_paths = getattr(route_result, "file_paths", None)

        if isinstance(file_paths, list):
            return [str(p) for p in file_paths]

        matched_files = getattr(route_result, "matched_files", None)

        if isinstance(matched_files, list):
            return [str(p) for p in matched_files]

        if isinstance(route_result, dict):
            values = (
                route_result.get("file_paths")
                or route_result.get("matched_files")
                or []
            )

            if isinstance(values, list):
                return [str(p) for p in values]

        if isinstance(route_result, list):
            return [str(p) for p in route_result]

        return []

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    def load(self, paths: List[str]) -> List[Any]:

        if not paths:
            return []

        try:
            result = self.loader.load(paths)

        except Exception as exc:
            logger.exception("KnowledgeLoader failed")
            self._debug(f"KnowledgeLoader failed: {exc}")
            return []

        items = getattr(result, "items", None)

        if isinstance(items, list):
            return items

        if isinstance(result, dict):
            return list(result.values())

        if isinstance(result, list):
            return result

        return []


# ------------------------------------------------------------
# 整形（Knowledge → JSON文字列）
# ------------------------------------------------------------

def knowledge_to_data(item: Any) -> Any:

    if isinstance(
        item,
        (dict, list, str, int, float, bool, type(None)),
    ):
        return item

    content = getattr(item, "content", None)

    if content is not None:
        return content

    data = getattr(item, "data", None)

    if data is not None:
        return data

    if hasattr(item, "__dict__"):
        try:
            return dict(item.__dict__)
        except Exception:
            pass

    return str(item)


def safe_json_response(knowledge: List[Any]) -> str:

    converted = [knowledge_to_data(item) for item in knowledge]

    if not converted:
        return "関連Knowledgeは見つかりませんでした。"

    payload: Any = converted[0] if len(converted) == 1 else converted

    return (
        "【JSON Knowledgeからの回答】\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
