# backend/api/routes_memory.py

import os
import uuid
import shutil
import tempfile
import zipfile
import json
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel  # 追加: リクエストボディ定義用

from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.embedding_service import EmbeddingService
from plugins.ai_memory.vector_store import InMemoryVectorStore, ChromaVectorStore
from plugins.ai_memory.workspace_scanner import WorkspaceScanner

from core.memory_manager import (
    get_chat_history,
    get_all_tasks,
    load_json as mm_load_json,
    save_json as mm_save_json,
)

# ⚠️ OcrRecruitHandlerの実際の場所に合わせてインポートしてください
# from plugins.ocr_handler import OcrRecruitHandler

router = APIRouter(
    prefix="/api/memory",
    tags=["Memory & Workspace"]
)

# =========================================================
# リクエストモデル定義
# =========================================================

class OCRRequest(BaseModel):
    image: str

# =========================================================
# パス定数（1か所だけで定義）
# =========================================================

_BACKEND_DIR = Path(__file__).parent.parent
MEMORY_DIR   = _BACKEND_DIR / ".ai_memory"
MEMORY_DIR.mkdir(exist_ok=True)

CHAT_HISTORY_DIR = MEMORY_DIR / "chat_history"
ZIP_HISTORY_FILE = MEMORY_DIR / "zip_history.json"
LONG_TERM_DIR    = MEMORY_DIR / "long_term"
PROJECT_DIR      = MEMORY_DIR / "projects"

DB_SETS_DIR = (
    _BACKEND_DIR / "plugins" / "sql_builder_v2" / "src" / "data" / "db_sets"
)

# =========================================================
# グローバルインスタンス（サーバー起動中に記憶を保持）
# =========================================================

global_vector_store = InMemoryVectorStore()
embedder = EmbeddingService()
chunker  = CodeChunker()


# =========================================================
# ローカルJSON helpers（Pathオブジェクト対応）
# =========================================================

def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"JSON保存エラー: {e}")


# =========================================================
# 🖼️ OCR スクリーンショット解析 (FastAPI対応版)
# =========================================================

@router.post("/ocr-screenshot")
async def ocr_screenshot(data: OCRRequest):
    try:
        # handler = OcrRecruitHandler()
        # response_type, content = await handler.handle("", data.image)
        
        # 動作確認用のダミーレスポンス（上記の実装に合わせてコメントアウトを外してください）
        response_type = "text"
        content = "OCRによる解析結果のテキストがここに入ります。"

        return {
            "response_type": response_type,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR処理中にエラーが発生しました: {e}")


# =========================================================
# 📋 Jobs & Folders (MemoryManager.jsx 対応)
# =========================================================

@router.get("/jobs")
async def get_jobs():
    # TODO: 実際のジョブ一覧を取得するロジックを実装してください
    return {"jobs": []}

@router.get("/folders")
async def get_folders():
    # TODO: 実際のフォルダ一覧を取得するロジックを実装してください
    return {"folders": []}


# =========================================================
# 📦 ZIPアップロード → RAGパイプライン
# =========================================================

@router.post("/upload-workspace")
async def upload_workspace(file: UploadFile = File(...)):
    filename = file.filename
    if not filename or not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="ZIPファイルのみ対応しています")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, filename)

    try:
        with open(zip_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        scanner       = WorkspaceScanner(root_path=extract_dir)
        scanned_files = scanner.scan()

        processed_files = 0
        total_chunks    = 0

        for file_info in scanned_files:
            try:
                content = Path(file_info.absolute_path).read_text(
                    encoding="utf-8", errors="replace"
                )
                chunks = chunker.chunk_file(
                    file_info.absolute_path, content, file_info.language
                )
                for chunk in chunks:
                    vector = embedder.embed(chunk.content)
                    global_vector_store.add(chunk, vector)
                    total_chunks += 1
                processed_files += 1
            except Exception as e:
                print(f"スキップ: {file_info.path} ({e})")

        # ZIP履歴を記録
        _record_zip_history(filename, processed_files, total_chunks)

        return {
            "status": "success",
            "message": f"{processed_files}個のファイルを解析し、{total_chunks}個の記憶を生成しました。",
            "stats": {
                "scanned_files": processed_files,
                "total_chunks": total_chunks,
                "total_memory_size": global_vector_store.count(),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG処理中にエラーが発生しました: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _record_zip_history(filename: str, scanned_files: int, total_chunks: int):
    histories = _load(ZIP_HISTORY_FILE, [])
    histories.insert(0, {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scanned_files": scanned_files,
        "total_chunks": total_chunks,
        "status": "active",
    })
    _save(ZIP_HISTORY_FILE, histories)


# =========================================================
# 📊 統計
# =========================================================

@router.get("/stats")
async def get_memory_stats():
    return {
        "status": "active",
        "total_chunks_in_memory": global_vector_store.count(),
    }


# =========================================================
# 💬 会話履歴  →  /api/memory/conversations
# =========================================================

@router.get("/conversations")
async def get_conversations():
    raw = get_chat_history(limit=50)
    return {
        "messages": [
            {
                "role":      msg.get("role", "unknown"),
                "content":   msg.get("content", ""),
                "timestamp": msg.get("timestamp", ""),
            }
            for msg in raw
        ]
    }

# =========================================================
# 💬 会話履歴をすべて削除  →  DELETE /api/memory/conversations
# =========================================================
@router.delete("/conversations")
async def clear_conversations():
    try:
        deleted_count = 0
        if CHAT_HISTORY_DIR.exists():
            for file_path in CHAT_HISTORY_DIR.glob("*.json"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ ファイル削除スキップ ({file_path}): {e}")

        return {
            "status": "success", 
            "message": f"{deleted_count}件の会話履歴ファイルを削除しました。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴の削除中にエラーが発生しました: {e}")


# =========================================================
# 📝 メモ（長期記憶）  →  /api/memory/notes
# =========================================================

@router.get("/notes")
async def get_notes():
    notes = []
    if LONG_TERM_DIR.exists():
        for path in LONG_TERM_DIR.glob("*.json"):
            data = _load(path, {})
            text = data.get("text", "")
            if text:
                notes.append(text)
    return {"notes": notes}


# =========================================================
# ✅ タスク  →  /api/memory/tasks
# =========================================================

@router.get("/tasks")
async def get_tasks():
    raw = get_all_tasks()
    return {
        "tasks": [
            {
                "title":    t.get("task_name", "無題"),
                "status":   t.get("status", "pending"),
                "priority": t.get("priority", 0),
            }
            for t in raw
        ]
    }


# =========================================================
# 📂 関連ファイル  →  /api/memory/files
# =========================================================

@router.get("/files")
async def get_files():
    files = []
    if PROJECT_DIR.exists():
        for path in PROJECT_DIR.glob("*.json"):
            data = _load(path, {})
            for fpath in data.get("recent_files", []):
                files.append({
                    "path":     fpath,
                    "language": _guess_language(fpath),
                    "size":     0,
                })
    return {"files": files}


def _guess_language(path: str) -> str:
    return {
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".json": "JSON", ".md": "Markdown", ".sql": "SQL",
    }.get(os.path.splitext(path)[-1].lower(), "unknown")


# =========================================================
# 📦 ZIP履歴  →  /api/memory/zip-history
# =========================================================

@router.get("/zip-history")
async def get_zip_history():
    return {"histories": _load(ZIP_HISTORY_FILE, [])}


@router.delete("/zip-history/{zip_id}")
async def delete_zip_history(zip_id: str):
    histories = _load(ZIP_HISTORY_FILE, [])
    filtered  = [h for h in histories if h.get("id") != zip_id]

    if len(filtered) == len(histories):
        raise HTTPException(status_code=404, detail="指定されたIDが見つかりません")

    _save(ZIP_HISTORY_FILE, filtered)

    try:
        store = ChromaVectorStore()
        store.collection.delete(where={"zip_id": zip_id})
        print(f"🗑️ ChromaDB: zip_id={zip_id} を削除しました")
    except Exception as e:
        print(f"⚠️ ChromaDB削除失敗（無視）: {e}")

    return {"ok": True, "deleted_id": zip_id}


# =========================================================
# 🗃️ DBセット取得
# =========================================================

@router.get("/db-set/{name}")
async def get_db_set(name: str):
    data = _load(DB_SETS_DIR / f"{name}.json", None)
    if data is None:
        raise HTTPException(status_code=404, detail=f"{name}.json が見つかりません")
    return {"name": name, "data": data}


# =========================================================
# ⚙️ バックグラウンドタスク
# =========================================================

@router.post("/run-task")
async def run_ai_task(task_type: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(_execute_heavy_ai_work, task_type)
    return {"status": "processing", "message": "タスクをバックグラウンドで開始しました。"}


def _execute_heavy_ai_work(task_type: str):
    print(f"裏で {task_type} を実行中...")