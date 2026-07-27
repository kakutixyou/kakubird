# plugins/sql_builder_v2/backend/api/routes_auth.py
import secrets
import sqlite3
from datetime import datetime, timedelta
import contextlib

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from db.history_db import get_db_connection

router = APIRouter()

# ★FastAPI標準のBearerトークン取得機能（Swagger UIでのテストも可能になります）
security = HTTPBearer()

# =========================================
# リクエスト/レスポンス モデル
# =========================================
class KeyGenerateRequest(BaseModel):
    client_name: str
    scope: str = "read_only"

# =========================================
# 【コア機能】APIキー検証（Dependency Injection用）
# =========================================
def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    他のAPIエンドポイントで Depends(verify_api_key) として呼び出すための関数。
    自動的に Authorization ヘッダーを検証し、ユーザー情報を返します。
    """
    api_key = credentials.credentials
    now = datetime.utcnow()

    # with構文を使うことで、エラー時も確実にDB接続を閉じます（DBロック防止）
    with contextlib.closing(get_db_connection()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM api_keys
            WHERE key_value = ?
            """,
            (api_key,)
        )
        key_data = cursor.fetchone()

    # --- 厳密なチェック ---
    if not key_data:
        raise HTTPException(status_code=401, detail="無効なAPIキーです")
    
    if not key_data["is_active"]:
        raise HTTPException(status_code=403, detail="このAPIキーは無効化されています")

    if key_data["expires_at"]:
        expires_at = datetime.fromisoformat(key_data["expires_at"])
        if expires_at < now:
            # 期限切れの場合は非アクティブに更新しておく（おまけの親切設計）
            with contextlib.closing(get_db_connection()) as conn:
                conn.cursor().execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_data["id"],))
                conn.commit()
            raise HTTPException(status_code=403, detail="APIキーの有効期限が切れています")

    return dict(key_data)


# =========================================
# APIキー生成（1時間有効）
# =========================================
@router.post("/generate")
async def generate_api_key(request: KeyGenerateRequest):
    new_key = f"sk-{secrets.token_urlsafe(32)}"
    expires_at = datetime.utcnow() + timedelta(hours=1)

    try:
        with contextlib.closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_keys (key_value, client_name, scope, expires_at, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (new_key, request.client_name, request.scope, expires_at)
            )
            conn.commit()

        return {
            "status": "success",
            "api_key": new_key,
            "expires_at": expires_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キーの生成に失敗しました: {str(e)}")


# =========================================
# APIキー一覧（期限チェック込み）
# =========================================
@router.get("/list")
async def list_api_keys():
    try:
        now = datetime.utcnow()
        with contextlib.closing(get_db_connection()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 期限切れを自動で無効化
            cursor.execute(
                """
                UPDATE api_keys
                SET is_active = 0
                WHERE expires_at IS NOT NULL AND expires_at < ? AND is_active = 1
                """,
                (now,)
            )

            cursor.execute(
                """
                SELECT id, key_value, client_name, scope, is_active, created_at, expires_at
                FROM api_keys
                ORDER BY created_at DESC
                """
            )
            keys = cursor.fetchall()
            conn.commit()

        return [dict(k) for k in keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# APIキー削除
# =========================================
@router.delete("/delete/{key_id}")
async def delete_api_key(key_id: int):
    try:
        with contextlib.closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="指定されたキーが見つかりません")

        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# ★新規：自己紹介＆権限確認API (フロントやGeminiが使う)
# =========================================
@router.get("/me")
async def get_my_info(current_key: dict = Depends(verify_api_key)):
    """
    通信してきたAPIキーの持ち主と、その「権限(できること)」を返します。
    """
    scope = current_key["scope"]
    
    # 権限(scope)に応じて、許可されるアクション(Geminiに教えるFunction)を定義
    allowed_actions = []
    if scope == "read_only":
        allowed_actions = ["execute_select_sql", "get_database_schema"]
    elif scope == "admin":
        allowed_actions = ["execute_select_sql", "get_database_schema", "execute_update_sql"]

    return {
        "status": "success",
        "client_name": current_key["client_name"],
        "scope": scope,
        "allowed_actions": allowed_actions,
        "expires_at": current_key["expires_at"]
    }