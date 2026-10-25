# api/services/handlers/GagHandler/evaluation.py
# -*- coding: utf-8 -*-
"""
evaluation.py

LLM出力のクリーニング、自然さ（Naturalness）・独創性（Originality）の決定論的計算、
および GagRuleEngine を用いた一括採点を行う純粋関数モジュール。
"""

from __future__ import annotations

import difflib
import re
from typing import List, Tuple

from .GagRuleEngine import GagEvaluation, GagRuleEngine, GagRuleProfile


def clean_generated_text(text: str) -> str:
    """
    LLM出力から不要な前置き、2段落目以降の解説、末尾の文字数カウント表記を除去する。
    """
    raw = (text or "").strip()
    if not raw:
        return ""

    # 1. 空行で区切られた最初の段落のみを採用（後半の自己解説や「※48文字です」等を切り捨てる）
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    first_para = paragraphs[0] if paragraphs else raw

    # 2. 先頭の「ネタ:」「回答：」等のラベルを除去
    cleaned = re.sub(
        r"^(?:ネタ|回答|生成結果|本文|ギャグ|ダジャレ|漫才)\s*[:：]\s*",
        "",
        first_para,
        flags=re.IGNORECASE,
    ).strip()

    # 3. 末尾の「（48文字）」「(32字)」「【45文字】」等のメタ表記を除去
    cleaned = re.sub(
        r"\s*[（(\[【]\s*\d+\s*(?:文字|字|chars?)\s*[^）)\]】]*[）)\]】]\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # 4. 外側のカギ括弧を剥がす（漫才の「A「…」B「…」」は壊さないよう全体囲みのみ）
    if (
        len(cleaned) >= 2
        and cleaned[0] in "「『"
        and cleaned[-1] in "」』"
        and cleaned[1:-1].count(cleaned[0]) == 0
    ):
        cleaned = cleaned[1:-1].strip()

    return cleaned


def calculate_naturalness(text: str, profile: GagRuleProfile) -> float:
    """
    決定論的に文の自然さ（0〜100）を近似する。
    - お題単語の直列連呼（「プールプール」等）を大きく減点
    - 同一2〜4文字の3連続リピートを減点
    - dajare スタイル時は短い体言止めを許容するため助詞チェックを緩和
    """
    if not text:
        return 0.0

    score = 85.0

    # 1. お題単語の直列連呼チェック
    for w in profile.target_words:
        if not w:
            continue
        if f"{w}{w}" in text or re.search(rf"{re.escape(w)}[、,\s]+{re.escape(w)}", text):
            score -= 45.0

    # 2. 同一2〜4文字の3回以上連続リピート（例: 「プルプルプル」）
    if re.search(r"(.{2,4})\1{2,}", text):
        score -= 40.0

    # 3. 助詞の有無チェック（style == "dajare" の場合は1つあればOK、それ以外は2つ以上）
    particles = re.findall(r"[がのをにへとではも]", text)
    min_particles = 1 if getattr(profile, "style", "general") == "dajare" else 2
    if len(particles) < min_particles:
        score -= 25.0

    # 4. 文末の成立チェック（句読点・感嘆符・終助詞・体言止め等）
    if len(text) < 6:
        score -= 30.0

    return max(0.0, min(100.0, score))


def calculate_originality(text: str, past_gags: List[str]) -> float:
    """
    過去の純粋なネタ本文リスト（past_gags）との文字列類似度から独創性（0〜100）を計算する。
    """
    if not text:
        return 0.0
    if not past_gags:
        return 85.0

    max_sim = max(
        (difflib.SequenceMatcher(None, text, past).ratio() for past in past_gags if past),
        default=0.0,
    )
    return round(max(0.0, min(100.0, 95.0 * (1.0 - max_sim))), 2)


def evaluate_candidate(
    engine: GagRuleEngine,
    text: str,
    profile: GagRuleProfile,
    past_gags: List[str],
) -> Tuple[GagEvaluation, float, float]:
    """
    自然さ・独創性を算出した上で GagRuleEngine.evaluate() を呼び出す統合ヘルパー。
    """
    nat_score = calculate_naturalness(text, profile)
    orig_score = calculate_originality(text, past_gags)
    ev = engine.evaluate(
        gag=text,
        profile=profile,
        naturalness_score=nat_score,
        originality_score=orig_score,
    )
    return ev, nat_score, orig_score