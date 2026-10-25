#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tools/gag/gag_tool.py
"""
GagTool

IntentInspector の Tool Fast-Routing から呼び出されるギャグ・大喜利・漫才判定プラグイン。
日本語の表記ゆれ（「おもしろい話をして」「他のネタを披露して」等）および
英語表現（"tell me a joke", "make me laugh", "pun" 等）の両方を高速判定し、
文字数制限・スタイル・お題単語・採点モードなどのルールを context["gag_rules"] に格納する。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Engine 側からも共通参照できるストップワード（日英対応）
GAG_STOP_WORDS: set[str] = {
    # 日本語
    "ギャグ", "ダジャレ", "だじゃれ", "駄洒落", "漫才", "笑点", "大喜利",
    "ボケ", "ネタ", "お題", "単語", "対象単語", "指定単語", "文字", "文字数",
    "設定", "ルール", "評価", "スコア", "点数", "採点", "アドバイス", "講評",
    "お願い", "作成", "生成", "たくさん", "最小限", "自然", "独創性", "意外性",
    "コント", "なぞかけ", "おもしろい話", "面白い話", "面白いこと", "おもしろいこと",
    "前回", "さっき", "同じ", "もう一回", "もう1回", "他のネタ", "別のネタ",
    # 英語
    "joke", "jokes", "gag", "gags", "pun", "puns", "comedy", "funny",
    "laugh", "manzai", "shoten", "ogiri", "word", "words", "topic",
    "theme", "char", "chars", "characters", "score", "advice",
}


class GagTool:
    """
    IntentInspector._run_tool_detector() から以下のシグネチャで呼び出される:
        is_match, reason = tool_cls.can_fast_route(
            self.message, self.msg_lower, _INSPECTOR_CACHE, context
        )
        lang = tool_cls.detect_language(
            self.message, self.msg_lower, _INSPECTOR_CACHE
        )
    """

    # --------------------------------------------------------
    # 1. スラッシュコマンド定義（日英共通）
    # --------------------------------------------------------
    SLASH_COMMANDS: Tuple[str, ...] = (
        "/gag",
        "/dajare",
        "/manzai",
        "/shoten",
        "/ogiri",
        "/joke",
        "/pun",
    )

    # --------------------------------------------------------
    # 2. 日本語キーワード & フレキシブル正規表現
    # --------------------------------------------------------
    GAG_KEYWORDS_JA: Tuple[str, ...] = (
        "ギャグ",
        "ダジャレ",
        "だじゃれ",
        "駄洒落",
        "漫才",
        "笑点",
        "大喜利",
        "ボケて",
        "ボケを",
        "笑わせて",
        "コント",
        "なぞかけ",
        "韻を踏",
        "一発芸",
    )

    # 「おもしろい話をして」「面白いことを言って」「他のネタを披露してほしい」等を網羅する正規表現
    JP_PHRASE_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(
            r"(?:面白い|おもしろい|オモロイ|おもろい|笑える|ウケる|うける)"
            r"(?:話|はなし|こと|事|ネタ|やつ)(?:を|でも|とか)?(?:して|言って|いって|話して|喋って|聞かせて|教えて|披露して|頼む|お願い)?"
        ),
        re.compile(
            r"(?:他の|別の|新しい|何か|なんか)?(?:ネタ|ギャグ|ダジャレ|だじゃれ|ボケ|漫才|ジョーク)"
            r"(?:を|でも|とか)?(?:言って|いって|話して|喋って|して|披露|見せて|聞かせて|やって|作って|出して|ちょうだい|お願い)"
        ),
        re.compile(r"(?:笑わせて|わらわせて|クスッとさせて|爆笑させて)"),
    )

    # --------------------------------------------------------
    # 3. 英語キーワード & フレーズ正規表現
    # --------------------------------------------------------
    EN_PHRASE_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(
            r"\b(?:tell|give|say|share|make|crack|drop|hear)\b.*"
            r"\b(?:joke|jokes|gag|gags|pun|puns|wordplay|dajare|manzai|shoten|ogiri|one-liner|dad\s+joke)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:make\s+me\s+laugh|say\s+something\s+funny|tell\s+me\s+something\s+funny|"
            r"funny\s+story|funny\s+joke|dad\s+joke|stand-?up\s+comedy|another\s+joke|more\s+jokes)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?:joke|pun|gag|dajare|manzai|shoten|ogiri)\s*(?:please|pls|me|time)?[!?.]*$",
            re.IGNORECASE,
        ),
    )

    # --------------------------------------------------------
    # 4. 開発・コード相談の除外フレーズ（「クラス」「エラー」単体の誤爆を防止）
    # --------------------------------------------------------
    CODE_OR_DEV_EXCLUSIONS: Tuple[str, ...] = (
        ".py",
        ".json",
        ".ts",
        ".js",
        "実装して",
        "コードを書",
        "スクリプトを書",
        "関数を作",
        "クラスを作",
        "バグを直",
        "エラーを直",
        "ファイルを修正",
        "intentinspector",
        "chatorchestrator",
        "gaghandler",
        "gagruleengine",
        "write code",
        "implement",
        "fix the bug",
        "refactor",
    )

    # 「前回のお題を維持する（再抽選しない）」フレーズ（日英対応）
    REROLL_FALSE_PHRASES: Tuple[str, ...] = (
        "もう一回",
        "もう1回",
        "もう一度",
        "同じお題",
        "前回のお題",
        "さっきのお題",
        "そのまま",
        "もっと短く",
        "もっと長く",
        "やり直し",
        "same topic",
        "same word",
        "try again",
        "one more time with the same",
        "make it shorter",
        "make it longer",
    )

    # 後方互換性のためのクラス属性エイリアス
    STOP_WORDS: set[str] = GAG_STOP_WORDS

    # ========================================================
    # Main Fast-Route Entry
    # ========================================================

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        ギャグ要求かどうかを判定し、(is_match, reason) を返す。
        抽出したルールは context["gag_rules"] に格納する。
        """
        raw_msg = str(message or "").strip()
        lower_msg = str(msg_lower or raw_msg.lower()).strip()

        if not raw_msg:
            return False, ""

        # 1. コードブロックが含まれている場合は除外
        if isinstance(context, dict) and (context.get("is_code") or context.get("has_html")):
            return False, ""

        # 2. スラッシュコマンドの厳密判定（/gagxyz への誤爆を防ぐ）
        cmd_trigger = cls._match_slash_command(lower_msg)

        # スラッシュコマンドでない場合、システム開発・実装の相談なら除外
        if not cmd_trigger and any(dev_kw in lower_msg for dev_kw in cls.CODE_OR_DEV_EXCLUSIONS):
            return False, ""

        # 3. トリガー判定（コマンド or 日本語表現 or 英語表現 or ルール直接宣言）
        matched_trigger = cmd_trigger or cls._detect_trigger(raw_msg, lower_msg)
        if not matched_trigger:
            return False, ""

        # 4. ルール・制約（文字数・スタイル・お題・採点方式・言語）の抽出
        extracted_rules = cls.extract_rules(raw_msg, lower_msg)

        # IntentInspector の context 辞書へ格納
        if isinstance(context, dict):
            context["gag_rules"] = extracted_rules

        style = extracted_rules.get("style", "general")
        min_c = extracted_rules.get("length_min", 20)
        max_c = extracted_rules.get("length_max", 50)
        lang = extracted_rules.get("language", "ja")
        words = extracted_rules.get("target_words", [])
        word_info = f", words={words}" if words else ", words=random(60/40)"

        reason_str = (
            f"gag_fast_route(trigger={matched_trigger}, lang={lang}, "
            f"style={style}, len={min_c}-{max_c}{word_info})"
        )

        return True, reason_str

    @classmethod
    def detect_language(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
    ) -> Optional[str]:
        """
        発話が英語メインか日本語メインかを判定して返す。
        """
        raw_msg = str(message or "").strip()
        if not raw_msg:
            return None
        # ひらがな・カタカナ・漢字が含まれていれば "ja"、英字のみで構成されていれば "en"
        if re.search(r"[ぁ-んァ-ヶ一-龥]", raw_msg):
            return "ja"
        if re.search(r"[a-zA-Z]{2,}", raw_msg):
            return "en"
        return None

    # ========================================================
    # Trigger & Rule Extraction Helpers
    # ========================================================

    @classmethod
    def _match_slash_command(cls, lower_msg: str) -> Optional[str]:
        for cmd in cls.SLASH_COMMANDS:
            if re.match(rf"^{re.escape(cmd)}(?:\s|$)", lower_msg):
                return f"command:{cmd}"
        return None

    @classmethod
    def _detect_trigger(cls, raw_msg: str, lower_msg: str) -> Optional[str]:
        """どのトリガー（日本語・英語・ルール宣言）にヒットしたかを返す。"""
        # 1. 日本語固定キーワード
        for kw in cls.GAG_KEYWORDS_JA:
            if kw.lower() in lower_msg:
                return f"keyword_ja:{kw}"

        # 2. 日本語フレキシブル表現（「おもしろい話をして」「他のネタを披露して」等）
        for pat in cls.JP_PHRASE_PATTERNS:
            m = pat.search(raw_msg)
            if m:
                return f"phrase_ja:{m.group(0)}"

        # 3. 英語フレーズ表現（"tell me a joke", "make me laugh", "funny story" 等）
        for pat in cls.EN_PHRASE_PATTERNS:
            m = pat.search(lower_msg)
            if m:
                return f"phrase_en:{m.group(0)}"

        # 4. 「お題は〇〇で20〜50文字」等のルール直接宣言（日英）
        if re.search(r"(?:お題|対象単語|指定単語|topic|target\s+words?)\s*(?:は|を|：|:|=)", raw_msg, re.I) and (
            any(w in lower_msg for w in ("文字", "単語", "char", "word"))
        ):
            return "rule_declaration"

        return None

    @classmethod
    def extract_rules(cls, raw_msg: str, lower_msg: Optional[str] = None) -> Dict[str, Any]:
        """
        ユーザーメッセージ（日本語・英語）からギャグ生成・採点用のパラメータを抽出する。
        """
        lower_msg = lower_msg if lower_msg is not None else raw_msg.lower()
        rules: Dict[str, Any] = {}

        # 0. 言語判定
        lang = cls.detect_language(raw_msg, lower_msg, {}) or "ja"
        rules["language"] = lang

        # ----------------------------------------------------
        # 1. 文字数制限の抽出（バグ修正済み + 英語対応）
        #    例: "20〜50文字", "20から50文字", "20 to 50 chars", "under 40 characters"
        # ----------------------------------------------------
        range_match = re.search(
            r"(\d+)\s*(?:〜|~|\-|ー|から|to)\s*(\d+)\s*(?:文字|字|chars?|characters?|words?)",
            raw_msg,
             flags=re.IGNORECASE,
        )
        if range_match:
            min_len = int(range_match.group(1))
            max_len = int(range_match.group(2))
            if min_len > max_len:
                min_len, max_len = max_len, min_len
            rules["length_min"] = min_len
            rules["length_max"] = max_len
        else:
            max_match = re.search(
                r"(?:(\d+)\s*(?:文字|字|chars?|characters?)\s*(?:以内|以下|まで)|"
                r"(?:under|max|within|up\s+to)\s*(\d+)\s*(?:chars?|characters?|words?))",
                raw_msg,
                flags=re.IGNORECASE,
            )
            min_match = re.search(
                r"(?:(\d+)\s*(?:文字|字|chars?|characters?)\s*(?:以上|から)|"
                r"(?:over|min|at\s+least)\s*(\d+)\s*(?:chars?|characters?|words?))",
                raw_msg,
                flags=re.IGNORECASE,
            )
            exact_match = re.search(
                r"(?:(\d+)\s*(?:文字|字)\s*(?:で|の|くらい|程度)|"
                r"(?:around|about)\s*(\d+)\s*(?:chars?|characters?))",
                raw_msg,
                flags=re.IGNORECASE,
            )

            if max_match or min_match:
                min_val = (min_match.group(1) or min_match.group(2)) if min_match else None
                max_val = (max_match.group(1) or max_match.group(2)) if max_match else None
                rules["length_min"] = int(min_val) if min_val else 20
                rules["length_max"] = int(max_val) if max_val else 50
            elif exact_match:
                val_str = exact_match.group(1) or exact_match.group(2)
                target_len = int(val_str)
                rules["length_min"] = max(5, target_len - 5)
                rules["length_max"] = target_len + 5
            else:
                rules["length_min"] = 20
                rules["length_max"] = 50

        # ----------------------------------------------------
        # 2. スタイルの抽出（日英対応）
        # ----------------------------------------------------
        if any(w in lower_msg for w in ("笑点", "/shoten", "なぞかけ", "shoten", "riddle")):
            rules["style"] = "shoten"
            rules["style_label"] = "笑点の大喜利風"
        elif (
            any(w in lower_msg for w in ("3人", "三人", "trio", "three-person", "3-person"))
            and any(w in lower_msg for w in ("漫才", "manzai", "comedy", "skit"))
        ):
            rules["style"] = "manzai_3p"
            rules["style_label"] = "3人漫才（ボケ2人・ツッコミ1人の掛け合い）"
        elif (
            any(w in lower_msg for w in ("1人", "一人", "ひとり", "solo", "stand-up", "standup"))
            and any(w in lower_msg for w in ("漫才", "manzai", "comedy"))
        ):
            rules["style"] = "manzai_solo"
            rules["style_label"] = "1人漫才（セルフボケ・ノリツッコミ）"
        elif any(w in lower_msg for w in ("漫才", "/manzai", "manzai", "double act", "duo comedy")):
            rules["style"] = "manzai"
            rules["style_label"] = "漫才の掛け合い"
        elif any(w in lower_msg for w in ("大喜利", "/ogiri", "ogiri")):
            rules["style"] = "ogiri"
            rules["style_label"] = "大喜利の回答"
        elif any(
            w in lower_msg
            for w in ("ダジャレ", "だじゃれ", "駄洒落", "韻を踏", "/dajare", "/pun", "pun", "puns", "wordplay", "dad joke")
        ):
            rules["style"] = "dajare"
            rules["style_label"] = "韻を踏む高度な連撃ダジャレ"
        else:
            rules["style"] = "general"
            rules["style_label"] = "リズム感のある高度な言葉遊び・ギャグ"

        # ----------------------------------------------------
        # 3. ジャンル（好み）の抽出（機械系、食べ物系、法律系：日英対応）
        # ----------------------------------------------------
        if any(w in lower_msg for w in ("機械", "メカ", "エンジニア", "ギア", "モーター", "machine", "mechanical", "gear", "motor", "engineering")):
            rules["genre"] = "machine"
        elif any(w in lower_msg for w in ("スパゲッティ", "パスタ", "食べ物", "料理", "グルメ", "spaghetti", "pasta", "food", "cooking")):
            rules["genre"] = "food"
        elif any(w in lower_msg for w in ("法律", "弁護士", "裁判", "六法", "商談", "ビジネス", "legal", "law", "lawyer", "court", "business")):
            rules["genre"] = "legal_business"

        # ----------------------------------------------------
        # 4. 単語カウントモード & 重み宣言（日英対応）
        # ----------------------------------------------------
        if any(
            p in lower_msg
            for p in ("単語を少なく", "少ない単語", "最小限", "少ないほど", "fewer words", "minimize words", "minimal words")
        ):
            rules["keyword_count_mode"] = "minimize"
        else:
            rules["keyword_count_mode"] = "maximize"

        if any(p in lower_msg for p in ("自然さを重視", "自然な表現", "natural")):
            rules["weight_focus"] = "naturalness"
        elif any(p in lower_msg for p in ("独創性を重視", "意外性を重視", "original", "unique")):
            rules["weight_focus"] = "originality"

        # ----------------------------------------------------
        # 5. 明示されたお題単語の抽出（日英対応）
        # ----------------------------------------------------
        target_words = cls._extract_target_words(raw_msg)
        if target_words:
            rules["target_words"] = target_words
            rules["target_word"] = target_words[0]
            if any(p in lower_msg for p in ("必ず使", "必須", "絶対に使", "must use", "required")):
                rules["required_words"] = list(target_words)

        # ----------------------------------------------------
        # 6. 再抽選フラグ（reroll）とスコア・アドバイス表示フラグ
        # ----------------------------------------------------
        rules["reroll"] = not any(phrase in lower_msg for phrase in cls.REROLL_FALSE_PHRASES)

        rules["show_score"] = any(
            w in lower_msg for w in ("点数", "スコア", "採点", "評価", "何点", "score", "rate", "points")
        )
        rules["show_advice"] = any(
            w in lower_msg for w in ("アドバイス", "講評", "コメント", "ダメ出し", "改善", "advice", "feedback", "critique")
        )

        return rules

    @classmethod
    def _extract_target_words(cls, raw_msg: str) -> List[str]:
        """「」『』""'' で囲まれた単語や、「お題は〇〇」「topic: XX」で指定された単語を抽出する。"""
        # 1. 日本語カギ括弧「」『』 または 英語クォート "..." '...'
        quoted = [
            w.strip()
            for w in re.findall(r"[「『\"']([^」』\"']{1,20})[」』\"']", raw_msg)
            if w.strip() and w.strip().lower() not in GAG_STOP_WORDS
        ]
        if quoted:
            return list(dict.fromkeys(quoted))

        # 2. 「お題は〇〇」「topic: apple, banana」
        decl_match = re.search(
            r"(?:対象単語|指定単語|使う単語|お題|topic|target\s+words?|keywords?)\s*(?:は|を|：|:|=)\s*([^\n。！!？?.]+)",
            raw_msg,
            flags=re.IGNORECASE,
        )
        if decl_match:
            words = [
                item.strip(" 「」『』\"'、,，.。!！?？")
                for item in re.split(r"[、,，\s]+|(?:and|&)", decl_match.group(1))
            ]
            cleaned = [w for w in words if w and w.lower() not in GAG_STOP_WORDS]
            if cleaned:
                return list(dict.fromkeys(cleaned))

        # 3. 「〇〇という単語を使って」「using the word XX」
        word_use_match = re.search(
            r"(?:([^\s、。，「『」』]{1,12})(?:という単語|を使って)|using\s+(?:the\s+word\s+)?([a-zA-Z0-9_\-]+))",
            raw_msg,
            flags=re.IGNORECASE,
        )
        if word_use_match:
            w = (word_use_match.group(1) or word_use_match.group(2) or "").strip()
            if w and w.lower() not in GAG_STOP_WORDS:
                return [w]

        return []