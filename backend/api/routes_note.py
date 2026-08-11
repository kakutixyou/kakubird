# =========================================================
# routes_note.py
# AIノート（メモ書き）管理用ルーティング
# =========================================================

import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

# APIRouterの初期化
router = APIRouter()

# ai_server.py の定義と合わせるために BASE_DIR と AI_MEMORY_DIR を設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")

# ノートが保存される専用ディレクトリのパス
NOTES_DIR = os.path.join(AI_MEMORY_DIR, "notes")

# =========================================================
# 1. AI Save Note (ノートの保存)
# =========================================================

@router.post("/api/note/save")
async def save_note_api(title: str, content: str):
    """
    タイトルと本文を受け取り、JSONファイルとして .ai_memory/notes/ 内に保存する
    ファイル名に使えない不正な文字（/ や \\）は自動でアンダースコア（_）に置換する
    """
    # 念のため、保存先ディレクトリが存在するか確認し、なければ作成
    os.makedirs(NOTES_DIR, exist_ok=True)

    # WindowsやLinuxのファイル名として禁止されている文字をセーフティ置換
    safe_title = (
        title
        .replace("/", "_")
        .replace("\\", "_")
    )

    note_path = os.path.join(NOTES_DIR, f"{safe_title}.json")

    # 保存するデータの構築
    data = {
        "title": title,
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        # UTF-8、インデント付きで綺麗にJSON保存
        with open(note_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save note: {str(e)}"
        )

    return {
        "status": "success",
        "note": data
    }

# =========================================================
# 2. AI Notes List (ノートの一覧取得)
# =========================================================

@router.get("/api/note/list")
async def list_notes_api():
    """
    .ai_memory/notes/ フォルダ内にある全てのJSONファイルを読み込み、
    保存されているノートの一覧を配列にして返す
    """
    # ディレクトリが存在しない場合は空のリストを返す（初回起動時など）
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR, exist_ok=True)
        return {
            "status": "success",
            "notes": []
        }

    notes = []

    try:
        for filename in os.listdir(NOTES_DIR):
            # JSONファイル以外はスキップ
            if not filename.endswith(".json"):
                continue

            path = os.path.join(NOTES_DIR, filename)

            # ファイルを読み込んでリストに追加
            with open(path, "r", encoding="utf-8") as f:
                notes.append(
                    json.load(f)
                )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list notes: {str(e)}"
        )

    return {
        "status": "success",
        "notes": notes
    }