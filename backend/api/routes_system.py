# To/backend/api/routes_system.py
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
# from sympy import evaluate
# from plugins.recruit.evaluator import evaluate

# ai_server.py と同じ階層、または sys.path に通した core からインポート
from core.session_manager import get_active_session, set_active_file, add_recent_action
from core.context_builder import build_ai_context
from core.ai_state_manager import load_current_state
from core.memory_manager import load_memory
# from recruit.evaluator import evaluate
from plugins.sql_builder_v2.backend_sql_v2.api_sql_v2.ai.schema_loader import load_sqlite_schema

# APIRouterの初期化
router = APIRouter()

# ai_server.py で定義されている環境変数やパスの定義と合わせるための設定
# (ai_server.py 側で sys.path が通っているため、BASE_DIR を再計算)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")

import sqlite3
import sys
from fastapi.responses import FileResponse # ✨ ダウンロード用にインポート追加
from pydantic import BaseModel
from fastapi import UploadFile, File
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/api
backend_dir = os.path.dirname(current_dir) # .../backend
project_root = os.path.dirname(backend_dir)
# from plugins.recruit.evaluator import evaluate
if project_root not in sys.path:
    sys.path.append(project_root)
from plugins.sql_builder_v2.backend_sql_v2.api_sql_v2.ai.schema_loader import load_sqlite_schema
# from plugins.sql_builder_v2.backend_sql_v2.api_sql_v2.ai.schema_loader import load_sqlite_schema
# from ai.schema_loader import load_sqlite_schema
# from backend.api.schema_loader import load_sqlite_schema
# from ai.schema_loader import load_sqlite_schema

router = APIRouter()

# 保存先ディレクトリの共通設定
DB_DIR = os.path.join("db", "migrations")

# =====
# 1. APIディスカバリ（既存のまま）
# =====
@router.post("/evaluate-job")
async def process_job_evaluation(ocr_text: str):
    """
    フロントエンドから送られてきたOCRテキスト（またはURLスクレイピング結果）を評価する
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="APIキーが設定されていません。")

    try:
        # evaluator.py に処理を丸投げ
        evaluation_result = evaluate(ocr_text, api_key)
        
        # フロントエンドのUI Block（JsonViewerBlockや独自のDashboardBlock）として返す
        return {
            "status": "success",
            "message": f"🤖 {evaluation_result['company_name']} の求人評価が完了しました。総合評価は {evaluation_result['score']['grade']} です。",
            "blocks": [
                {
                    "type": "JsonViewerBlock",
                    "props": {
                        "title": "📊 求人審査レポート",
                        "data": evaluation_result
                    }
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"評価中にエラーが発生しました: {str(e)}")
    
@router.get("/services")
async def discover_services():
    return {
        "status": "success",
        "version": "1.0.0",
        "services": [
            {
                "id": "sql_builder",
                "name": "SQL Data API",
                "description": "データベースに対してクエリを実行し、データを取得・操作します。",
                "endpoint_base": "/api/sql",
                "capabilities": [
                    {"action": "execute_select", "description": "データの検索と取得"},
                    {"action": "get_schema", "description": "テーブル構造の確認"},
                    {"action": "execute_raw", "description": "生のSQL文の実行（要admin権限）"}
                ],
                "icon": "database"
            },
            {
                "id": "css_generator",
                "name": "CSS Style API",
                "description": "プロンプトからTailwindや素のCSSを生成・適用します。",
                "endpoint_base": "/api/css",
                "capabilities": [
                    {"action": "generate_class", "description": "Tailwindクラスの生成"},
                    {"action": "generate_raw_css", "description": "生のCSSコードの生成"}
                ],
                "icon": "palette"
            },
            {
                "id": "system",
                "name": "System API",
                "description": "システムに関する情報や操作を提供します。",
                "endpoint_base": "/api/system",
                "capabilities": [
                    {"action": "discover_services", "description": "利用可能なAPIサービスのリストを取得"},
                    {"action": "create_database", "description": "新規SQLiteデータベースを作成"},
                    {"action": "list_databases", "description": "生成済みDBの一覧を取得"} # 追記
                ],
                "icon": "cog"
            }
        ]
    }

# =====
# 2. データベース作成 API（既存のまま）
# =====
class CreateDBRequest(BaseModel):
    db_name: str  

@router.post("/create-db")
async def create_database(req: CreateDBRequest):
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    db_path = os.path.join(DB_DIR, f"{req.db_name}.db")

    if os.path.exists(db_path):
        return {
            "status": "exists", 
            "message": f"Database '{req.db_name}' already exists.", 
            "path": db_path
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"✅ 新規DB作成成功: {db_path}")
        return {
            "status": "success",
            "message": f"Database '{req.db_name}' created successfully.",
            "path": db_path
        }
    except Exception as e:
        print(f"❌ DB作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create DB: {str(e)}")


# ===
# ✨ 3. 【新規追加】生成済みデータベース一覧取得 API (これで404を一掃！)
# ===
@router.get("/databases")
async def list_databases():
    """
    db/migrations/ フォルダ内にある .db ファイルをスキャンして一覧を返します。
    """
    db_files = []
    
    if os.path.exists(DB_DIR):
        for file in os.listdir(DB_DIR):
            if file.endswith(".db"):
                path = os.path.join(DB_DIR, file)
                size_kb = round(os.path.getsize(path) / 1024)
                
                # 更新日時の取得（簡易的にYYYY-MM-DD文字列にする）
                from datetime import datetime
                mtime = os.path.getmtime(path)
                mod_time_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

                db_files.append({
                    "name": file.replace(".db", ""), # 画面表示用に拡張子を取るかはお好みで調整
                    "size_kb": size_kb,
                    "modified_at": mod_time_str
                })
                
    return {"databases": db_files}


# ===
# ✨ 4. 【新規追加】データベース削除 API
# ===
@router.delete("/delete-db/{name}")
async def delete_database(name: str):
    # .db がついていなければ補完
    filename = name if name.endswith(".db") else f"{name}.db"
    db_path = os.path.join(DB_DIR, filename)
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"Database '{filename}' not found.")
        
    try:
        os.remove(db_path)
        print(f"🗑️ DB削除成功: {db_path}")
        return {"status": "success", "message": f"データベース '{filename}' を削除しました。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"削除に失敗しました: {str(e)}")


# ===
# ✨ 5. 【新規追加】データベース ダウンロード API
# ===
@router.get("/download-db/{name}")
async def download_database(name: str):
    filename = name if name.endswith(".db") else f"{name}.db"
    db_path = os.path.join(DB_DIR, filename)
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(
        path=db_path, 
        media_type="application/octet-stream", 
        filename=filename
    )

# =====
# 6. DBスキーマ取得
# =====

@router.get("/schema/{db_name}")
async def get_schema(db_name: str):

    filename = (
        db_name
        if db_name.endswith(".db")
        else f"{db_name}.db"
    )

    db_path = os.path.join(DB_DIR, filename)

    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=404,
            detail="Database not found."
        )

    try:
        schema = load_sqlite_schema(db_path)

        return {
            "status": "success",
            "database": filename,
            "schema": schema
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
        
# =====
# 7. テーブル一覧取得
# =====

@router.get("/tables/{db_name}")
async def get_tables(db_name: str):

    filename = (
        db_name
        if db_name.endswith(".db")
        else f"{db_name}.db"
    )

    db_path = os.path.join(DB_DIR, filename)

    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=404,
            detail="Database not found."
        )

    try:
        conn = sqlite3.connect(db_path)

        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%';
        """)

        tables = [
            row[0]
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            "status": "success",
            "tables": tables
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
        
# =====
# 8. テーブルデータ取得
# =====

@router.get("/table-data/{db_name}/{table_name}")
async def get_table_data(
    db_name: str,
    table_name: str
):

    filename = (
        db_name
        if db_name.endswith(".db")
        else f"{db_name}.db"
    )

    db_path = os.path.join(DB_DIR, filename)

    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=404,
            detail="Database not found."
        )

    try:
        conn = sqlite3.connect(db_path)

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        cursor.execute(
            f"SELECT * FROM {table_name} LIMIT 100"
        )

        rows = [
            dict(row)
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            "status": "success",
            "table": table_name,
            "rows": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
        
@router.get("/api/status")
async def ai_status():
    """
    サーバーの稼働状態、使用中のモデル、アクティブなセッション情報を取得
    """
    session = get_active_session()

    return {
        "status": "running",
        "model": OLLAMA_MODEL,
        "session": session,
        "memory_dir": AI_MEMORY_DIR,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ===
# 2. Current AI Context
# ===

@router.get("/api/context")
async def get_current_context():
    """
    現在のAIが把握しているコンテキスト（文脈情報）を構築して返す
    """
    context = build_ai_context()

    return {
        "status": "success",
        "context": context
    }

# ===
# 3. AI Self Analysis
# ===

@router.get("/api/ai/self-analysis")
async def ai_self_analysis():
    """
    現在の状態、セッション、記憶しているキーの一覧を自己分析して返す
    """
    current_state = load_current_state()
    session = get_active_session()
    memory = load_memory()

    summary = {
        "active_project": current_state.get("active_project"),
        "session_id": session.get("session_id"),
        "recent_actions": session.get("recent_actions", [])[:10],
        "memory_keys": list(memory.keys())[:20]
    }

    return {
        "status": "success",
        "analysis": summary
    }

# ===
# 4. AI File Open
# ===

@router.post("/api/file/open")
async def open_file_api(file_path: str):
    """
    指定されたパスのファイルを開き、中身をテキストとして読み込む
    同時に、アクティブなファイルとしてセッションに記録する
    """
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File Not Found: {file_path}"
        )

    # アクティブファイルを更新
    set_active_file(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file: {str(e)}"
        )

    # 最近のアクションにログを追加
    add_recent_action("open_file", file_path)

    return {
        "status": "success",
        "path": file_path,
        "content": content
    }

# ===
# 5. AI Search
# ===

@router.get("/api/search")
async def search_memory_api(keyword: str):
    """
    記憶（メモリデータ）の中から、キーワードが含まれるものを部分一致で検索する
    """
    memory = load_memory()
    matched = {}

    for key, value in memory.items():
        if keyword.lower() in str(value).lower():
            matched[key] = value

    return {
        "status": "success",
        "results": matched
    }