# backend/api/services/handlers/GagHandler/prompt_builder.py
# -*- coding: utf-8 -*-
"""
prompt_builder.py

- LLMに渡すプロンプトを自然な日本語ダジャレ向けに調整する
- 固定の文に縛られず、比較・反転・結論の流れを要求する
- 複数個生成モードにも対応する
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .GagRuleEngine import GagEvaluation, GagRuleProfile

STYLE_EXAMPLES: Dict[str, str] = {
    "dajare": "GitHub CopilotがPRを見たら、reviewのほうがbranchより先に落ち着く。merge後の気持ちも、issueより安定してる。",
    "shoten": "司会「PRとかけてreviewと解きます」回答「どちらもmerge前の心が揺れてるから、issueに落ち着くんです」",
    "manzai": "A「branchが長いね」B「そうだね、reviewも長いよ」A「じゃあ今日はmergeして、気持ちを短くしよう」",
    "general": "雨の会議で財布を見たら、コーヒーとPRが同時に落ち着いて、気分だけmergeしたかった。",
}

def build_gag_prompt(
    user_message: str,
    profile: GagRuleProfile,
    rules: Dict[str, Any],
    retry_feedback: Optional[str] = None,
) -> str:
    style_key = getattr(profile, "style", None) or rules.get("style", "general")
    style_label = rules.get("style_label", "リズム感のある高度な言葉遊び・ギャグ")
    count = max(1, int(rules.get("count", 1)))
    list_mode = bool(rules.get("list_mode", False))
    topic = str(rules.get("topic", "general"))

    target_words = profile.target_words or rules.get("target_words") or ["GitHub Copilot", "PR"]
    required_words = profile.required_words or []

    if list_mode and count > 1:
        list_line = (
            f"\n- {count}個のネタを、番号付きで出力してください。\n"
            "- 同じフレーズを繰り返さず、別の切り口にしてください。\n"
            "- 各ネタは文として成立させてください。\n"
            "- 技術語と日常語を混ぜると自然で笑える。\n"
            "- 1つ目から最後まで、比較・反転・結論の流れがあるようにしてください。\n"
        )
    else:
        list_line = (
            "\n- 1つだけのネタを出してください。\n"
            "- 同じ語彙を連続で使わない。\n"
            "- 文として成立させてください。\n"
            "- 技術語と生活の語彙を混ぜてください。\n"
            "- 比較・反転・結論が一文に入っていると自然です。\n"
        )

    word_rule = (
        f"お題語: {target_words}\n"
        "必ず文の中で意味が通るように使ってください。\n"
        "単語の羅列ではなく、主語・述語・比較・結論がある文にしてください。\n"
        "同じ単語を連続で使わないでください。\n"
        "技術語と生活語を混ぜて、言い回しを多様にしてください。\n"
    )

    req_line = f"\n- 必須単語: {required_words}" if required_words else ""
    feedback_section = f"\n\n{retry_feedback}" if retry_feedback else ""

    return f"""
あなたは日本語の言葉遊びに長けたコメディアンAIです。
以下の条件を厳密に守って、ネタ本文だけを出してください。

【テーマ】: {topic}
【スタイル】: {style_label}
【文字数】: {profile.min_characters or 20}文字以上、{profile.max_characters or 50}文字以内
{word_rule}{req_line}
{list_line}

- 同じ語句を連続させない
- 技術語と日常語を混ぜる
- 例: PR + 雨 + 財布 + 会議 + コーヒー
- 文として意味が通る
- 「比較」「反転」「結論」がある
- ただし、説明文ではなく、ネタ本文だけ
- ラベル、前置き、文字数書き込み、解説は不要

【参考例】
{STYLE_EXAMPLES.get(style_key, STYLE_EXAMPLES["general"])}

【ユーザー依頼】: {user_message}{feedback_section}
""".strip()

def build_retry_feedback(
    previous_text: str,
    ev: GagEvaluation,
    profile: GagRuleProfile,
    naturalness_score: float,
    advice_patch: str = "",
) -> str:
    """
    前回のダジャレの弱点を、明確に伝える。
    """
    reasons: List[str] = []

    if ev.missing_required_words:
        reasons.append(f"必須単語 {ev.missing_required_words} が抜けています。文中で自然に使ってください。")

    if profile.keyword_count_mode == "maximize" and ev.keyword_occurrences < 1:
        reasons.append("お題語が少ないです。比較や反転の中に自然に織り込んでください。")

    if naturalness_score < 50.0:
        reasons.append("言葉の連呼が多いです。主語・比較・結論を一文に入れてください。")

    if profile.min_characters and ev.character_count < profile.min_characters:
        reasons.append("短すぎます。比較の流れと結論を足してください。")

    if profile.max_characters and ev.character_count > profile.max_characters:
        reasons.append("長すぎます。余計な説明を削って、短い反転でまとめてください。")

    if advice_patch:
        reasons.append(advice_patch)

    return (
        f"【前回の出力（{ev.score}点）】: 「{previous_text}」\n"
        "【改善指示】: " + " ".join(reasons)
    )