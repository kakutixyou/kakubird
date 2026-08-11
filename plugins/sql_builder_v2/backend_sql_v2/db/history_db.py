import sqlite3
import os
#history_db.py
# DBファイルの保存場所（backendディレクトリの直下に history.db を作成します）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "history.db")

def get_db_connection():
    """
    履歴データベースへの接続を取得するヘルパー関数。
    他のファイル（履歴Serviceなど）からDBを操作する際に使い回せます。
    """
    conn = sqlite3.connect(DB_PATH)
    # 検索結果をタプルではなく辞書のようにキーでアクセスできるようにする設定
    conn.row_factory = sqlite3.Row 
    return conn

# backend/db/history_db.py

def init_history_db():
    print(f"履歴データベースの初期化を開始します... (パス: {DB_PATH})")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 既存の実行履歴テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sql_query TEXT NOT NULL,
            template_type TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ★ 追加：APIキー管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_value TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            scope TEXT DEFAULT 'admin',     -- ★追加: 権限 (admin, read_only, write_only)
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("履歴データベースの初期化が完了しました。")