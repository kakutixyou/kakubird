# js_handler.py
from email import message
from typing import Any, Dict, List, Optional, Tuple
import json
import os
import re
import traceback
from enum import Enum
from api.services.handlers.base_handler import BaseHandlerler import BaseHandler

# 2026年現在の公式推奨SDK（google-genai）を使用。環境に応じて適宜インポートを調整してください
# pip install google-genai
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False
    # async def can_handle(self, message: str) -> bool:
    #     msg_lower = message.lower()
    #     search_keywords = [
    #         "探して", "調べて", "検索して", "見つけて", 
    #         "教えて", "探したい", "検索", "似た"
    #     ]
    #     return "github" in msg_lower and any(k in msg_lower for k in search_keywords)
# 1. 定数・パス設定
_DIR = os.path.dirname(__file__)
_KEYWORDS_JSON = os.path.join(_DIR, "js_keywords.json")
JS_COMMANDS = {"/js", "/javascript", "/script", "/animate", "/interact"}

# 2. JSBehaviorStyle Enum (JSが担当する動的振る舞いのタイプ)
class JSBehaviorStyle(str, Enum):
    INTERACTIVE = "interactive" # クリック、モーダル、タブ切り替えなど
    ANIMATION = "animation" # スクロール連動、パーティクル、アニメーション
    VALIDATION = "validation" # フォームバリデーション、計算ロジック
    UTILITY = "utility" # ダークモード切り替え、タイマーなど
    NONE = "none" # JS不要

# 3. 外部JSONファイルのロード関数 (html_handlerと同等の設計)
def _load_json(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f" [JSHandler] {os.path.basename(filepath)} が見つかりません。デフォルト値で動作します。", flush=True)
        return {}
    except json.JSONDecodeError as e:
        print(f" [JSHandler] {os.path.basename(filepath)} のパースエラー: {e}", flush=True)
    return {}

# 起動時にJSONをメモリに読み込んでおく
_KW = _load_json(_KEYWORDS_JSON)

# 4. JSHandler 本体
class JSHandler(BaseHandler):

    __init__()

    estimate_size()

    calculate_score()

    _infer_behavior_style()

    _build_system_instruction()

    _build_user_prompt()

    _call_gemini()

    _clean_response()

    _validate_js()

    execute()
def estimate_size(self, message: str) -> int:
    if "アニメーション" in message or "派手に" in message:
        return 8000
    return 3000

async def calculate_score(self, message: str) -> int:
    """
    JSHandler が処理すべき確信度を返す（0～100）
    基本方針：
    ・/js /script などのコマンドは100点
    ・「動かす」「クリック」などの動的要望キーワードを検知してスコア化
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # ----------------------------------------------------
    # 1. コマンド指定は最優先
    # ----------------------------------------------------
    if any(msg_lower.startswith(cmd) for cmd in JS_COMMANDS):
        return 100

    # ----------------------------------------------------
    # 2. 動的処理・JSを「作りたい意図」があるか
    # ----------------------------------------------------
    intent_words = [
    # 日本語
    "動く", "動かす", "クリック", "チェンジ", "切り替え", "ポップアップ",
    "モーダル", "スライド", "アニメーション", "js", "javascript", "スクリプト",
    "タブ", "タイマー", "カウント", "バリデーション", "保存", "エフェクト",
    # 英語
    "click", "event", "modal", "slide", "animate", "animation", "js",
    "javascript", "script", "toggle", "darkmode", "scroll", "fade"
    ]

    intent_score = 0
    for w in intent_words:
        if w.lower() in msg_lower:
            intent_score += 1

    # 動的な意図が一切無いなら、JSHandlerの出番はないので0点
    if intent_score == 0:
        return 0

    score = 20 # 最低限のフックがあればベース20点

    # ----------------------------------------------------
    # 3. キーワード辞書(js_keywords.json) がある場合の加点ロジック
    # ----------------------------------------------------
    # トリガー言葉の検知 (html_handlerの設計を踏襲)
    triggers = _KW.get("triggers", {})
    trigger_words = triggers.get("ja", []) + triggers.get("en", [])

    trigger_hits = 0
    for t in trigger_words:
        if t.lower() in msg_lower:
            trigger_hits += 1
    score += trigger_hits * 15

    # 挙動（Behavior）キーワードの検知
    behavior_kw = _KW.get("behavior_keywords", {})
    behavior_hits = 0
    for _, data in behavior_kw.items():
        if not isinstance(data, dict): continue
    words = data.get("ja", []) + data.get("en", [])
    for w in words:
        if w.lower() in msg_lower:
            behavior_hits += 1
    score += behavior_hits * 10

    # ----------------------------------------------------
    # 4. 最終調整
    # ----------------------------------------------------
    score = max(score, 0)
    score = min(score, 100)
    return score

def _infer_behavior_style(self, message: str) -> JSBehaviorStyle:
    """ユーザーのメッセージから、どの系統のJSを求めているか推測する"""
    msg_lower = message.lower()

    if any(w in msg_lower for w in ["アニメーション", "動かす", "演出", "animate", "scroll"]):
        return JSBehaviorStyle.ANIMATION
    if any(w in msg_lower for w in ["フォーム", "チェック", "バリデーション", "validate", "input"]):
        return JSBehaviorStyle.VALIDATION
    if any(w in msg_lower for w in ["ダークモード", "タイマー", "カウント", "clock", "mode"]):
        return JSBehaviorStyle.UTILITY

    return JSBehaviorStyle.INTERACTIVE

    # ----------------------------------------------------
        # 5. メイン実行処理 (Gemini API 呼び出し)
        # ----------------------------------------------------
async def execute(self, message: str, generated_html: Optional[str] = None) -> str:
            """
            オーケストレーターから呼ばれるメイン処理。
            前段のWatson等が作った HTML コードをコンテキストとして受け取り、
            それにジャストフィットするJavaScriptをGeminiに生成させる。
            """
            if not self.client:
                return "/* [JSHandler Error] Gemini Client is not initialized. Check API Key. */"

            self.detected_style = self._infer_behavior_style(message)

            # HTMLの有無に応じたプロンプトの組み立て
            html_context = generated_html.strip() if generated_html else ""

            system_instruction = (
                "あなたは超一流のフロントエンドエンジニアです。\n"
                "提示された【HTML構造】を完全に理解し、【ユーザーの要望】を満たすピュアJavaScript（ES6+）を書いてください。\n\n"
                "【厳守ルール】\n"
                "1. 提供されたHTMLに存在するID、クラス、タグ名だけを正確にターゲットにしてください（存在しない要素へのquerySelectorは厳禁）。\n"
                "2. グローバル変数を汚染しないよう、コード全体を window.addEventListener('DOMContentLoaded', ...) 内にカプセル化してください。\n"
                "3. マークダウンの ```javascript ... ``` ブロックでコードのみを出力し、それ以外の解説テキストは一切出力しないでください。"
            )

            user_content = f"""
    【ユーザーの要望】: {message}
    【検知されたスタイル】: {self.detected_style.value}

    【対象のHTML構造】:
    ```html
    {html_context}
    """