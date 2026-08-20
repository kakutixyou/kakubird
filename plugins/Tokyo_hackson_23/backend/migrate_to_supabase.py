#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/migrate_to_supabase.py
──────────────────────────────
ローカルの SQLite (data/opendata_queue.db) に溜まったデータを、
環境変数 DATABASE_URL で指定された Supabase (PostgreSQL) に一括同期するスクリプト。
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "opendata_queue.db"

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ エラー: 環境変数 DATABASE_URL が設定されていません。")
        return

    if not DB_PATH.exists():
        print(f"❌ エラー: ローカルのSQLiteが見つかりません ({DB_PATH})")
        return

    print("🔌 ローカルのSQLiteに接続中...")
    sqlite_conn = sqlite3.connect(str(DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row

    print("🔌 Supabase (PostgreSQL) に接続中...")
    pg_conn = psycopg2.connect(db_url)
    pg_conn.autocommit = False

    tables = ["opendata_queue", "ward_scores", "normalized_facilities"]

    try:
        with pg_conn.cursor() as pg_cur:
            for table in tables:
                print(f"\n📦 テーブル '{table}' の同期を開始...")
                
                try:
                    sqlite_cur = sqlite_conn.execute(f"SELECT * FROM {table}")
                    rows = sqlite_cur.fetchall()
                except sqlite3.OperationalError:
                    print(f"⚠️ ローカルのSQLiteにテーブル '{table}' が存在しません。スキップします。")
                    continue

                if not rows:
                    print(f"⚠️ ローカルの '{table}' は空です。スキップします。")
                    continue

                columns = [description[0] for description in sqlite_cur.description]
                data_tuples = [tuple(row) for row in rows]
                columns_str = ", ".join([f'"{col}"' for col in columns])
                
                # 修正: EXCLUDED."col" 形式に変更
                update_set = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['theme', 'id', 'city_name']])
                
                if table == "ward_scores":
                    conflict_keys = "theme, city_name"
                else:
                    conflict_keys = "theme, id"

                if update_set:
                    query = f"""
                        INSERT INTO {table} ({columns_str}) 
                        VALUES %s 
                        ON CONFLICT ({conflict_keys}) 
                        DO UPDATE SET {update_set}
                    """
                else:
                    query = f"""
                        INSERT INTO {table} ({columns_str}) 
                        VALUES %s 
                        ON CONFLICT ({conflict_keys}) 
                        DO NOTHING
                    """

                print(f"   ➔ {len(data_tuples)} 件のレコードを転送中...")
                execute_values(pg_cur, query, data_tuples)

            pg_conn.commit()
            print("\n🎉 すべてのデータのSupabaseへの同期が完了しました！")

    except Exception as e:
        pg_conn.rollback()
        print(f"\n❌ 同期中にエラーが発生しました（ロールバックしました）: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate()