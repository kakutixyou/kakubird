# api/services/handlers/ChatHandler/responders/project_conversation.py
from __future__ import annotations

from typing import Callable, Optional

from ..project_flow.context import (
    has_project_context,
    looks_like_project_message,
)
from ..project_flow.conversation import (
    compose_project_conversation_response,
)
from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import GenerateFn, HandlerResult, record_assistant


class ProjectConversationResponder:
    """アプリ要件相談中（Knowledge無し）の応答。"""

    name = "project_conversation"

    def __init__(
        self,
        results: ResultBuilder,
        generate: GenerateFn,
        llm_available: Callable[[], bool],
    ) -> None:
        self._results = results
        self._generate = generate
        self._llm_available = llm_available

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        if not (
            has_project_context(ctx.project_context)
            and looks_like_project_message(ctx.resolved_message)
            and not ctx.loaded_knowledge
        ):
            return None

        state = ctx.state

        response = compose_project_conversation_response(
            ctx.project_context
        )

        use_llm = state.ai_enabled and self._llm_available()

        if use_llm:
            llm_response = self._generate(
                user_message=ctx.resolved_message,
                analysis=ctx.analysis,
                state=state,
                summary=ctx.summary,
            )

            if llm_response:
                response = llm_response

        source = "local_llm" if use_llm else "project_rule"

        record_assistant(ctx, response, source)

        return self._results.finalize(
            message=response,
            source=source,
            state=state,
            current_signals=ctx.current_signals,
            extra=ctx.base_extra(),
        )
