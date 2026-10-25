# api/services/handlers/ChatHandler/responders/build.py
from __future__ import annotations

from typing import Any, Callable, Optional

from ..project_flow.build_intent import is_build_intent
from ..project_flow.build_runner import handle_project_build
from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import HandlerResult


class BuildResponder:
    """明示的なBuild命令なら Build を実行する。

    実行先の優先順位:
        1. build_delegate（ProjectBuilderHandler.build_project）
        2. 自前の ProjectBuildService
    """

    name = "project_build"

    def __init__(
        self,
        results: ResultBuilder,
        debug: Callable[[str], None],
        get_build_service: Callable[[], Any],
        get_build_delegate: Callable[[], Any],
        llm_available: Callable[[], bool],
        clean_existing: bool = True,
    ) -> None:
        self._results = results
        self._debug = debug
        self._get_build_service = get_build_service
        self._get_build_delegate = get_build_delegate
        self._llm_available = llm_available
        self._clean_existing = clean_existing

    def _use_ai(self, ctx: TurnContext) -> bool:
        constraints = {
            str(item).strip().lower()
            for item in ctx.project_context.get("constraints", []) or []
        }

        return self._llm_available() and "no_ai" not in constraints

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        if not is_build_intent(
            message=ctx.resolved_message,
            analysis=ctx.analysis,
            project_context=ctx.project_context,
        ):
            return None

        self._debug("project build intent detected")

        return await handle_project_build(
            build_service=self._get_build_service(),
            build_delegate=self._get_build_delegate(),
            request=ctx.request,
            message=ctx.resolved_message,
            use_ai=self._use_ai(ctx),
            clean_existing=self._clean_existing,
            results=self._results,
            debug=self._debug,
            state=ctx.state,
            current_signals=ctx.current_signals,
            analysis=ctx.analysis,
            requirement_result=ctx.requirement_result,
            context_result=ctx.context_result,
            topic_result=ctx.topic_result,
        )
