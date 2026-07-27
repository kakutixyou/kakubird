
# To/backend/api/services/db_service.py

import json
import os
import traceback
from typing import Dict, Any, List, Optional


# =========================================================
# Constants
# =========================================================

DB_SETS_DIR = os.path.join(
    "src",
    "data",
    "db_sets"
)

IGNORE_FILES = [
    "index.js",
    "sqlExamples.js",
]


# =========================================================
# Utility Functions
# =========================================================

def ensure_db_directory() -> None:
    """
    db_sets ディレクトリ存在確認
    """

    os.makedirs(
        DB_SETS_DIR,
        exist_ok=True
    )


def list_db_set_files() -> List[str]:
    """
    db_sets 配下のJSON一覧取得
    """

    ensure_db_directory()

    return [
        filename
        for filename in os.listdir(DB_SETS_DIR)
        if (
            filename.endswith(".json")
            and filename not in IGNORE_FILES
        )
    ]


def extract_topic_key(
    filename: str
) -> str:
    """
    xxx.json -> xxx
    """

    return filename.replace(".json", "")


# =========================================================
# Database Knowledge Search
# =========================================================

def search_matching_topics(
    user_message: str
) -> List[str]:
    """
    メッセージから一致するDBトピック検出

    Example:
        user_message:
            "users テーブルを見せて"

        returns:
            ["users"]
    """

    matched_topics = []

    files = list_db_set_files()

    msg_lower = user_message.lower()

    for filename in files:

        topic_key = extract_topic_key(
            filename
        )

        if topic_key.lower() in msg_lower:

            matched_topics.append(
                topic_key
            )

    return matched_topics


# =========================================================
# File Loading
# =========================================================

def load_raw_json_text(
    topic_key: str
) -> Optional[str]:
    """
    JSONファイルを生テキストで返す
    """

    file_path = os.path.join(
        DB_SETS_DIR,
        f"{topic_key}.json"
    )

    if not os.path.exists(file_path):
        return None

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()

    except Exception:

        traceback.print_exc()

        return None


def load_json_data(
    topic_key: str
) -> Optional[Dict[str, Any]]:
    """
    JSONパース済みデータ取得
    """

    file_path = os.path.join(
        DB_SETS_DIR,
        f"{topic_key}.json"
    )

    if not os.path.exists(file_path):
        return None

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        traceback.print_exc()

        return None


# =========================================================
# UI Response Builder
# =========================================================

def build_sql_example_modal_response(
    topic_key: str,
    raw_text: str
) -> Dict[str, Any]:
    """
    SqlExampleModal UI用レスポンス
    """

    return {
        "message":
            f"{topic_key} に関するサンプル構造をロードしました。",

        "blocks": [
            {
                "type": "SqlExampleModal",
                "props": {
                    "source": f"{topic_key}.js",
                    "raw_data": raw_text,
                }
            }
        ]
    }


def build_database_creation_guide() -> str:
    """
    DB作成ガイド
    """

    return (
        "データベースの新規作成リクエストを検出しました。\n\n"
        "System API の `/api/system/create-db` "
        "を利用してください。"
    )


# =========================================================
# Main Routing Logic
# =========================================================

async def handle_database_routing(
    user_message: str
) -> Optional[Dict[str, Any]]:
    """
    orchestrator から呼ばれるDB routing

    Returns:
        None:
            DB routing 不一致

        Dict:
            response data
    """

    try:

        matched_topics = search_matching_topics(
            user_message
        )

        # -------------------------------------------------
        # DB閲覧系
        # -------------------------------------------------
        if (
            any(
                keyword in user_message
                for keyword in [
                    "見せて",
                    "教えて",
                    "開いて",
                    "一覧",
                ]
            )
            and matched_topics
        ):

            primary_topic = matched_topics[0]

            raw_text = load_raw_json_text(
                primary_topic
            )

            if not raw_text:

                return {
                    "response_type": "text",
                    "content":
                        "DBサンプルの読み込みに失敗しました。"
                }

            return {
                "response_type": "ui_code",

                "content":
                    build_sql_example_modal_response(
                        primary_topic,
                        raw_text
                    )
            }

        # -------------------------------------------------
        # DB新規作成
        # -------------------------------------------------
        if (
            any(
                keyword in user_message
                for keyword in [
                    "作って",
                    "作成",
                    "新規",
                ]
            )
            and "データベース" in user_message
        ):

            return {
                "response_type": "text",

                "content":
                    build_database_creation_guide()
            }

        return None

    except Exception:

        traceback.print_exc()

        return {
            "response_type": "text",
            "content":
                "DBサービス内部エラーが発生しました。"
        }


# =========================================================
# SQLite Discovery
# =========================================================

def discover_sqlite_databases(
    db_dir: str = "./"
) -> List[str]:
    """
    実在SQLite DB一覧取得
    """

    try:

        if not os.path.exists(db_dir):
            return []

        return [
            filename.replace(".db", "")
            for filename in os.listdir(db_dir)
            if filename.endswith(".db")
        ]

    except Exception:

        traceback.print_exc()

        return []


# =========================================================
# DB Metadata
# =========================================================

def build_database_context_text(
    db_names: List[str]
) -> str:
    """
    LLM context用DB一覧テキスト
    """

    if not db_names:

        return ""

    return (
        "\n【現在システム内に実在するSQLiteデータベース】\n"
        f"{', '.join(db_names)}\n"
    )


# =========================================================
# Future Expansion Notes
# =========================================================

"""
将来的な拡張ポイント

1. SQLite Schema Parser
--------------------------------------------------------
PRAGMA table_info()

2. Real SQL Query Execution
--------------------------------------------------------
SELECT * FROM ...

3. Query Safety Layer
--------------------------------------------------------
危険SQL防止

4. DB Tool Calling
--------------------------------------------------------
LLM tool integration

5. Auto ER Diagram
--------------------------------------------------------
Mermaid生成

6. Multi Database Support
--------------------------------------------------------
PostgreSQL
MySQL
MongoDB

7. DB Embedding Search
--------------------------------------------------------
自然言語検索

8. Migration System
--------------------------------------------------------
schema versioning

9. Visual Table Editor
--------------------------------------------------------
GUI管理

10. AI SQL Generator
--------------------------------------------------------
NL -> SQL
"""

