# api/services/handlers/ChatHandler/constants.py
"""ChatHandler の定数（外部依存なし）。"""

from __future__ import annotations

HANDLER_NAME = "ChatHandler"

CHATBOT_MODE = "chatbot"
AI_MODE = "ai"

DEFAULT_SCORE = 60

# 未使用（旧ChatHandlerから移植。不要なら削除可）
CASUAL_WORDS = (
    "こんにちは", "こんばんは", "おはよう", "ありがとう", "ありがと",
    "なるほど", "そうだね", "だよね", "確かに", "面白い", "すごい",
    "どう思う", "どうかな", "相談", "話したい",
)

# ------------------------------------------------------------
# AI / Chatbot モード切替
# ------------------------------------------------------------

AI_ENABLE_WORDS = (
    "aiモード", "aiモードにして", "aiを有効", "aiをオン",
    "生成aiを使う", "local llmを使う",
)

CHATBOT_ENABLE_WORDS = (
    "チャットボットモード", "chatbotモード", "jsonモード",
    "ルールベースモード", "aiを無効", "aiをオフ", "生成aiを使わない",
)

# ------------------------------------------------------------
# Project 会話
# 「アプリ相談中か」の判定語。Build開始判定とは別。
# ------------------------------------------------------------

PROJECT_WORDS = (
    "アプリ", "webアプリ", "ウェブアプリ", "プロジェクト",
    "react", "next.js", "nextjs", "html",
    "画面", "機能", "ページ", "データベース",
    "バックエンド", "フロントエンド",
)

# ------------------------------------------------------------
# Build Intent
# 「作りたい」= 要件相談 / 「作って」= Build命令
# ------------------------------------------------------------

PROJECT_BUILD_INTENTS = frozenset({
    "build_app", "build_project", "create_project", "generate_app",
    "generate_project", "start_build", "project_build",
    "implement_project",
})

# 単独でBuild命令になる（対象・文脈が語に含まれている）
BUILD_PHRASES_STRONG = (
    "じゃあ作って", "では作って", "それで作って", "これで作って",
    "この内容で作って", "この要件で作って", "この仕様で作って",
    "アプリを作って", "アプリを生成して",
    "プロジェクトを作って", "プロジェクトを生成して",
)

# 要件(Project Context)が溜まっている時だけBuild命令になる
BUILD_PHRASES_NEED_CONTEXT = (
    "実際に作って", "実装を始めて", "実装を開始して",
    "ビルドして", "buildして", "buildしてほしい",
    "コードを生成して",
)

# 「それだけ」を言った時だけBuild命令になる（要件が必要）
# 例: 「生成して」→ Build / 「要約を生成して」→ Build ではない
BUILD_PHRASES_BARE = (
    "生成して", "実装して", "作って",
)

# 説明・質問のための文はコマンドとして扱わない
INFORMATIONAL_MARKERS = (
    "とは", "って何", "って何？", "どうやって", "やり方", "方法",
    "違い", "について", "教えて", "説明", "なぜ", "なんで",
    "どういう", "どう違う",
)

# ------------------------------------------------------------
# finalize 時に error 状態を解除する source
# ※旧コードは "local_llm+knowledge" が漏れていたため追加
# ------------------------------------------------------------

ERROR_CLEARING_SOURCES = (
    "json", "rule", "project_rule", "local_llm", "local_llm+knowledge",
)

# ------------------------------------------------------------
# calculate_score 用（IntentInspector の mode 名と揃えること）
# ------------------------------------------------------------

# 他ハンドラーが担当するモード → ChatHandler は 0 点
DELEGATED_MODES = frozenset({
    "project_build", "app_generation", "code_analysis",
    "script_extraction", "math_calculation",
    "project_builder",   # mode_rule.py の ProjectBuilderModeRule が出す名前
})

# アプリ関連の発話（「アプリ」等の語で発火する）。
# project_builder_policy="chat" のとき ChatHandler が要件相談として引き受ける
PROJECT_CONSULT_MODES = frozenset({"project_builder"})

PROJECT_BUILDER_POLICIES = ("delegate", "chat")
PROJECT_CONSULT_SCORE = 80

# ChatHandler が担当するモード
CHAT_MODES = frozenset({
    "chat", "casual_chat", "general_chat", "greeting", "thanks",
})

MODE_CHANGE_INTENTS = frozenset({
    "ai_mode_enable", "chatbot_mode_enable", "mode_change",
})
