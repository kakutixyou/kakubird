# api/services/handlers/ChatHandler/responders/chatbot.py
from __future__ import annotations

from typing import Optional

from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import HandlerResult, record_assistant
from .text_rules import compose_chatbot_fallback


class ChatbotResponder:
    """chatbotモード（ルールのみ）の応答。"""

    name = "chatbot"

    def __init__(self, results: ResultBuilder) -> None:
        self._results = results

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        if not ctx.state.chatbot_enabled:
            return None

        response = compose_chatbot_fallback(
            message=ctx.resolved_message,
            intent=ctx.intent,
            state=ctx.state,
        )

        record_assistant(ctx, response, "rule")

        return self._results.finalize(
            message=response,
            source="rule",
            state=ctx.state,
            current_signals=ctx.current_signals,
            extra=ctx.base_extra(),
        )
