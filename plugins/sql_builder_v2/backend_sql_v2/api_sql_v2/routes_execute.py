# To(と)/sql_builder_v2/backend_sql_v2/api_sql_v2/routes_execute.py
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional

# 各モジュールのインポート（フォルダ構成に合わせています）
from api.routes_auth import verify_api_key
from services.sql_service import SQLService
from repositories.sql_repository import SQLRepository

router = APIRouter()

# =====
# リクエストモデル (クエリビルダー用)
# =====
class Condition(BaseModel):
    field: str
    operator: str
    value: Any

class QueryRequest(BaseModel):
    table: str
    columns: List[str]
    conditions: Optional[List[Condition]] = None
    limit: Optional[int] = None

# =====
# リクエストモデル (生SQL用)
# =====
class RawQueryRequest(BaseModel):
    query: str

# =====
# 1. クエリビルダー実行API (SELECT専用)
# =====
@router.post("/run")
async def execute_builder_sql(
    request: QueryRequest, 
    # ★ 先ほど作った verify_api_key を Depends で呼び出す
    current_key: dict = Depends(verify_api_key) 
):
    """
    JSON形式で条件を受け取り、SQLを組み立てて実行するAPI。
    基本的にSELECT文になるため、read_only 権限でも実行可能。
    """
    try:
        # Pydantic v2 の場合は model_dump()、v1 の場合は dict() を使用
        # request_data = request.dict() 
        request_data = request.model_dump()

        # 依存性注入 (DI) パターンでサービスを呼び出し
        repo = SQLRepository() 
        service = SQLService(repo)
        
        # サービスの実行
        result = service.execute_query(request_data)
        
        return {
            "status": "success",
            "executed_by": current_key["client_name"], # 誰が実行したかログを残す用途に使える
            "data": result
        }
    except ValueError as e:
        # SQLの組み立てエラーなど
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # その他の予期せぬエラー
        raise HTTPException(status_code=500, detail=f"クエリ実行中にエラーが発生しました: {str(e)}")


# =====
# 2. 生SQL実行API (権限チェック付き)
# =====
@router.post("/run_raw")
async def execute_raw_sql(
    request: RawQueryRequest,
    current_key: dict = Depends(verify_api_key)
):
    sql = request.query.strip()
    
    # ★ 権限チェックをより強力にアップデート！
    if current_key["scope"] == "read_only":
        # 1. 最初の単語が SELECT か WITH かチェック (大文字小文字問わず)
        if not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
            raise HTTPException(
                status_code=403, 
                detail="【権限エラー】あなたのAPIキーではデータ更新・削除は実行できません。"
            )
        
        # 2. セミコロン(;)による複数文の実行をブロック（簡易的なSQLインジェクション対策）
        # 文末のセミコロンはOKだが、途中にセミコロンがある場合は弾く
        if ";" in sql.rstrip(";"):
            raise HTTPException(
                status_code=400, 
                detail="【セキュリティエラー】複数のSQL文を一度に実行することは許可されていません。"
            )

    try:
        repo = SQLRepository()
        service = SQLService(repo)
        
        result = service.execute_raw_query(sql) # 将来的には # type: ignore を外す
        
        return {
            "status": "success",
            "executed_by": current_key["client_name"],
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQLエラー: {str(e)}")