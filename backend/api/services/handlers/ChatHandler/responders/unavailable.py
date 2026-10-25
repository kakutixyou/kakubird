# api/services/handlers/ChatHandler/responders/unavailable.py
from __future__ import annotations

from typing import Optional

from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import HandlerResult, record_assistant


class LlmUnavailableResponder:
    """最後の砦。どのResponderも答えられなかった場合に必ず返す。"""

    name = "llm_unavailable"

    def __init__(self, results: ResultBuilder) -> None:
        self._results = results

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        response = (
            "AIモードは有効ですが、"
            "LocalLLMEngineを現在利用できません。"
            "登録済みのJSON Knowledgeで回答できる"
            "内容を入力してください。"
        )

        ctx.state.set_error("local_llm_unavailable")

        record_assistant(ctx, response, "system")

        return self._results.finalize(
            message=response,
            source="system",
            state=ctx.state,
            current_signals=ctx.current_signals,
            extra={
                "intent": ctx.intent,
                "analysis": ctx.analysis,
                "project_context": ctx.project_context,
            },
        )
