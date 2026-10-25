# api/services/handlers/ChatHandler/knowledge_filter.py
"""Orchestrator が付与する system 文脈と、実Knowledgeを分ける。

ChatOrchestrator._invoke_handler は毎回
    system/knowledge_health, system/project_progress
を loaded_knowledge に追加する。これを「Knowledgeがある」と数えると、
要件相談・chatbotフォールバックの分岐に永久に到達しない。
"""

from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Tuple

SYSTEM_CONTENT_TYPES = frozenset({"generated_context"})
SYSTEM_ID_PREFIX = "system/"


def is_system_context(item: Any) -> bool:

    if not isinstance(item, Mapping):
        return False

    if str(item.get("content_type") or "").lower() in SYSTEM_CONTENT_TYPES:
        return True

    for key in ("id", "source_path"):
        value = item.get(key)

        if isinstance(value, str) and value.startswith(SYSTEM_ID_PREFIX):
            return True

    return False


def split_knowledge(items: Iterable[Any]) -> Tuple[List[Any], List[Any]]:
    """(実Knowledge, system文脈) に分ける。"""

    real: List[Any] = []
    system: List[Any] = []

    for item in items or []:
        (system if is_system_context(item) else real).append(item)

    return real, system


def has_knowledge_channel(request: Any) -> bool:
    """Orchestrator が Knowledge を管理している（loaded_knowledge 属性がある）か。

    True の場合、ChatHandler は自前の Router / Loader を使わない。
    空でも「Orchestrator が選んだ結果が空」という意味になる。
    """

    return getattr(request, "loaded_knowledge", None) is not None
