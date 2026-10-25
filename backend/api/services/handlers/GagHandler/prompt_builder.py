# api/services/handlers/GagHandler/prompt_builder.py
# -*- coding: utf-8 -*-
"""
prompt_builder.py

GagRuleProfile とスタイル設定から、LLM用のギャグ生成プロンプトおよび
再生成時の具体的なダメ出しフィードバックを構築する。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .GagRuleEngine import GagEvaluation, GagRuleProfile

STYLE_EXAMPLES: Dict[str, str] = {
    "dajare": "解体される階段を買いたい、値段が高い、財布が痛い、商談のメモを書いた、桜が咲いた、予定が空いた！",
    "shoten": "司会「商談とかけて階段と解きます」回答「どちらも解体（買いたい）と願う人が多く、上るほど財布が痛いです」",
    "manzai": "A「プールがプルプルしてるぞ！」B「いや水面の波だろ！ルールでスルーすな！」",
    "manzai_3p": "A「階段買いたい！」B「値段高いし財布痛いよ！」C「いや商談のメモ書いたんかい！予定空いたわ！」",
    "manzai_solo": "階段を買いたい…って誰が解体屋やねん！値段が高い、財布が痛い、でも予定が空いたから買っちゃおう！",
    "general": "商談で冗談交じりの大展開、期待と不安で胃が痛い。予定が空いたし、美味い鯛でも食べたい！",
}


def build_gag_prompt(
    user_message: str,
    profile: GagRuleProfile,
    rules: Dict[str, Any],
    retry_feedback: Optional[str] = None,
) -> str:
    style_key = getattr(profile, "style", None) or rules.get("style", "general")
    style_label = rules.get("style_label", "リズム感のある高度な言葉遊び・ギャグ")
    example = STYLE_EXAMPLES.get(style_key, STYLE_EXAMPLES["general"])

    min_chars = profile.min_characters or 20
    max_chars = profile.max_characters or 50
    target_words = profile.target_words
    required_words = profile.required_words
    target_occ = profile.target_occurrences

    if profile.keyword_count_mode == "minimize":
        word_rule = (
            f"対象単語 {target_words} の使用回数を最小限（0〜1回）に抑えつつ、文脈の妙で笑わせてください。"
        )
    else:
        word_rule = (
            f"お題単語 {target_words} を合計 {target_occ}回以上 文章中に登場させてください。\n"
            "   「× プルプルしたプール → 〇 プールがプルプルしている」のように、"
            "少し強引でも助詞（が・を・に・で）を挟んで主語・述語のある文にねじ込んでください。"
        )

    req_line = f"\n- 必須単語（欠けると大幅減点）: {required_words}" if required_words else ""
    feedback_section = f"\n\n{retry_feedback}" if retry_feedback else ""

    return f"""
あなたは言葉遊びとリズム感に優れたプロのコメディアンAIです。
以下の条件を守り、最高密度のネタを1つだけ作成してください。

【スタイル】: {style_label}
【文字数制限】: {min_chars}文字以上、{max_chars}文字以内（制限ギリギリを狙うこと）
【採点ルール】:
- {word_rule}{req_line}
- 単語の直列連呼（例：「プールプールプール」）は0点になります。必ず助詞を挟んで文にしてください。
- 同じ母音・韻を踏む語彙をテンポよく連鎖させてください。

【高評価のお手本】:
{example}

【ユーザーの依頼】: {user_message}{feedback_section}
※解説や前置き、文字数カウント（「（48文字）」等）は一切出力せず、ネタの本文のみを1段落で出力してください。
""".strip()


def build_retry_feedback(
    previous_text: str,
    ev: GagEvaluation,
    profile: GagRuleProfile,
    naturalness_score: float,
    advice_patch: str = "",
) -> str:
    """再生成時にプロンプトへ追加する具体的なダメ出し指示。"""
    reasons: List[str] = []
    target_occ = profile.target_occurrences if profile.target_occurrences is not None else 1

    if ev.missing_required_words:
        reasons.append(f"必須単語 {ev.missing_required_words} が抜けています。必ず文頭に入れてください。")

    if profile.keyword_count_mode == "maximize" and ev.keyword_occurrences < target_occ:
        reasons.append(
            f"前回はお題単語 {profile.target_words} が {ev.keyword_occurrences}回 しか使えませんでした。"
            f"目標の {target_occ}回以上 になるよう、修飾語や目的語にも追加してください。"
        )
    elif profile.keyword_count_mode == "minimize" and ev.keyword_occurrences > 1:
        reasons.append(
            f"前回はお題単語を {ev.keyword_occurrences}回 使ってしまいました。0〜1回に減らしてください。"
        )

    if profile.min_characters and ev.character_count < profile.min_characters:
        diff = profile.min_characters - ev.character_count
        reasons.append(f"文字数が {diff}文字 足りません。韻を踏むフレーズを足して伸ばしてください。")
    elif profile.max_characters and ev.character_count > profile.max_characters:
        diff = ev.character_count - profile.max_characters
        reasons.append(f"文字数が {diff}文字 超過しています。余分な接続詞を削って短くしてください。")

    if naturalness_score < 50.0:
        reasons.append("単語の単純連呼が検出されました。助詞を挟んで自然な文脈にしてください。")

    if advice_patch:
        reasons.append(advice_patch)

    return f"【前回の出力（{ev.score}点）】: 「{previous_text}」\n【改善指示】: " + " ".join(reasons)