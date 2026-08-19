# api/routes_nlp.py

from fastapi import APIRouter, HTTPException
from schemas.nlp_models import (
    AnalysisRequest,
    AnalysisResponse,
    TemplatePart,
    BuildRequest,
    BuildResponse
)
from services import nlp_service
from services.ai_orchestrator import AIOrchestrator

# ===
# NLP (自然言語解析) ルーター
# ===
router = APIRouter()
orchestrator = AIOrchestrator()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    ユーザーからのテキスト入力を受け取り、AIOrchestratorで処理してSQLを返す。
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="テキストが空です")

    # 脳（Orchestrator）に全て委譲！
    # ※前回作成した orchestrator のメソッド名は `process` としています
    raw = await orchestrator.process(text, user_id="default")

    # dict[str, str] の parts を TemplatePart モデルに変換（エラー回避のため .get を使用）
    parts = [TemplatePart(**p) for p in raw.get("parts", [])]

    return AnalysisResponse(
        type=raw.get("type", "unknown"),
        title=raw.get("title", "名称未設定"),
        icon=raw.get("icon", "database"),
        description=raw.get("description", ""),
        sql=raw.get("sql", ""),
        parts=parts,
        input=text,
    )


@router.get("/templates", response_model=list[AnalysisResponse])
async def get_all_templates():
    """
    全テンプレート種別のサンプルを一覧で返す（UIのギャラリー表示用）。
    ※ ここはOrchestratorを通さず、純粋なカタログとして出力します
    """
    all_types = [
        'subquery', 'left_join', 'right_join', 'inner_join',
        'insert', 'update', 'delete', 'group_by', 'select',
    ]
    # ギャラリー表示用のダミーエンティティ
    dummy_entities = {'tables': ['table_a', 'table_b'], 'columns': [], 'conditions': []}
    results = []
    
    for t in all_types:
        # Service を呼び出して各テンプレートを生成
        raw = nlp_service.build_sql_template(t, '', dummy_entities)
        parts = [TemplatePart(**p) for p in raw.get("parts", [])]
        
        results.append(AnalysisResponse(
            type=t,
            title=raw.get("title", "テンプレート"),
            icon=raw.get("icon", "database"),
            description=raw.get("description", ""),
            sql=raw.get("sql", ""),
            parts=parts,
            input='',
        ))
        
    return results


@router.post("/build", response_model=BuildResponse)
async def build_custom(request: BuildRequest):
    """
    ユーザーが編集したパーツ（テーブル名・条件など）からSQLを再構築して返す。
    """
    # 煩雑な if-elif-else のSQL組み立てロジックは Service に隠蔽する
    sql = nlp_service.build_custom_sql(request.type, request.parts)
    
    return BuildResponse(sql=sql, type=request.type)