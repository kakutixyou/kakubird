# api/services/handlers/GagHandler/generator.py
# -*- coding: utf-8 -*-
"""
generator.py

共有LLM基盤（generate_with_local_llm）の呼び出しと、
Ollama停止時でも指定単語・スタイル・文字数（20〜50文字）を満たす
複数テンプレートのルールベース合成器を提供する。
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, Optional, Tuple

from api.services.handlers.ChatHandler.llm_bridge import generate_with_local_llm

from .GagRuleEngine import GagRuleProfile

# 2語指定時でも意味が通じ、かつ目標出現回数（3回以上）と20〜50文字を満たすテンプレート群
TWO_WORD_TEMPLATES: Dict[str, list[str]] = {
    "shoten": [
        "「{w1}」とかけて「{w2}」と解く。どちらも{w1}の商談で{w2}の値段が高いと財布が痛いです！",
        "司会「{w1}と{w2}で一句」回答「{w1}がプルプルし、{w2}を買いたいけれど{w1}で財布が痛い！」",
    ],
    "manzai": [
        "「{w1}で{w2}を買いたい！」「いや{w1}の値段高いし{w2}で財布痛いよ！」「{w1}が空いたわ！」",
        "「{w1}がプルプルしてるぞ！」「それ{w2}やないかい！{w1}と{w2}の商談で胃が痛いわ！」",
    ],
    "general": [
        "解体される{w1}と{w2}を買いたい、{w1}の値段が高い、財布が痛い、{w2}のメモを書いた、予定が空いた！",
        "{w1}がプルプルしている{w2}で{w1}を買いたい！{w2}の値段が高いし、期待と不安で胃が痛い！",
        "{w1}の商談で{w2}の冗談を言ったら、{w1}の値段が高いと財布が痛い！予定が空いたし{w2}を食べたい！",
        "ルールでスルーされた{w1}と{w2}、クールに{w1}をループさせたら{w2}の予定が急に空いた！",
    ],
}

SINGLE_WORD_TEMPLATES: list[str] = [
    "{w}がプルプルしている{w}で、解体される{w}を買いたい！値段が高い、財布が痛い、予定が空いた！",
    "{w}の商談で{w}の冗談を言ったら、{w}の値段が高いと財布が痛い！桜が咲いたし予定が空いた！",
    "ルールでスルーされた{w}、プールでプルプルしている{w}を見たら、急に{w}を買いたい！",
]


def generate_gag_once(
    prompt: str,
    raw_user_message: str,
    profile: GagRuleProfile,
    rules: Dict[str, Any],
    local_llm: Any,
    fallback_generate: Optional[Callable[..., Optional[str]]],
    analysis: Dict[str, Any],
    state: Any,
    summary: Dict[str, Any],
    knowledge_data: Any,
    debug: Optional[Callable[[str], None]] = None,
) -> Tuple[str, str]:
    """
    1. local_llm があれば generate_with_local_llm (prompt_builder=None) で生成
    2. 失敗時は注入された fallback_generate を試行
    3. いずれも無ければ複数テンプレート合成（synthesize_fallback_gag）を返す
    """
    if local_llm is not None and callable(generate_with_local_llm):
        try:
            res = generate_with_local_llm(
                local_llm=local_llm,
                prompt_builder=None,  # 雑談用PromptBuilderとの二重ラップを防止
                user_message=prompt,
                analysis=analysis,
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
                debug=debug,
            )
            if res and str(res).strip():
                return str(res).strip(), "local_llm+gag"
        except Exception as exc:
            if debug:
                debug(f"generate_with_local_llm failed: {exc}")

    if callable(fallback_generate):
        try:
            res = fallback_generate(
                user_message=raw_user_message,
                analysis={"intent": "gag_request", **(analysis or {})},
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
            )
            if res and str(res).strip():
                return str(res).strip(), "fallback_llm+gag"
        except Exception as exc:
            if debug:
                debug(f"fallback_generate failed: {exc}")

    return synthesize_fallback_gag(profile, rules), "rule_engine_gag"


def synthesize_fallback_gag(profile: GagRuleProfile, rules: Dict[str, Any]) -> str:
    words = profile.target_words or rules.get("target_words") or ["階段", "商談"]
    style = getattr(profile, "style", None) or rules.get("style", "general")

    if len(words) >= 2:
        w1, w2 = words[0], words[1]
        bucket = "shoten" if style == "shoten" else "manzai" if "manzai" in style else "general"
        templates = TWO_WORD_TEMPLATES[bucket]
        return random.choice(templates).format(w1=w1, w2=w2)

    w = words[0] if words else "階段"
    return random.choice(SINGLE_WORD_TEMPLATES).format(w=w)