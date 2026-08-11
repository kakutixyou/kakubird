from db.history_db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# カラム一覧取得
cursor.execute("PRAGMA table_info(api_keys);")
columns = [col[1] for col in cursor.fetchall()]

# 存在しなければ追加
if "expires_at" not in columns:
    cursor.execute("ALTER TABLE api_keys ADD COLUMN expires_at TEXT;")

if "is_active" not in columns:
    cursor.execute("ALTER TABLE api_keys ADD COLUMN is_active INTEGER DEFAULT 1;")

conn.commit()
conn.close()

print("Migration safe done!")