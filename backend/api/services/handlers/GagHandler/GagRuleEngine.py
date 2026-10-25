# api/services/handlers/GagHandler/GagRuleEngine.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GagRuleProfile:
    """客ごとに変更できるギャグ評価ルール。"""

    keyword_count_mode: str = "maximize"
    keyword_weight: int = 60
    naturalness_weight: int = 20
    originality_weight: int = 20

    target_words: list[str] = field(default_factory=list)
    required_words: list[str] = field(default_factory=list)
    used_words: list[str] = field(default_factory=list)  # 重複防止用の履歴

    max_characters: int | None = 50
    min_characters: int | None = 20

    # GagHandler側の min_chars / max_chars 参照との互換プロパティ
    @property
    def min_chars(self) -> int | None:
        return self.min_characters

    @property
    def max_chars(self) -> int | None:
        return self.max_characters

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    target_occurrences = None
    target_occurrences = None


@dataclass
class GagEvaluation:
    score: float
    keyword_score: float
    keyword_occurrences: int
    matched_required_words: list[str]
    missing_required_words: list[str]
    character_count: int
    rule_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GagRuleEngine:
    """
    客の宣言を評価ルールへ変換し、ギャグを採点する。

    お題単語が明示されていない場合は、重複を避けつつ以下の確率で自動抽選する：
    - 60%: 異種ジャンル混合ランダム（機械系×食べ物系×法律系×日常系）
    - 40%: 会話履歴・文脈から抽出した単語＋内蔵リストのハイブリッド
    """

    MAX_SCORE = 100.0

    # 1. 異種ジャンル別シードプール（JSONファイル不要の内蔵辞書）
    GENRE_WORD_POOLS: dict[str, list[str]] = {
        
        "machine": [
            "ギア", "モーター", "トルク", "バルブ", "ベアリング",
            "ピストン", "コンプレッサー", "タービン", "油圧", "ナット",
        ],
        "food": [
            "スパゲッティ", "プリン", "ちくわ", "エスプレッソ", "カルボナーラ",
            "マカロニ", "ナポリタン", "クロワッサン", "茶碗蒸し", "鯛",
        ],
        "legal_business": [
            "商談", "善意の第三者", "コンプライアンス", "示談", "契約書",
            "裁判官", "六法全書", "異議あり", "決算", "稟議",
        ],
        "daily_surreal": [
            "階段", "プール", "布団", "校長先生", "財布",
            "桜", "アルミ缶", "宿題", "エレベーター", "扇風機",
        ],
    }

    # 会話文から拾わない一般的な除外ワード（ストップワード）
    STOP_WORDS: set[str] = {
        "ギャグ", "ダジャレ", "だじゃれ", "漫才", "笑点", "ボケ", "ネタ",
        "お題", "単語", "対象単語", "指定単語", "文字", "文字数", "設定",
        "ルール", "評価", "スコア", "お願い", "作成", "生成", "自分",
        "今日", "それ", "これ", "あれ", "どれ", "ため", "よう", "こと",
        "もの", "ところ", "たくさん", "最小限", "自然", "独創性", "意外性",
    }

    def create_profile(
        self,
        declaration: str,
        previous: GagRuleProfile | dict[str, Any] | None = None,
        history_texts: list[str] | None = None,
    ) -> GagRuleProfile:
        text = str(declaration or "").strip()

        if isinstance(previous, GagRuleProfile):
            profile = GagRuleProfile(**previous.to_dict())
        elif isinstance(previous, dict):
            valid_keys = GagRuleProfile.__dataclass_fields__.keys()
            filtered = {k: v for k, v in previous.items() if k in valid_keys}
            profile = GagRuleProfile(**filtered)
        else:
            profile = GagRuleProfile()

        # --------------------------------------------------------
        # 1. 単語カウントモードの判定
        # --------------------------------------------------------
        if any(
            phrase in text
            for phrase in (
                "単語を多く",
                "単語が多いほど",
                "単語をたくさん",
                "複数の単語",
                "単語数が多いほど",
            )
        ):
            profile.keyword_count_mode = "maximize"

        elif any(
            phrase in text
            for phrase in (
                "単語を少なく",
                "単語が少ないほど",
                "少ない単語",
                "単語数が少ないほど",
                "最小限の単語",
            )
        ):
            profile.keyword_count_mode = "minimize"

        # --------------------------------------------------------
        # 2. 文字数制限の抽出（例: 20~50文字、40文字以内）
        # --------------------------------------------------------
        range_match = re.search(r"(\d+)\s*[〜~\-ーから]\s*(\d+)\s*文字", text)
        if range_match:
            profile.min_characters = int(range_match.group(1))
            profile.max_characters = int(range_match.group(2))
        else:
            max_match = re.search(r"(\d+)\s*文字(?:以内|以下|まで)", text)
            min_match = re.search(r"(\d+)\s*文字(?:以上|から)", text)
            if max_match:
                profile.max_characters = int(max_match.group(1))
            if min_match:
                profile.min_characters = int(min_match.group(1))

        # --------------------------------------------------------
        # 3. 評価重みの宣言
        # --------------------------------------------------------
        if "自然さを重視" in text or "自然な表現" in text:
            profile.naturalness_weight = 60
            profile.keyword_weight = 20
            profile.originality_weight = 20

        if "独創性を重視" in text or "意外性を重視" in text:
            profile.originality_weight = 60
            profile.keyword_weight = 20
            profile.naturalness_weight = 20

        # --------------------------------------------------------
        # 4. お題単語の決定（明示指定 or 60%/40%ランダム抽選）
        # --------------------------------------------------------
        explicit_words = self._extract_explicit_words(text)

        if explicit_words:
            profile.target_words = explicit_words
        else:
            # 明示指定がない場合は、60%で異種ジャンル混合、40%で会話履歴ハイブリッド
            profile.target_words = self._select_random_target_words(
                declaration_text=text,
                history_texts=history_texts,
                used_words=profile.used_words,
            )

        # 選ばれた単語を使用済みリストへ記録（重複回避用）
        for w in profile.target_words:
            if w and w not in profile.used_words:
                profile.used_words.append(w)

        # 必須単語の判定（例: 「りんごは必ず使って」）
        profile.required_words = [
            w for w in profile.required_words if w in profile.target_words
        ]
        for word in profile.target_words:
            if (
                word in text
                and any(
                    phrase in text
                    for phrase in ("必ず使", "必須", "絶対に使")
                )
            ):
                if word not in profile.required_words:
                    profile.required_words.append(word)

        # --------------------------------------------------------
        # 5. 重みを正規化して合計100にする
        # --------------------------------------------------------
        weights = [
            max(0, profile.keyword_weight),
            max(0, profile.naturalness_weight),
            max(0, profile.originality_weight),
        ]
        total = sum(weights)

        if total == 0:
            weights = [60, 20, 20]
            total = 100

        (
            profile.keyword_weight,
            profile.naturalness_weight,
            profile.originality_weight,
        ) = [round(weight * 100 / total) for weight in weights]

        profile.originality_weight += (
            100
            - profile.keyword_weight
            - profile.naturalness_weight
            - profile.originality_weight
        )

        return profile

    # ========================================================
    # お題単語の抽出・60% / 40% ランダム抽選ロジック
    # ========================================================

    def _extract_explicit_words(self, text: str) -> list[str]:
        """ユーザーが明示的に指定したお題単語を抽出する。"""
        first_line = text.splitlines()[0] if text else ""

        # 1. 「」や『』で囲まれた単語（最優先）
        quoted = [
            w.strip()
            for w in re.findall(r"[「『]([^」』]{1,15})[」』]", first_line)
            if w.strip() and w.strip() not in self.STOP_WORDS
        ]
        if quoted:
            return list(dict.fromkeys(quoted))

        # 2. 「対象単語は りんご、学校」のような宣言
        match = re.search(
            r"(?:対象単語|指定単語|使う単語|お題)\s*(?:は|を|：|:)\s*([^\n]+)",
            first_line,
        )
        if match:
            words = [
                item.strip(" 「」『』\"'、,。.!！?")
                for item in re.split(r"[、,，\s]+", match.group(1))
            ]
            cleaned = [
                w for w in words if w and w not in self.STOP_WORDS
            ]
            if cleaned:
                return list(dict.fromkeys(cleaned))

        return []

    def _select_random_target_words(
        self,
        declaration_text: str,
        history_texts: list[str] | None,
        used_words: list[str],
        pick_count: int = 2,
    ) -> list[str]:
        """
        60%の確率で「1. 異種ジャンル混合ランダム」、
        40%の確率で「2. 会話履歴＋内蔵リストのハイブリッド」を実行する。
        """
        roll = random.random()  # 0.0 <= roll < 1.0

        # 40%の確率 (0.60 <= roll < 1.0): パターン2（会話履歴＋内蔵リストのハイブリッド）
        if roll >= 0.60:
            context_candidates = self._extract_context_words(
                declaration_text, history_texts, used_words
            )
            if context_candidates:
                chosen_context = random.choice(context_candidates)
                # もう1語は内蔵の異種ジャンルからランダムに選んで掛け合わせる
                genre_words = self._pick_from_genres(
                    used_words=used_words + [chosen_context],
                    count=max(1, pick_count - 1),
                )
                return [chosen_context] + genre_words

        # 60%の確率 (0.0 <= roll < 0.60) または履歴に単語がない場合: パターン1（異種ジャンル混合）
        return self._pick_from_genres(used_words=used_words, count=pick_count)

    def _pick_from_genres(
        self,
        used_words: list[str],
        count: int = 2,
    ) -> list[str]:
        """異なるジャンルから重複しないように単語をピックアップする。"""
        genres = list(self.GENRE_WORD_POOLS.keys())
        random.shuffle(genres)

        selected: list[str] = []
        used_set = set(used_words)

        for genre in genres:
            if len(selected) >= count:
                break
            pool = self.GENRE_WORD_POOLS[genre]
            available = [
                w for w in pool if w not in used_set and w not in selected
            ]
            # 該当ジャンルの単語を使い切っていた場合はプール全体から選ぶ（リセット効果）
            if not available:
                available = [w for w in pool if w not in selected]
            if available:
                selected.append(random.choice(available))

        return selected

    def _extract_context_words(
        self,
        declaration_text: str,
        history_texts: list[str] | None,
        used_words: list[str],
    ) -> list[str]:
        """会話履歴や宣言文から、名詞らしいキーワード（漢字2〜6文字、カタカナ3〜8文字）を抽出する。"""
        combined = "\n".join([declaration_text] + (history_texts or []))
        # 内部メタデータのキー名（gag_style等）が混ざらないよう日本語のみ抽出
        candidates = re.findall(r"[一-龥]{2,6}|[ァ-ヶー]{3,8}", combined)

        used_set = set(used_words)
        valid_words: list[str] = []

        for word in candidates:
            if (
                word not in self.STOP_WORDS
                and word not in used_set
                and word not in valid_words
            ):
                valid_words.append(word)

        return valid_words

    # ========================================================
    # 採点・評価ロジック
    # ========================================================

    @staticmethod
    def count_keyword_occurrences(
        text: str,
        target_words: list[str],
    ) -> int:
        """指定単語の出現数。空文字列は数えない。"""
        return sum(text.count(word) for word in target_words if word)

    @staticmethod
    def _keyword_score(
        occurrences: int,
        mode: str,
    ) -> float:
        """
        単語数の点数を0～100にする。
        上限を設け、単語の無制限な繰り返しによる点数のインフレを抑える。
        """
        if mode == "minimize":
            return max(
                0.0,
                100.0 - min(occurrences, 20) * 5.0,
            )

        return min(
            100.0,
            occurrences * 5.0,
        )

    def evaluate(
        self,
        gag: str,
        profile: GagRuleProfile,
        naturalness_score: float = 50.0,
        originality_score: float = 50.0,
    ) -> GagEvaluation:
        text = str(gag or "").strip()

        occurrences = self.count_keyword_occurrences(
            text,
            profile.target_words,
        )

        keyword_score = self._keyword_score(
            occurrences,
            profile.keyword_count_mode,
        )

        naturalness_score = max(0.0, min(100.0, naturalness_score))
        originality_score = max(0.0, min(100.0, originality_score))

        score = (
            keyword_score * profile.keyword_weight
            + naturalness_score * profile.naturalness_weight
            + originality_score * profile.originality_weight
        ) / 100.0

        matched = [
            word for word in profile.required_words if word in text
        ]
        missing = [
            word for word in profile.required_words if word not in text
        ]

        # 必須単語が欠けた場合は減点
        if profile.required_words:
            compliance = len(matched) / len(profile.required_words)
            score *= compliance

        character_count = len(text)

        # 文字数制約は追加条件として適用
        if (
            profile.max_characters is not None
            and character_count > profile.max_characters
        ):
            score *= 0.8

        if (
            profile.min_characters is not None
            and character_count < profile.min_characters
        ):
            score *= 0.8

        return GagEvaluation(
            score=round(max(0.0, min(100.0, score)), 2),
            keyword_score=round(keyword_score, 2),
            keyword_occurrences=occurrences,
            matched_required_words=matched,
            missing_required_words=missing,
            character_count=character_count,
            rule_mode=profile.keyword_count_mode,
        )
    def create_profile_from_rules(self, rules, previous=None, history_texts=None):
        if rules is None:
            rules = {}

        if isinstance(previous, GagRuleProfile):
            profile = GagRuleProfile(**previous.to_dict())
        elif isinstance(previous, dict):
            valid_keys = GagRuleProfile.__dataclass_fields__.keys()
            filtered = {k: v for k, v in previous.items() if k in valid_keys}
            profile = GagRuleProfile(**filtered)
        else:
            profile = GagRuleProfile()

        if not isinstance(rules, dict):
            return profile

        # 文字数
        if "length_min" in rules and rules["length_min"] is not None:
            profile.min_characters = int(rules["length_min"])
        if "length_max" in rules and rules["length_max"] is not None:
            profile.max_characters = int(rules["length_max"])

        if "min_characters" in rules and rules["min_characters"] is not None:
            profile.min_characters = int(rules["min_characters"])
        if "max_characters" in rules and rules["max_characters"] is not None:
            profile.max_characters = int(rules["max_characters"])

        # 単語
        target_words = rules.get("target_words") or []
        if target_words:
            profile.target_words = [str(w) for w in target_words if str(w).strip()]
        elif getattr(profile, "target_words", None):
            profile.target_words = [str(w) for w in profile.target_words if str(w).strip()]

        required_words = rules.get("required_words") or []
        if required_words:
            profile.required_words = [str(w) for w in required_words if str(w).strip()]

        # キーワード数モード
        if rules.get("keyword_count_mode"):
            profile.keyword_count_mode = str(rules["keyword_count_mode"])

        # 重み
        if rules.get("weight_focus") == "naturalness":
            profile.naturalness_weight = 60
            profile.keyword_weight = 20
            profile.originality_weight = 20
        elif rules.get("weight_focus") == "originality":
            profile.originality_weight = 60
            profile.keyword_weight = 20
            profile.naturalness_weight = 20

        # 既存のロジックに戻す
        weights = [
            max(0, profile.keyword_weight),
            max(0, profile.naturalness_weight),
            max(0, profile.originality_weight),
        ]
        total = sum(weights)
        if total == 0:
            weights = [60, 20, 20]
            total = 100

        (
            profile.keyword_weight,
            profile.naturalness_weight,
            profile.originality_weight,
        ) = [round(weight * 100 / total) for weight in weights]

        profile.originality_weight += (
            100
            - profile.keyword_weight
            - profile.naturalness_weight
            - profile.originality_weight
        )

        return profile