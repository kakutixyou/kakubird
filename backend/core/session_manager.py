# =========================================================
# session_manager.py
# AIセッション管理システム
# 会話セッション / プロジェクト状態 / 作業状態
# =========================================================

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# =========================================================
# 基本設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_DIR = os.path.join(
    BASE_DIR,
    ".ai_memory",
    "sessions"
)

os.makedirs(SESSION_DIR, exist_ok=True)

ACTIVE_SESSION_FILE = os.path.join(
    SESSION_DIR,
    "active_session.json"
)

# =========================================================
# JSON共通
# =========================================================

def save_json(path: str, data: Any):

    try:

        with open(path, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(f"❌ JSON保存失敗: {path}")
        print(e)

# =========================================================
# JSON読込
# =========================================================

def load_json(path: str, default=None):

    if default is None:
        default = {}

    if not os.path.exists(path):
        return default

    try:

        with open(path, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception as e:

        print(f"❌ JSON読込失敗: {path}")
        print(e)

        return default

# =========================================================
# セッション生成
# =========================================================

def create_session(
    project_name: str = "default_project",
    mode: str = "development"
) -> Dict[str, Any]:

    session_id = str(uuid.uuid4())

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    session_data = {
        "session_id": session_id,
        "project_name": project_name,
        "mode": mode,

        "created_at": now,
        "updated_at": now,

        "message_count": 0,

        "active_file": None,
        "active_component": None,

        "opened_files": [],

        "recent_actions": [],

        "status": "active"
    }

    session_file = os.path.join(
        SESSION_DIR,
        f"{session_id}.json"
    )

    save_json(session_file, session_data)

    set_active_session(session_id)

    print(f"🧠 Session Created: {session_id}")

    return session_data

# =========================================================
# セッション保存
# =========================================================

def save_session(session_data: Dict[str, Any]):

    session_id = session_data["session_id"]

    session_data["updated_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    session_file = os.path.join(
        SESSION_DIR,
        f"{session_id}.json"
    )

    save_json(session_file, session_data)

# =========================================================
# セッション取得
# =========================================================

def load_session(
    session_id: str
) -> Dict[str, Any]:

    session_file = os.path.join(
        SESSION_DIR,
        f"{session_id}.json"
    )

    return load_json(session_file, {})

# =========================================================
# アクティブセッション設定
# =========================================================

def set_active_session(
    session_id: str
):

    data = {
        "session_id": session_id,
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    save_json(
        ACTIVE_SESSION_FILE,
        data
    )

# =========================================================
# アクティブセッション取得
# =========================================================

def get_active_session() -> Dict[str, Any]:

    active = load_json(
        ACTIVE_SESSION_FILE,
        {}
    )

    session_id = active.get("session_id")

    if not session_id:

        return create_session()

    session = load_session(session_id)

    if not session:

        return create_session()

    return session

# =========================================================
# メッセージ数加算
# =========================================================

def increment_message_count():

    session = get_active_session()

    session["message_count"] += 1

    save_session(session)

# =========================================================
# アクティブファイル更新
# =========================================================

def set_active_file(
    file_path: str
):

    session = get_active_session()

    session["active_file"] = file_path

    opened_files = session.get(
        "opened_files",
        []
    )

    if file_path in opened_files:
        opened_files.remove(file_path)

    opened_files.insert(0, file_path)

    opened_files = opened_files[:30]

    session["opened_files"] = opened_files

    save_session(session)

# =========================================================
# アクティブComponent更新
# =========================================================

def set_active_component(
    component_name: str
):

    session = get_active_session()

    session["active_component"] = component_name

    save_session(session)

# =========================================================
# 最近の操作追加
# =========================================================

def add_recent_action(
    action_type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
):

    session = get_active_session()

    actions = session.get(
        "recent_actions",
        []
    )

    actions.insert(0, {
        "type": action_type,
        "description": description,
        "metadata": metadata or {},
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    })

    actions = actions[:50]

    session["recent_actions"] = actions

    save_session(session)

# =========================================================
# 最近操作取得
# =========================================================

def get_recent_actions(
    limit: int = 10
) -> List[Dict[str, Any]]:

    session = get_active_session()

    return session.get(
        "recent_actions",
        []
    )[:limit]

# =========================================================
# 開いているファイル取得
# =========================================================

def get_opened_files() -> List[str]:

    session = get_active_session()

    return session.get(
        "opened_files",
        []
    )

# =========================================================
# セッション一覧
# =========================================================

def get_all_sessions() -> List[Dict[str, Any]]:

    sessions = []

    for filename in os.listdir(SESSION_DIR):

        if not filename.endswith(".json"):
            continue

        if filename == "active_session.json":
            continue

        path = os.path.join(
            SESSION_DIR,
            filename
        )

        data = load_json(path, {})

        if data:
            sessions.append(data)

    sessions.sort(
        key=lambda x: x.get(
            "updated_at",
            ""
        ),
        reverse=True
    )

    return sessions

# =========================================================
# セッション切替
# =========================================================

def switch_session(
    session_id: str
) -> bool:

    session = load_session(session_id)

    if not session:
        return False

    set_active_session(session_id)

    print(f"🔄 Session Switched: {session_id}")

    return True

# =========================================================
# セッション終了
# =========================================================

def close_session(
    session_id: str
):

    session = load_session(session_id)

    if not session:
        return

    session["status"] = "closed"

    save_session(session)

    print(f"🛑 Session Closed: {session_id}")

# =========================================================
# セッション削除
# =========================================================

def delete_session(
    session_id: str
):

    session_file = os.path.join(
        SESSION_DIR,
        f"{session_id}.json"
    )

    if os.path.exists(session_file):

        os.remove(session_file)

        print(f"🗑️ Session Deleted: {session_id}")

# =========================================================
# Session Summary
# =========================================================

def build_session_summary() -> str:

    session = get_active_session()

    summary = f"""
# Current Session

Session ID:
{session.get("session_id")}

Project:
{session.get("project_name")}

Mode:
{session.get("mode")}

Messages:
{session.get("message_count")}

Active File:
{session.get("active_file")}

Active Component:
{session.get("active_component")}

Opened Files:
{len(session.get("opened_files", []))}

Recent Actions:
{len(session.get("recent_actions", []))}
"""

    return summary

# =========================================================
# セッションエクスポート
# =========================================================

def export_session(
    session_id: str,
    output_path: str = None
):

    session = load_session(session_id)

    if not session:
        return

    if output_path is None:

        output_path = f"./session_export_{session_id}.json"

    save_json(output_path, session)

    print(f"📦 Session Exported: {output_path}")

# =========================================================
# Cleanup
# =========================================================

def cleanup_old_sessions(
    keep_latest: int = 10
):

    sessions = get_all_sessions()

    if len(sessions) <= keep_latest:
        return

    old_sessions = sessions[keep_latest:]

    for session in old_sessions:

        session_id = session.get("session_id")

        if session_id:

            delete_session(session_id)

    print(
        f"🧹 Cleaned {len(old_sessions)} old sessions"
    )

# =========================================================
# 自動復元
# =========================================================

def restore_last_session() -> Dict[str, Any]:

    sessions = get_all_sessions()

    if not sessions:

        return create_session()

    latest = sessions[0]

    switch_session(
        latest["session_id"]
    )

    print(
        f"♻️ Restored Session: {latest['session_id']}"
    )

    return latest

# =========================================================
# Debug
# =========================================================

def debug_print_session():

    session = get_active_session()

    print("\n==============================")
    print("🧠 Active Session")
    print("==============================")

    print(
        json.dumps(
            session,
            ensure_ascii=False,
            indent=2
        )
    )

# =========================================================
# テスト
# =========================================================

if __name__ == "__main__":

    print("🧠 Session Manager Test")

    session = create_session(
        project_name="To（と）",
        mode="development"
    )

    increment_message_count()

    set_active_file(
        "frontend/src/hooks/useAiChat.js"
    )

    set_active_component(
        "AiChatPanel"
    )

    add_recent_action(
        "open_file",
        "useAiChat.js を開いた"
    )

    add_recent_action(
        "scan_project",
        "ZIP解析を実行"
    )

    print(
        build_session_summary()
    )

    debug_print_session()

    export_session(
        session["session_id"]
    )