# api/services/handlers/ChatHandler/responders/knowledge.py
from __future__ import annotations

from typing import Any, Callable, Optional

from ..result_builder import ResultBuilder
from ..turn_context import TurnContext
from .base import GenerateFn, HandlerResult, record_assistant
from .text_rules import compose_response


class KnowledgeResponder:
    """Knowledgeがある場合の応答（AI: LLM+根拠 / chatbot: ルール整形）。"""

    name = "knowledge"

    def __init__(
        self,
        results: ResultBuilder,
        response_composer: Any,
        generate: GenerateFn,
        llm_available: Callable[[], bool],
        debug: Callable[[str], None],
        fallback_generate: Optional[GenerateFn] = None,  # ← 自作LLM用に追加
    ) -> None:
        self._results = results
        self._composer = response_composer
        self._generate = generate
        self._llm_available = llm_available
        self._debug = debug
        self._fallback_generate = fallback_generate

    async def try_respond(self, ctx: TurnContext) -> Optional[HandlerResult]:

        if not ctx.loaded_knowledge:
            return None

        state = ctx.state
        response = None
        source = "json"

        # 1. メインのLLM（Ollama等）での生成を試みる
        if state.ai_enabled and self._llm_available():
            response = self._generate(
                user_message=ctx.resolved_message,
                analysis=ctx.analysis,
                state=state,
                summary=ctx.summary,
                knowledge_data=ctx.llm_knowledge,
            )
            if response:
                source = "local_llm+knowledge"

        # 2. メインLLMが失敗した場合のフォールバック処理
        if not response:
            if state.ai_enabled:
                self._debug("Main LLM unavailable. Trying fallback LLM...")
                
                # 自作LLM（GagHandlerの軽量版など）が渡されていれば実行
                if self._fallback_generate:
                    response = self._fallback_generate(
                        user_message=ctx.resolved_message,
                        analysis=ctx.analysis,
                        state=state,
                        summary=ctx.summary,
                        knowledge_data=ctx.llm_knowledge,
                    )
                    if response:
                        source = "self_made_llm+knowledge"

                # 自作LLMも無い、または失敗した場合は、エラーを出さずにChatbot（ルールベース）で凌ぐ
                if not response:
                    self._debug("Fallback LLM unavailable. Using chatbot rules.")
                    response = compose_response(
                        self._composer,
                        user_message=ctx.resolved_message,
                        intent=ctx.intent,
                        knowledge=ctx.loaded_knowledge,
                        state=state,
                        debug=self._debug,
                    )
                    source = "fallback_chatbot"
                    state.set_error("local_llm_fallback_used") # 内部的にエラー状態だけは記録
            else:
                # もともとChatbotモードの場合
                response = compose_response(
                    self._composer,
                    user_message=ctx.resolved_message,
                    intent=ctx.intent,
                    knowledge=ctx.loaded_knowledge,
                    state=state,
                    debug=self._debug,
                )

        record_assistant(ctx, response, source)

        return self._results.finalize(
            message=response,
            source=source,
            state=state,
            current_signals=ctx.current_signals,
            extra={
                **ctx.base_extra(),
                "knowledge_paths": ctx.knowledge_paths,
            },
        )