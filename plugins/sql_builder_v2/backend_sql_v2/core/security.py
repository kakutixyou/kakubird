import os
from dotenv import load_dotenv
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# .env ファイルを読み込む
load_dotenv()

# .env から APIキーを取得（設定がない場合のデフォルト値を第2引数に指定）
# API_KEY = os.getenv("SQL_BUILDER_API_KEY", "default-dev-key-12345")
API_KEY_NAME = "access_token"
API_KEY = "nannkakaku"
# HTTPヘッダーの "access_token" という項目を探す設定
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_from_header: str = Security(api_key_header)):
    """
    FastAPIの各ルートで 'Depends(get_api_key)' として使用。
    ヘッダーのキーが .env の値と一致するか検証します。
    """
    if api_key_from_header == API_KEY:
        return api_key_from_header
    
    # キーが一致しない、または存在しない場合は 403 Forbidden を返す
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials. Invalid API Key."
    )
    
def verify_api_key(token: str) -> bool:
    """
    フロントエンドから送られてきたAPIキー（トークン）が正しいか検証する関数
    """
    # 開発用：とりあえず今はどんなキーが来てもヨシとする場合
    # return True 

    # 本格的な実装：環境変数に設定した秘密のキーと一致するかチェックする
    expected_token = os.getenv("API_SECRET_KEY", "my_secret_token_123")
    return token == expected_token