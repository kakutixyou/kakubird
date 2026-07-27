# api/ai/claude_ai.py

import anthropic
from core.config import ANTHROPIC_API_KEY
import os
from dotenv import load_dotenv
from .judge import evaluate_response
# 💡 修正ポイント①: 非同期関数（async def）の中で使うため、AsyncAnthropic に変更
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "ここにあなたの_Claude_API_キーを直接書いてもOK")
# 既存（routes_chat.py から直接呼ばれる版）

async def run_claude_ai(req) -> str:
    
    # 💡 修正ポイント②: await をつけて非同期で呼び出す
    message = await client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1024,
        system="あなたは優秀なSQLエンジニアです。SQLは必ず ```sql ``` で囲んで返してください。",
        messages=[{"role": "user", "content": req.message}]
    )
    
    # 💡 修正ポイント③: type が "text" かどうかを確認してから取り出す（これでエラーが消えます）
    for block in message.content:
        if block.type == "text":
            return block.text
            
    return ""  # 万が一テキストが含まれていなかった場合の安全策

# ★ 今回追加：プロンプトをそのまま受け取る版
async def run_claude_ai_raw(prompt: str) -> str:
    message = await client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    for block in message.content:
        if block.type == "text":
            return block.text
            
    return ""