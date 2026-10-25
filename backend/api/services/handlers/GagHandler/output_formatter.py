# api/services/handlers/GagHandler/output_formatter.py
# -*- coding: utf-8 -*-
"""
output_formatter.py

ユーザーへの返却テキストを整形する。
原則としてネタ本文には内部スコアを混ぜず、ユーザーが要求した時のみ末尾に付与する。
"""

from __future__ import annotations

from typing import Any, Dict

from .GagRuleEngine import GagEvaluation, GagRuleProfile


def should_request_advice(user_message: str, rules: Dict[str, Any]) -> bool:
    return bool(
        rules.get("show_advice")
        or any(w in user_message for w in ("アドバイス", "講評", "コメント", "ダメ出し", "改善"))
    )


def should_show_score(user_message: str, rules: Dict[str, Any]) -> bool:
    return bool(
        rules.get("show_score")
        or any(w in user_message for w in ("点数", "スコア", "採点", "評価", "何点"))
    )


def format_gag_output(
    gag_text: str,
    evaluation: GagEvaluation,
    profile: GagRuleProfile,
    advice_data: Dict[str, Any],
    user_message: str,
    rules: Dict[str, Any],
) -> str:
    blocks = [gag_text]

    if should_show_score(user_message, rules):
        words_label = "・".join(profile.target_words) if profile.target_words else "なし"
        blocks.append(
            f"📊 【採点】 {evaluation.score}点 "
            f"（{evaluation.character_count}文字 / お題『{words_label}』使用: {evaluation.keyword_occurrences}回）"
        )

    if should_request_advice(user_message, rules) and advice_data.get("comment"):
        blocks.append(f"💡 【裏方Geminiのアドバイス】\n{advice_data['comment']}")

    return "\n\n".join(blocks)