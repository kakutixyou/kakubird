# backend/api/services/handlers/GagHandler/GagHandler.py
# -*- coding: utf-8 -*-
"""
GagHandler.py

- 複数個生成モード（GagTool不在時でも「10個」「5つ」等を確実に検出）
- 繰り返し回数（repeat_count）・最低使用回数（minimum_use）対応
- 類義語ヒント（synonym_hint）・新しいネタ要求（fresh_topic）対応
- バッチ生成時のネタ被り防止（running_past_gags による動的除外）
- お題未指定の複数生成時でも多彩なワードを自動ローテーション
"""

from __future__ import annotations

import asyncio
import copy
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

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
from .generator import DEFAULT_WORD_BANK, generate_gag_once, synthesize_fallback_gag
from .output_formatter import format_gag_output
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

logger = logging.getLogger(__name__)

_GAG_KEYWORDS = (
    "ダジャレ", "だじゃれ", "ギャグ", "漫才", "笑点",
    "ボケ", "笑わせて", "面白いこと", "ネタ", "親父ギャグ", "オヤジギャグ"
)


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
    ) -> None:
        super().__init__()
        self.enable_debug = enable_debug
        self.fallback_generate = fallback_generate
        self.prompt_builder = prompt_builder or _try_init(optional_deps.PromptBuilder, "PromptBuilder")
        self.local_llm = local_llm or _try_init(optional_deps.LocalLLMEngine, "LocalLLMEngine")
        self.rule_engine = rule_engine or GagRuleEngine()
        self.results = ResultBuilder(debug=self._debug, enable_debug=self.enable_debug)

    def _debug(self, message: str) -> None:
        logger.debug("[%s] %s", self.HANDLER_NAME, message)
        if self.enable_debug:
            print(f"🤡 [{self.HANDLER_NAME}] {message}", flush=True)

    async def calculate_score(self, message: str, current_signals: Optional[Dict[str, Any]] = None) -> int:
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

        msg_str = str(message or "")
        if GagTool is not None:
            try:
                is_match, _ = GagTool.can_fast_route(msg_str, msg_str.lower(), {}, {})
                if is_match:
                    return self.DEFAULT_SCORE
            except Exception as exc:
                logger.warning("GagTool.can_fast_route failed: %s", exc)

        # GagTool がインポートできない場合でもキーワードで確実にキャッチする
        if any(kw in msg_str for kw in _GAG_KEYWORDS):
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

        # ルール抽出（GagTool + フォールバック正規表現のハイブリッド）
        rules = self._resolve_rules(message, current_signals, analysis)
        prev_profile = load_profile(state)
        past_gags = load_gag_history(state)
        history_texts = load_user_history_texts(state)

        # profile 生成
        profile = self.rule_engine.create_profile_from_rules(
            rules=rules,
            previous=prev_profile,
            history_texts=history_texts,
        )

        if profile is None:
            logger.warning("Gag profile creation failed; fallback default profile used")
            profile = GagRuleProfile()

        # count / repeat / synonym / minimum_use / fresh_topic を読む
        list_count = max(1, int(rules.get("count", 1)))
        list_mode = bool(rules.get("list_mode", False)) or list_count > 1
        repeat_count = max(1, int(rules.get("repeat_count", 1)))
        minimum_use = max(0, int(rules.get("minimum_use", 0)))
        synonym_hint = bool(rules.get("synonym_hint", False))
        fresh_topic = bool(rules.get("fresh_topic", False))

        # 1. list_mode（複数個生成：「ダジャレを10個考えて」など）
        if list_mode and list_count > 1:
            batch_result = await asyncio.to_thread(
                self._run_generation_batch,
                message,
                rules,
                profile,
                past_gags,
                analysis,
                state,
                summary,
                knowledge_data,
                list_count,
                repeat_count,
                minimum_use,
                synonym_hint,
                fresh_topic,
            )

            gags, best_eval, advice_data, source = batch_result
            final_text = format_gag_output(gags, best_eval, profile, advice_data, message, rules)

            # 生成したすべてのダジャレを履歴に記録して次回以降の被りを防ぐ
            for g in gags:
                save_turn_data(state, profile, g, best_eval.score if best_eval else 0.0)

            state.add_user_message(content=message, intent="gag_request", topic="お笑い")
            state.add_assistant_message(content=final_text, source=source, intent="gag_request", topic="お笑い")

            return self.results.finalize(
                message=final_text,
                source=source,
                state=state,
                current_signals=current_signals,
                extra={
                    "intent": "gag_request",
                    "gag_score": best_eval.score if best_eval else 0.0,
                    "gag_evaluation": best_eval.to_dict() if best_eval else {},
                    "gag_profile": profile.to_dict(),
                    "gemini_advice": advice_data,
                    "gag_list_count": len(gags),
                    "repeat_count": repeat_count,
                    "minimum_use": minimum_use,
                    "synonym_hint": synonym_hint,
                },
            )

        # 2. 単発生成（1個をじっくりリトライして最高得点を狙う）
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
            repeat_count,
            minimum_use,
            synonym_hint,
            fresh_topic,
        )

        if best_eval is None:
            best_eval = GagEvaluation(
                score=0.0,
                keyword_score=0.0,
                keyword_occurrences=0,
                matched_required_words=[],
                missing_required_words=[],
                character_count=0,
                rule_mode=profile.keyword_count_mode,
            )

        save_turn_data(state, profile, best_gag, best_eval.score)
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
                "repeat_count": repeat_count,
                "minimum_use": minimum_use,
                "synonym_hint": synonym_hint,
            },
        )

    def _run_generation_batch(
        self,
        user_message: str,
        rules: Dict[str, Any],
        profile: GagRuleProfile,
        past_gags: List[str],
        analysis: Dict[str, Any],
        state: Any,
        summary: Dict[str, Any],
        knowledge_data: Any,
        count: int,
        repeat_count: int,
        minimum_use: int,
        synonym_hint: bool,
        fresh_topic: bool,
    ) -> Tuple[List[str], GagEvaluation, Dict[str, Any], str]:
        generated: List[str] = []
        best_eval: Optional[GagEvaluation] = None
        best_source = "rule_engine_gag"

        # 今回生成したネタも逐次追加して、バッチ内の重複を100%防ぐリスト
        running_past_gags: List[str] = list(past_gags or [])

        # ユーザー指定のお題があれば使い、無ければ DEFAULT_WORD_BANK 全体をローテーションする
        user_words = [
            w for w in (profile.target_words or rules.get("target_words") or [])
            if w and w != "（自由なお題）"
        ]
        word_pool = list(user_words) if user_words else list(DEFAULT_WORD_BANK)

        # generate_gag_once 側で「10個」と二重解釈されないよう、単発要求メッセージに正規化
        single_req_message = re.sub(r"\d+\s*(?:個|つ|連発|本|件|発)", "1個", user_message)

        for idx in range(max(1, count)):
            target_word = word_pool[idx % len(word_pool)]
            secondary_word = word_pool[(idx + 1) % len(word_pool)] if len(word_pool) > 1 else "PR"

            sub_rules = dict(rules)
            sub_rules["count"] = 1
            sub_rules["list_mode"] = False
            sub_rules["reroll"] = True
            sub_rules["repeat_count"] = repeat_count
            sub_rules["minimum_use"] = minimum_use
            sub_rules["synonym_hint"] = synonym_hint
            sub_rules["fresh_topic"] = fresh_topic
            sub_rules["target_words"] = [target_word, secondary_word]
            sub_rules["past_gags"] = running_past_gags

            # 採点器（evaluate_candidate）が target_word の出現回数（occ）を正しくカウントできるよう、
            # サブプロファイルにも今回のお題ワードをセットする
            sub_profile = copy.deepcopy(profile)
            if not getattr(sub_profile, "target_words", None):
                sub_profile.target_words = [target_word]

            try:
                prompt = build_gag_prompt(single_req_message, sub_profile, sub_rules, retry_feedback=None)
            except Exception as exc:
                logger.warning("build_gag_prompt in batch failed: %s", exc)
                prompt = ""

            raw_text, source = generate_gag_once(
                prompt=prompt,
                raw_user_message=single_req_message,
                profile=sub_profile,
                rules=sub_rules,
                local_llm=self.local_llm,
                fallback_generate=self.fallback_generate,
                analysis=analysis,
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
                debug=self._debug,
            )

            cleaned = clean_generated_text(raw_text) or synthesize_fallback_gag(sub_profile, sub_rules)
            ev, _, _ = evaluate_candidate(self.rule_engine, cleaned, sub_profile, running_past_gags)

            self._debug(
                f"Batch[{idx + 1}/{count}] ({target_word}): score={ev.score}, occ={ev.keyword_occurrences}, chars={ev.character_count}"
            )

            if best_eval is None or ev.score > best_eval.score:
                best_eval = ev
                best_source = source

            generated.append(cleaned)
            running_past_gags.append(cleaned)

        if best_eval is None:
            best_eval = GagEvaluation(
                score=0.0,
                keyword_score=0.0,
                keyword_occurrences=0,
                matched_required_words=[],
                missing_required_words=[],
                character_count=0,
                rule_mode=profile.keyword_count_mode,
            )

        return generated[:count], best_eval, {}, best_source

    def _run_generation_loop(
        self,
        user_message: str,
        rules: Dict[str, Any],
        profile: GagRuleProfile,
        past_gags: List[str],
        analysis: Dict[str, Any],
        state: Any,
        summary: Dict[str, Any],
        knowledge_data: Any,
        repeat_count: int,
        minimum_use: int,
        synonym_hint: bool,
        fresh_topic: bool,
    ) -> Tuple[str, GagEvaluation, Dict[str, Any], str]:
        best_gag = ""
        best_eval: Optional[GagEvaluation] = None
        best_source = "rule_engine_gag"
        retry_feedback: Optional[str] = None
        running_past_gags: List[str] = list(past_gags or [])

        # お題が完全に空だと occ=0 でスコアが17点前後になるため、最低1つはターゲットを設定
        active_profile = copy.deepcopy(profile)
        if not getattr(active_profile, "target_words", None):
            rule_words = rules.get("target_words") or []
            if rule_words:
                active_profile.target_words = list(rule_words)
            else:
                active_profile.target_words = [DEFAULT_WORD_BANK[0]]

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            loop_rules = dict(rules)
            loop_rules["past_gags"] = running_past_gags
            if not loop_rules.get("target_words"):
                loop_rules["target_words"] = list(active_profile.target_words)

            try:
                prompt = build_gag_prompt(user_message, active_profile, loop_rules, retry_feedback)
            except Exception as exc:
                logger.warning("build_gag_prompt failed: %s", exc)
                prompt = ""

            raw_text, source = generate_gag_once(
                prompt=prompt,
                raw_user_message=user_message,
                profile=active_profile,
                rules=loop_rules,
                local_llm=self.local_llm,
                fallback_generate=self.fallback_generate,
                analysis=analysis,
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
                debug=self._debug,
            )

            cleaned = clean_generated_text(raw_text) or synthesize_fallback_gag(active_profile, loop_rules)
            ev, nat_score, orig_score = evaluate_candidate(
                self.rule_engine, cleaned, active_profile, running_past_gags
            )

            self._debug(
                f"Attempt {attempt}: score={ev.score}, occ={ev.keyword_occurrences}, chars={ev.character_count}"
            )

            running_past_gags.append(cleaned)

            if best_eval is None or ev.score > best_eval.score:
                best_gag = cleaned
                best_eval = ev
                best_source = source

            in_range = (
                (active_profile.min_characters is None or ev.character_count >= active_profile.min_characters)
                and (active_profile.max_characters is None or ev.character_count <= active_profile.max_characters)
            )

            meets_repeat = (repeat_count <= 1) or (ev.keyword_occurrences >= repeat_count)
            meets_minimum = (minimum_use <= 0) or (ev.keyword_occurrences >= minimum_use)

            if (
                ev.score >= self.PASSING_SCORE
                and not ev.missing_required_words
                and in_range
                and meets_repeat
                and meets_minimum
            ):
                break

            retry_feedback = build_retry_feedback(cleaned, ev, active_profile, nat_score)
            if attempt >= self.MAX_ATTEMPTS:
                break

        if best_eval is None:
            fallback = synthesize_fallback_gag(active_profile, rules)
            best_gag = fallback
            best_eval = GagEvaluation(
                score=60.0,
                keyword_score=0.0,
                keyword_occurrences=0,
                matched_required_words=[],
                missing_required_words=[],
                character_count=len(fallback),
                rule_mode=active_profile.keyword_count_mode,
            )
            best_source = "rule_engine_gag"

        return best_gag, best_eval, {}, best_source

    @classmethod
    def _resolve_rules(cls, message: str, signals: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        intent_analysis = signals.get("intent_analysis", {}) if isinstance(signals, dict) else {}
        rules: Dict[str, Any] = {}

        if isinstance(signals, dict) and isinstance(signals.get("gag_rules"), dict):
            rules.update(signals["gag_rules"])
        elif isinstance(intent_analysis, dict) and isinstance(intent_analysis.get("gag_rules"), dict):
            rules.update(intent_analysis["gag_rules"])
        elif isinstance(analysis, dict) and isinstance(analysis.get("gag_rules"), dict):
            rules.update(analysis["gag_rules"])

        if not rules and GagTool is not None:
            try:
                extracted = GagTool.extract_rules(message, message.lower())
                if isinstance(extracted, dict):
                    rules.update(extracted)
            except Exception as exc:
                logger.warning("GagTool.extract_rules failed: %s", exc)

        # GagTool が無い・または取りこぼした場合でも、「10個」や「お題」を確実に補完する
        fallback_rules = cls._extract_fallback_rules(message)
        for k, v in fallback_rules.items():
            if k not in rules or rules[k] in (None, "", [], 1, False):
                rules[k] = v

        return rules

    @staticmethod
    def _extract_fallback_rules(message: str) -> Dict[str, Any]:
        """メッセージから個数・繰り返し回数・お題ワードを抽出する安全装置。"""
        msg = str(message or "")
        out: Dict[str, Any] = {}

        # 1. 個数抽出（例：「10個」「5つ」「3連発」）
        m_count = re.search(r"(\d+)\s*(?:個|つ|連発|本|件|発)", msg)
        if m_count:
            cnt = max(1, min(int(m_count.group(1)), 15))
            out["count"] = cnt
            out["list_mode"] = cnt > 1

        # 2. 繰り返し回数抽出（例：「2回使って」「3回繰り返して」）
        m_rep = re.search(r"(\d+)\s*(?:回|度)", msg)
        if m_rep:
            rep = max(1, min(int(m_rep.group(1)), 5))
            out["repeat_count"] = rep
            out["minimum_use"] = rep

        # 3. 既知のお題ワードが含まれていれば抽出
        matched_words = [w for w in DEFAULT_WORD_BANK if w in msg]

        # 「『〇〇』でダジャレ」「「〇〇」を使ったダジャレ」のようなカギ括弧指定も抽出
        bracket_words = re.findall(r"[「『](.+?)[」』]", msg)
        for bw in bracket_words:
            bw_clean = bw.strip()
            if bw_clean and bw_clean not in matched_words:
                matched_words.insert(0, bw_clean)

        if matched_words:
            out["target_words"] = matched_words

        # 4. 新ネタ要求判定
        if any(w in msg for w in ("新しい", "別の", "他の", "聞いたことがない", "被らない")):
            out["fresh_topic"] = True
            out["reroll"] = True

        return out


GagHandler = Gaghandler