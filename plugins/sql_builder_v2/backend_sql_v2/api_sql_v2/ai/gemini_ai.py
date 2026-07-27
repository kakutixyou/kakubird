import os
from google import genai
from core.config import GEMINI_API_KEY
from .judge import evaluate_response

# 1. クライアントを初期化 (APIキーを直接渡す)
client = genai.Client(api_key=GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"))

# 2. モデルの指定方法を変更
MODEL_ID = "gemini-1.5-flash"

async def run_gemini_ai_raw(prompt: str) -> str:
    # 3. generate_content の呼び出し方をクライアント経由に変更
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    return response.text

async def run_gemini_ai(req) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY が設定されていません")

    prompt = f"""
あなたは優秀なSQLエンジニアです。
以下の質問に対してSQLを生成してください。
必ず ```sql ``` で囲んで返してください。

質問: {req.message}
"""
    # 4. generate_content の呼び出し
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    return response.text