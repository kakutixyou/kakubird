# api/services/handlers/GagHandler/generator.py
# -*- coding: utf-8 -*-
"""
generator.py (high-score version)

設計方針:
1. 「音の重なり（韻・語呂合わせ）」を核に文を組み立てる
2. 採点条件（必須ワード・出現回数・文字数レンジ）を生成側でも守る
   - repeat_count / minimum_use / required_words / min_characters / max_characters
3. LLM は複数サンプル → 制約適合度で最良を選ぶ → 足りなければ修復(repair)
4. 辞書にない単語でも、そのまま使える反復型の文型で成立させる
5. state.history・rules["past_gags"]・モジュールキャッシュで被りを排除
6. 「10個考えて」などの複数個リクエストにも対応
"""

from __future__ import annotations

import random
import re
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

from api.services.handlers.ChatHandler.llm_bridge import generate_with_local_llm
from .GagRuleEngine import GagRuleProfile

_RECENT_GENERATED_GAGS: List[str] = []
_MAX_RECENT_CACHE = 50

# LLM を何回サンプリングして最良を選ぶか（rules["llm_samples"] で上書き可）
_DEFAULT_LLM_SAMPLES = 2

# ==========================
# 音ペア辞書
# ==========================
PUN_KNOWLEDGE_BASE: Dict[str, Dict[str, str]] = {
    "GitHub Copilot": {"pun": "コパイロットが濃いパイロット", "sub": "操縦席のコード", "act": "ナイスフライトでバグを回避した"},
    "PR": {"pun": "PR（ピーアール）で自己PR", "sub": "渾身のコミット", "act": "レビュアーの心にマージされた"},
    "review": {"pun": "レビューの途中で目がビュンビュン", "sub": "大量の差分", "act": "LGTMを出して落ち着いた"},
    "branch": {"pun": "ブランチを切りながら食べるブランチ（昼食）", "sub": "休日のカフェ", "act": "コンフリクトなしで消化できた"},
    "commit": {"pun": "コミットに心を込めっと", "sub": "深夜の修正", "act": "一発でテストを通過した"},
    "merge": {"pun": "マージで！？まじで！？", "sub": "本番ブランチ", "act": "無事にリリースまで完了した"},
    "repo": {"pun": "リポジトリの状況を現場からリポート", "sub": "最新の履歴", "act": "きれいに整理されていた"},
    "issue": {"pun": "イシュー（Issue）を一周回って解決", "sub": "放置されたタスク", "act": "ようやくクローズできた"},
    "deploy": {"pun": "デプロイ完了！さあ出風呂いい？（お風呂出ていい？）", "sub": "金曜夜のリリース", "act": "湯冷めする前に本番反映できた"},
    "デプロイ": {"pun": "デプロイ完了！もう出風呂いい？", "sub": "本番サーバー", "act": "お湯が冷める前に安定稼働した"},
    "release": {"pun": "リリース作業で心がりりーす（解放）", "sub": "長かった開発期間", "act": "ようやくぐっすり眠れた"},
    "CI": {"pun": "CI（シーアイ）の結果をジーっと見合い（しあい）", "sub": "緑のチェックマーク", "act": "ビルド成功でガッツポーズした"},
    "cache": {"pun": "キャッシュを消したらキャッシュ（現金）が減った気がした", "sub": "ブラウザのメモリ", "act": "動作だけはサクサクになった"},
    "ログ": {"pun": "ログを漁ってろく（6）時間経過", "sub": "エラーの痕跡", "act": "原因の1行をついに特定した"},
    "API": {"pun": "API（エーピーアイ）が動いて、えっぴー！（ハッピー！）", "sub": "JSONレスポンス", "act": "ステータス200で絶好調だ"},
    "バグ": {"pun": "バグを直してくれた仲間と熱いハグ", "sub": "徹夜のデバッグ", "act": "涙なしで画面を見つめた"},
    "lint": {"pun": "lint（リント）が通って凛（りん）としたコード", "sub": "インデントの乱れ", "act": "警告ゼロで気持ちよく保存した"},
    "hotfix": {"pun": "hotfix（ホットフィックス）でほっと一息つく", "sub": "緊急パッチ", "act": "障害を最小限で食い止めた"},
    "rollback": {"pun": "ロールバックして、ロールパンをパクッ", "sub": "切り戻し作業", "act": "お腹もサーバーも落ち着いた"},
    "雨": {"pun": "雨（あめ）の日は、甘い飴（あめ）をなめよう", "sub": "窓の外の天気", "act": "気分が晴れて作業が進んだ"},
    "猫": {"pun": "猫（ねこ）がキーボードの上で寝転（ねころ）んだ", "sub": "謎のショートカット入力", "act": "かわいいからすべて許した"},
    "会議": {"pun": "会議（かいぎ）の議題は、怪奇（かいき）現象！？", "sub": "終わらない打ち合わせ", "act": "結論が出てようやく解散した"},
    "財布": {"pun": "財布（さいふ）を落としたけど、中身は無事でセーフ！", "sub": "帰り道のポケット", "act": "冷や汗をかいたけど安心した"},
    "階段": {"pun": "階段（かいだん）で聞く、ちょっと怖い怪談（かいだん）", "sub": "夜のオフィスビル", "act": "思わず一段飛ばしで駆け上がった"},
    "コーヒー": {"pun": "コーヒーを飲んで、気分は好調（こうちょう）ヒィー！", "sub": "眠気覚ましの一杯", "act": "集中力が一気に戻ってきた"},
    "スパゲッティ": {"pun": "スパゲッティコードを、スッパリ切って整理！", "sub": "絡まった関数", "act": "リファクタリングで美しくなった"},
    "プリン": {"pun": "プリンを食べて、頭もプリッとフル回転！", "sub": "3時のおやつ", "act": "糖分補給でバグも解決した"},
    "電車": {"pun": "電車（でんしゃ）の中で、ひらめきが連射（れんしゃ）！", "sub": "通勤ラッシュ", "act": "スマホのメモ帳がアイデアで埋まった"},
    "昼休み": {"pun": "昼休み（ひるやすみ）は、ひるまず休むのみ！", "sub": "午後のタスク", "act": "しっかり充電して復活した"},
    "洗濯": {"pun": "洗濯（せんたく）をするか寝るか、究極の選択（せんたく）！", "sub": "休日の朝", "act": "結局どちらも片付けてスッキリした"},
}

DEFAULT_WORD_BANK: List[str] = list(PUN_KNOWLEDGE_BASE.keys())

# ==========================
# 文型ライブラリ
# ==========================
PATTERN_LIBRARY: List[str] = [
    "「{A_pun}！」と叫んだら、{A_sub}までピタッと止まって{A_act}。",
    "{A}を見つめて一言、「{A_pun}」。おかげで{A_sub}もすっかり{A_act}。",
    "{B}より先に{A}を片付けようとしたら、{A_pun}！結果オーライで{A_act}。",
    "「{A_pun}」なんてダジャレを言っていたら、{B}の横で{A_sub}が{A_act}。",
    "{A}と{B}を並べてみたら、「{A_pun}」状態！それでも最後は{A_act}。",
    "現場から速報です。{A_pun}！これにより{A_sub}は{A_act}とのことです。",
    "{A_sub}で困っていたら、先輩が「{A_pun}」とニヤリ。緊張が解けて{A_act}。",
    "もしも{A}が喋れたら、「{A_pun}」って言うはず。そんな妄想をしていたら{A_act}。",
]

PATTERN_LIBRARY_GITHUB: List[str] = [
    "GitHub上で事件発生！{A_pun}！でも{B}のおかげで{A_act}。",
    "プルリクのコメントに「{A_pun}」と書いたら、{A_sub}が一瞬で承認されて{A_act}。",
    "エンジニアの格言：「{A_pun}」。これを守れば、{B}があっても{A_act}。",
    "{A_sub}をレビュー中に「{A_pun}！」とひらめき、そのまま勢いで{A_act}。",
    "CIが回るのを待ちながら「{A_pun}」。気づけば{B}も一緒に{A_act}。",
]

PATTERN_LIBRARY_DAILY: List[str] = [
    "今日のハイライト：{A_pun}！そのあと{B}も加わって、平和に{A_act}。",
    "一息つきながら「{A_pun}」。{A_sub}の疲れも吹き飛んで{A_act}。",
    "{A_sub}の途中でふと「{A_pun}」と思いつき、なんだか楽しくなって{A_act}。",
    "{B}を眺めながら「{A_pun}！」と呟いたら、周りの空気も和んで{A_act}。",
]

# 辞書にない単語用。お題ワード {W} を必ず複数回含む「反復型」で、
# 意味が通る範囲で言葉のリズムを作る（出現回数の採点にも強い）。
DYNAMIC_PUN_TEMPLATES: List[Dict[str, str]] = [
    {
        "pun": "{W}は{W}でも、{W}だからこそ{W}らしい！",
        "sub": "{W}の準備",
        "act": "最後までバッチリ完成させた",
    },
    {
        "pun": "{W}と聞いて、思わず「{W}？{W}！」と二度見した",
        "sub": "目の前の{W}",
        "act": "みんなから拍手喝采を浴びた",
    },
    {
        "pun": "{W}だけに、{W}しないで{W}しよう！",
        "sub": "{W}のクオリティ",
        "act": "いい感じに仕上がった",
    },
    {
        "pun": "{W}を制する者は{W}を制す！つまり{W}が最強",
        "sub": "{W}との相性",
        "act": "過去最高スピードで片付いた",
    },
    {
        "pun": "{W}の{W}による{W}のための一日",
        "sub": "{W}の魅力",
        "act": "結局どっぷりハマってしまった",
    },
]

# 回数・文字数が足りないときの修復用フレーズ
_REPAIR_TAILS: List[str] = [
    "ここで一言、{W}！",
    "しかも{W}だから、もう一回{W}！",
    "というわけで、{W}でした。",
]
_PAD_FILLERS: List[str] = [
    "ちなみに、これは{W}だけにちょっとした自信作です。",
    "もう一度言います、{W}！",
]


# ==========================
# 補助関数
# ==========================
def _normalize_words(values: Any) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        out = [v.strip() for v in re.split(r"[,、\s]+", values)]
        return [v for v in out if v and v != "（自由なお題）"]
    if isinstance(values, (list, tuple, set)):
        res: List[str] = []
        for v in values:
            if isinstance(v, str):
                vv = v.strip()
                if vv and vv != "（自由なお題）":
                    res.append(vv)
        return res
    return []


def _extract_requested_count(raw_message: str, default: int = 1) -> int:
    if not raw_message:
        return default
    m = re.search(r"(\d+)\s*(?:個|つ|連発|本|件|発)", str(raw_message))
    if m:
        try:
            return max(1, min(int(m.group(1)), 15))
        except ValueError:
            pass
    return default


def _strip_numbering(line: str) -> str:
    return re.sub(r"^\d+[\.\s、:：]+", "", line.strip())


def _extract_past_gags_from_state(state: Any, rules: Dict[str, Any]) -> List[str]:
    past: List[str] = list(_RECENT_GENERATED_GAGS)

    rule_past = rules.get("past_gags")
    if isinstance(rule_past, list):
        past.extend(str(x) for x in rule_past if x)

    if state is not None:
        history = getattr(state, "history", None)
        if isinstance(history, list):
            for item in history[-20:]:
                if isinstance(item, dict) and item.get("role") == "assistant":
                    content = str(item.get("content", "")).strip()
                    for line in content.splitlines():
                        clean_line = _strip_numbering(line)
                        if clean_line:
                            past.append(clean_line)
    return past


def _pick_words(
    profile: Optional[GagRuleProfile],
    rules: Dict[str, Any],
    raw_user_message: str = "",
) -> List[str]:
    """
    優先順: profile.target_words → rules["target_words"] → 発話中の既知語 → ランダム補充
    """
    picked: List[str] = []
    if profile is not None:
        picked.extend(_normalize_words(getattr(profile, "target_words", None)))
        picked.extend(_normalize_words(getattr(profile, "required_words", None)))
    picked.extend(_normalize_words(rules.get("target_words")))

    if raw_user_message:
        for known_word in DEFAULT_WORD_BANK:
            if known_word in raw_user_message and known_word not in picked:
                picked.append(known_word)

    uniq_picked: List[str] = []
    for w in picked:
        if w not in uniq_picked:
            uniq_picked.append(w)

    bank = [w for w in DEFAULT_WORD_BANK if w not in uniq_picked]
    random.shuffle(bank)
    return (uniq_picked + bank)[: max(4, len(uniq_picked))]


def _get_pun_info(word: str) -> Dict[str, str]:
    if word in PUN_KNOWLEDGE_BASE:
        return PUN_KNOWLEDGE_BASE[word]
    for k, v in PUN_KNOWLEDGE_BASE.items():
        if k in word or word in k:
            return v
    tmpl = random.choice(DYNAMIC_PUN_TEMPLATES)
    return {
        "pun": tmpl["pun"].format(W=word),
        "sub": tmpl["sub"].format(W=word),
        "act": tmpl["act"].format(W=word),
    }


def _make_word_slots(words: List[str]) -> Dict[str, str]:
    w_a = words[0] if len(words) > 0 else "GitHub Copilot"
    w_b = words[1] if len(words) > 1 else "PR"
    w_c = words[2] if len(words) > 2 else "雨"
    w_d = words[3] if len(words) > 3 else "merge"

    info_a = _get_pun_info(w_a)
    info_b = _get_pun_info(w_b)

    return {
        "A": w_a, "B": w_b, "C": w_c, "D": w_d,
        "A_pun": info_a["pun"], "A_sub": info_a["sub"], "A_act": info_a["act"],
        "B_pun": info_b["pun"], "B_sub": info_b["sub"], "B_act": info_b["act"],
    }


def _choose_pattern(topic: str) -> str:
    if topic == "github_copilot":
        return random.choice(PATTERN_LIBRARY_GITHUB + PATTERN_LIBRARY)
    if topic == "daily":
        return random.choice(PATTERN_LIBRARY_DAILY + PATTERN_LIBRARY)
    return random.choice(PATTERN_LIBRARY + PATTERN_LIBRARY_GITHUB + PATTERN_LIBRARY_DAILY)


def _build_text(topic: str, words: List[str]) -> str:
    slots = _make_word_slots(words)
    pattern = _choose_pattern(topic)
    try:
        return pattern.format(**slots)
    except Exception:
        return random.choice(PATTERN_LIBRARY).format(**slots)


def _similarity_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def is_novel_candidate(candidate: str, past_gags: List[str], threshold: float = 0.68) -> bool:
    for past in past_gags:
        if not past:
            continue
        if candidate == past or _similarity_ratio(candidate, past) >= threshold:
            return False
    return True


def _record_generated_gag(gag_text: str) -> None:
    for line in str(gag_text).splitlines():
        clean = _strip_numbering(line)
        if clean and clean not in _RECENT_GENERATED_GAGS:
            _RECENT_GENERATED_GAGS.append(clean)
    while len(_RECENT_GENERATED_GAGS) > _MAX_RECENT_CACHE:
        _RECENT_GENERATED_GAGS.pop(0)


# ==========================
# 採点条件に合わせた制約チェック & 修復
# ==========================
def _constraint_words(profile: Optional[GagRuleProfile], rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """(必須ワード, 出現回数を数えるワード) を返す。"""
    required = _normalize_words(getattr(profile, "required_words", None)) if profile else []
    targets = _normalize_words(getattr(profile, "target_words", None)) if profile else []
    if not targets:
        targets = _normalize_words(rules.get("target_words"))
    if not required:
        required = _normalize_words(rules.get("required_words"))
    return required, targets


def _need_occurrences(rules: Dict[str, Any]) -> int:
    try:
        rep = int(rules.get("repeat_count", 1) or 1)
        mn = int(rules.get("minimum_use", 0) or 0)
    except (TypeError, ValueError):
        return 1
    return max(rep, mn, 1)


def _count_occurrences(text: str, words: List[str]) -> int:
    return sum(text.count(w) for w in words if w)


def _char_range(profile: Optional[GagRuleProfile]) -> Tuple[Optional[int], Optional[int]]:
    lo = getattr(profile, "min_characters", None) if profile else None
    hi = getattr(profile, "max_characters", None) if profile else None
    return lo, hi


def _heuristic_score(text: str, profile: Optional[GagRuleProfile], rules: Dict[str, Any]) -> float:
    """
    GagRuleEngine の採点を呼べない場所で候補を比較するための簡易スコア。
    必須語・出現回数・文字数レンジ・リズム要素（！「」・繰り返し）を見る。
    """
    if not text:
        return 0.0
    required, targets = _constraint_words(profile, rules)
    need = _need_occurrences(rules)
    lo, hi = _char_range(profile)
    n = len(text)
    score = 40.0

    if required:
        hit = sum(1 for w in required if w in text)
        score += 25.0 * hit / len(required)
    else:
        score += 25.0

    if targets:
        occ = _count_occurrences(text, targets)
        score += 20.0 if occ >= need else 20.0 * occ / max(need, 1)
    else:
        score += 20.0

    in_range = (lo is None or n >= lo) and (hi is None or n <= hi)
    if in_range:
        score += 10.0
    # 範囲指定がないときは 20〜70 字をちょうどよい長さとみなす
    if lo is None and hi is None and 20 <= n <= 70:
        score += 3.0

    if "！" in text or "？" in text:
        score += 1.0
    if "「" in text and "」" in text:
        score += 1.0
    return score


def _repair_text(text: str, profile: Optional[GagRuleProfile], rules: Dict[str, Any]) -> str:
    """必須語・出現回数・文字数が不足していたら、自然な短文を足して補う。"""
    if not text:
        return text
    required, targets = _constraint_words(profile, rules)
    need = _need_occurrences(rules)
    lo, hi = _char_range(profile)
    out = text.strip()

    # 1. 必須ワード
    for w in required:
        if w not in out:
            out += f"ここで一言、{w}！"

    # 2. 出現回数
    if targets:
        w = targets[0]
        guard = 0
        while _count_occurrences(out, targets) < need and guard < 6:
            out += random.choice(_REPAIR_TAILS).format(W=w)
            guard += 1

    # 3. 文字数: 長すぎる場合は文末で切る（必須語が消えない場合のみ）
    if hi is not None and len(out) > hi:
        cut = out[:hi]
        idx = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"))
        if idx >= 0:
            cut = cut[: idx + 1]
        if all(w in cut for w in required) and (not targets or _count_occurrences(cut, targets) >= need):
            out = cut

    # 4. 文字数: 短すぎる場合は補足を足す
    if lo is not None and len(out) < lo and targets:
        guard = 0
        while len(out) < lo and guard < 4:
            out += random.choice(_PAD_FILLERS).format(W=targets[0])
            guard += 1
        if hi is not None and len(out) > hi:
            out = out[:hi]

    return out


# ==========================
# ルールベース候補生成
# ==========================
def build_novel_candidates(
    words: List[str],
    topic: str,
    past_gags: List[str],
    count: int = 5,
    max_attempts: int = 60,
    profile: Optional[GagRuleProfile] = None,
    rules: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    複数候補を生成し、過去・今回リスト内で似ていないものだけ残す。
    profile / rules があれば制約適合度の高い候補を優先して採用する。
    """
    rules = rules or {}
    candidates: List[str] = []
    attempts = 0

    pool = list(words)
    for w in DEFAULT_WORD_BANK:
        if w not in pool:
            pool.append(w)

    # ユーザー指定語は常に主語に使う候補として優先
    fixed = _normalize_words(getattr(profile, "target_words", None)) if profile else []
    used_primary_words = set()

    def _make(primary: str) -> str:
        others = [w for w in pool if w != primary]
        random.shuffle(others)
        text = _build_text(topic, [primary] + others[:3])
        return _repair_text(text, profile, rules) if profile is not None else text

    while attempts < max_attempts and len(candidates) < count:
        attempts += 1
        if fixed:
            primary = fixed[len(candidates) % len(fixed)] if attempts <= len(fixed) * 3 else random.choice(pool)
        else:
            unused = [w for w in pool if w not in used_primary_words] or list(pool)
            if len(unused) == len(pool):
                used_primary_words.clear()
            primary = random.choice(unused)

        # 同じ主語で数案作り、制約適合度が最高のものを選ぶ
        trials = [_make(primary) for _ in range(3)]
        trials.sort(key=lambda t: _heuristic_score(t, profile, rules), reverse=True)
        candidate = trials[0]

        if candidate and is_novel_candidate(candidate, past_gags + candidates):
            candidates.append(candidate)
            used_primary_words.add(primary)

    while len(candidates) < count and attempts < max_attempts + 20:
        attempts += 1
        random.shuffle(pool)
        candidate = _build_text(topic, pool[:4])
        if profile is not None:
            candidate = _repair_text(candidate, profile, rules)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    if not candidates:
        candidates = [_build_text(topic, pool[:4])]

    return candidates[:count]


def synthesize_fallback_gag(profile: GagRuleProfile, rules: Dict[str, Any]) -> str:
    words = _pick_words(profile, rules)
    topic = str(rules.get("topic", "general"))
    past_gags = _extract_past_gags_from_state(None, rules)
    cands = build_novel_candidates(
        words, topic, past_gags=past_gags, count=1, profile=profile, rules=rules
    )
    result = cands[0]
    _record_generated_gag(result)
    return result


# ==========================
# 本体
# ==========================
def _try_llm(
    prompt: str,
    local_llm: Any,
    analysis: Dict[str, Any],
    state: Any,
    summary: Dict[str, Any],
    knowledge_data: Any,
    debug: Optional[Callable[[str], None]],
) -> Optional[str]:
    try:
        res = generate_with_local_llm(
            local_llm=local_llm,
            prompt_builder=None,
            user_message=prompt,
            analysis=analysis,
            state=state,
            summary=summary,
            knowledge_data=knowledge_data,
            debug=debug,
        )
        if res and str(res).strip():
            return str(res).strip()
    except Exception as exc:
        if debug:
            debug(f"generate_with_local_llm failed: {exc}")
    return None


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
    1. LLM を複数サンプル → 制約適合度が最高の候補を採用（不足は repair）
    2. fallback_generate（単発のみ）
    3. 音ペア辞書＋新規性保証＋制約修復のルールエンジン
    """
    requested_count = _extract_requested_count(raw_user_message, default=1)
    past_gags = _extract_past_gags_from_state(state, rules)

    # 1. Local LLM: 単発要求のときだけ。複数サンプルして最良を選ぶ
    if requested_count == 1 and local_llm is not None and callable(generate_with_local_llm):
        samples = int(rules.get("llm_samples", _DEFAULT_LLM_SAMPLES) or _DEFAULT_LLM_SAMPLES)
        pool: List[Tuple[float, str]] = []
        for _ in range(max(1, samples)):
            text = _try_llm(prompt, local_llm, analysis, state, summary, knowledge_data, debug)
            if text and is_novel_candidate(text, past_gags):
                pool.append((_heuristic_score(text, profile, rules), text))
        if pool:
            pool.sort(key=lambda x: x[0], reverse=True)
            best = _repair_text(pool[0][1], profile, rules)
            _record_generated_gag(best)
            return best, "local_llm+gag"

    # 2. fallback_generate（単発のみ）
    if requested_count == 1 and callable(fallback_generate):
        try:
            res = fallback_generate(
                user_message=raw_user_message,
                analysis={"intent": "gag_request", **(analysis or {})},
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
            )
            if res and str(res).strip():
                text = str(res).strip()
                if is_novel_candidate(text, past_gags):
                    text = _repair_text(text, profile, rules)
                    _record_generated_gag(text)
                    return text, "fallback_llm+gag"
        except Exception as exc:
            if debug:
                debug(f"fallback_generate failed: {exc}")

    # 3. ルールエンジン
    words = _pick_words(profile, rules, raw_user_message=raw_user_message)
    topic = str(rules.get("topic", "general"))
    candidates = build_novel_candidates(
        words=words,
        topic=topic,
        past_gags=past_gags,
        count=requested_count,
        profile=profile,
        rules=rules,
    )

    if requested_count > 1:
        final_text = "\n".join(f"{i + 1}. {gag}" for i, gag in enumerate(candidates))
    else:
        final_text = candidates[0]

    _record_generated_gag(final_text)
    return final_text, "rule_engine_gag"
