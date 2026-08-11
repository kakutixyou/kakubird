#!/bin/bash

# ==========================================
# ポート設定（vite.config.tsと完全に一致させる）
# ==========================================
HTML_ENGINE_PORT=8001
CSS_ENGINE_PORT=8002
SQL_ENGINE_PORT=8003
AI_ENGINE_PORT=8004
MAIN_BACKEND_PORT=3001  # 👈 Viteが探しているポートに合わせる！

echo "🚀 Starting all engines..."

# 1. HTMLエンジン起動
echo "Starting HTML Engine (port $HTML_ENGINE_PORT)..."
# ( ) で囲むことで、元のディレクトリ位置を維持したまま実行できます
(python engines/html_engine.py) &
HTML_PID=$!

# 2. CSSエンジン起動
echo "Starting CSS Engine (port $CSS_ENGINE_PORT)..."
(cd plugins/my-awesome-builder-main/packages/render-engine && npm run dev) &
CSS_PID=$!

# 3. SQLエンジン起動
echo "Starting SQL Engine (port $SQL_ENGINE_PORT)..."
(cd plugins/sql_builder_v2/backend && python server.py) &
SQL_PID=$!

# 4. AIエンジン起動 (ai_server.py)
echo "Starting AI Engine (port $AI_ENGINE_PORT)..."
# 注意: ai_server.py 内部で 8765 などのポートを指定している場合は、それに従います
(cd backend/api && python ai_server.py) &
AI_PID=$!

# ==========================================
# 5. メインバックエンド起動 (Node.js)
# ==========================================
echo "Starting Main Backend (port $MAIN_BACKEND_PORT)..."
# 環境変数 PORT に 3001 を強制的に指定して起動する
# ※package.jsonがあるディレクトリ（backendかルート）にいる前提です
PORT=$MAIN_BACKEND_PORT npm run dev &
MAIN_PID=$!

echo "✅ All systems go! Press Ctrl+C to stop all servers."

# トラップ：Ctrl+C で全プロセスを綺麗に終了する
trap "echo '🛑 Stopping all engines...'; kill $HTML_PID $CSS_PID $SQL_PID $AI_PID $MAIN_PID; exit" INT TERM EXIT

# メインプロセスが終わらないように待機
wait