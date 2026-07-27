# To(と)/plugins/sql_builder_v2/backend_sql_v2/api_sql_v2/routes_chat.py
import sys

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Optional
import os

from ai.custom_ai import run_custom_ai
from ai.gemini_ai import run_gemini_ai
from ai.claude_ai import run_claude_ai
from ai.judge import evaluate_response
# ai_server.pyにつなげる
# ✅ MemoryManagerをインポート
from core.memory_manager import (
    save_chat_message,
    get_chat_history,
)
# import google.generativeai as genai
from core.security import verify_api_key
import traceback
# ai_server.py がある backend フォルダをインポートの最優先ルートとして強制追加
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    mode: str = "custom"
    db_type: str = "sqlite"
    db_path: str = "backend/history.db"
    conn_str: str = ""

class ChatResponse(BaseModel):
    reply: str
    source: Optional[str] = "custom"


def convert_history(history: List[Message]):
    return [
        {"role": m.role, "content": m.content}
        for m in history
        if m.role in ("user", "assistant")
    ]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    if authorization:
        print("🔑 [認証成功]")

    history = convert_history(req.history)

    # ✅ ①  ユーザーメッセージをまず保存
    save_chat_message("user", req.message)

    # ✅ ②  過去の会話履歴をDBから取得してhistoryに注入
    #         フロントから渡されたhistoryより永続DBを優先
    db_history = get_chat_history(limit=20)
    if db_history:
        # memory_managerのフォーマット → routes_chatのフォーマットに変換
        req.history = [
            Message(role=m["role"], content=m["content"])
            for m in db_history
            if m["role"] in ("user", "assistant")
        ]

    try:
        if req.mode == "custom":
            custom_result = await run_custom_ai(req)
            reply = custom_result.get("reply", "")
            quality = evaluate_response(reply)

            if quality == "good":
                # ✅ ③  AIの返答を保存
                save_chat_message("assistant", reply, {"source": "custom"})
                return ChatResponse(reply=reply, source="custom")

            if quality == "danger":
                return ChatResponse(reply="安全でないSQLが検出されました。", source="error")

            # リトライ
            try:
                req.message = f"{req.message}（スキーマに沿ったSQLを生成してください）"
                retry_result = await run_custom_ai(req)
                retry_reply = retry_result.get("reply", "")

                if evaluate_response(retry_reply) == "good":
                    save_chat_message("assistant", retry_reply, {"source": "custom_retry"})
                    return ChatResponse(reply=retry_reply, source="custom")

            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=str(e))

            # Claude fallback
            try:
                claude_reply = await run_claude_ai(req)
                if claude_reply:
                    save_chat_message("assistant", claude_reply, {"source": "claude"})
                    return ChatResponse(reply=claude_reply, source="claude")
            except Exception as e:
                print("Claude fallback失敗:", e)

            return ChatResponse(
                reply="回答を生成できませんでした。質問を少し変えてみてください。",
                source="error"
            )

        elif req.mode == "gemini":
            reply = await run_gemini_ai(req)
            save_chat_message("assistant", reply, {"source": "gemini"})
            return ChatResponse(reply=reply, source="gemini")

        elif req.mode == "claude":
            reply = await run_claude_ai(req)
            save_chat_message("assistant", reply, {"source": "claude"})
            return ChatResponse(reply=reply, source="claude")

        else:
            raise HTTPException(status_code=400, detail="無効なmodeです")

    except Exception as e:
        print("Chatエラー:", e)
        raise HTTPException(status_code=500, detail=str(e))