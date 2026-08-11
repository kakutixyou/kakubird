# =========================================================
# memory_manager.py
# AI記憶システム管理
# 長期記憶 / 作業記憶 / 会話履歴 / プロジェクト記憶
# =========================================================

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# =========================================================
# 基本パス設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")

CHAT_HISTORY_DIR = os.path.join(MEMORY_DIR, "chat_history")
PROJECT_MEMORY_DIR = os.path.join(MEMORY_DIR, "projects")
LONG_TERM_MEMORY_DIR = os.path.join(MEMORY_DIR, "long_term")
TASK_MEMORY_DIR = os.path.join(MEMORY_DIR, "tasks")

os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
os.makedirs(PROJECT_MEMORY_DIR, exist_ok=True)
os.makedirs(LONG_TERM_MEMORY_DIR, exist_ok=True)
os.makedirs(TASK_MEMORY_DIR, exist_ok=True)

# =========================================================
# ファイル
# =========================================================

ACTIVE_SESSION_FILE = os.path.join(
    MEMORY_DIR,
    "active_session.json"
)

# =========================================================
# JSON保存共通
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
# JSON読込共通
# =========================================================
def load_json(path: str, default: Any = None) -> Any:

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
# セッション管理
# =========================================================

def create_new_session(
    project_name: str = "default_project"
) -> Dict[str, Any]:

    session_data = {
        "session_id": str(uuid.uuid4()),
        "project_name": project_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message_count": 0
    }

    save_json(
        ACTIVE_SESSION_FILE,
        session_data
    )

    return session_data

# =========================================================
# 現在セッション取得
# =========================================================

def get_active_session() -> Dict[str, Any]:

    if not os.path.exists(ACTIVE_SESSION_FILE):

        return create_new_session()

    return load_json(ACTIVE_SESSION_FILE, {})

# =========================================================
# セッション更新
# =========================================================

def update_session_activity():

    session = get_active_session()

    session["last_active"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    session["message_count"] = (
        session.get("message_count", 0) + 1
    )

    save_json(
        ACTIVE_SESSION_FILE,
        session
    )

# =========================================================
# チャット履歴保存
# =========================================================

def save_chat_message(
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):

    session = get_active_session()

    session_id = session["session_id"]

    history_file = os.path.join(
        CHAT_HISTORY_DIR,
        f"{session_id}.json"
    )

    history = load_json(history_file, [])

    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "metadata": metadata or {}
    }

    history.append(message)

    save_json(history_file, history)

    update_session_activity()

    return message

# =========================================================
# チャット履歴取得
# =========================================================

def get_chat_history(
    limit: int = 20
) -> List[Dict[str, Any]]:

    session = get_active_session()

    session_id = session["session_id"]

    history_file = os.path.join(
        CHAT_HISTORY_DIR,
        f"{session_id}.json"
    )

    history = load_json(history_file, [])

    return history[-limit:]

# =========================================================
# プロジェクト記憶保存
# =========================================================

def save_project_memory(
    project_name: str,
    key: str,
    value: Any
):

    project_file = os.path.join(
        PROJECT_MEMORY_DIR,
        f"{project_name}.json"
    )

    memory = load_json(project_file, {})

    memory[key] = value

    memory["updated_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_json(project_file, memory)

# =========================================================
# プロジェクト記憶取得
# =========================================================

def get_project_memory(
    project_name: str
) -> Dict[str, Any]:

    project_file = os.path.join(
        PROJECT_MEMORY_DIR,
        f"{project_name}.json"
    )

    return load_json(project_file, {})

# =========================================================
# 長期記憶保存
# =========================================================

def save_long_term_memory(
    category: str,
    text: str,
    tags: Optional[List[str]] = None
):

    memory_id = str(uuid.uuid4())

    memory_data = {
        "id": memory_id,
        "category": category,
        "text": text,
        "tags": tags or [],
        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    output_file = os.path.join(
        LONG_TERM_MEMORY_DIR,
        f"{memory_id}.json"
    )

    save_json(output_file, memory_data)

    return memory_data

# =========================================================
# 長期記憶検索
# =========================================================

def search_long_term_memory(
    keyword: str
) -> List[Dict[str, Any]]:

    results = []

    for filename in os.listdir(LONG_TERM_MEMORY_DIR):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(
            LONG_TERM_MEMORY_DIR,
            filename
        )

        data = load_json(path, {})

        text = data.get("text", "")

        if keyword.lower() in text.lower():

            results.append(data)

    return results

# =========================================================
# タスク保存
# =========================================================

def save_task(
    task_name: str,
    details: str,
    status: str = "pending"
):

    task_id = str(uuid.uuid4())

    task_data = {
        "id": task_id,
        "task_name": task_name,
        "details": details,
        "status": status,
        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    save_json(task_file, task_data)

    return task_data

# =========================================================
# タスク更新
# =========================================================

def update_task_status(
    task_id: str,
    status: str
):

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    task_data = load_json(task_file, {})

    if not task_data:
        return False

    task_data["status"] = status

    task_data["updated_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_json(task_file, task_data)

    return True

# =========================================================
# タスク一覧取得
# =========================================================

def get_all_tasks() -> List[Dict[str, Any]]:

    tasks = []

    for filename in os.listdir(TASK_MEMORY_DIR):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(
            TASK_MEMORY_DIR,
            filename
        )

        data = load_json(path, {})

        if data:
            tasks.append(data)

    return tasks

# =========================================================
# プロジェクト分析メモ保存
# =========================================================

def save_project_analysis(
    project_name: str,
    analysis: Dict[str, Any]
):

    analysis_dir = os.path.join(
        PROJECT_MEMORY_DIR,
        project_name
    )

    os.makedirs(analysis_dir, exist_ok=True)

    output_file = os.path.join(
        analysis_dir,
        "analysis.json"
    )

    analysis["updated_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_json(output_file, analysis)

# =========================================================
# プロジェクト分析取得
# =========================================================

def load_project_analysis(
    project_name: str
) -> Dict[str, Any]:

    path = os.path.join(
        PROJECT_MEMORY_DIR,
        project_name,
        "analysis.json"
    )

    return load_json(path, {})

# =========================================================
# 最近触ったファイル記憶
# =========================================================

def remember_recent_file(
    project_name: str,
    file_path: str
):

    project_memory = get_project_memory(project_name)

    recent_files = project_memory.get(
        "recent_files",
        []
    )

    if file_path in recent_files:
        recent_files.remove(file_path)

    recent_files.insert(0, file_path)

    recent_files = recent_files[:20]

    save_project_memory(
        project_name,
        "recent_files",
        recent_files
    )
# =========================================================
# 汎用メモリ管理 (ai_server.py 互換用)
# =========================================================

GENERAL_MEMORY_FILE = os.path.join(MEMORY_DIR, "general_memory.json")

def load_memory() -> Dict[str, Any]:
    """
    ai_server.py の /api/search 等で呼ばれる汎用メモリ読込
    """
    return load_json(GENERAL_MEMORY_FILE, {})

def save_memory(key: str, value: Any):
    """
    ai_server.py の ZIPアップロード時等に呼ばれる汎用メモリ保存
    """
    memory = load_memory()
    memory[key] = value
    save_json(GENERAL_MEMORY_FILE, memory)
# =========================================================
# 最近触ったファイル取得
# =========================================================

def get_recent_files(
    project_name: str
) -> List[str]:

    memory = get_project_memory(project_name)

    return memory.get("recent_files", [])

# =========================================================
# Memory統計
# =========================================================

def get_memory_statistics() -> Dict[str, Any]:

    chat_count = len(os.listdir(CHAT_HISTORY_DIR))
    long_term_count = len(os.listdir(LONG_TERM_MEMORY_DIR))
    task_count = len(os.listdir(TASK_MEMORY_DIR))

    project_count = len([
        f for f in os.listdir(PROJECT_MEMORY_DIR)
        if f.endswith(".json")
    ])

    return {
        "chat_sessions": chat_count,
        "long_term_memories": long_term_count,
        "tasks": task_count,
        "projects": project_count
    }

# =========================================================
# メモリ全体要約
# =========================================================

def build_memory_summary() -> str:

    stats = get_memory_statistics()

    session = get_active_session()

    summary = f"""
🧠 AI Memory Summary

Current Project:
{session.get("project_name")}

Session ID:
{session.get("session_id")}

Message Count:
{session.get("message_count")}

Chat Sessions:
{stats["chat_sessions"]}

Long Term Memories:
{stats["long_term_memories"]}

Tasks:
{stats["tasks"]}

Projects:
{stats["projects"]}
"""

    return summary

# =========================================================
# 全記憶エクスポート
# =========================================================

def export_all_memory(
    output_path: str = "./memory_export.json"
):

    export_data = {
        "session": get_active_session(),
        "history": get_chat_history(100),
        "tasks": get_all_tasks(),
        "statistics": get_memory_statistics()
    }

    save_json(output_path, export_data)

    print(f"📦 Memory Exported: {output_path}")

# =========================================================
# テスト
# =========================================================

if __name__ == "__main__":

    print("🧠 Memory Manager Test")

    session = create_new_session(
        "To(と)"
    )

    print(session)

    save_chat_message(
        "user",
        "stream処理どこ？"
    )

    save_chat_message(
        "assistant",
        "useAiChat.jsです"
    )

    save_long_term_memory(
        category="architecture",
        text="useAiChat.js がメインルーター",
        tags=["frontend", "react"]
    )

    task = save_task(
        "RAG改善",
        "Chunk検索精度を改善する"
    )

    print(task)

    print("\n")
    print(build_memory_summary())

    export_all_memory()
    
    