import os
import json
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from .base_handler import BaseHandler
from ..inspectors.IntentInSpector import IntentInspector

# ---------------------------------------------------------
# 1. 定数・パス設定
# ---------------------------------------------------------
_DIR = os.path.dirname(__file__)
_JSON_DIR = os.path.abspath(os.path.join(_DIR, "..", "..", "..", "..", ".ai_memory", "html_etc"))

_KEYWORDS_JSON = os.path.join(_JSON_DIR, "html_keywords.json")
_THEMES_JSON = os.path.join(_JSON_DIR, "html_themes.json")
HTML_COMMANDS = {"/html", "/css", "/design"}

class SurfaceStyle(str, Enum):
    GLASS        = "glass"
    FROSTED_DARK = "frosted-dark"
    ELEVATED     = "elevated"
    BORDERED     = "bordered"
    FLAT         = "flat"
    GLOW         = "glow"
    NEUMORPHISM  = "neumorphism"
    PAPER        = "paper"

def _load_json(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [HTMLHandler] JSONロード失敗: {os.path.basename(filepath)} - {e}", flush=True)
        return {}

_KW = _load_json(_KEYWORDS_JSON)
_THEMES = _load_json(_THEMES_JSON)

# ---------------------------------------------------------
# 2. HTML / CSS テンプレート生成モック
# ---------------------------------------------------------
def _build_html(surface: SurfaceStyle, theme_name: str, message: str) -> str:
    return f"<div class='{surface.value}'>\n  <h1>{theme_name}</h1>\n  <p>HTML generated successfully.</p>\n</div>"

def _build_css(surface: SurfaceStyle, theme_name: str) -> str:
    base_vars = f"/* Theme: {theme_name} */\n"
    theme_data = _THEMES.get(surface.value, {})
    css_content = theme_data.get("css", "/* No CSS defined for this theme */\n:root {}")
    return base_vars + css_content

# ==========================================
# 3. HTMLHandler 本体
# ==========================================
class HTMLHandler(BaseHandler):
    def __init__(self):
        # Inspectorから受け取ったメタデータを保持する箱
        self.detected_surface: Optional[str] = None
        self.detected_theme:   Optional[str] = None
        self.detected_targets: List[str]     = []

    def estimate_size(self, message: str) -> int:
        if "cssのみ" in message:
            return 3000
        return 15000

    async def can_handle(self, message: str) -> bool:
        msg_lower = message.lower()
        if any(msg_lower.startswith(cmd) for cmd in HTML_COMMANDS):
            return True
        
        html_keywords = ["html", "ボタン", "button", "ui", "コンポーネント", "マークアップ", "一式作って"]
        return any(k in msg_lower for k in html_keywords)

    # ----------------------------------------------------
    # 🌟 Inspectorへの委譲による劇的ダイエット
    # ----------------------------------------------------
    async def calculate_score(self, message: str, signals=None) -> int:
        msg_lower = message.strip().lower()

        # 1. 絶対コマンドは強制100点（即決）
        if any(msg_lower.startswith(cmd) for cmd in HTML_COMMANDS):
            return 100

        # 2. Inspector（共通の審査員）に丸投げ
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        if analysis["mode"] == "ui_design":
            # Inspectorが見つけた要素を、handle実行時のために保存しておく
            self.detected_surface = analysis.get("surface")
            self.detected_theme = analysis.get("theme")
            self.detected_targets = analysis.get("targets", [])
            
            # Inspectorの安全なスコア（最大85点）を返す
            return analysis["score"]

        return 0

    # ----------------------------------------------------
    # 🌟 独自推論メソッドを排除し、Inspectorの恩恵をフル活用
    # ----------------------------------------------------
    async def handle(self, message: str) -> Tuple[str, Any]:
        print("⚡ HTML Handler 発動: HTML/CSSコードの生成を開始します")
        try:
            # 1. Inspectorが保存してくれた値を復元（なければデフォルト値）
            surface_str = self.detected_surface or "glass"
            theme_name = (self.detected_theme or surface_str).capitalize()
            targets = self.detected_targets

            # コマンドで直接タイトルが指定されている場合のフォールバック
            msg_lower = message.lower()
            for cmd in HTML_COMMANDS:
                if msg_lower.strip().startswith(cmd):
                    after = re.sub(rf"{re.escape(cmd)}\s*", "", message, flags=re.IGNORECASE).strip()
                    if after: 
                        theme_name = after[:60]
                        break

            # Enumへの安全なキャスト
            try:
                surface = SurfaceStyle(surface_str)
            except ValueError:
                surface = SurfaceStyle.GLASS

            # 2. CSSとHTMLの生成
            css_code = _build_css(surface, theme_name)
            
            if "button" in targets:
                html_code = f"<div class='{surface.value}' style='padding: 2rem; text-align: center;'>\n  <button class='btn' style='padding: 10px 20px; font-weight: bold;'>生成されたボタン</button>\n</div>"
            elif "card" in targets:
                html_code = f"<div class='{surface.value}' style='padding: 1.5rem; border-radius: 8px;'>\n  <h2>{theme_name} Card</h2>\n  <p>カードのダミーテキストです。</p>\n</div>"
            elif "form" in targets:
                html_code = f"<div class='{surface.value}' style='padding: 1.5rem;'>\n  <input type='text' placeholder='入力してください' style='margin-bottom: 10px; display: block;'/>\n  <button class='btn'>送信</button>\n</div>"
            else:
                html_code = _build_html(surface, theme_name, message)

            # 3. フロントエンドに返すブロック構造を作成
            chat_message = f"テーマ **{theme_name}** ({surface.value} スタイル) のUIコンポーネントを生成しました。\n\n"
            
            content = {
                "message": chat_message,
                "blocks": [
                    {
                        "type": "HtmlCssPreviewBlock",
                        "component_name": f"{theme_name} Component",
                        "html": html_code,
                        "css": css_code 
                    }
                ]
            }
            
            return "ui_code", content

        except Exception as e:
            traceback.print_exc()
            return "text", "HTMLの生成中にエラーが発生しました。"

    def _infer_surface(self, message: str) -> SurfaceStyle:
        msg_lower = message.lower()
        named = _KW.get("named_themes", {})
        for name, info in named.items():
            if name.lower() in msg_lower or name in message:
                return SurfaceStyle(info["surface"])

        surface_kw = _KW.get("surface_keywords", {})
        surface_scores = {s: 0 for s in surface_kw if not s.startswith("_")}
        for surface_name, kw_data in surface_kw.items():
            if surface_name.startswith("_"): continue
            for word in kw_data.get("ja", []) + kw_data.get("en", []):
                if word.lower() in msg_lower or word in message:
                    surface_scores[surface_name] += 1

        if surface_scores:
            best_surface = max(surface_scores, key=lambda k: surface_scores[k])
            if surface_scores[best_surface] > 0:
                try: return SurfaceStyle(best_surface)
                except ValueError: pass

        msg_s = message.lower().strip()
        if any(msg_s.startswith(cmd) for cmd in HTML_COMMANDS):
            return SurfaceStyle.GLOW

        return SurfaceStyle.GLASS

    def _infer_theme_name(self, message: str, surface: SurfaceStyle) -> str:
        msg_lower = message.lower()
        
        # 1. userがコマンドで直接指定した名前があればそれを優先
        for cmd in HTML_COMMANDS:
            if msg_lower.strip().startswith(cmd):
                after = re.sub(rf"{re.escape(cmd)}\s*", "", message, flags=re.IGNORECASE).strip()
                if after: return after[:60]

        # 2. キーワード辞書から推測
        named = _KW.get("named_themes", {})
        for name, info in named.items():
            if name.lower() in msg_lower or name in message:
                return name

        # 3. それ以外は surface から基本テーマ名を生成
        if surface:
            return surface.value.capitalize()

        return "HTML Theme"

    async def execute(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        AIモデルを呼び出し、結果をフロントエンドの HtmlCssPreviewBlock 形式に成形して返す
        """
        # ※ 注意: 実際に HTMLSnipper を使う場合はインポートのコメントアウトを外してください
        # from backend.api.services.snippers.html_snipper import HTMLSnipper
        # snipper = HTMLSnipper()

        # 1. 現在のメッセージから Surface や Theme を推測
        surface = self._infer_surface(message)
        theme_name = self._infer_theme_name(message, surface)

        # 2. Snipperに渡すインテントデータを構築
        intent_data = {
            "targets": ["dummy_layout"],  # 必要に応じて可変に
            "theme": theme_name,
            "surface": surface.value,
            "actions": ["create" if "作って" in message or "作成" in message else "update"],
            "responsive": True if "レスポンシブ" in message else False
        }

        # 3. Snipperを使ってAI用のシステムプロンプト（コンテキスト）を生成
        # ai_context_prompt = snipper.snip(intent_data)

        # 4. LLM（AI）の呼び出し (プロジェクトのLLMクライアントに合わせて書き換えてください)
        # ai_response_raw = await self.llm_client.generate(
        #     system_prompt=ai_context_prompt,
        #     user_prompt=message
        # )
        
        # --- AIからの返答の擬似サンプル (実際はLLMがこの形式のJSONを返却するように指示) ---
        ai_response_raw = """
        {
          "message": "ダミーデータをベースに、ご要望のスタイルを反映したUIコンポーネントを作成しました。",
          "html": "<div class='card'><h2>新着情報</h2><p>ここにダミーテキストが入ります。</p><button class='btn'>詳細を見る</button></div>",
          "css": ".card { padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); } .btn { background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }",
          "component_name": "InformationCard"
        }
        """
        # --------------------------------------------------------------------------------

        # 5. AIの出力をパース
        try:
            ai_data = json.loads(ai_response_raw)
        except json.JSONDecodeError:
            # 万が一JSONパースに失敗した場合のフォールバック
            ai_data = {
                "message": ai_response_raw,
                "html": _build_html(surface, theme_name, message),
                "css": _build_css(surface, theme_name),
                "component_name": "FallbackComponent"
            }

        # 6. フロントエンドの「AiChatMessageList」および「HtmlCssPreviewBlock」が期待する構造に変換
        return {
            "id": "generate_msg_id", # ユニークなID
            "role": "ai",
            "type": "ui_code",       # フロント側で WidgetCard 内にブロック展開されるトリガー
            "response_type": "ui_code",
            "content": {
                "message": ai_data.get("message", ""),
                "blocks": [
                    {
                        "type": "HtmlCssPreviewBlock", # blockRenderersにマッピングされる名前
                        "component_name": ai_data.get("component_name", "GeneratedUI"),
                        "html": ai_data.get("html", ""),
                        "css": ai_data.get("css", "")
                    }
                ]
            }
        }