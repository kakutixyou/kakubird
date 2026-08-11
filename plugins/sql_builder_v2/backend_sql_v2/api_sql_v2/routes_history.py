# backend/api/routes_history.py

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3

# 先ほど作成した history_db.py から接続関数をインポート
from db.history_db import get_db_connection

router = APIRouter()

# =========================================================
# 1. スキーマ定義
# ※後で schemas/history_models.py に移動させるとさらに綺麗です
# =========================================================
class HistoryCreate(BaseModel):
    """履歴作成用のリクエストモデル"""
    sql_query: str = Field(..., description="実行したSQL文")
    template_type: Optional[str] = Field(None, description="使用したテンプレート種別（手入力の場合はNone）")
    status: str = Field(..., description="実行結果 (例: 'success', 'error')")

class HistoryResponse(BaseModel):
    """履歴取得時のレスポンスモデル"""
    id: int
    sql_query: str
    template_type: Optional[str]
    status: str
    created_at: str


# =========================================================
# 2. データベース接続の管理 (Dependency Injection)
# =========================================================
def get_db():
    """
    APIが呼ばれるたびにDB接続を開き、レスポンスを返す時に確実に閉じるための関数。
    """
    conn = get_db_connection()
    try:
        yield conn  # エンドポイントの処理中はここで接続を渡す
    finally:
        conn.close() # 処理が終わったら必ず閉じる


# =========================================================
# 3. エンドポイント
# =========================================================

@router.get("/", response_model=List[HistoryResponse])
async def get_history(
    limit: int = Query(50, description="取得する最大件数", ge=1, le=200),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    保存されているSQLの実行履歴を新しい順に取得します。
    """
    try:
        cursor = db.cursor()
        # 新しいものから順に、指定された件数(limit)だけ取得
        cursor.execute(
            "SELECT id, sql_query, template_type, status, created_at FROM query_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        
        # sqlite3.Row オブジェクトを通常の辞書に変換して返す
        return [dict(row) for row in rows]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴の取得に失敗しました: {str(e)}")


@router.post("/", response_model=HistoryResponse)
async def add_history(
    item: HistoryCreate,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    新しい実行履歴をデータベースに保存します。
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO query_history (sql_query, template_type, status) VALUES (?, ?, ?)",
            (item.sql_query, item.template_type, item.status)
        )
        db.commit() # 変更を確定
        
        # 保存したばかりのデータのIDを取得
        new_id = cursor.lastrowid
        
        # 保存した内容をそのまま取得して返す（created_at 等を含めるため）
        cursor.execute("SELECT id, sql_query, template_type, status, created_at FROM query_history WHERE id = ?", (new_id,))
        new_row = cursor.fetchone()
        
        return dict(new_row)
        
    except Exception as e:
        db.rollback() # エラーが起きたら変更を破棄して安全な状態に戻す
        raise HTTPException(status_code=500, detail=f"履歴の保存に失敗しました: {str(e)}")


@router.delete("/{history_id}")
async def delete_history(
    history_id: int,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    指定したIDの履歴を削除します。
    """
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM query_history WHERE id = ?", (history_id,))
        db.commit()
        
        # 削除された行が0件だった場合（存在しないIDが指定された場合）
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
            
        return {"message": "履歴を削除しました", "id": history_id}
        
    except HTTPException:
        raise # 404エラーはそのまま返す
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"履歴の削除に失敗しました: {str(e)}")