# api/services/handlers/ChatHandler/mode_switch.py
"""AI / Chatbot モード切替の判定と応答文。"""

from __future__ import annotations

from typing import Optional

from .constants import (
    AI_ENABLE_WORDS,
    AI_MODE,
    CHATBOT_ENABLE_WORDS,
    CHATBOT_MODE,
    INFORMATIONAL_MARKERS,
)


def _mode_from_text(message: str) -> Optional[str]:
    """文面からモード切替の命令を読む。

    「aiモードって何？」のような説明要求は切替命令として扱わない。
    """

    lowered = message.lower()

    if any(marker in lowered for marker in INFORMATIONAL_MARKERS):
        return None

    if any(word in lowered for word in CHATBOT_ENABLE_WORDS):
        return CHATBOT_MODE

    if any(word in lowered for word in AI_ENABLE_WORDS):
        return AI_MODE

    return None


def extract_requested_mode(request, message: str) -> Optional[str]:

    chat_mode = getattr(request, "chat_mode", None)

    if chat_mode in (CHATBOT_MODE, AI_MODE):
        return chat_mode

    ai_mode = getattr(request, "ai_mode", None)

    if isinstance(ai_mode, bool):
        return AI_MODE if ai_mode else CHATBOT_MODE

    return _mode_from_text(message)


def mode_switch_response(message: str) -> Optional[str]:

    mode = _mode_from_text(message)

    if mode == CHATBOT_MODE:
        return (
            "チャットボットモードに切り替えました。"
            "このモードでは生成AIを使用せず、"
            "JSON Knowledgeとルールだけを使います。"
        )

    if mode == AI_MODE:
        return (
            "AIモードに切り替えました。"
            "JSON Knowledgeを優先し、"
            "必要な場合にLocalLLMを使用します。"
        )

    return None
