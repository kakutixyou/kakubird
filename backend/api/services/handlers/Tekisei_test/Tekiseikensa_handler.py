# Tekiseikensa_handler.py
"""
タイピング / 照合(間違い探し)適性検査ハンドラー

役割
----------------------------
・「数字のみ」「数字+複数単語」などのタイピング問題セットを生成する
・「間違い修正テスト(照合)」問題セットを生成する
    左側 = 一部に誤りを含むデータ、右側 = 本来の正しいデータ
    項目: 名前 / 性別 / 生年月日 / 住所1 / 住所2 / 電話番号 / アドレス / 備考
・出題ロジックはコードに直書きせず、backend/knowledge_store/tekiseikensa/problems.json に外出しする
  → 今後似た問題タイプ(かな入力、英単語、伝票照合等)を追加するときはJSONにセットを足すだけで済む
・正誤判定・速度計測の"計算"はフロント(TypingTestBlock.jsx / ProofreadingTestBlock.jsx)側で行う。
  ここではあくまで「出題」と、任意で送られてくる「結果の記録」を担当する。

スコアリングについて
----------------------------
IntentInspector側の actions.json / targets.json / mode_rules.json にキーワードを
登録していなくても、このHandler単体は self.calculate_score() で自前スコアリングするため
最低限動作する。ただし IntentInspector が生成する context(target_categories 等)を
PromptBuilder が使っている場合は、キーワード未登録だと文脈の質が落ちる点に注意。
"""

import os
import json
import random
import re
from typing import Any, Dict, List, Optional, Tuple

_DIR = os.path.dirname(__file__)

# backend/api/services/handlers -> backend/knowledge_store/tekiseikensa/problems.json
_PROBLEMS_PATH_CANDIDATES = [
    os.path.join(_DIR, "..", "..", "..", "knowledge_store", "tekiseikensa", "problems.json"),
    os.path.join("backend", "knowledge_store", "tekiseikensa", "problems.json"),
    os.path.join("knowledge_store", "tekiseikensa", "problems.json"),
]

# タイピング系トリガー
_TRIGGER_KEYWORDS = [
    "タイピング", "適性検査", "入力速度", "正答率", "正解率",
    "数字のみ", "数字と単語", "数字 単語", "typing test", "typing練習",
    "タイピング練習", "適性テスト",
    # 照合(間違い探し)系トリガー
    "間違い探し", "間違い修正", "誤り修正", "校正テスト", "照合テスト",
    "データ照合", "誤植チェック", "見比べ", "proofreading",
]

_MODE_KEYWORDS = {
    "proofreading": [
        "間違い探し", "間違い修正", "誤り修正", "校正", "照合", "見比べ", "proofreading",
    ],
    "numbers_only": ["数字のみ", "数字だけ", "数字only"],
    "numbers_and_words": ["数字と単語", "数字 単語", "数字+単語", "数字プラス単語"],
}

_RESULT_KEYWORDS = ["結果報告", "タイピング結果", "適性検査結果", "照合結果"]

# 照合テストの項目とその表示ラベル・並び順(フロント側の描画順もこれに合わせる)
PROFILE_FIELDS: List[Tuple[str, str]] = [
    ("name", "名前"),
    ("gender", "性別"),
    ("birthdate", "生年月日"),
    ("address1", "住所1"),
    ("address2", "住所2"),
    ("phone", "電話番号"),
    ("email", "アドレス"),
    ("notes", "備考"),
]


class TekiseikensaHandler:
    """
    chat_orchestrator.py の Handler インターフェースに合わせる:
      - async def calculate_score(self, message, current_signals=None) -> int
      - async def handle(self, request) -> Tuple[str, dict]
      - estimate_size(message) -> int  (任意)
    """

    def __init__(self):
        self._problems_cache: Optional[Dict[str, Any]] = None

    # =========================================================
    # 問題セットJSONの読み込み
    # =========================================================

    def _load_problem_config(self) -> Dict[str, Any]:
        if self._problems_cache is not None:
            return self._problems_cache

        for path in _PROBLEMS_PATH_CANDIDATES:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._problems_cache = json.load(f)
                        return self._problems_cache
                except json.JSONDecodeError:
                    print(f"⚠️ [Tekiseikensa] 問題JSONが壊れています: {path}")

        print("⚠️ [Tekiseikensa] problems.json が見つからないため、内蔵デフォルトを使用します。")
        self._problems_cache = _DEFAULT_CONFIG
        return self._problems_cache

    # =========================================================
    # スコアリング (orchestratorのforループから呼ばれる)
    # =========================================================

    async def calculate_score(self, message: str, current_signals: Optional[dict] = None) -> int:
        msg = (message or "").lower()

        for kw in _TRIGGER_KEYWORDS:
            if kw.lower() in msg:
                return 100

        for kw in _RESULT_KEYWORDS:
            if kw.lower() in msg:
                return 100

        return 0

    def estimate_size(self, message: str) -> int:
        return 500

    # =========================================================
    # モード判定
    # =========================================================

    def _detect_mode(self, message: str) -> str:
        msg = (message or "").lower()

        # proofreading系を先にチェック(優先度高)
        for kw in _MODE_KEYWORDS["proofreading"]:
            if kw.lower() in msg:
                return "proofreading"

        for mode in ("numbers_only", "numbers_and_words"):
            for kw in _MODE_KEYWORDS[mode]:
                if kw.lower() in msg:
                    return mode

        # デフォルトは数字+単語(より実践的なため)
        return "numbers_and_words"

    def _detect_count(self, message: str, default: int) -> int:
        m = re.search(r"(\d+)\s*問", message or "")
        if m:
            try:
                return max(1, min(50, int(m.group(1))))
            except ValueError:
                pass
        return default

    # =========================================================
    # 問題生成: タイピング系
    # =========================================================

    def _generate_random_digits(self, params: Dict[str, Any], count_override: Optional[int] = None) -> List[str]:
        digit_length = params.get("digit_length", 6)
        count = count_override or params.get("count", 10)

        problems = []
        for _ in range(count):
            digits = "".join(str(random.randint(0, 9)) for _ in range(digit_length))
            problems.append(digits)
        return problems

    def _generate_digits_with_words(
        self,
        params: Dict[str, Any],
        word_banks: Dict[str, List[str]],
        count_override: Optional[int] = None,
    ) -> List[str]:
        digit_length = params.get("digit_length", 3)
        word_count = params.get("word_count", 2)
        count = count_override or params.get("count", 10)
        bank_key = params.get("word_bank_key", "general")

        bank = word_banks.get(bank_key, [])
        if not bank:
            bank = ["ことば"]

        problems = []
        for _ in range(count):
            digits = "".join(str(random.randint(0, 9)) for _ in range(digit_length))
            words = random.sample(bank, k=min(word_count, len(bank)))
            problems.append(" ".join([digits] + words))
        return problems

    # =========================================================
    # 問題生成: 照合(間違い探し)系
    # =========================================================

    def _random_name(self, profile_data: Dict[str, Any], gender: str) -> str:
        last = random.choice(profile_data.get("last_names", ["山田"]))
        pool_key = "first_names_male" if gender == "男性" else "first_names_female"
        first = random.choice(profile_data.get(pool_key, ["太郎"]))
        return f"{last} {first}"

    def _random_birthdate(self, profile_data: Dict[str, Any]) -> str:
        year = random.randint(1955, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}年{month:02d}月{day:02d}日"

    def _random_address1(self, profile_data: Dict[str, Any]) -> str:
        pref = random.choice(profile_data.get("prefectures", ["東京都"]))
        city = random.choice(profile_data.get("cities", ["中央区"]))
        return f"{pref}{city}"

    def _random_address2(self, profile_data: Dict[str, Any]) -> str:
        block = random.randint(1, 9)
        num = random.randint(1, 30)
        room = random.randint(101, 909)
        suffix = random.choice(profile_data.get("building_suffixes", ["マンション"]))
        return f"{block}-{num} {suffix}{room}号室"

    def _random_phone(self, profile_data: Dict[str, Any]) -> str:
        return f"090-{random.randint(1000,9999)}-{random.randint(1000,9999)}"

    def _random_email(self, profile_data: Dict[str, Any]) -> str:
        local = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=6))
        domain = random.choice(profile_data.get("email_domains", ["example.com"]))
        return f"{local}@{domain}"

    def _random_notes(self, profile_data: Dict[str, Any]) -> str:
        return random.choice(profile_data.get("notes_phrases", ["特記事項なし"]))

    def _generate_field(self, field: str, profile_data: Dict[str, Any], gender: Optional[str] = None) -> str:
        if field == "gender":
            return random.choice(["男性", "女性"])
        if field == "name":
            return self._random_name(profile_data, gender or "男性")
        if field == "birthdate":
            return self._random_birthdate(profile_data)
        if field == "address1":
            return self._random_address1(profile_data)
        if field == "address2":
            return self._random_address2(profile_data)
        if field == "phone":
            return self._random_phone(profile_data)
        if field == "email":
            return self._random_email(profile_data)
        if field == "notes":
            return self._random_notes(profile_data)
        return ""

    def _corrupt_field(self, field: str, correct_value: str, profile_data: Dict[str, Any], gender: str) -> str:
        """correct_value と異なる、もっともらしい値を返す(単純なゴミ文字列にはしない)"""
        for _ in range(5):
            candidate = self._generate_field(field, profile_data, gender=gender)
            if candidate != correct_value:
                return candidate
        return correct_value + "'"

    def _generate_profile_diff(
        self,
        params: Dict[str, Any],
        profile_data: Dict[str, Any],
        count_override: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        count = count_override or params.get("count", 10)
        min_errors = params.get("min_errors", 1)
        max_errors = params.get("max_errors", 3)

        field_keys = [f for f, _ in PROFILE_FIELDS]
        problems = []

        for _ in range(count):
            gender = random.choice(["男性", "女性"])

            correct = {"gender": gender}
            for field in field_keys:
                if field == "gender":
                    continue
                correct[field] = self._generate_field(field, profile_data, gender=gender)

            error_count = random.randint(min_errors, min(max_errors, len(field_keys)))
            error_fields = random.sample(field_keys, k=error_count)

            left = dict(correct)
            for field in error_fields:
                left[field] = self._corrupt_field(field, correct[field], profile_data, gender)

            problems.append({
                "left": left,
                "correct": correct,
                "error_fields": error_fields,
            })

        return problems

    # =========================================================
    # 問題セット組み立て
    # =========================================================

    def build_problem_set(self, mode: str, count_override: Optional[int] = None) -> Dict[str, Any]:
        config = self._load_problem_config()
        problem_sets = config.get("problem_sets", {})
        word_banks = config.get("word_banks", {})
        profile_data = config.get("profile_data", {})

        set_def = problem_sets.get(mode)
        if set_def is None:
            mode = "numbers_only"
            set_def = problem_sets.get(
                mode, {"generator": "random_digits", "params": {"digit_length": 6, "count": 10}}
            )

        generator_name = set_def.get("generator", "random_digits")
        params = set_def.get("params", {})

        if generator_name == "digits_with_words":
            problems = self._generate_digits_with_words(params, word_banks, count_override)
            kind = "typing"
        elif generator_name == "profile_diff":
            problems = self._generate_profile_diff(params, profile_data, count_override)
            kind = "proofreading"
        else:
            problems = self._generate_random_digits(params, count_override)
            kind = "typing"

        return {
            "mode": mode,
            "label": set_def.get("label", mode),
            "problems": problems,
            "kind": kind,
        }

    # =========================================================
    # 結果の記録 (任意: フロントから送り返された場合)
    # =========================================================

    def _maybe_record_result(self, message: str) -> Optional[str]:
        if not any(kw in (message or "") for kw in _RESULT_KEYWORDS):
            return None
        return "結果を受け取りました。お疲れさまでした！続けて別のモードも試せます。"

    # =========================================================
    # メインエントリ
    # =========================================================

    async def handle(self, request) -> Tuple[str, dict]:
        message = getattr(request, "message", "") or ""

        result_message = self._maybe_record_result(message)
        if result_message:
            return "text", {"message": result_message, "blocks": []}

        mode = self._detect_mode(message)
        count = self._detect_count(message, default=10)

        problem_set = self.build_problem_set(mode, count_override=count)

        if problem_set["kind"] == "proofreading":
            block = {
                "type": "ProofreadingTestBlock",
                "props": {
                    "mode": problem_set["mode"],
                    "label": problem_set["label"],
                    "fields": [{"key": k, "label": v} for k, v in PROFILE_FIELDS],
                    "problems": problem_set["problems"],
                },
            }
        else:
            block = {
                "type": "TypingTestBlock",
                "props": {
                    "mode": problem_set["mode"],
                    "label": problem_set["label"],
                    "problems": problem_set["problems"],
                },
            }

        return "ui_code", {
            "message": f"「{problem_set['label']}」モードで{len(problem_set['problems'])}問用意しました。準備ができたら開始してください。",
            "blocks": [block],
        }


# =========================================================
# JSONが見つからない場合のフォールバック定義
# =========================================================
_DEFAULT_CONFIG = {
    "problem_sets": {
        "numbers_only": {
            "label": "数字のみ",
            "generator": "random_digits",
            "params": {"digit_length": 6, "count": 10},
        },
        "numbers_and_words": {
            "label": "数字＋複数単語",
            "generator": "digits_with_words",
            "params": {"digit_length": 3, "word_count": 2, "count": 10, "word_bank_key": "general"},
        },
        "proofreading": {
            "label": "間違い修正テスト（照合）",
            "generator": "profile_diff",
            "params": {"count": 10, "min_errors": 1, "max_errors": 3},
        },
    },
    "word_banks": {
        "general": ["りんご", "さくら", "とうきょう", "ひまわり", "こうえん", "でんしゃ", "としょかん", "たいよう"],
    },
    "profile_data": {
        "last_names": ["山田", "佐藤", "鈴木", "田中", "高橋"],
        "first_names_male": ["太郎", "健一", "翔太", "大輔"],
        "first_names_female": ["花子", "美咲", "由美", "彩"],
        "prefectures": ["東京都", "神奈川県", "大阪府"],
        "cities": ["中央区", "港区", "北区", "西区"],
        "building_suffixes": ["マンション", "アパート", "ハイツ"],
        "email_domains": ["example.com", "mail.co.jp"],
        "notes_phrases": ["特記事項なし", "要確認", "連絡先変更予定あり"],
    },
}