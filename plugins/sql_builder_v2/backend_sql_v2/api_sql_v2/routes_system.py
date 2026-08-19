# sql_builder_v2/backend/api/routes_system.py

import os
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
from datetime import datetime
from ai.schema_loader import load_sqlite_schema
router = APIRouter()
# 
# =====
# 1. APIディスカバリ（提供しているサービス一覧を返す）
# =====
@router.get("/schema/{db_name}")
async def get_schema(db_name: str):

    db_path = os.path.join(
        "db",
        "migrations",
        db_name
    )

    if not db_path.endswith(".db"):
        db_path += ".db"

    schema = load_sqlite_schema(db_path)

    return {
        "status": "success",
        "schema": schema
    }
@router.get("/services")
async def discover_services():
    """
    フロントエンドに対して、現在利用可能なAPIサービスの一覧とその仕様（できること）を教えます。
    """
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
                    {"action": "create_database", "description": "新規SQLiteデータベースを作成"} # ここを追加しました！
                ],
                "icon": "cog"
            }
        ]
    }

# =====
# 2. データベース作成 API
# =====

# フロントエンドから受け取るJSONの型定義
class CreateDBRequest(BaseModel):
    db_name: str  # 例: "my_new_project"

@router.post("/create-db")
async def create_database(req: CreateDBRequest):
    """
    指定された名前で新しいSQLiteデータベースファイルを生成します。
    """
    # 保存先ディレクトリの設定（sql_builder_v2/backend/db/migrations/ の中に作ります）
    db_dir = os.path.join("db", "migrations")
    
    # フォルダが存在しない場合は自動的に作成する
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # 最終的なファイルパス（例: db/migrations/my_new_project.db）
    db_path = os.path.join(db_dir, f"{req.db_name}.db")

    # すでに同じ名前のデータベースが存在する場合の処理
    if os.path.exists(db_path):
        return {
            "status": "exists", 
            "message": f"Database '{req.db_name}' already exists.", 
            "path": db_path
        }

    try:
        # SQLiteファイルを作成し、接続して即座に閉じる（これで空のファイルができます）
        conn = sqlite3.connect(db_path)
        
        # ※ もし初期テーブル（usersなど）も一緒に作りたい場合はここで実行できます
        # conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        
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
    
# 3. 生成済みDBの一覧を取得
@router.get("/databases")
async def list_databases():
    """
    生成済みのデータベース一覧と、そのメタデータ（サイズ・更新日時）を取得します。
    """
    # 以前作成したDBの保存先パスに合わせています
    db_dir = os.path.join("db", "migrations")
    
    try:
        # フォルダがまだ存在しない場合は、エラーにせず空のリストを返す
        if not os.path.exists(db_dir):
            return {"databases": []}

        databases_info = []

        # フォルダ内をスキャンして .db ファイルだけを拾い上げる
        for filename in os.listdir(db_dir):
            if filename.endswith(".db"):
                filepath = os.path.join(db_dir, filename)
                
                # ファイルの詳細情報（メタデータ）を取得
                stats = os.stat(filepath)
                size_kb = round(stats.st_size / 1024, 2)  # KB単位に変換して小数点2桁で丸める
                modified_time = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                databases_info.append({
                    "name": filename,             # ファイル名 (例: test.db)
                    "size_kb": size_kb,           # サイズ (例: 12.5)
                    "modified_at": modified_time  # 更新日時 (例: 2026-05-08 12:00:00)
                })

        # 更新日時が新しい順（降順）にソートして返す
        databases_info.sort(key=lambda x: x["modified_at"], reverse=True)

        return {"status": "success", "databases": databases_info}

    except Exception as e:
        print(f"❌ DBリスト取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="データベース一覧の取得に失敗しました")
    
# 4. 指定したDBファイルをダウンロード
@router.get("/download-db/{db_name}")
async def download_database(db_name: str):
    # セキュリティのため、変なパスが入らないようファイル名だけに制限
    clean_name = os.path.basename(db_name)
    if not clean_name.endswith(".db"):
        clean_name += ".db"
        
    db_path = os.path.join("db", "migrations", clean_name)
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    return FileResponse(
        path=db_path,
        filename=clean_name,
        media_type='application/x-sqlite3'
    )
    
# =====
# 5. 指定したDBファイルを削除
# =====

# 削除禁止DB
PROTECTED_DATABASES = [
    "init.db",
    "history.db"
]

@router.delete("/delete-db/{db_name}")
async def delete_database(db_name: str):
    """
    指定されたSQLiteデータベースを削除します。
    """

    try:
        # 危険なパスを防ぐ
        clean_name = os.path.basename(db_name)

        if not clean_name.endswith(".db"):
            clean_name += ".db"

        # 保護DBチェック
        if clean_name in PROTECTED_DATABASES:
            raise HTTPException(
                status_code=403,
                detail=f"{clean_name} は保護されているため削除できません"
            )

        db_path = os.path.join("db", "migrations", clean_name)

        # 存在確認
        if not os.path.exists(db_path):
            raise HTTPException(
                status_code=404,
                detail="削除対象のDBが存在しません"
            )

        # 削除実行
        os.remove(db_path)

        print(f"🗑️ DB削除成功: {clean_name}")

        return {
            "status": "success",
            "message": f"{clean_name} を削除しました"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ DB削除エラー: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail=f"DB削除に失敗しました: {str(e)}"
        )