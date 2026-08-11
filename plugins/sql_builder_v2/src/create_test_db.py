import sqlite3
import os

# データベースファイルの名前と場所
db_path = "sample_history.db"

# もし既にファイルがあれば削除（何度でもやり直せるように）
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# テーブルの作成
cursor.execute("""
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    faction TEXT NOT NULL,
    role TEXT NOT NULL,
    power INTEGER
)
""")

# テストデータの挿入
sample_data = [
    ("劉秀", "後漢", "皇帝", 95),
    ("王莽", "新", "皇帝", 80),
    ("樊崇", "赤眉軍", "指導者", 85),
    ("馮異", "後漢", "将軍", 90),
    ("劉玄", "緑林軍", "皇帝", 70)
]

cursor.executemany(
    "INSERT INTO characters (name, faction, role, power) VALUES (?, ?, ?, ?)",
    sample_data
)

conn.commit()
conn.close()

print(f"テスト用データベース '{db_path}' を作成しました！アプリから開いてみてください。")