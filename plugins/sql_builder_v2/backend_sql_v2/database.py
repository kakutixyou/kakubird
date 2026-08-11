import sqlite3
from contextlib import contextmanager
import sqlite3
import urllib.parse
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any

class DatabaseManager:
    """
    SQLiteデータベースへの接続とデータ操作を管理するクラス
    """

    @staticmethod
    @contextmanager
    def get_connection(db_path: str, read_only: bool = False):
        """
        データベースへの安全な接続を提供するコンテキストマネージャ
        
        :param db_path: SQLiteファイルの絶対パス
        :param read_only: Trueの場合、読み取り専用モードで接続する
        """
        path = Path(db_path)
        if not path.exists():
            raise FileNotFoundError(f"データベースファイルが見つかりません: {db_path}")

        # URI形式のパスを作成 (Windowsのパス区切り文字などを適切に処理)
        # 読み取り専用モードの場合は 'mode=ro' を付加
        encoded_path = urllib.parse.quote(str(path.absolute()))
        db_uri = f"file:{encoded_path}"
        if read_only:
            db_uri += "?mode=ro"

        # uri=True を指定することで、mode=ro などのパラメータを有効にする
        conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # カラム名でアクセスできるようにする
        
        try:
            yield conn
        finally:
            conn.close()

    @classmethod
    def get_schema(cls, db_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        データベース内の全テーブル名とカラム情報を取得する
        """
        schema = {}
        with cls.get_connection(db_path, read_only=True) as conn:
            # テーブル一覧を取得
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()

            for (table_name,) in tables:
                # 各テーブルのカラム情報を取得
                cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                schema[table_name] = [
                    {"name": c[1], "type": c[2], "pk": bool(c[5])}
                    for c in cols
                ]
        return schema


from contextlib import contextmanager
from pathlib import Path
import urllib.parse

HISTORY_DB_PATH = Path.home() / ".sql_builder" / "history.sqlite"
HISTORY_DB_PATH.parent.mkdir(exist_ok=True)

@contextmanager
def get_user_db(db_path: str, read_only: bool = False):
    """DB接続ロジックをここに集約（エラーを修正した完成版）"""
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
        
    db_uri = f"file:{urllib.parse.quote(db_path)}"
    if read_only:
        db_uri += "?mode=ro"
    
    conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_history_db():
    with sqlite3.connect(HISTORY_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id TEXT PRIMARY KEY, sql TEXT NOT NULL, db_path TEXT NOT NULL,
                success INTEGER NOT NULL, row_count INTEGER, error TEXT, executed_at REAL NOT NULL
            )
        """)
    @classmethod
    def export_all_to_dict(cls, db_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        データベース全体のデータをJSON出力可能な辞書形式で取得する
        """
        export_data = {}
        with cls.get_connection(db_path, read_only=True) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            for (table_name,) in tables:
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                # カラム名を取得
                columns = [desc[0] for desc in cursor.description]
                # 全行を辞書のリストに変換
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                export_data[table_name] = rows
                
        return export_data

