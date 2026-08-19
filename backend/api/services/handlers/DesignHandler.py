# DesignHandler.py
from  api.services.inspectors.IntentInSpector import IntentInspector
import json
import os
import re
import traceback
from enum import Enum
from typing import Any, Optional, Tuple

from .base_handler import BaseHandler

# 基本的にCSS担当
# 1. 定数・パス設定
_DIR = os.path.dirname(__file__)
_KEYWORDS_JSON = os.path.join(_DIR, "design_keywords.json")
_THEMES_JSON = os.path.join(_DIR, "design_themes.json")
DESIGN_COMMANDS = {"/css", "/design", "/html"}

# 2. SurfaceStyle Enum
class SurfaceStyle(str, Enum):
    GLASS        = "glass"
    FROSTED_DARK = "frosted-dark"
    ELEVATED     = "elevated"
    BORDERED     = "bordered"
    FLAT         = "flat"
    GLOW         = "glow"
    NEUMORPHISM  = "neumorphism"
    PAPER        = "paper"

# 3. 外部JSONファイルのロード関数
def _load_json(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"   [DesignHandler] {os.path.basename(filepath)} が見つかりません", flush=True)
        return {}
    except json.JSONDecodeError as e:
        print(f"   [DesignHandler] {os.path.basename(filepath)} のパースエラー: {e}", flush=True)
        return {}

# 起動時にJSONをメモリに読み込んでおく
_KW = _load_json(_KEYWORDS_JSON)
_THEMES = _load_json(_THEMES_JSON)

# 4. CSS / HTML テンプレート生成
def _build_css(surface: SurfaceStyle, theme_name: str) -> str:
    base_vars = f"/* Theme: {theme_name} */\n"
    
    # JSONから該当するテーマのCSSを取得。なければ空のCSSを返す
    theme_data = _THEMES.get(surface.value, {})
    css_content = theme_data.get("css", "/* No CSS defined for this theme */\n:root {}")
    
    return base_vars + css_content

def _build_html(surface: SurfaceStyle, theme_name: str, message: str) -> str:
    return f"<div class='{surface.value}'>\n  <h1>{theme_name}</h1>\n  <p>Design generated successfully.</p>\n</div>"

# 
# 5. DesignHandler 本体
# 
class DesignHandler(BaseHandler):
    def __init__(self):
        self.detected_surface: Optional[SurfaceStyle] = None
        self.detected_theme:   Optional[str]          = None
        self.detected_mode:    str                    = "html"

    def estimate_size(self, message: str) -> int:
        """これから出力するであろう文字数をざっくり予想する"""
        if "cssのみ" in message:
            return 3000
        return 15000

    # 🚨 追加：can_handle メソッド
    async def can_handle(self, message: str) -> bool:
        """
        最低限、スコアが0点以上になる可能性があるかどうかを判定します。
        今回は calculate_score がメインで動くため、基本的には True を返すか、
        キーワードが含まれているかどうかの簡易チェックを行います。
        """
        msg_lower = message.lower()
        
        # コマンドが含まれていれば確実に対応
        if any(msg_lower.startswith(cmd) for cmd in DESIGN_COMMANDS):
            return True
            
        design_keywords = [
            "css", "デザイン", "スタイル", "装飾", "見た目", "レイアウト"
        ]
        return any(k in msg_lower for k in design_keywords)

    async def calculate_score(self, message: str) -> int:
            """
            DesignHandler が処理すべき確信度を返す（0～100）
            """
            msg_lower = message.strip().lower()

            # ----------------------------------------------------
            # 1. コマンド指定は最優先 (絶対コマンド = 100点)
            # ----------------------------------------------------
            if any(msg_lower.startswith(cmd) for cmd in DESIGN_COMMANDS):
                return 100

            # ----------------------------------------------------
            # 2. IntentInspector に自然言語の解析を丸投げ
            # ----------------------------------------------------
            inspector = IntentInspector(message)
            inspection_result = inspector.inspect()

            # Inspector側ですでに 85点上限のキャップ がかかったスコアを受け取る
            final_score = inspection_result["score"]

            # もし必要なら、ここで取得した themes や surface を
            # self.detected_surface などに保存しておくと、後の handle() で使えて便利です
            self.detected_surface = inspection_result.get("surface")
            self.detected_theme = inspection_result.get("theme")
            self.detected_mode = "html"

            return final_score
 

    # 🚨 修正：クラス内に配置（インデント修正）
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
        if any(msg_s.startswith(cmd) for cmd in DESIGN_COMMANDS):
            return SurfaceStyle.GLOW

        return SurfaceStyle.GLASS

    # 🚨 修正：クラス内に配置（インデント修正）
    def _infer_theme_name(self, message: str, surface: SurfaceStyle) -> str:
        msg_lower = message.lower()
        
        # 1. userがコマンドで直接指定した名前があればそれを優先
        for cmd in DESIGN_COMMANDS:
            if msg_lower.strip().startswith(cmd):
                after = re.sub(rf"{re.escape(cmd)}\s*", "", message, flags=re.IGNORECASE).strip()
                if after: return after[:60]

        # 2. キーワード辞書から推測
        named = _KW.get("named_themes", {})
        for name, info in named.items():
            if name.lower() in msg_lower or name in message:
                return info["title"]

        # 3. 外部JSONからデフォルトタイトルを取得
        theme_data = _THEMES.get(surface.value, {})
        if "title" in theme_data:
            return theme_data["title"]
            
        # フォールバック
        return surface.value.replace("-", " ").title()

    # 🚨 修正：クラス内に配置（インデント修正）
    async def handle(self, message: str) -> Optional[Tuple[str, Any]]:
        try:
            surface    = self._infer_surface(message)
            theme_name = self._infer_theme_name(message, surface)

            css_code = _build_css(surface, theme_name)
            html_code = _build_html(surface, theme_name, message)

            chat_message = f"テーマ **{theme_name}** ({surface.value} スタイル) を生成しました。\n\n"
            
            content = {
                "message": chat_message,
                "blocks": [
                    {
                        "type": "HtmlCssPreviewBlock",
                        "component_name": theme_name,
                        "html": html_code,
                        "css": css_code 
                    }
                ]
            }
            return "ui_code", content

        except Exception as e:
            traceback.print_exc()
            return None
        """

/* ─── Glass Surface · 幽霊のような透明素材 ─── */
:root {
  --glass-bg: rgba(255,255,255,0.08);
  --glass-border: rgba(255,255,255,0.18);
  --glass-blur: 20px;
  --glass-shadow: 0 8px 32px rgba(0,0,0,0.37);
  --glass-text: rgba(255,255,255,0.92);
  --glass-text-muted: rgba(255,255,255,0.55);
  --glass-accent: rgba(180,220,255,0.7);
}
body {
  min-height: 100vh;
  background: radial-gradient(ellipse at 20% 50%, #0a0a2e 0%, #000010 100%);
  font-family: 'Cormorant Garamond','Hiragino Mincho ProN',serif;
  color: var(--glass-text);
  overflow-x: hidden;
}
body::before {
  content:''; position:fixed; inset:0;
  background:
    radial-gradient(circle at 15% 85%, rgba(100,150,255,.06) 0%,transparent 50%),
    radial-gradient(circle at 85% 15%, rgba(200,100,255,.04) 0%,transparent 50%);
  pointer-events:none; z-index:0;
}
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow), inset 0 1px 0 rgba(255,255,255,.1);
  padding: 2rem 2.5rem;
  position: relative; overflow: hidden;
  transition: transform var(--transition-slow), box-shadow var(--transition-slow);
}
.glass-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg,transparent,rgba(255,255,255,.6) 40%,rgba(255,255,255,.6) 60%,transparent);
}
.glass-card:hover {
  transform: translateY(-4px) scale(1.005);
  box-shadow: 0 16px 48px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.15);
}
@keyframes ghost-appear {
  from { opacity:0; transform:translateY(12px); filter:blur(4px); }
  to   { opacity:1; transform:translateY(0);    filter:blur(0);   }
}
.ghost-text { animation:ghost-appear 1.2s cubic-bezier(.22,1,.36,1) forwards; opacity:0; }
.ghost-text:nth-child(1){animation-delay:.1s}
.ghost-text:nth-child(2){animation-delay:.3s}
.ghost-text:nth-child(3){animation-delay:.5s}
@keyframes float-ghost {
  0%,100%{transform:translateY(0) rotate(0deg);    opacity:.4}
  33%    {transform:translateY(-20px) rotate(5deg); opacity:.7}
  66%    {transform:translateY(10px) rotate(-3deg); opacity:.3}
}
.ghost-particle {
  position:absolute; border-radius:50%;
  background:radial-gradient(circle,rgba(180,220,255,.3) 0%,transparent 70%);
  animation:float-ghost 6s ease-in-out infinite; pointer-events:none;
}元々ここには"が3こがあった。

    # elif surface == SurfaceStyle.FROSTED_DARK:
    #     return base_vars + 元々ここには"が3こがあった。
/* ─── Frosted-Dark Surface · 月光・夜の霧 ─── */
:root {
  --frost-bg: rgba(10,10,30,0.75);
  --frost-border: rgba(120,140,200,0.2);
  --frost-blur: 30px;
  --frost-shadow: 0 12px 40px rgba(0,0,20,0.6);
  --frost-text: #e8ecf8;
  --frost-text-muted: rgba(200,210,240,.6);
  --frost-accent: #7eb8f7;
  --moonlight-silver: rgba(220,235,255,.85);
}
body {
  min-height:100vh;
  background:
    radial-gradient(ellipse at 50% -10%,rgba(40,60,120,.5) 0%,transparent 60%),
    linear-gradient(180deg,#020210 0%,#04041a 50%,#010108 100%);
  font-family:'Playfair Display','Noto Serif JP',serif;
  color:var(--frost-text);
}
body::before {
  content:''; position:fixed;
  top:-20%; left:50%; transform:translateX(-50%);
  width:600px; height:600px;
  background:radial-gradient(circle,rgba(160,200,255,.08) 0%,rgba(100,150,255,.04) 40%,transparent 70%);
  pointer-events:none;
  animation:moonlight-pulse 8s ease-in-out infinite;
}
@keyframes moonlight-pulse {
  0%,100%{opacity:.6;transform:translateX(-50%) scale(1)}
  50%    {opacity:1; transform:translateX(-50%) scale(1.1)}
}
.frosted-panel {
  background:var(--frost-bg);
  backdrop-filter:blur(var(--frost-blur)) saturate(180%);
  -webkit-backdrop-filter:blur(var(--frost-blur)) saturate(180%);
  border:1px solid var(--frost-border);
  border-radius:var(--radius-md);
  box-shadow:var(--frost-shadow),0 0 0 1px rgba(255,255,255,.03),inset 0 0 60px rgba(120,160,255,.03);
  padding:2.5rem 3rem; position:relative;
}
.frosted-panel::after {
  content:''; position:absolute; top:-1px; left:20%; right:20%; height:1px;
  background:linear-gradient(90deg,transparent,var(--moonlight-silver),transparent);
  opacity:.6;
}
@keyframes note-fall {
  0%  {transform:translateY(-100px) rotate(0deg);  opacity:0}
  10% {opacity:.6}
  90% {opacity:.3}
  100%{transform:translateY(110vh) rotate(720deg); opacity:0}
}
.musical-note {
  position:fixed; font-size:1.5rem; color:var(--frost-accent);
  animation:note-fall linear infinite; pointer-events:none;
  filter:drop-shadow(0 0 6px var(--frost-accent));
}
@keyframes allegro-pulse {
  0%,100%{letter-spacing:.05em;opacity:.9}
  50%    {letter-spacing:.15em;opacity:1}
}
.allegro-title {
  animation:allegro-pulse .8s ease-in-out infinite;
  font-weight:700; font-size:clamp(2rem,5vw,4rem);
  background:linear-gradient(135deg,var(--moonlight-silver) 0%,var(--frost-accent) 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}

    # elif surface == SurfaceStyle.GLOW:
    #     return base_vars + 

/* ─── Glow Surface · 革命の炎・爆発するエネルギー ─── */
:root {
  --glow-primary: #ff3a3a;
  --glow-secondary: #ff8c00;
  --glow-accent: #ffee00;
  --glow-bg: #0a0000;
  --glow-text: #fff5e0;
  --glow-text-muted: rgba(255,240,200,.6);
}
body {
  min-height:100vh;
  background:
    radial-gradient(ellipse at 30% 70%,rgba(180,20,0,.2) 0%,transparent 50%),
    radial-gradient(ellipse at 70% 30%,rgba(255,80,0,.1) 0%,transparent 50%),
    linear-gradient(160deg,#0a0000 0%,#120000 100%);
  font-family:'DM Mono','Courier New',monospace;
  color:var(--glow-text); overflow-x:hidden;
}
body::before {
  content:''; position:fixed; inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,50,0,.015) 2px,rgba(255,50,0,.015) 4px);
  pointer-events:none; z-index:1;
}
.glow-card {
  background:rgba(255,30,0,.05);
  border:1px solid rgba(255,60,0,.4);
  border-radius:4px; padding:2rem; position:relative;
  box-shadow:0 0 20px rgba(255,50,0,.1),inset 0 0 20px rgba(255,30,0,.05);
  transition:box-shadow var(--transition-fast);
}
.glow-card:hover{box-shadow:0 0 40px rgba(255,80,0,.3),0 0 80px rgba(255,50,0,.15),inset 0 0 30px rgba(255,60,0,.1)}
.glow-card::before{content:'';position:absolute;width:8px;height:8px;background:var(--glow-primary);border-radius:50%;filter:blur(3px);box-shadow:0 0 10px var(--glow-primary),0 0 20px var(--glow-secondary);top:-4px;left:-4px}
.glow-card::after{content:'';position:absolute;width:8px;height:8px;background:var(--glow-primary);border-radius:50%;filter:blur(3px);box-shadow:0 0 10px var(--glow-primary),0 0 20px var(--glow-secondary);bottom:-4px;right:-4px}
@keyframes revolution-flicker {
  0%,100%{opacity:1;  text-shadow:0 0 10px var(--glow-primary),0 0 20px var(--glow-secondary)}
  92%    {opacity:1;  text-shadow:0 0 10px var(--glow-primary)}
  93%    {opacity:.4; text-shadow:none}
  94%    {opacity:1;  text-shadow:0 0 30px var(--glow-accent)}
  96%    {opacity:.6; text-shadow:none}
  97%    {opacity:1;  text-shadow:0 0 10px var(--glow-primary),0 0 40px var(--glow-secondary)}
}
.revolution-title {
  font-size:clamp(2.5rem,6vw,5rem); font-weight:900; letter-spacing:-.02em;
  text-transform:uppercase; color:var(--glow-text);
  animation:revolution-flicker 5s ease-in-out infinite;
}
@keyframes beam-scan {
  0%  {transform:translateX(-100%) skewX(-15deg)}
  100%{transform:translateX(200%)  skewX(-15deg)}
}
.energy-beam{position:absolute;inset:0;overflow:hidden;border-radius:inherit;pointer-events:none}
.energy-beam::before {
  content:''; position:absolute; top:0; bottom:0; width:60px;
  background:linear-gradient(90deg,transparent,rgba(255,150,50,.15),transparent);
  animation:beam-scan 3s linear infinite;
}

    # elif surface == SurfaceStyle.NEUMORPHISM:
    #   return base_vars + 

/* ─── Neumorphism Surface · やわらかな立体感 ─── */
:root {
  --neu-bg: #e8ecf0;
  --neu-shadow-dark: rgba(163,177,198,.7);
  --neu-shadow-light: rgba(255,255,255,.9);
  --neu-text: #4a5568;
  --neu-text-muted: #8896aa;
  --neu-accent: #667eea;
  --neu-accent-glow: rgba(102,126,234,.3);
}
body{min-height:100vh;background:var(--neu-bg);font-family:'Nunito','Hiragino Sans',sans-serif;color:var(--neu-text)}
.neu-card {
  background:var(--neu-bg); border-radius:var(--radius-lg); padding:2rem;
  box-shadow:8px 8px 16px var(--neu-shadow-dark),-8px -8px 16px var(--neu-shadow-light);
  transition:box-shadow var(--transition-slow);
}
.neu-card:active{box-shadow:4px 4px 8px var(--neu-shadow-dark),-4px -4px 8px var(--neu-shadow-light),inset 2px 2px 5px var(--neu-shadow-dark),inset -2px -2px 5px var(--neu-shadow-light)}
.neu-button {
  background:var(--neu-bg); border:none; border-radius:var(--radius-sm);
  padding:.75rem 1.5rem; color:var(--neu-accent); font-weight:700; cursor:pointer;
  box-shadow:4px 4px 10px var(--neu-shadow-dark),-4px -4px 10px var(--neu-shadow-light);
  transition:all var(--transition-fast);
}
.neu-button:hover{box-shadow:6px 6px 14px var(--neu-shadow-dark),-6px -6px 14px var(--neu-shadow-light),0 0 0 1px var(--neu-accent-glow)}
.neu-input {
  background:var(--neu-bg); border:none; border-radius:var(--radius-sm);
  padding:.75rem 1rem; color:var(--neu-text); outline:none;
  box-shadow:inset 3px 3px 8px var(--neu-shadow-dark),inset -3px -3px 8px var(--neu-shadow-light);
  transition:box-shadow var(--transition-fast);
}
.neu-input:focus{box-shadow:inset 4px 4px 10px var(--neu-shadow-dark),inset -4px -4px 10px var(--neu-shadow-light),0 0 0 2px var(--neu-accent-glow)}元々ここには"が3こがあった。

    # elif surface == SurfaceStyle.ELEVATED:
    # return base_vars + 

/* ─── Elevated Surface · 重力を感じる立体感 ─── */
:root {
  --elev-bg-page:#f4f5f7; --elev-bg-card:#ffffff;
  --elev-shadow-1:0 1px 3px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.24);
  --elev-shadow-2:0 3px 6px rgba(0,0,0,.15),0 2px 4px rgba(0,0,0,.12);
  --elev-shadow-3:0 10px 20px rgba(0,0,0,.15),0 3px 6px rgba(0,0,0,.1);
  --elev-shadow-4:0 14px 28px rgba(0,0,0,.25),0 10px 10px rgba(0,0,0,.22);
  --elev-text:#1a202c; --elev-text-muted:#718096; --elev-accent:#3182ce;
}
body{background:var(--elev-bg-page);font-family:'IBM Plex Sans','Hiragino Sans',sans-serif;color:var(--elev-text)}
.card-1{background:var(--elev-bg-card);border-radius:var(--radius-sm);box-shadow:var(--elev-shadow-1);padding:1rem;  transition:box-shadow var(--transition-fast),transform var(--transition-fast)}
.card-2{background:var(--elev-bg-card);border-radius:var(--radius-sm);box-shadow:var(--elev-shadow-2);padding:1.5rem;transition:box-shadow var(--transition-fast),transform var(--transition-fast)}
.card-3{background:var(--elev-bg-card);border-radius:var(--radius-md);box-shadow:var(--elev-shadow-3);padding:2rem;  transition:box-shadow var(--transition-fast),transform var(--transition-fast)}
.card-4{background:var(--elev-bg-card);border-radius:var(--radius-md);box-shadow:var(--elev-shadow-4);padding:2.5rem;transition:box-shadow var(--transition-fast),transform var(--transition-fast)}
.card-1:hover{box-shadow:var(--elev-shadow-2);transform:translateY(-2px)}
.card-2:hover{box-shadow:var(--elev-shadow-3);transform:translateY(-3px)}
.card-3:hover{box-shadow:var(--elev-shadow-4);transform:translateY(-4px)}元々ここには"が3こがあった。

    # elif surface == SurfaceStyle.BORDERED:
    # return base_vars + 

/* ─── Bordered Surface · シャープなアウトライン ─── */
:root {
  --border-width:1.5px; --border-color:rgba(0,0,0,.85);
  --bg-page:#fafafa; --bg-card:#ffffff;
  --text-primary:#0a0a0a; --text-muted:#555; --accent:#1a1aff;
}
body{background:var(--bg-page);font-family:'Space Mono',monospace;color:var(--text-primary)}
.bordered-card {
  background:var(--bg-card); border:var(--border-width) solid var(--border-color);
  border-radius:0; padding:2rem;
  box-shadow:4px 4px 0 var(--border-color);
  transition:box-shadow var(--transition-fast),transform var(--transition-fast);
}
.bordered-card:hover{box-shadow:6px 6px 0 var(--border-color);transform:translate(-2px,-2px)}元々ここには"が3こがあった。

    elif surface == SurfaceStyle.PAPER:
    return base_vars + 

/* ─── Paper Surface · 温かみのある紙の質感 ─── */
:root {
  --paper-bg:#f8f4e8; --paper-card:#fffef5;
  --paper-border:rgba(160,140,90,.3);
  --paper-text:#2c2416; --paper-text-muted:rgba(44,36,22,.55);
  --paper-accent:#8b4513;
}
body {
  background:var(--paper-bg);
  font-family:'Lora','Georgia','Hiragino Mincho ProN',serif;
  color:var(--paper-text);
}
.paper-card {
  background:var(--paper-card); border:1px solid var(--paper-border);
  border-radius:2px; padding:2rem 2.5rem; position:relative;
  box-shadow:0 1px 3px rgba(160,140,90,.2),0 4px 12px rgba(160,140,90,.1),inset 0 0 0 1px rgba(255,255,255,.5);
}
.paper-card::before {
  content:''; position:absolute; left:3.5rem; top:0; bottom:0;
  width:1px; background:rgba(200,150,100,.3);
}元々ここには"が3こがあった。

    # else:  # FLAT
    # return base_vars + 

/* ─── Flat Surface · 純粋なミニマリズム ─── */
:root {
  --flat-bg:#ffffff; --flat-text:#111111;
  --flat-text-muted:#888888; --flat-accent:#000000;
  --flat-divider:rgba(0,0,0,.08);
}
body{background:var(--flat-bg);font-family:'Helvetica Neue','Hiragino Sans',sans-serif;color:var(--flat-text)}
.flat-card{background:var(--flat-bg);border-bottom:1px solid var(--flat-divider);padding:2rem 0;transition:background var(--transition-fast)}
.flat-card:hover{background:rgba(0,0,0,.02)}元々ここには"が3こがあった。



# 5.  HTML テンプレート生成
#     packages/render-engine/src/components/blocks/ の構造を参考


def _build_html(surface: SurfaceStyle, theme_name: str, original_message: str) -> str:
    css = _build_css(surface, theme_name)

    if surface == SurfaceStyle.GLASS:
        return f<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{theme_name}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&display=swap" rel="stylesheet">
  <style>*{{margin:0;padding:0;box-sizing:border-box}}{css}
    .hero{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem;position:relative;z-index:1}}
    h1{{font-size:clamp(2.5rem,6vw,5rem);font-weight:300;font-style:italic;color:rgba(255,255,255,.9);text-shadow:0 0 40px rgba(180,220,255,.4);margin-bottom:1rem}}
    p{{color:var(--glass-text-muted);font-size:1.1rem;line-height:1.8}}
    .cards{{display:flex;gap:1.5rem;flex-wrap:wrap;justify-content:center;margin-top:3rem}}
    .glass-card{{width:300px}}
  </style>
</head>
<body>
  <div class="ghost-particle" style="width:200px;height:200px;top:10%;left:15%;animation-duration:8s;"></div>
  <div class="ghost-particle" style="width:120px;height:120px;top:60%;right:20%;animation-duration:11s;animation-delay:-3s;"></div>
  <div class="ghost-particle" style="width:80px;height:80px;bottom:15%;left:40%;animation-duration:7s;animation-delay:-5s;"></div>
  <section class="hero">
    <h1 class="ghost-text">{theme_name}</h1>
    <p class="ghost-text" style="text-align:center;max-width:480px;">{original_message}</p>
    <div class="cards">
      <div class="glass-card">
        <p class="ghost-text" style="color:var(--glass-text);font-size:.85rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.5rem;">Surface · Glass</p>
        <p class="ghost-text" style="color:var(--glass-text-muted);line-height:1.7;">幽霊のような透明感。存在するのか、しないのか。光を通し、影を落とす。</p>
      </div>
      <div class="glass-card">
        <p class="ghost-text" style="color:var(--glass-accent);font-size:.85rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.5rem;">Backdrop Blur</p>
        <p class="ghost-text" style="color:var(--glass-text-muted);line-height:1.7;">背後の世界をわずかに歪め、夢と現実の境界を曖昧にする霞の膜。</p>
      </div>
    </div>
  </section>
</body></html>

    # elif surface == SurfaceStyle.FROSTED_DARK:
    #     return f
      <!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{theme_name}</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">
  <style>*{{margin:0;padding:0;box-sizing:border-box}}{css}
    .stage{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem 2rem;position:relative}}
    .subtitle{{font-size:.9rem;letter-spacing:.3em;text-transform:uppercase;color:var(--frost-text-muted);margin-bottom:1.5rem}}
    .frosted-panel{{max-width:640px;width:100%;margin-top:3rem}}
    .movement{{display:flex;gap:.5rem;margin-top:2rem}}
    .bar{{flex:1;height:4px;background:linear-gradient(90deg,var(--frost-accent),transparent);border-radius:2px;animation:bar-animate 2s ease-in-out infinite}}
    .bar:nth-child(2){{animation-delay:.2s}}.bar:nth-child(3){{animation-delay:.4s;animation-duration:1.5s}}.bar:nth-child(4){{animation-delay:.1s;animation-duration:2.5s}}.bar:nth-child(5){{animation-delay:.3s}}
    @keyframes bar-animate{{0%,100%{{opacity:.3;transform:scaleX(.6)}}50%{{opacity:1;transform:scaleX(1)}}}}
  </style>
</head>
<body>
  <span class="musical-note" style="left:10%;animation-duration:12s;">♩</span>
  <span class="musical-note" style="left:30%;animation-duration:15s;animation-delay:-4s;">♪</span>
  <span class="musical-note" style="left:55%;animation-duration:10s;animation-delay:-8s;">♫</span>
  <span class="musical-note" style="left:75%;animation-duration:13s;animation-delay:-2s;">♩</span>
  <span class="musical-note" style="left:88%;animation-duration:11s;animation-delay:-6s;">♬</span>
  <main class="stage">
    <p class="subtitle">Sonata No.14 in C♯ minor · Op.27</p>
    <h1 class="allegro-title">{theme_name}</h1>
    <div class="movement">
      <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
    </div>
    <div class="frosted-panel">
      <p style="color:var(--frost-text-muted);line-height:1.9;font-size:.95rem;">{original_message}</p>
      <p style="color:var(--frost-text);margin-top:1.5rem;font-size:1.1rem;font-style:italic;">
        月の光が鍵盤の上に降り注ぐ夜。第三楽章 Presto agitato —<br>
        嵐のように激しく、しかし月明かりの中の孤独のように静かに。
      </p>
    </div>
  </main>
</body></html>

    elif surface == SurfaceStyle.GLOW:
        return f
      <!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{theme_name}</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>*{{margin:0;padding:0;box-sizing:border-box}}{css}
    .arena{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem;position:relative;z-index:2}}
    .subtitle{{font-size:.75rem;letter-spacing:.4em;text-transform:uppercase;color:var(--glow-text-muted);margin-bottom:1.5rem;border:1px solid rgba(255,60,0,.3);padding:.4rem 1rem}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem;max-width:900px;width:100%;margin-top:3rem}}
    .tag{{display:inline-block;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase;color:var(--glow-primary);border:1px solid currentColor;padding:.2rem .5rem;margin-bottom:.75rem}}
    p{{color:var(--glow-text-muted);line-height:1.7;font-size:.9rem}}
  </style>
</head>
<body>
  <main class="arena">
    <p class="subtitle">CSS · REVOLUTION · SYSTEM</p>
    <h1 class="revolution-title">{theme_name}</h1>
    <div class="cards-grid">
      <div class="glow-card"><div class="energy-beam"></div><span class="tag">Surface · Glow</span><p>{original_message}</p></div>
      <div class="glow-card"><div class="energy-beam"></div><span class="tag">Anti-AI CSS</span><p>ジェネリックなAI生成スタイルへの抵抗。既成の美しさを破壊し、再構築する。</p></div>
      <div class="glow-card"><div class="energy-beam"></div><span class="tag">Style System</span><p>packages/style-system の思想：表面はルールに従い、精神は自由でいる。</p></div>
    </div>
  </main>
</body></html>

    else:
        card_class = {
            SurfaceStyle.NEUMORPHISM: "neu-card",
            SurfaceStyle.ELEVATED:   "card-3",
            SurfaceStyle.BORDERED:   "bordered-card",
            SurfaceStyle.PAPER:      "paper-card",
            SurfaceStyle.FLAT:       "flat-card",
        }.get(surface, "flat-card")

        return f<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{theme_name}</title>
  <style>*{{margin:0;padding:0;box-sizing:border-box}}{css}
    .page{{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}}
    .container{{max-width:640px;width:100%}}
    h1{{font-size:2.5rem;margin-bottom:1rem}}
    p{{line-height:1.8}}
  </style>
</head>
<body>
  <div class="page"><div class="container">
    <div class="{card_class}">
      <h1>{theme_name}</h1>
      <p style="margin-top:1rem;">{original_message}</p>
    </div>
  </div></div>
</body></html>"""

