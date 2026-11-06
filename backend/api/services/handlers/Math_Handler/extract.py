# backend/api/services/handlers/MathHandler/extract.py
"""自然言語入力から数式・為替・基数変換・論理演算の意図とパラメータを抽出するモジュール。

インジェクション対策としてのホワイトリスト検証および正規表現パースを備え、
基本情報技術者試験レベルの計算・論理問題にも対応します。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)

# ========================================================
# 1. 汎用ユーティリティ関数
# ========================================================

def message_text(message: Any) -> str:
    """メッセージオブジェクトから文字列を安全に取り出します。"""
    return message.strip() if isinstance(message, str) else str(message or "").strip()

def extract_message(request: Any) -> str:
    """リクエストオブジェクトからプロンプト・メッセージ本文を抽出します。"""
    if isinstance(request, str):
        return request.strip()
    if isinstance(request, Mapping):
        for key in ("message", "prompt", "query", "text", "content"):
            value = request.get(key)
            if value is not None and str(value).strip():
                return message_text(value)
        return ""
    for attribute in ("message", "prompt", "query", "text", "content"):
        value = getattr(request, attribute, None)
        if value is not None and str(value).strip():
            return message_text(value)
    return ""

def extract_signals(request: Any) -> Dict[str, Any]:
    """リクエストからシグナル辞書を安全に取得します。"""
    if isinstance(request, Mapping):
        value = request.get("current_signals") or request.get("signals") or {}
    else:
        value = getattr(request, "current_signals", None) or getattr(request, "signals", None) or {}
    return dict(value) if isinstance(value, Mapping) else {}

def normalized_signal(value: Any) -> str:
    """シグナル文字列を正規化します。"""
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


# ========================================================
# 2. 抽出データモデル定義
# ========================================================

@dataclass
class ExtractedMath:
    """抽出された演算意図とパラメータを格納するデータクラス。"""
    # 算術式
    formula: str = ""
    
    # 為替換算
    is_currency_conversion: bool = False
    base_currency: str = ""
    target_currency: str = ""
    amount: float = 0.0

    # 基数変換 (例: 16進数0.C -> 10進数)
    is_base_conversion: bool = False
    source_base: int = 10
    target_base: int = 10
    raw_value: str = ""

    # 論理・集合演算 (例: A and not B, XOR合成, ド・モルガン)
    is_logic_expression: bool = False
    logic_formula: str = ""
    variables: List[str] = field(default_factory=list)


# ========================================================
# 3. 自然言語パーサー・抽出コアロジック
# ========================================================

class Extractor:
    """自然言語から数学・論理演算の意図を安全に抽出するクラス。"""

    # 為替パターン
    _CURRENCY_PATTERN = re.compile(
        r"([\d,]+(?:\.\d+)?)\s*(円|ドル|ユーロ|ウォン|ズウォティ|USD|JPY|EUR|KRW|PLN).*(円|ドル|ユーロ|ウォン|ズウォティ|USD|JPY|EUR|KRW|PLN)",
        re.IGNORECASE,
    )

    # 基数変換パターン（例: "16進数0.Cを10進数に", "7/32を2進数で"）
    _BASE_CONV_PATTERN = re.compile(
        r"(?:(?P<src_base>2|8|10|16)進数?(?:の)?\s*)?"
        r"(?P<val>[0-9a-fA-F]+(?:\.[0-9a-fA-F]+)?|\d+\s*/\s*\d+)\s*"
        r"(?:を|から)?\s*"
        r"(?P<dst_base>2|8|10|16)進数?",
        re.IGNORECASE,
    )

    # 論理演算・集合演算記号の正規化マッピング
    _LOGIC_REPLACEMENTS = {
        "￣": " not ",
        "~": " not ",
        "¬": " not ",
        "∩": " and ",
        "∧": " and ",
        "∪": " or ",
        "∨": " or ",
        "⊕": " xor ",
        "論理積": " and ",
        "論理和": " or ",
        "排他的論理和": " xor ",
        "否定": " not ",
    }

    def extract(self, text: str) -> ExtractedMath:
        """テキストを走査し、各種演算の意図を抽出・正規化して返します。"""
        if not text:
            return ExtractedMath()

        # ----------------------------------------------------
        # 1. 為替変換の抽出
        # ----------------------------------------------------
        currency_match = self._CURRENCY_PATTERN.search(text)
        if currency_match:
            amount_str = currency_match.group(1).replace(",", "")
            try:
                amount = float(amount_str)
                return ExtractedMath(
                    is_currency_conversion=True,
                    amount=amount,
                    base_currency=currency_match.group(2),
                    target_currency=currency_match.group(3),
                )
            except ValueError:
                pass

        # ----------------------------------------------------
        # 2. 基数変換（n進数・小数・分数）の抽出
        # ----------------------------------------------------
        base_match = self._BASE_CONV_PATTERN.search(text)
        if base_match:
            val = base_match.group("val").strip()
            dst_base = int(base_match.group("dst_base"))
            src_base_group = base_match.group("src_base")

            # 明示的な基数指定がない場合の推測
            if src_base_group:
                src_base = int(src_base_group)
            elif "/" in val:
                src_base = 10
            elif any(c in val.lower() for c in "abcdef"):
                src_base = 16
            else:
                src_base = 10

            return ExtractedMath(
                is_base_conversion=True,
                source_base=src_base,
                target_base=dst_base,
                raw_value=val,
            )

        # ----------------------------------------------------
        # 3. 論理演算・集合式の抽出（基本情報技術者試験対応）
        # ----------------------------------------------------
        normalized_logic = text
        for symbol, repl in self._LOGIC_REPLACEMENTS.items():
            normalized_logic = normalized_logic.replace(symbol, repl)

        # 論理キーワードまたは識別子が含まれるか判定
        logic_tokens = [" and ", " or ", " not ", " xor "]
        if any(token in normalized_logic.lower() for token in logic_tokens) or re.search(r"\b[A-Za-z]\s*[-∩∪∧∨]\s*[A-Za-z]\b", text):
            # 変数候補 (A, B, L1, L2, x, y など) の抽出
            var_candidates = sorted(list(set(re.findall(r"\b[A-Za-z][0-9]?\b", normalized_logic))))
            # 余計な単語を削り、安全な論理式文字列を構築
            safe_logic_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_() -")
            cleaned_logic = "".join(c for c in normalized_logic if c in safe_logic_chars)
            cleaned_logic = re.sub(r"\s+", " ", cleaned_logic).strip()

            return ExtractedMath(
                is_logic_expression=True,
                logic_formula=cleaned_logic,
                variables=var_candidates,
            )

        # ----------------------------------------------------
        # 4. 通常の算術式の抽出（単位換算・DoS対策・サニタイズ）
        # ----------------------------------------------------
        text_lower = text.lower()
        text_lower = re.sub(r"無限大数|無限|∞", "inf", text_lower)

        unit_map = {
            "ミリ": "*1e-3",
            "センチ": "*1e-2",
            "キロ": "*1e3",
            "万": "*1e4",
            "億": "*1e8",
            "兆": "*1e12",
            "ペタ": "*1e15",
            "無量大数": "*1e68",
        }
        for jp_unit, math_val in unit_map.items():
            text_lower = re.sub(rf"(?<=[\d\.\)])\s*{jp_unit}", math_val, text_lower)

        allowed_chars = set("0123456789+-*/%^().einf ")
        sanitized = "".join(c for c in text_lower if c in allowed_chars).strip()

        expression_pattern = re.compile(
            r"(?:inf|\d|\()\s*"
            r"[0-9\+\-\*\/\%\^\(\)\.\seinf]*"
            r"[\+\-\*\/\%\^]"
            r"[0-9\+\-\*\/\%\^\(\)\.\seinf]*"
            r"(?:inf|\d|\))"
        )

        match = expression_pattern.search(sanitized)
        clean_formula = ""

        if match:
            clean_formula = match.group(0).strip()
        else:
            math_keywords = [
                "計算", "たす", "足す", "プラス", "ひく", "引く", "マイナス",
                "かける", "掛ける", "わる", "割る", "答え", "合計", "平均", "換算",
            ]
            if any(keyword in text for keyword in math_keywords):
                num_match = re.search(r"(?:inf|\d+(?:\.\d+)?(?:e[+-]?\d+)?)", sanitized)
                if num_match:
                    clean_formula = num_match.group(0)

        # DoS対策（巨大な指数計算のブロック）
        if ("**" in clean_formula or "^" in clean_formula) and re.search(r"(?:\*\*|\^)\s*[0-9]{4,}", clean_formula):
            logger.warning(f"巨大な累乗計算を検知したためブロックしました: {clean_formula}")
            clean_formula = ""

        return ExtractedMath(formula=clean_formula)


# ========================================================
# 4. LLM出力・コードブロック抽出ユーティリティ
# ========================================================

class MathExtractor:
    """LLMレスポンス等のテキストからコードブロックや簡易数式を抽出するクラス。"""

    _CODE_BLOCK_PATTERN = re.compile(
        r"```(?:python|py)?\s*(.*?)```",
        re.IGNORECASE | re.DOTALL,
    )

    _INLINE_MATH_PATTERN = re.compile(
        r"^\s*([\d\.\+\-\*\/\%\(\)\s]+)\s*$"
    )

    @classmethod
    def extract_python_code(cls, text: str) -> Optional[str]:
        if not text:
            return None

        matches = cls._CODE_BLOCK_PATTERN.findall(text)
        if matches:
            extracted = matches[0].strip()
            if extracted:
                return extracted

        heuristics_match = (
            "def " in text or
            "print(" in text or
            "import " in text
        )
        has_japanese_explanation = any(w in text for w in ("です", "ます", "以下に"))

        if heuristics_match and not has_japanese_explanation:
            logger.debug("MarkdownタグなしのPythonコードを検出しました。フォールバックを適用します。")
            return text.strip()

        return None

    @classmethod
    def extract_simple_math(cls, text: str) -> Optional[str]:
        if not text:
            return None

        clean_text = text.replace(" ", "")
        match = cls._INLINE_MATH_PATTERN.match(clean_text)
        if match:
            return match.group(1)

        return None


# ========================================================
# 公開API定義
# ========================================================

__all__ = [
    "message_text",
    "extract_message",
    "extract_signals",
    "normalized_signal",
    "ExtractedMath",
    "Extractor",
    "MathExtractor",
]
