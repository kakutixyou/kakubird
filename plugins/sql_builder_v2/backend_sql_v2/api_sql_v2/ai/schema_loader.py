# sql_builder_v2/backend/api/ai/schema_loader.py

from typing import Dict, List

def format_schema(tables: Dict[str, List[dict]]) -> str:
    """
    AIに渡すテキスト形式に整形
    """
    lines = ["利用可能なテーブル構造:"]
    
    for table, columns in tables.items():
        cols = ", ".join([f"{c['name']}({c['type']})" for c in columns])
        lines.append(f"- {table}: {cols}")
    
    return "\n".join(lines)
# backend/api/ai/schema_loader.py（続き）

import sqlite3

def load_sqlite_schema(db_path: str) -> Dict[str, List[dict]]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = {}

    # テーブル一覧取得
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    table_names = [row[0] for row in cursor.fetchall()]

    for table in table_names:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()

        tables[table] = [
            {
                "name": col[1],
                "type": col[2]
            }
            for col in columns
        ]

    conn.close()
    return tables
# backend/api/ai/schema_loader.py（続き）

import psycopg2

def load_postgres_schema(conn_str: str) -> Dict[str, List[dict]]:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()

    tables = {}

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public';
    """)

    table_names = [row[0] for row in cursor.fetchall()]

    for table in table_names:
        cursor.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s;
        """, (table,))

        columns = cursor.fetchall()

        tables[table] = [
            {"name": col[0], "type": col[1]}
            for col in columns
        ]

    conn.close()
    return tables
# backend/api/ai/schema_loader.py（最後）

def get_schema_text(db_type: str = "sqlite", db_path: str = "", conn_str: str = "") -> str:
    
    if db_type == "sqlite":
        tables = load_sqlite_schema(db_path)

    elif db_type == "postgres":
        tables = load_postgres_schema(conn_str)

    else:
        return "スキーマ情報を取得できませんでした"

    return format_schema(tables)