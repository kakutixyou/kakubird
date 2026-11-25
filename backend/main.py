# GitHub Copilot からの補完機能 :contentReference[oaicite:0]{index=0}

print("2? backend/main.py が起動しました", flush=True)
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.routes_memory import router as memory_router
from api.routes_chat import router as chat_router
from engine.HTML_engine import HTMLEngine
from engine.orchestrator.gemini_orchestrator import GeminiOrchestrator

app = FastAPI()
def main():
    user_input = "卑弥呼が治めていた国について、歴史の小テスト用の解説��作って"
    orchestrator = GeminiOrchestrator()
    result = orchestrator.execute(user_input)
    if result["status"] == "success":
        print("\n=== 最終的なAIの回答 ===")
        print(result["response"])
    else:
        print("\n=== エラー ===")
        print(result["message"])

if __name__ == "__main__":
    main()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_router)
app.include_router(chat_router)

class HtmlRequest(BaseModel):
    html: str

@app.post("/api/analyze-html")
async def analyze_html(request: HtmlRequest):
    try:
        engine = HTMLEngine()
        result = engine.analyze(request.html)
        return {"status": "success", "score": result.score, "complexity": result.complexity, "warnings": result.warnings, "meta": result.meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from typing import Dict
from api.services.manager import SupabaseManager

db_manager = SupabaseManager()

class UserScoreRequest(BaseModel):
    user_scores: Dict[str, float]
    only_with_video: bool = False

@app.post("/api/recommend")
def get_recommendations(request: UserScoreRequest):
    results = db_manager.recommend_careers(user_scores=request.user_scores, only_with_video=request.only_with_video)
    return {"status": "success", "data": results}

from api.routes_topic_analysis import router as topic_analysis_router
from api.routes_stock_followup import router as stock_followup_router
app.include_router(topic_analysis_router)
app.include_router(stock_followup_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
