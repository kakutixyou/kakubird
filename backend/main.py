# backend/main.py
print("2? backend/main.py が起動しました", flush=True)
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.routes_memory import router as memory_router
from api.routes_chat import router as chat_router
from engine.HTML_engine import HTMLEngine
from engine.orchestrator.gemini_orchestrator import GeminiOrchestrator
# ※インポートパスは実際のフォルダ構成に合わせて調整してください
# from engine.HTML_engine import HTMLEngine
# from services.handlers.ocr_recruit_handler import OcrRecruitHandler

app = FastAPI()
def main():
    # ユーザーからの入力を受け取る（例として歴史システムに関する質問）
    user_input = "卑弥呼が治めていた国について、歴史の小テスト用の解説を作って"

    # オーケストレーターをインスタンス化して実行
    orchestrator = GeminiOrchestrator()
    result = orchestrator.execute(user_input)

    # 結果のハンドリング
    if result["status"] == "success":
        print("\n=== 最終的なAIの回答 ===")
        print(result["response"])
    else:
        print("\n=== エラー ===")
        print(result["message"])

if __name__ == "__main__":
    main()
# ===
# 🌐 CORS（Cross-Origin Resource Sharing）の設定
# ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # フロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],  # すべてのメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)

# ===
# 🚀 ルーターの登録
# ===
# routes_memory.py 側で prefix="/api/memory" を設定しているので、ここでは prefix を外します！
app.include_router(memory_router)

# chat_router 側で prefix を設定しているかどうかに応じて調整してください
# もし routes_chat.py で prefix を設定していないなら、ここを prefix="/api/chat" にします
app.include_router(chat_router) 


# ===
# 📄 HTML解析 API (これはそのまま残します)
# ===
class HtmlRequest(BaseModel):
    html: str

@app.post("/api/analyze-html")
async def analyze_html(request: HtmlRequest):
    try:
        engine = HTMLEngine()
        result = engine.analyze(request.html)
        
        return {
            "status": "success",
            "score": result.score,
            "complexity": result.complexity,
            "warnings": result.warnings,
            "meta": result.meta 
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from api.services.manager import SupabaseManager  # 先ほど作ったファイル

app = FastAPI()
db_manager = SupabaseManager()

# JSXから送られてくるデータの形を定義
class UserScoreRequest(BaseModel):
    user_scores: Dict[str, float]
    only_with_video: bool = False

# JSXからアクセスするURL（エンドポイント）を作る
@app.post("/api/recommend")
def get_recommendations(request: UserScoreRequest):
    # SupabaseManagerに処理を任せる
    results = db_manager.recommend_careers(
        user_scores=request.user_scores,
        only_with_video=request.only_with_video
    )
    # 結果をJSXへ返す
    return {"status": "success", "data": results}
if __name__ == "__main__":
    # ポート8765でサーバーを起動
    uvicorn.run(app, host="127.0.0.1", port=8765)