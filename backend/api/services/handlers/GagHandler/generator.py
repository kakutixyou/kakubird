# api/services/handlers/GagHandler/generator.py
# -*- coding: utf-8 -*-
"""
generator.py

設計方針:
1. 「単なるランダムな穴埋め」ではなく、「音の重なり（韻・語呂合わせ）」を核にして文を組み立てる
2. お題単語（A）に対して、音が似ている相方（A_pun）と関連動作（Action）をペアで割り当てる
3. 辞書にない未知の単語でも、反復・語尾変化で確実にダジャレとして成立する文型を用意する
4. state.history とモジュール内キャッシュの両方から past_gags を収集し、ネタ被りを徹底排除する
5. 「10個考えて」などの複数個リクエストにも自動で対応する
"""

from __future__ import annotations

import random
import re
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

from api.services.handlers.ChatHandler.llm_bridge import generate_with_local_llm
from .GagRuleEngine import GagRuleProfile

# プロセス内で直近に出したダジャレを記憶し、連続呼び出しでも絶対に被らせないキャッシュ
_RECENT_GENERATED_GAGS: List[str] = []
_MAX_RECENT_CACHE = 50

# ==========================
# 語彙の土台 & 音ペア辞書（ダジャレの核）
# ==========================
# key: お題ワード
# pun: 音が重なる語呂合わせワード
# sub: セットで使うと文脈が自然になる補助ワード
# act: オチに使える自然な述語・状況
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
# 文型ライブラリ（リズム・オチ重視）
# ==========================
# 重要:
# - {A}: お題単語
# - {A_pun}: {A}を使った音遊びフレーズ
# - {A_sub}: {A}に関連する情景ワード
# - {A_act}: オチの行動
# - {B}: 対比・掛け合わせ用の第2ワード
# - {B_pun}: {B}を使った音遊びフレーズ

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

# 辞書にない未知のお題ワード（例：「みかん」「布団」「Python」など）が来た時の万能ダジャレ生成テンプレート
DYNAMIC_PUN_TEMPLATES: List[Dict[str, str]] = [
    {
        "pun": "{W}が{W}（みかん・未完）のままじゃ終われない",
        "sub": "{W}の準備",
        "act": "最後までバッチリ完成させた",
    },
    {
        "pun": "{W}だけに、{W}（いい感）じに仕上がった",
        "sub": "{W}のクオリティ",
        "act": "みんなから拍手喝采を浴びた",
    },
    {
        "pun": "{W}を見たら、心が「{W}（ドカン）」と盛り上がった",
        "sub": "目の前の{W}",
        "act": "テンション最高潮で乗り切った",
    },
    {
        "pun": "{W}のことが気になって、{W}（いかん）ともしがたい",
        "sub": "{W}の魅力",
        "act": "結局どっぷりハマってしまった",
    },
    {
        "pun": "{W}を使って、{W}（快感）なリズムで作業中",
        "sub": "{W}との相性",
        "act": "過去最高スピードで片付いた",
    },
]


# ==========================
# 補助関数
# ==========================
def _normalize_words(values: Any) -> List[str]:
    if values is None:
        return []

    if isinstance(values, str):
        # カンマ・読点・空白で分割
        out = [v.strip() for v in re.split(r"[,、\s]+", values)]
        return [v for v in out if v and v != "（自由なお題）"]

    if isinstance(values, list):
        out: List[str] = []
        for v in values:
            if isinstance(v, str):
                vv = v.strip()
                if vv and vv != "（自由なお題）":
                    out.append(vv)
        return out

    return []


def _extract_requested_count(raw_message: str, default: int = 1) -> int:
    """
    ユーザーのメッセージから「10個」「5つ」「3連発」などの要求個数を抽出する（最大15個）。
    """
    if not raw_message:
        return default
    m = re.search(r"(\d+)\s*(?:個|つ|連発|本|件|発)", str(raw_message))
    if m:
        try:
            val = int(m.group(1))
            return max(1, min(val, 15))
        except ValueError:
            pass
    return default


def _extract_past_gags_from_state(state: Any, rules: Dict[str, Any]) -> List[str]:
    """
    state.history、rules["past_gags"]、およびモジュール内キャッシュから
    過去に出力したダジャレ一覧を集める。
    """
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
                    if content:
                        # 複数行の場合は行ごとに分割して登録
                        for line in content.splitlines():
                            clean_line = re.sub(r"^\d+[\.\s、:：]+", "", line.strip())
                            if clean_line:
                                past.append(clean_line)
    return past


def _pick_words(
    profile: Optional[GagRuleProfile],
    rules: Dict[str, Any],
    raw_user_message: str = "",
) -> List[str]:
    """
    語彙は次の優先順で選ぶ:
    1. profile.target_words
    2. rules["target_words"]
    3. ユーザー発話に含まれる辞書登録ワード
    4. DEFAULT_WORD_BANK からランダム選出
    """
    picked: List[str] = []

    if profile is not None:
        picked.extend(_normalize_words(getattr(profile, "target_words", None)))

    picked.extend(_normalize_words(rules.get("target_words")))

    # ユーザー発話の中に既知の単語があれば優先採用
    if raw_user_message:
        for known_word in DEFAULT_WORD_BANK:
            if known_word in raw_user_message and known_word not in picked:
                picked.append(known_word)

    # 重複除去しつつ順序維持
    uniq_picked: List[str] = []
    for w in picked:
        if w not in uniq_picked:
            uniq_picked.append(w)

    # 4語に満たない場合はワードバンクから補充
    bank = [w for w in DEFAULT_WORD_BANK if w not in uniq_picked]
    random.shuffle(bank)
    return (uniq_picked + bank)[: max(4, len(uniq_picked))]


def _get_pun_info(word: str) -> Dict[str, str]:
    """
    お題ワードに対する音遊び情報（pun, sub, act）を取得する。
    辞書にない未知の単語でも動的テンプレートで必ずダジャレ化する。
    """
    if word in PUN_KNOWLEDGE_BASE:
        return PUN_KNOWLEDGE_BASE[word]

    # 部分一致チェック
    for k, v in PUN_KNOWLEDGE_BASE.items():
        if k in word or word in k:
            return v

    # 未知の単語向け動的ダジャレ生成
    tmpl = random.choice(DYNAMIC_PUN_TEMPLATES)
    return {
        "pun": tmpl["pun"].format(W=word),
        "sub": tmpl["sub"].format(W=word),
        "act": tmpl["act"].format(W=word),
    }


def _make_word_slots(words: List[str]) -> Dict[str, str]:
    """
    A/B/C/D の基本スロットに加え、ダジャレ用の音遊びスロット（A_pun, A_sub, A_act 等）を生成する。
    既存のカスタム文型（{A}〜{D}のみを使うもの）とも100%後方互換性を保つ。
    """
    w_a = words[0] if len(words) > 0 else "GitHub Copilot"
    w_b = words[1] if len(words) > 1 else "PR"
    w_c = words[2] if len(words) > 2 else "雨"
    w_d = words[3] if len(words) > 3 else "merge"

    info_a = _get_pun_info(w_a)
    info_b = _get_pun_info(w_b)

    return {
        "A": w_a,
        "B": w_b,
        "C": w_c,
        "D": w_d,
        "A_pun": info_a["pun"],
        "A_sub": info_a["sub"],
        "A_act": info_a["act"],
        "B_pun": info_b["pun"],
        "B_sub": info_b["sub"],
        "B_act": info_b["act"],
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
        fallback = random.choice(PATTERN_LIBRARY)
        return fallback.format(**slots)


def _similarity_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def is_novel_candidate(candidate: str, past_gags: List[str], threshold: float = 0.68) -> bool:
    """
    新規性チェック。過去のネタと似すぎる場合は False。
    threshold を 0.68 に引き締め、同じお題や同じ文型の連続採用を防ぐ。
    """
    for past in past_gags:
        if not past:
            continue
        if candidate == past or _similarity_ratio(candidate, past) >= threshold:
            return False
    return True


def _record_generated_gag(gag_text: str) -> None:
    """生成したダジャレをキャッシュに登録し、次回以降の重複を防ぐ。"""
    for line in str(gag_text).splitlines():
        clean = re.sub(r"^\d+[\.\s、:：]+", "", line.strip())
        if clean and clean not in _RECENT_GENERATED_GAGS:
            _RECENT_GENERATED_GAGS.append(clean)
    while len(_RECENT_GENERATED_GAGS) > _MAX_RECENT_CACHE:
        _RECENT_GENERATED_GAGS.pop(0)


def build_novel_candidates(
    words: List[str],
    topic: str,
    past_gags: List[str],
    count: int = 5,
    max_attempts: int = 60,
) -> List[str]:
    """
    複数候補を生成して、過去および今回のリスト内で似ていないものだけ残す。
    たくさん要求された場合（例：10個）でも主語（A）が毎回変わるようにローテーションする。
    """
    candidates: List[str] = []
    attempts = 0

    # 候補生成用の語彙プールを広めに確保（10個要求されても主語が被らないようにする）
    pool = list(words)
    for w in DEFAULT_WORD_BANK:
        if w not in pool:
            pool.append(w)

    used_primary_words = set()

    while attempts < max_attempts and len(candidates) < count:
        attempts += 1

        # まだ主語(A)として使っていない単語を優先的に先頭にする
        unused_primaries = [w for w in pool if w not in used_primary_words]
        if not unused_primaries:
            used_primary_words.clear()
            unused_primaries = list(pool)

        primary = random.choice(unused_primaries)
        others = [w for w in pool if w != primary]
        random.shuffle(others)

        local_words = [primary] + others[:3]
        candidate = _build_text(topic, local_words)

        # 過去のダジャレ ＋ 今回すでに採用した候補 の両方に対して類似度チェック
        combined_past = past_gags + candidates
        if candidate and is_novel_candidate(candidate, combined_past):
            candidates.append(candidate)
            used_primary_words.add(primary)

    # 万が一目標数に届かなかった場合は閾値を緩めて補充
    while len(candidates) < count and attempts < max_attempts + 20:
        attempts += 1
        random.shuffle(pool)
        candidate = _build_text(topic, pool[:4])
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    if not candidates:
        fallback = _build_text(topic, pool[:4])
        candidates = [fallback]

    return candidates[:count]


# ==========================
# fallback 生成
# ==========================
def synthesize_fallback_gag(profile: GagRuleProfile, rules: Dict[str, Any]) -> str:
    """
    最後の砦となる fallback 生成。
    """
    words = _pick_words(profile, rules)
    topic = str(rules.get("topic", "general"))
    past_gags = _extract_past_gags_from_state(None, rules)
    cands = build_novel_candidates(words, topic, past_gags=past_gags, count=1)
    result = cands[0]
    _record_generated_gag(result)
    return result


# ==========================
# 本体の生成関数
# ==========================
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
    1. local_llm が使えれば使う
    2. 複数個リクエスト（「10個考えて」など）や LLM 失敗時は、
       音ペア辞書＋新規性保証つきの build_novel_candidates で高品質なダジャレを返す
    """
    requested_count = _extract_requested_count(raw_user_message, default=1)
    past_gags = _extract_past_gags_from_state(state, rules)

    # 1. Local LLM 試行
    if local_llm is not None and callable(generate_with_local_llm):
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
                text = str(res).strip()
                if is_novel_candidate(text, past_gags):
                    _record_generated_gag(text)
                    return text, "local_llm+gag"
        except Exception as exc:
            if debug:
                debug(f"generate_with_local_llm failed: {exc}")

    # 2. 複数個要求されていない場合のみ、単発の fallback_generate を試行
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
                    _record_generated_gag(text)
                    return text, "fallback_llm+gag"
        except Exception as exc:
            if debug:
                debug(f"fallback_generate failed: {exc}")

    # 3. 音ペア辞書＆重複排除エンジンで生成
    words = _pick_words(profile, rules, raw_user_message=raw_user_message)
    topic = str(rules.get("topic", "general"))
    candidates = build_novel_candidates(
        words=words,
        topic=topic,
        past_gags=past_gags,
        count=requested_count,
    )

    if requested_count > 1:
        final_text = "\n".join(f"{i + 1}. {gag}" for i, gag in enumerate(candidates))
    else:
        final_text = candidates[0]

    _record_generated_gag(final_text)
    return final_text, "rule_engine_gag"