# ===
# routes_system.py
# システム・ステータス・コンテキスト関連ルーティング
# ===
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException

# coreモジュール群のインポート
from core.project_scanner import scan_project, build_project_summary, detect_hotspots
from core.session_manager import add_recent_action
from core.ai_state_manager import save_current_state
from core.memory_manager import save_memory, save_project_analysis
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException

# ai_server.py と同じ階層、または sys.path に通した core からインポート
from core.session_manager import get_active_session, set_active_file, add_recent_action
from core.context_builder import build_ai_context
from core.ai_state_manager import load_current_state
from core.memory_manager import load_memory

# APIRouterの初期化
router = APIRouter()

# ai_server.py で定義されている環境変数やパスの定義と合わせるための設定
# (ai_server.py 側で sys.path が通っているため、BASE_DIR を再計算)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")

# ===
# 1. Health Check & Status
# ===

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
    
# ===
# 1. Project Scan (ローカルディレクトリの解析)
# ===

@router.post("/api/project/scan")
async def project_scan_api(project_path: str):
    """
    指定されたローカルディレクトリのパスを解析し、プロジェクト構造を読み込む
    """
    if not os.path.exists(project_path):
        raise HTTPException(
            status_code=404,
            detail=f"Project Path Not Found: {project_path}"
        )

    project_name = os.path.basename(project_path.rstrip("/\\"))
    
    try:
        # プロジェクトの解析を実行
        result = scan_project(
            target_dir=project_path,
            project_name=project_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}"
        )

    # セッションログに追加
    add_recent_action("project_scan", f"{project_path} を解析")

    return {
        "status": "success",
        "result": result
    }

# ===
# 2. ZIP Upload (ZIPファイルをアップロードして解析)
# ===

@router.post("/api/memory/upload-zip")
async def upload_zip_memory(file: UploadFile = File(...)):
    """
    ZIPファイルをアップロードし、一時フォルダで解凍してからプロジェクト解析を実行、
    AIの記憶（メモリ）に定着させる一連のフロー
    """
    print("=")
    print(f"📦 ZIP Upload Started: {file.filename}")
    print("=")

    # 一時ディレクトリの作成
    temp_dir = tempfile.mkdtemp()

    # 安全なファイル名の取得（None回避）
    safe_filename = getattr(file, "filename", None) or "uploaded.zip"
    zip_path = os.path.join(temp_dir, safe_filename)

    try:
        # -------------------------------------------------
        # 1. ZIPファイルの保存
        # -------------------------------------------------
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # -------------------------------------------------
        # 2. 解凍処理
        # -------------------------------------------------
        extract_dir = os.path.join(temp_dir, "project")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"📂 Extracted to: {extract_dir}")

        # -------------------------------------------------
        # 3. プロジェクト解析の実行
        # -------------------------------------------------
        project_name = os.path.splitext(safe_filename)[0]

        result = scan_project(
            target_dir=extract_dir,
            project_name=project_name
        )

        # -------------------------------------------------
        # 4. サマリーとホットスポット（重要箇所）の抽出
        # -------------------------------------------------
        summary = build_project_summary(project_name)
        hotspots = detect_hotspots(project_name)

        # -------------------------------------------------
        # 5. メモリと状態の保存
        # -------------------------------------------------
        save_project_analysis(project_name, result)
        
        save_memory(
            key=f"project_summary_{project_name}",
            value=summary
        )

        save_current_state({
            "active_project": project_name,
            "last_uploaded_zip": safe_filename,
            "last_scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        add_recent_action("upload_zip", f"{safe_filename} をAIへ記憶")

        print(f"✅ ZIP解析完了: {project_name}")

        # フロントエンドに返すレスポンス
        return {
            "status": "success",
            "project_name": project_name,
            "summary": summary,
            "hotspots": hotspots[:10],
            "statistics": result.get("statistics", {}),
            "message": f"{project_name} の構造を記憶しました"
        }

    except zipfile.BadZipFile:
        print("❌ ZIPエラー: 不正なファイル形式です")
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP File"
        )
    except Exception as e:
        print(f"❌ ZIP解析失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )
    finally:
        # -------------------------------------------------
        # 6. 一時ファイルのクリーンアップ (必ず実行)
        # -------------------------------------------------
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("🧹 一時フォルダを削除しました")