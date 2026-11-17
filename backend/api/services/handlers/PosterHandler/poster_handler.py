# backend/api/services/handlers/poster_handler.py
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# to-model-app/src を import パスに追加
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[4] if len(_HERE.parents) >= 5 else Path.cwd()
_TO_MODEL_SRC = _PROJECT_ROOT / "to-model-app" / "src"
if _TO_MODEL_SRC.is_dir() and str(_TO_MODEL_SRC) not in sys.path:
    sys.path.insert(0, str(_TO_MODEL_SRC))

from tools.poster_builder_tool import PosterSpec, create_and_store_poster_kit

# ==========================================
# to_model 各モジュールの安全な動的インポート
# ==========================================
try:
    from to_model.grammar.reference_resolver import ReferenceResolver
except Exception:
    ReferenceResolver = None

try:
    from to_model.intent.predict import predict_intent
except Exception:
    predict_intent = None

try:
    from to_model.reasoning.decision_policy import DecisionPolicy
except Exception:
    DecisionPolicy = None

try:
    from to_model.reasoning.jp_nlu_memo import extract_structured_memo
except Exception:
    extract_structured_memo = None

try:
    from to_model.adapters.local_model_adapter import LocalModelAdapter
except Exception:
    LocalModelAdapter = None


# 文脈トーン別の配色・スタイル定義
CONTEXT_STYLE_MAP: Dict[str, Dict[str, Any]] = {
    "nocode_business": {
        "pattern": "nocode_tool",
        "theme_hex": "0F766E",  # ティールグリーン
        "accent_hex": "FEF08A",
        "sub_bg_hex": "F0FDFA",
        "subtitle_default": "＼ 手入力・集計の手間をゼロにする業務改善 ／",
    },
    "tournament_hype": {
        "pattern": "tournament",
        "theme_hex": "991B1B",  # クリムゾンレッド
        "accent_hex": "FDE047",
        "sub_bg_hex": "FEF2F2",
        "subtitle_default": "🔥 挑戦者求む！エントリー受付中 🔥",
    },
    "senior_friendly": {
        "pattern": "event_workshop",
        "theme_hex": "1E3A8A",  # 高コントラスト濃紺
        "accent_hex": "FEF08A",
        "sub_bg_hex": "EFF6FF",
        "subtitle_default": "＼ 初めての方・シニアの方も安心してご参加いただけます ／",
    },
    "catalog_showcase": {
        "pattern": "grid_catalog",
        "theme_hex": "9A3412",  # オレンジブラウン
        "accent_hex": "FDE047",
        "sub_bg_hex": "FFF7ED",
        "subtitle_default": "＼ 注目のブース・機能を一挙ご紹介 ／",
    },
    "medical_welfare": {
        "pattern": "event_workshop",
        "theme_hex": "0369A1",  # 清潔感のあるスカイブルー
        "accent_hex": "E0F2FE",
        "sub_bg_hex": "F0F9FF",
        "subtitle_default": "＼ 地域の健康と安心をサポートするご案内 ／",
    },
}


class ToModelPosterContextAnalyzer:
    """
    to-model-app の grammar / intent / reasoning / adapter を使って、
    会話履歴と現在の発話から PosterSpec を動的に構築・変化させるクラス。
    """

    def __init__(self) -> None:
        self.ref_resolver = ReferenceResolver() if ReferenceResolver else None
        self.local_adapter = LocalModelAdapter() if LocalModelAdapter else None

    def resolve_context_and_build_spec(
        self,
        message: str,
        current_signals: Dict[str, Any],
        loaded_knowledge: List[Dict[str, Any]],
    ) -> Tuple[PosterSpec, Dict[str, Any]]:
        """
        1. 直前のPosterSpec（文脈引き継ぎ）の復元
        2. 指示語（これ・さっきの）の解決
        3. to_model による文脈スタイル＆レイアウト決定
        4. 詳細パラメータの上書き
        """
        trace_info: Dict[str, Any] = {"used_modules": []}

        # --------------------------------------------------
        # Step 1: 前回のポスター状態があれば引き継ぐ（「色を赤に変えて」等の差分指示対応）
        # --------------------------------------------------
        last_poster_dict = current_signals.get("last_poster_spec")
        if isinstance(last_poster_dict, dict) and any(
            w in message for w in ("変えて", "変更", "さっきの", "同じ内容で", "パターンだけ", "色だけ")
        ):
            spec = PosterSpec(**{
                k: v for k, v in last_poster_dict.items() if k in PosterSpec.__dataclass_fields__
            })
            trace_info["used_modules"].append("signal_state_restore (差分更新)")
        else:
            spec = PosterSpec()

        # --------------------------------------------------
        # Step 2: ReferenceResolver で会話履歴から「それ・さっきのテーマ」を解決
        # --------------------------------------------------
        resolved_text = message
        conv_state = current_signals.get("conversation_state", {})
        history_list = conv_state.get("history", []) if isinstance(conv_state, dict) else []

        if self.ref_resolver and hasattr(self.ref_resolver, "resolve"):
            try:
                resolved_text = self.ref_resolver.resolve(message, history=history_list)
                trace_info["used_modules"].append("to_model.grammar.ReferenceResolver")
            except Exception:
                pass
        elif history_list and any(w in message for w in ("これ", "それ", "さっきの", "この")):
            # フォールバック：直前のユーザー発話またはAI応答のトピックを結合
            last_turns = " ".join(str(h.get("content", "")) for h in history_list[-3:] if isinstance(h, dict))
            resolved_text = f"{message}\n[直前の文脈: {last_turns[:300]}]"
            trace_info["used_modules"].append("context_history_fallback")

        # --------------------------------------------------
        # Step 3: to_model.intent / decision_policy で文脈トーンを判定
        # --------------------------------------------------
        context_key = self._classify_context_style(resolved_text, current_signals)
        trace_info["detected_context"] = context_key

        style_cfg = CONTEXT_STYLE_MAP.get(context_key, CONTEXT_STYLE_MAP["senior_friendly"])
        spec.pattern = style_cfg["pattern"]
        spec.theme_hex = style_cfg["theme_hex"]
        spec.accent_hex = style_cfg["accent_hex"]
        spec.sub_bg_hex = style_cfg["sub_bg_hex"]
        if spec.subtitle == PosterSpec.subtitle:
            spec.subtitle = style_cfg["subtitle_default"]

        # --------------------------------------------------
        # Step 4: jp_nlu_memo またはルールで文脈からタイトル・3大ポイントを動的生成
        # --------------------------------------------------
        self._populate_content_from_context(spec, resolved_text, context_key, loaded_knowledge, trace_info)

        return spec, trace_info

    def _classify_context_style(self, text: str, signals: Dict[str, Any]) -> str:
        t_low = text.lower()

        # 1. to_model.intent.predict が利用可能なら推論を実行
        if callable(predict_intent):
            try:
                pred = predict_intent(text)
                pred_label = str(pred.get("label") if isinstance(pred, dict) else pred)
                if "nocode" in pred_label or "tool" in pred_label:
                    return "nocode_business"
                if "tournament" in pred_label or "game" in pred_label:
                    return "tournament_hype"
                if "medical" in pred_label:
                    return "medical_welfare"
            except Exception:
                pass

        # 2. 文脈キーワード＆ターゲット層判定
        if any(w in t_low for w in ("ノーコード", "appsheet", "ツール", "自動化", "業務", "システム", "アプリ")):
            return "nocode_business"
        if any(w in t_low for w in ("大会", "コンテスト", "ハッカソン", "選手権", "バトル", "eスポーツ", "賞金")):
            return "tournament_hype"
        if any(w in t_low for w in ("カタログ", "一覧", "ブース", "マルシェ", "4選", "グリッド", "比較")):
            return "catalog_showcase"
        if any(w in t_low for w in ("健康", "医療", "相談会", "検診", "福祉", "ケア")):
            return "medical_welfare"
        return "senior_friendly"

    def _populate_content_from_context(
        self,
        spec: PosterSpec,
        resolved_text: str,
        context_key: str,
        loaded_knowledge: List[Dict[str, Any]],
        trace_info: Dict[str, Any],
    ) -> None:
        # 1. 文脈別の初期デフォルト文言セット
        if context_key == "nocode_business":
            spec.title = "プログラミング不要！業務改善ノーコードツール導入ガイド"
            spec.overview_body = (
                "現場の担当者が自分の手でスケジュール管理・電話帳・集計シートを構築・改善できる仕組みです。"
            )
            spec.points = [
                ("STEP 1. 既存シートをそのまま連携", "普段使っているスプレッドシートや表から自動で画面を生成します。"),
                ("STEP 2. スマホ・PCの両方で共有", "外出先や現場の端末からワンタップで予定や記録を入力できます。"),
                ("STEP 3. 集計・レポートも完全自動化", "二重入力や転記ミスをなくし、本来の業務に集中できます。"),
            ]
        elif context_key == "tournament_hype":
            spec.title = "特別杯・コンテスト出場者＆観覧エントリー大募集！"
            spec.overview_body = (
                "日頃のアイデアやスキルをぶつけ合う特別イベント！初心者部門・熟練者部門の2トラックで開催します。"
            )
            spec.points = [
                ("1. 予選ラウンド＆デモ体験", "各ブース・ブロックに分かれて作品を披露します。"),
                ("2. 決勝ステージ＆投票", "会場の参加者と審査員の投票でグランプリを決定します。"),
                ("3. 表彰式・参加者交流会", "入賞者への特典贈呈と情報交換タイムを実施します。"),
            ]
        elif context_key == "catalog_showcase":
            spec.title = "注目の4大プログラム＆出展ブースご案内"
            spec.points = [
                ("① 体験・ワークショップ枠", "初心者でも30分で楽しく作れるハンズオンコーナーです。"),
                ("② 作品・ツール展示枠", "実際に動くデモ機や最新事例を自由に触って体験できます。"),
                ("③ 個別相談・サポート枠", "普段の困りごとや導入手順をスタッフに直接相談できます。"),
                ("④ ステージ・特別企画枠", "時間限定の実演イベントや抽選会を開催します。"),
            ]

        # 2. KnowledgeRouter が関連知識（イベント情報等）を拾っていれば概要に反映
        if loaded_knowledge:
            first_kb = loaded_knowledge[0]
            kb_desc = str(first_kb.get("description") or "")
            if kb_desc and len(kb_desc) > 10:
                spec.overview_body = kb_desc[:160]
                trace_info["used_modules"].append(f"KnowledgeRouter({first_kb.get('title')})")

        # 3. ユーザー発話内の明示指定を最優先で上書き
        title_m = re.search(r"(?:タイトル|題名)\s*[:：]\s*([^\n]+)", resolved_text) or re.search(
            r"[「『]([^」』]{2,45})[」』]", resolved_text
        )
        if title_m:
            spec.title = title_m.group(1).strip()

        sub_m = re.search(r"(?:サブタイトル|キャッチ)\s*[:：]\s*([^\n]+)", resolved_text)
        if sub_m:
            spec.subtitle = sub_m.group(1).strip()

        date_m = re.search(r"(?:日時|日程|開催日)\s*[:：]\s*([^\n]+)", resolved_text)
        if date_m:
            spec.date_str = date_m.group(1).strip()

        venue_m = re.search(r"(?:会場|場所)\s*[:：]\s*([^\n]+)", resolved_text)
        if venue_m:
            spec.venue_str = venue_m.group(1).strip()

        url_m = re.search(r"(https?://[^\s\)」』]+)", resolved_text)
        if url_m:
            spec.qr_url = url_m.group(1).strip()

        # 明示的な色変更指示（「紫にして」「緑色に変えて」等）
        color_overrides = {
            "青": ("1E3A8A", "EFF6FF"),
            "緑": ("14532D", "F0FDF4"),
            "赤": ("991B1B", "FEF2F2"),
            "オレンジ": ("9A3412", "FFF7ED"),
            "紫": ("581C87", "FAF5FF"),
            "黒": ("0F172A", "F1F5F9"),
        }
        for c_kw, (m_hex, s_hex) in color_overrides.items():
            if f"{c_kw}色" in resolved_text or f"{c_kw}に" in resolved_text or f"{c_kw}系" in resolved_text:
                spec.theme_hex = m_hex
                spec.sub_bg_hex = s_hex
                break


class PosterGeneratorHandler:
    """
    ChatOrchestrator から呼び出され、to-model-app の文脈解析を通して
    ポスターの内容・レイアウトを動的に変化させ、ZIP (R2 / local) を返すハンドラー。
    """

    def __init__(self) -> None:
        self.analyzer = ToModelPosterContextAnalyzer()

    async def calculate_score(self, message: str, current_signals: Dict[str, Any] | None = None) -> int:
        text = (message or "").lower()
        if any(w in text for w in ("ポスター", "チラシ", "フライヤー", "poster", "flyer")):
            return 125
        # 直前にポスターを作っていて「色を赤に変えて」「2×2グリッドにして」と言われた場合も捕捉
        if isinstance(current_signals, dict) and current_signals.get("last_used_handler") == "PosterGeneratorHandler":
            if any(w in text for w in ("変えて", "変更", "グリッド", "大会風", "ノーコード風", "色")):
                return 115
        return 0

    def get_search_keywords(self, message: str) -> List[str]:
        return ["poster", "チラシ", "イベント"]

    async def handle(self, request: Any) -> Tuple[str, Dict[str, Any]]:
        message = str(getattr(request, "message", "") or "")
        current_signals = getattr(request, "current_signals", {})
        if not isinstance(current_signals, dict):
            current_signals = {}
        loaded_knowledge = getattr(request, "loaded_knowledge", [])
        if not isinstance(loaded_knowledge, list):
            loaded_knowledge = []

        # 1. to_model パイプラインで文脈から PosterSpec を構築
        spec, trace_info = self.analyzer.resolve_context_and_build_spec(
            message=message,
            current_signals=current_signals,
            loaded_knowledge=loaded_knowledge,
        )

        # 2. Word (.docx) 生成 ＆ R2 / ローカルZIP保存
        artifact = create_and_store_poster_kit(spec)

        # 3. 次ターンの「色だけ変えて」等の文脈維持のために PosterSpec を user_signals に保存
        current_signals["last_poster_spec"] = {
            "pattern": spec.pattern,
            "title": spec.title,
            "subtitle": spec.subtitle,
            "theme_hex": spec.theme_hex,
            "accent_hex": spec.accent_hex,
            "sub_bg_hex": spec.sub_bg_hex,
            "overview_title": spec.overview_title,
            "overview_body": spec.overview_body,
            "points": spec.points,
            "date_str": spec.date_str,
            "venue_str": spec.venue_str,
            "capacity_str": spec.capacity_str,
            "organizer_str": spec.organizer_str,
            "qr_url": spec.qr_url,
        }

        used_mods = ", ".join(trace_info.get("used_modules") or ["Rule+ContextEngine"])

        return (
            "project_build",
            {
                "message": (
                    f"🧠 **文脈連動ポスター生成完了**（コンテキスト判定: `{trace_info.get('detected_context')}` / レイアウト: `{spec.pattern}`）\n"
                    f"- **タイトル**: {spec.title}\n"
                    f"- **連動モジュール**: `{used_mods}`\n"
                    f"- **保存先**: `{artifact['storage']}` ({artifact['expires_note']})"
                ),
                "update_signals": current_signals,
                "blocks": [
                    {
                        "type": "ProjectDownloadBlock",
                        "props": {
                            "title": f"📦 {spec.title}",
                            "description": f"文脈判定: {trace_info.get('detected_context')} / パターン: {spec.pattern}",
                            "filename": artifact["filename"],
                            "downloadUrl": artifact["download_url"],
                            "storage": artifact["storage"],
                            "sizeKb": artifact["size_kb"],
                            "expiresNote": artifact["expires_note"],
                        },
                    },
                    {
                        "type": "MarkdownBlock",
                        "props": {
                            "content": (
                                f"### 📥 [{artifact['filename']} をダウンロードする]({artifact['download_url']})\n\n"
                                "💡 **文脈に応じた連続アレンジも可能です（そのまま続けて話しかけてください）：**\n"
                                "- 「タイトルはそのままで、**大会っぽく赤色**に変えて」\n"
                                "- 「**4枠のカタログ風**にレイアウトを変えて」\n"
                                "- 「会場を**吉祥寺コミュニティセンター**に変更して再発行して」"
                            )
                        },
                    },
                ],
            },
        )