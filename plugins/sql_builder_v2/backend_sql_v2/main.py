# backend/main.py

# =====
# 1. 各ルーターのインポート
# =====
from api import routes_auth
from api import routes_execute
from api import routes_system  # ★ 今回作成したシステムAPIをインポート
from api import routes_nlp  
from api.routes_memory import router as memory_router
# from api.routes_sql import router as sql_router

# (routes_sqlやroutes_historyなど、他のファイルもあればここでインポートします)
"""
スポーツ用品レンタル管理 - SQL AI バックエンド
FastAPI + SQLite + Anthropic Claude API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, json, re, os, httpx
from pathlib import Path
 
app = FastAPI(
    title="SaaS API Gateway",
    description="動的にUIを生成するための自己記述型APIサーバー",
    version="1.0.0"
)
app.include_router(memory_router)
# # app = FastAPI(title="SQL AI API")#SQLを沢山読み込めないため廃止
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent / "sports_rental.db"

# ── スキーマを動的に取得 ────────────────────────────────────────
def get_schema() -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    schema_lines = []
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    for t in tables:
        tname = t["name"]
        cols = conn.execute(f"PRAGMA table_info({tname})").fetchall()
        col_defs = ", ".join(f"{c['name']} ({c['type']})" for c in cols)
        schema_lines.append(f"- `{tname}`: {col_defs}")
    conn.close()
    return "\n".join(schema_lines)

# ── システムプロンプト（カンニングペーパー）────────────────────
SYSTEM_PROMPT_TEMPLATE = """あなたはSQLiteの専門家です。
以下のDBスキーマを元に、ユーザーの日本語の質問を実行可能なSELECT文に変換してください。

【DBスキーマ】
{schema}

【テーブル補足】
- items: 商品テーブル（name=商品名, category=カテゴリ, daily_price=日額, stock=在庫）
- customers: 顧客テーブル（name=顧客名, email, phone, created_at=登録日）
- rentals: レンタル履歴（customer_id, item_id, rent_date=開始日, return_date=返却日,
           days=日数, total_price=合計金額, status=renting/returned）

【SQL変換ルール】
- 「〜ごとに合計/集計」→ GROUP BY + SUM() または COUNT()
- 「〜の順で/ランキング」→ ORDER BY（高い順=DESC, 低い順=ASC）
- 「上位N件」→ LIMIT N
- 「今レンタル中」→ WHERE status = 'renting'
- 「返却済み」→ WHERE status = 'returned'
- JOINが必要な場合は適切に結合する
- customers.name と items.name の区別に注意

【出力形式】
SQLだけを返してください。説明文・マークダウン・コードブロック記号（```）は一切不要です。
必ずSELECT文で終わること。UPDATE/DELETE/DROP等は生成禁止。"""

# ── AI呼び出し（リトライ付き） ───────────────────────────────────
async def generate_sql(question: str, error_feedback: str = "") -> str:
    schema = get_schema()
    system = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    user_content = question
    if error_feedback:
        user_content = f"""前回のSQLでエラーが発生しました。
エラー内容: {error_feedback}
元の質問: {question}
エラーを修正した正しいSQLを返してください。"""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 512,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            },
            timeout=30,
        )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"]["message"])
    return data["content"][0]["text"].strip()

# ── SQL実行 ────────────────────────────────────────────────────
def run_sql(sql: str) -> dict:
    # 安全チェック（SELECT以外を弾く）
    clean = sql.strip().upper()
    if not clean.startswith("SELECT"):
        raise ValueError("SELECT文のみ実行可能です")
    for kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]:
        if re.search(rf"\b{kw}\b", clean):
            raise ValueError(f"危険なキーワード '{kw}' が含まれています")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    columns = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return {"columns": columns, "rows": rows}

# ── リクエスト/レスポンス型 ───────────────────────────────────
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    columns: list
    rows: list
    question: str

# ── エンドポイント ────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    sql = ""
    last_error = ""

    # リトライループ（最大2回）
    for attempt in range(3):
        try:
            sql = await generate_sql(req.question, last_error if attempt > 0 else "")
            # コードブロック記号が残った場合の後処理
            sql = re.sub(r"```sql|```", "", sql).strip()
            result = run_sql(sql)
            return QueryResponse(
                sql=sql,
                columns=result["columns"],
                rows=result["rows"],
                question=req.question,
            )
        except Exception as e:
            last_error = str(e)
            if attempt == 2:
                raise HTTPException(
                    status_code=400,
                    detail={"error": last_error, "sql": sql, "attempts": attempt + 1},
                )

@app.get("/tables")
def list_tables():
    conn = sqlite3.connect(DB_PATH)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    result = {}
    for (tname,) in tables:
        rows = conn.execute(f"SELECT * FROM {tname} LIMIT 3").fetchall()
        cols = [d[0] for d in rows[0].cursor.description] if rows else []
        result[tname] = {
            "columns": [{"name": c} for c in cols],
            "preview": [list(r) for r in rows],
        }
    conn.close()
    return result

@app.get("/health")
def health():
    return {"status": "ok"}


# =====
# 2. CORSの設定 (超重要！)
# =====
# React (localhost:5173) からのアクセスを許可するために必須です
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:8000", "http://localhost:3000"], # フロントエンドのURL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====
# 3. ルーターの登録 (URLのマッピング)
# =====
# 認証関連のAPI (生成、一覧、/me など) -> http://localhost:8000/api/auth/...
app.include_router(routes_auth.router, prefix="/api/auth", tags=["Authentication"])

# SQL実行関連のAPI (/run, /run_raw など) -> http://localhost:8000/api/sql/...
app.include_router(routes_execute.router, prefix="/api/sql", tags=["SQL Execution"])

# ★ システム・ディスカバリAPI (/services など) -> http://localhost:8000/api/...
app.include_router(routes_system.router, prefix="/api", tags=["System Discovery"]) # type: ignore


# =====
# ルートURL（動作確認用）
# =====
@app.get("/")
def read_root():
    return {"message": "API Server is running. Visit /docs for Swagger UI."}