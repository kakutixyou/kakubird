import sqlite3
import json
import os

# DBファイルの保存先（backendフォルダの直下）
DB_PATH = "backend/jobs.db"

def init_job_db():
    """テーブルが存在しなければ作成する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruitment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            overall_label TEXT,
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_job_to_db(evaluation_result: dict) -> bool:
    """求人データのJSON(辞書型)を受け取り、SQLiteに保存する"""
    try:
        init_job_db() # 念のため毎回テーブルの存在確認を行う（一瞬で終わります）
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 検索しやすさのために名前と評価ラベルだけ抽出
        company_name = evaluation_result.get("company", {}).get("name", "不明")
        overall_label = evaluation_result.get("ai_analysis", {}).get("overall_label", "unknown")
        
        # 辞書型をJSON文字列に変換
        json_string = json.dumps(evaluation_result, ensure_ascii=False)
        
        # DBに書き込み
        cursor.execute("""
            INSERT INTO recruitment_jobs (company_name, overall_label, raw_json)
            VALUES (?, ?, ?)
        """, (company_name, overall_label, json_string))
        
        conn.commit()
        conn.close()
        
        print(f"💾 【DB保存成功】{company_name} の求人データを jobs.db に記録しました！")
        return True
    except Exception as e:
        print(f"🚨 【DB保存エラー】: {e}")
        return False
# （既存の init_job_db, save_job_to_db の下に追加してください）

def get_all_jobs() -> list:
    """保存されているすべての求人データを取得する"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 新しい順（降順）にデータを取得
        cursor.execute("""
            SELECT id, company_name, overall_label, created_at, raw_json 
            FROM recruitment_jobs 
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            jobs.append({
                "id": row[0],
                "company_name": row[1],
                "overall_label": row[2],
                "created_at": row[3],
                # JSON文字列を辞書型に戻す
                "raw_json": json.loads(row[4]) if row[4] else {}
            })
        return jobs
    except Exception as e:
        print(f"🚨 【DB読み込みエラー】: {e}")
        return []