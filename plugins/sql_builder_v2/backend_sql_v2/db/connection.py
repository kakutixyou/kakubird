import sqlite3
import urllib.parse
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def get_user_db(db_path: str, read_only: bool = False):
    """ユーザーのSQLiteファイルへの安全な接続"""
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    if path.suffix not in (".sqlite", ".db", ".sqlite3"):
        raise ValueError(f"Unsupported file type: {path.suffix}")

    # URI形式に変換（オーバーライドされていた最新のロジックを採用）
    db_uri = f"file:{urllib.parse.quote(db_path)}"
    if read_only:
        db_uri += "?mode=ro"

    conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()