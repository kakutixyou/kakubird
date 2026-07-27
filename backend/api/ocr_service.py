# backend/api/ocr_service.py
"""
OCR + AI自動分類サービス
- 求人スクリーンショット  → jobs/     テーブル・JSON
- フォルダ構成スクリーンショット → folders/ テーブル・JSON
- approval は即 applied（承認ステップなし）
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image  # type: ignore

# EasyOCR は起動時に1回だけロード
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        import easyocr  # type: ignore
        print("🔤 EasyOCR 初期化中（初回のみ時間がかかります）...")
        _reader = easyocr.Reader(["ja", "en"])
    return _reader


# =========================================================
# OCR
# =========================================================

def extract_text(image_path: Path) -> str:
    """画像からテキストを抽出する"""
    reader = get_reader()
    results = reader.readtext(str(image_path), detail=0)
    return "\n".join(results)


# =========================================================
# AI による自動分類 + 構造化
# =========================================================

def classify_and_parse(raw_text: str) -> dict:
    """
    OCRテキストを Claude に渡して:
      1. 画像タイプを判定  ("job" | "folder_structure" | "other")
      2. タイプに応じた構造化データを返す
    """
    import httpx

    prompt = f"""以下のテキストはスクリーンショットをOCRで読んだものです。

まず内容を判定し、JSONのみ返してください（前置き・コードブロック記号不要）。

【判定ルール】
- 求人・採用・会社名・職種・給与・応募などが含まれる → type: "job"
- フォルダ名・ファイル名・ディレクトリ構造・拡張子が多い → type: "folder_structure"
- それ以外 → type: "other"

【typeが "job" の場合の出力形式】
{{
  "type": "job",
  "company_name": "...",
  "job_title": "...",
  "contact": "...",
  "salary": "...",
  "location": "...",
  "memo": "AIが重要と判断したその他情報を自由記述",
  "raw_text": "（入力テキストをそのまま）"
}}

【typeが "folder_structure" の場合の出力形式】
{{
  "type": "folder_structure",
  "root_name": "最上位フォルダ名 or プロジェクト名",
  "summary": "このフォルダ構成が何のプロジェクトか一言で説明",
  "tree": [
    {{"path": "src/", "kind": "dir"}},
    {{"path": "src/index.tsx", "kind": "file"}}
  ],
  "raw_text": "（入力テキストをそのまま）"
}}

【typeが "other" の場合】
{{
  "type": "other",
  "raw_text": "（入力テキストをそのまま）"
}}

OCRテキスト:
{raw_text}"""

    try:
        res = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )
        text = res.json()["content"][0]["text"].strip()
        # コードブロックが混入した場合の保険
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Claude解析失敗、fallback: {e}")
        return {"type": "other", "raw_text": raw_text}


# =========================================================
# SQLite
# =========================================================

DB_PATH = Path(".ai_memory/memory.db")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # 求人テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id           TEXT PRIMARY KEY,
                company_name TEXT,
                job_title    TEXT,
                contact      TEXT,
                salary       TEXT,
                location     TEXT,
                memo         TEXT,
                raw_text     TEXT,
                image_path   TEXT,
                json_path    TEXT,
                approval_id  TEXT,
                created_at   TEXT
            )
        """)
        # フォルダ構成テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS folder_structures (
                id          TEXT PRIMARY KEY,
                root_name   TEXT,
                summary     TEXT,
                tree_json   TEXT,
                raw_text    TEXT,
                image_path  TEXT,
                json_path   TEXT,
                approval_id TEXT,
                created_at  TEXT
            )
        """)
        conn.commit()


def insert_job(job: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO jobs
            (id,company_name,job_title,contact,salary,location,memo,
             raw_text,image_path,json_path,approval_id,created_at)
            VALUES
            (:id,:company_name,:job_title,:contact,:salary,:location,:memo,
             :raw_text,:image_path,:json_path,:approval_id,:created_at)
        """, job)
        conn.commit()


def insert_folder(folder: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO folder_structures
            (id,root_name,summary,tree_json,raw_text,
             image_path,json_path,approval_id,created_at)
            VALUES
            (:id,:root_name,:summary,:tree_json,:raw_text,
             :image_path,:json_path,:approval_id,:created_at)
        """, folder)
        conn.commit()


def delete_record(table: str, record_id: str):
    allowed = {"jobs", "folder_structures"}
    if table not in allowed:
        raise ValueError(f"不正なテーブル名: {table}")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
        conn.commit()


def list_jobs() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def list_folders() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM folder_structures ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # tree_json を Python オブジェクトに戻す
        try:
            d["tree"] = json.loads(d.get("tree_json") or "[]")
        except Exception:
            d["tree"] = []
        result.append(d)
    return result