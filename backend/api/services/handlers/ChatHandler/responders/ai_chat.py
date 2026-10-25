# api/services/handlers/ChatHandler/responders/ai_chat.py
from __future__ import annotations

from typing import Optional

from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import GenerateFn, HandlerResult, record_assistant


class AiChatResponder:
    """AIモードでLocalLLMに直接答えさせる。生成できなければ None。"""

    name = "ai_chat"

    def __init__(self, results: ResultBuilder, generate: GenerateFn) -> None:
        self._results = results
        self._generate = generate

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        if not ctx.state.ai_enabled:
            return None

        response = self._generate(
            user_message=ctx.resolved_message,
            analysis=ctx.analysis,
            state=ctx.state,
            summary=ctx.summary,
        )

        if not response:
            return None

        record_assistant(ctx, response, "local_llm")

        return self._results.finalize(
            message=response,
            source="local_llm",
            state=ctx.state,
            current_signals=ctx.current_signals,
            extra=ctx.base_extra(),
        )
