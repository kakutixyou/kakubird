"""
design_api.py
=============
Flask chat API server with language detection, API routing,
and step-by-step print() logging.

Processing flow:
  [2️⃣ Backend]  POST /api/chat  → receive
  [3️⃣ Process]  language detection & routing
  [4️⃣ Backend]  generate response

Console log legend:
  🟢  Backend received / responded
  🟡  Processing (detection & routing)
  🔴  Error / warning
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
import re

# ---------------------------------------------------------------------------
# Path setup – reuse schema_rules when available
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

try:
    from schema_rules import (
        detect_mood_from_keywords,
        detect_domain_from_keywords,
    )
except ImportError:
    def detect_mood_from_keywords(text):
        return "professional"

    def detect_domain_from_keywords(text):
        return "education"

# ---------------------------------------------------------------------------
# Language detection (mirrors languageDetector.js logic in Python)
# ---------------------------------------------------------------------------

LANGUAGE_KEYWORDS = {
    "tailwind": [
        "tailwind", "tw-", "utility class", "utility-class", "jit", "purge",
        "tailwindcss", "bg-", "text-", "flex ", "grid ", "p-", "m-", "rounded",
        "shadow", "hover:", "focus:", "dark:", "responsive",
    ],
    "scss": [
        "scss", "sass", "$variable", "@mixin", "@include", "@extend", "@use",
        "@forward", "nesting", "ampersand",
    ],
    "postcss": [
        "postcss", "autoprefixer", "@apply", "css variable", "custom property",
        "var(--", ":root",
    ],
    "styled-components": [
        "styled-components", "styled.", "css`", "createglobalstyle",
        "themeprovider", "keyframes`",
    ],
    "css-modules": [
        "css module", "css modules", ".module.css", "composes",
    ],
    "sql": [
        "sql", "select ", "insert ", "update ", "delete ", "create table",
        "drop table", "join ", "where ", "group by", "order by", "having ",
        "sqlite", "postgresql", "mysql", "database", "schema", "query",
        "クエリ", "データベース", "テーブル",
    ],
    "react": [
        "react", "jsx", "tsx", "usestate", "useeffect", "component", "props",
        "hook", "context", "redux", "zustand",
    ],
    "css": [
        "css", "stylesheet", "selector", "property", "cascade", "specificity",
        "media query", "animation", "transition", "flexbox", "grid",
        "スタイル", "スタイリング",
    ],
}

STYLING_LANGUAGES = {"tailwind", "css", "scss", "postcss", "styled-components", "css-modules"}
SQL_LANGUAGES = {"sql"}


def detect_language(text: str) -> dict:
    """Detect the programming language / framework from a message."""
    lower = text.lower()
    scores = {}
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            pattern = re.escape(kw)
            matches = re.findall(pattern, lower)
            score += len(matches)
        scores[lang] = score

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return {"language": "unknown", "confidence": 0.0, "scores": scores}

    language = max(scores, key=scores.get)
    confidence = min(max_score / 5.0, 1.0)
    return {"language": language, "confidence": confidence, "scores": scores}


def resolve_api_type(language: str, scores: dict) -> str:
    """Resolve whether to route to 'sql', 'css', or 'default'."""
    if language in SQL_LANGUAGES:
        return "sql"
    if language in STYLING_LANGUAGES:
        return "css"

    sql_score = scores.get("sql", 0)
    css_score = max(scores.get(lang, 0) for lang in STYLING_LANGUAGES)
    if sql_score > css_score and sql_score > 0:
        return "sql"
    if css_score > sql_score and css_score > 0:
        return "css"
    return "default"


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the React front-end


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------------------
# Chat endpoint  POST /api/chat
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():
    request_id = str(uuid.uuid4())[:8]
    received_at = time.time()

    # ── 2️⃣  Receive ─────────────────────────────────────────────────────────
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])
    mode = data.get("mode", "auto")
    db_path = data.get("db_path", "")
    api_key = data.get("api_key", "")

    print(f"\n🟢 [バックエンド - 2️⃣] POSTリクエスト受信")
    print(f"   🆔 Request ID : {request_id}")
    print(f"   📥 Path       : {request.path}")
    print(f"   ⏱️  Timestamp  : {_now_iso()}")
    print(f"   📊 Message    : {message!r}")
    print(f"   📊 Mode       : {mode}")
    print(f"   📊 History    : {len(history)} turns")

    if not message:
        print(f"🔴 [バックエンド] message フィールドが必要です (req={request_id})")
        return jsonify({"error": "message field is required"}), 400

    # ── 3️⃣  Language detection & routing ───────────────────────────────────
    detection = detect_language(message)
    language = detection["language"]
    confidence = detection["confidence"]
    scores = detection["scores"]
    api_type = resolve_api_type(language, scores)

    print(f"\n🟡 [処理 - 3️⃣] 言語検出＆ルーティング")
    print(f"   🆔 Request ID    : {request_id}")
    print(f"   🔍 Detected Lang : {language}  (confidence: {confidence:.0%})")
    print(f"   🛣️  Routing to   : {api_type} API")
    print(f"   📐 Mode          : {mode}")
    print(f"   📊 Scores        : { {k: v for k, v in scores.items() if v > 0} }")

    # ── 4️⃣  Generate response ───────────────────────────────────────────────
    reply = _generate_reply(message, language, api_type, history, db_path)
    processing_ms = int((time.time() - received_at) * 1000)

    print(f"\n🟢 [バックエンド - 4️⃣] レスポンス生成")
    print(f"   🆔 Request ID      : {request_id}")
    print(f"   📤 Type            : {api_type}")
    print(f"   🌍 Language        : {language}")
    print(f"   💬 Reply generated : {_truncate(reply, 80)!r}")
    print(f"   ⏱️  Processing time : {processing_ms}ms")

    response_body = {
        "reply": reply,
        "source": api_type,
        "language": language,
        "confidence": confidence,
        "request_id": request_id,
        "processing_ms": processing_ms,
    }

    return jsonify(response_body), 200


def _truncate(text: str, max_len: int = 100) -> str:
    """Return text truncated to max_len characters with '...' suffix if needed."""
    return text[:max_len] + "..." if len(text) > max_len else text


def _generate_reply(message: str, language: str, api_type: str, history: list, db_path: str) -> str:
    """
    Stub reply generator.
    In production, replace this with calls to Gemini / Claude / OpenAI.
    """
    snippet = _truncate(message)
    if api_type == "sql":
        return f"SQL APIで処理します。検出言語: {language}。ご質問: {snippet}"
    if api_type == "css":
        return f"CSS/スタイリング APIで処理します。検出言語: {language}。ご質問: {snippet}"
    return f"汎用AIで処理します。ご質問: {snippet}"


# ---------------------------------------------------------------------------
# Language detection endpoint  POST /api/detect-language
# ---------------------------------------------------------------------------

@app.route("/api/detect-language", methods=["POST"])
def detect_language_endpoint():
    """Expose language detection as a standalone API."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "text field is required"}), 400

    result = detect_language(text)
    api_type = resolve_api_type(result["language"], result["scores"])

    print(f"\n🟡 [言語検出] /api/detect-language")
    print(f"   🔍 Language : {result['language']}  (confidence: {result['confidence']:.0%})")
    print(f"   🛣️  Route    : {api_type}")

    return jsonify({
        "language": result["language"],
        "confidence": result["confidence"],
        "api_type": api_type,
        "scores": {k: v for k, v in result["scores"].items() if v > 0},
    }), 200


# ---------------------------------------------------------------------------
# Health check  GET /api/health
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": _now_iso(),
        "endpoints": ["/api/chat", "/api/detect-language", "/api/health"],
    }), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    print(f"🔴 [バックエンド] 500 Internal Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"\n🟢 [バックエンド] design_api.py 起動")
    print(f"   Port    : {port}")
    print(f"   Debug   : {os.environ.get('FLASK_DEBUG', 'false')}")
    print(f"   Started : {_now_iso()}\n")
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true", port=port, host="0.0.0.0")
