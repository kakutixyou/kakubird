# api/services/handlers/GagHandler/GagHandler.py
# -*- coding: utf-8 -*-
"""
GagHandler.py

薄いオーケストレーション層（200行以下）。
ルール抽出(GagTool) → 状態復元(profile_store) → 採点・再生成ループ(evaluation / generator / prompt_builder)
→ 出力整形(output_formatter) のパイプラインを非同期安全に統括する。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Tuple

from api.services.handlers.base_handler import BaseHandler
from api.services.handlers.ChatHandler import optional_deps
from api.services.handlers.ChatHandler.request_utils import (
    analysis_from_request_or_signals,
    extract_message,
    extract_signals,
)
from api.services.handlers.ChatHandler.result_builder import ResultBuilder
from api.services.handlers.ChatHandler.state_restore import restore_state

from .evaluation import clean_generated_text, evaluate_candidate
from .GagRuleEngine import GagEvaluation, GagRuleEngine, GagRuleProfile
from .generator import generate_gag_once, synthesize_fallback_gag
from .output_formatter import format_gag_output, should_request_advice
from .profile_store import (
    load_gag_history,
    load_profile,
    load_user_history_texts,
    save_turn_data,
)
from .prompt_builder import build_gag_prompt, build_retry_feedback

try:
    from tools.gag.gag_tool import GagTool
except ImportError:
    try:
        from api.services.tools.gag.gag_tool import GagTool
    except ImportError:
        GagTool = None

# try:
#     from advice.Geminiadvice_tool import GeminiAdviceTool
# except ImportError:
#     try:
#         from api.services.advice.Geminiadvice_tool import GeminiAdviceTool
#     except ImportError:
#         GeminiAdviceTool = None

logger = logging.getLogger(__name__)


def _try_init(factory: Any, name: str) -> Any:
    if factory is None:
        return None
    try:
        return factory()
    except Exception as exc:
        logger.warning("%s init failed: %s", name, exc)
        return None


class Gaghandler(BaseHandler):
    HANDLER_NAME = "Gaghandler"
    DEFAULT_SCORE = 95
    MAX_ATTEMPTS = 3
    PASSING_SCORE = 70.0

    def __init__(
        self,
        local_llm: Any = None,
        prompt_builder: Any = None,
        enable_debug: bool = True,
        fallback_generate: Optional[Callable[..., Optional[str]]] = None,
        rule_engine: Optional[GagRuleEngine] = None,
        advice_tool: Any = None,
    ) -> None:
        super().__init__()
        self.enable_debug = enable_debug
        self.fallback_generate = fallback_generate
        self.prompt_builder = prompt_builder or _try_init(optional_deps.PromptBuilder, "PromptBuilder")
        self.local_llm = local_llm or _try_init(optional_deps.LocalLLMEngine, "LocalLLMEngine")
        self.rule_engine = rule_engine or GagRuleEngine()
        # self.advice_tool = advice_tool or (GeminiAdviceTool() if GeminiAdviceTool else None)
        self.results = ResultBuilder(debug=self._debug, enable_debug=self.enable_debug)

    def _debug(self, message: str) -> None:
        logger.debug("[%s] %s", self.HANDLER_NAME, message)
        if self.enable_debug:
            print(f"🤡 [{self.HANDLER_NAME}] {message}", flush=True)

    async def calculate_score(
        self, message: str, current_signals: Optional[Dict[str, Any]] = None
    ) -> int:
        if not getattr(self, "enabled", True):
            return 0
        intent_analysis = (current_signals or {}).get("intent_analysis", {})
        forced = str(intent_analysis.get("forced_handler", ""))
        intent = str(intent_analysis.get("intent", "")).lower()
        routing = intent_analysis.get("routing", {})
        if (
            forced in ("GagHandler", "Gaghandler")
            or intent in ("gag_request", "gag")
            or routing.get("gag_tool") is True
        ):
            return 100
        if GagTool is not None:
            msg_str = str(message or "")
            is_match, _ = GagTool.can_fast_route(msg_str, msg_str.lower(), {}, {})
            if is_match:
                return self.DEFAULT_SCORE
        return 0

    def estimate_size(self, message: str) -> int:
        return 800

    async def handle(self, request: Any) -> Tuple[str, Any]:
        message = extract_message(request)
        current_signals = extract_signals(request)
        state = restore_state(current_signals, "ai", self._debug)

        if not message.strip():
            return self.results.simple(
                "どんなネタを作りたいか教えてください。",
                self.HANDLER_NAME or "Gaghandler",
                state,
            )

        analysis = analysis_from_request_or_signals(request, current_signals, message, self._debug)
        summary = getattr(state, "summary", {}) or {}
        knowledge_data = getattr(request, "loaded_knowledge", None)
        state.next_turn()

        # 1. ルールと過去状態の復元
        rules = self._resolve_rules(message, current_signals, analysis)
        prev_profile = load_profile(state)
        past_gags = load_gag_history(state)
        history_texts = load_user_history_texts(state)

        profile = self.rule_engine.create_profile_from_rules(
            rules=rules, previous=prev_profile, history_texts=history_texts
        )
        assert profile is not None

        # 2. 同期LLMがイベントループを塞がないようスレッドで生成・採点ループを実行
        best_gag, best_eval, advice_data, source = await asyncio.to_thread(
            self._run_generation_loop,
            message,
            rules,
            profile,
            past_gags,
            analysis,
            state,
            summary,
            knowledge_data,
        )

        # 3. 純粋なネタ本文のみを専用履歴に保存
        save_turn_data(state, profile, best_gag, best_eval.score)

        # 4. 出力整形と履歴更新
        final_text = format_gag_output(best_gag, best_eval, profile, advice_data, message, rules)
        state.add_user_message(content=message, intent="gag_request", topic="お笑い")
        state.add_assistant_message(content=final_text, source=source, intent="gag_request", topic="お笑い")

        return self.results.finalize(
            message=final_text,
            source=source,
            state=state,
            current_signals=current_signals,
            extra={
                "intent": "gag_request",
                "gag_score": best_eval.score,
                "gag_evaluation": best_eval.to_dict(),
                "gag_profile": profile.to_dict(),
                "gemini_advice": advice_data,
            },
        )

    def _run_generation_loop(
        self,
        user_message: str,
        rules: Dict[str, Any],
        profile: GagRuleProfile,
        past_gags: list[str],
        analysis: Dict[str, Any],
        state: Any,
        summary: Dict[str, Any],
        knowledge_data: Any,
    ) -> Tuple[str, GagEvaluation, Dict[str, Any], str]:
        best_gag = ""
        best_eval: Optional[GagEvaluation] = None
        best_source = "rule_engine_gag"
        best_nat = 80.0
        best_orig = 80.0
        retry_feedback: Optional[str] = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            prompt = build_gag_prompt(user_message, profile, rules, retry_feedback)
            raw_text, source = generate_gag_once(
                prompt, user_message, profile, rules, self.local_llm,
                self.fallback_generate, analysis, state, summary, knowledge_data, self._debug,
            )
            cleaned = clean_generated_text(raw_text) or synthesize_fallback_gag(profile, rules)
            ev, nat_score, orig_score = evaluate_candidate(self.rule_engine, cleaned, profile, past_gags)

            self._debug(f"Attempt {attempt}: score={ev.score}, occ={ev.keyword_occurrences}, chars={ev.character_count}")

            if best_eval is None or ev.score > best_eval.score:
                best_gag, best_eval, best_source, best_nat, best_orig = (
                    cleaned, ev, source, nat_score, orig_score
                )

            in_range = (
                (profile.min_characters is None or ev.character_count >= profile.min_characters)
                and (profile.max_characters is None or ev.character_count <= profile.max_characters)
            )
            if ev.score >= self.PASSING_SCORE and not ev.missing_required_words and in_range:
                break
            if source != "local_llm+gag":
                break

            retry_feedback = build_retry_feedback(cleaned, ev, profile, nat_score)

        assert best_eval is not None
        # advice_data: Dict[str, Any] = {}
        # if self.advice_tool and should_request_advice(user_message, rules):
        #     if hasattr(self.advice_tool, "build_improvement_bundle"):
        #         advice_data = self.advice_tool.build_improvement_bundle(
        #             best_gag, best_eval.to_dict(), profile.to_dict(), best_nat, best_orig
        #         )
        #     elif hasattr(self.advice_tool, "generate_advice"):
        #         advice_data = self.advice_tool.generate_advice(
        #             best_gag, best_eval.to_dict(), profile.to_dict(), rules
        #         )

        # return best_gag, best_eval, advice_data, best_source
        return best_gag, best_eval, {}, best_source

    @staticmethod
    def _resolve_rules(message: str, signals: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        intent_analysis = signals.get("intent_analysis", {})
        rules = (
            signals.get("gag_rules")
            or intent_analysis.get("gag_rules")
            or (analysis.get("gag_rules") if isinstance(analysis, dict) else None)
        )
        if isinstance(rules, dict) and rules:
            return dict(rules)
        return GagTool.extract_rules(message, message.lower()) if GagTool else {}


GagHandler = Gaghandler