# ============================================================
# memory_manager.py
# AI記憶システム管理
#
# 機能:
# - セッション管理
# - 会話履歴
# - 長期記憶
# - 好きなこと / 興味
# - タスク
# - 予定
# - 大きな課題
# - プロジェクト記憶
# - 最近触ったファイル
# - Memory統計
# - Memory Overview
# - 全記憶エクスポート
# - 全記憶削除
# - 壊れたJSONの自動復旧
# ============================================================

import os
import json
import uuid
import shutil

from datetime import datetime
from typing import Dict, Any, List, Optional


# ============================================================
# 基本パス
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MEMORY_DIR = os.path.join(
    BASE_DIR,
    ".ai_memory"
)

CHAT_HISTORY_DIR = os.path.join(
    MEMORY_DIR,
    "chat_history"
)

PROJECT_MEMORY_DIR = os.path.join(
    MEMORY_DIR,
    "projects"
)

LONG_TERM_MEMORY_DIR = os.path.join(
    MEMORY_DIR,
    "long_term"
)

TASK_MEMORY_DIR = os.path.join(
    MEMORY_DIR,
    "tasks"
)


# ============================================================
# Memoryディレクトリ生成
# ============================================================

def ensure_memory_directories():
    """
    AI Memoryで利用するディレクトリを生成する。
    """

    directories = [
        MEMORY_DIR,
        CHAT_HISTORY_DIR,
        PROJECT_MEMORY_DIR,
        LONG_TERM_MEMORY_DIR,
        TASK_MEMORY_DIR,
    ]

    for directory in directories:
        os.makedirs(
            directory,
            exist_ok=True
        )


ensure_memory_directories()


# ============================================================
# Memoryファイル
# ============================================================

ACTIVE_SESSION_FILE = os.path.join(
    MEMORY_DIR,
    "active_session.json"
)

GENERAL_MEMORY_FILE = os.path.join(
    MEMORY_DIR,
    "general_memory.json"
)


# ============================================================
# 共通
# ============================================================

def now_string() -> str:
    """
    現在時刻を統一形式で返す。
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# 安全なJSON保存
# ============================================================

def save_json(
    path: str,
    data: Any
) -> bool:
    """
    JSONを安全に保存する。

    直接本体ファイルに書き込まず、
    一度 .tmp に保存してから置換する。

    これにより書込み途中でPythonが終了した場合でも、
    JSON破損の可能性を減らす。
    """

    try:
        directory = os.path.dirname(path)

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        temp_path = f"{path}.tmp"

        with open(
            temp_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_path,
            path
        )

        return True

    except Exception as error:

        print(
            f"❌ JSON保存失敗: {path}"
        )

        print(error)

        return False


# ============================================================
# 壊れたJSONバックアップ
# ============================================================

def backup_broken_json(
    path: str
):
    """
    壊れているJSONを削除する前に
    .broken_日時 という名前で退避する。
    """

    if not os.path.exists(path):
        return

    try:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_path = (
            f"{path}.broken_{timestamp}"
        )

        shutil.copy2(
            path,
            backup_path
        )

        print(
            f"📦 壊れたJSONを退避しました: {backup_path}"
        )

    except Exception as error:

        print(
            f"⚠ JSONバックアップ失敗: {path}"
        )

        print(error)


# ============================================================
# 安全なJSON読込
# ============================================================

def load_json(
    path: str,
    default: Any = None,
    backup_if_broken: bool = True
) -> Any:
    """
    JSON読込。

    JSONが存在しない、または壊れている場合は
    default を返す。
    """

    if default is None:
        default = {}

    if not os.path.exists(path):
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError as error:

        print(
            f"❌ JSON形式エラー: {path}"
        )

        print(error)

        if backup_if_broken:
            backup_broken_json(path)

        return default

    except Exception as error:

        print(
            f"❌ JSON読込失敗: {path}"
        )

        print(error)

        return default


# ============================================================
# セッション作成
# ============================================================

def create_new_session(
    project_name: str = "default_project"
) -> Dict[str, Any]:
    """
    新しいAIセッションを生成する。
    """

    session_data = {
        "session_id": str(uuid.uuid4()),
        "project_name": project_name,
        "created_at": now_string(),
        "last_active": now_string(),
        "message_count": 0,
    }

    save_json(
        ACTIVE_SESSION_FILE,
        session_data
    )

    print(
        "🧠 新しいAI Memory Sessionを生成:",
        session_data["session_id"]
    )

    return session_data


# ============================================================
# 現在セッション取得
# ============================================================

def get_active_session() -> Dict[str, Any]:
    """
    現在のセッションを取得。

    active_session.json が壊れていた場合や、
    session_id が存在しない場合は、
    新しいセッションを自動生成する。
    """

    if not os.path.exists(
        ACTIVE_SESSION_FILE
    ):

        return create_new_session()

    session = load_json(
        ACTIVE_SESSION_FILE,
        {}
    )

    # ----------------------------------------
    # JSON破損 / 空データ
    # ----------------------------------------

    if not isinstance(
        session,
        dict
    ):

        print(
            "⚠ active_session.json がdictではありません。"
        )

        return create_new_session()

    # ----------------------------------------
    # session_id が無い
    # ----------------------------------------

    if not session.get(
        "session_id"
    ):

        print(
            "⚠ session_id が存在しません。"
        )

        return create_new_session(
            project_name=session.get(
                "project_name",
                "default_project"
            )
        )

    # ----------------------------------------
    # 不足項目補完
    # ----------------------------------------

    changed = False

    if "project_name" not in session:
        session["project_name"] = (
            "default_project"
        )

        changed = True

    if "created_at" not in session:
        session["created_at"] = (
            now_string()
        )

        changed = True

    if "last_active" not in session:
        session["last_active"] = (
            now_string()
        )

        changed = True

    if "message_count" not in session:
        session["message_count"] = 0

        changed = True

    if changed:
        save_json(
            ACTIVE_SESSION_FILE,
            session
        )

    return session


# ============================================================
# セッション更新
# ============================================================

def update_session_activity():
    """
    セッションの最終活動時刻と
    メッセージ数を更新する。
    """

    session = get_active_session()

    session["last_active"] = (
        now_string()
    )

    session["message_count"] = (
        session.get(
            "message_count",
            0
        ) + 1
    )

    save_json(
        ACTIVE_SESSION_FILE,
        session
    )


# ============================================================
# プロジェクト変更
# ============================================================

def set_active_project(
    project_name: str
) -> Dict[str, Any]:
    """
    現在のプロジェクト名を変更する。
    """

    session = get_active_session()

    session["project_name"] = (
        project_name
    )

    session["last_active"] = (
        now_string()
    )

    save_json(
        ACTIVE_SESSION_FILE,
        session
    )

    return session


# ============================================================
# チャット履歴保存
# ============================================================

def save_chat_message(
    role: str,
    content: str,
    metadata: Optional[
        Dict[str, Any]
    ] = None
) -> Dict[str, Any]:
    """
    現在セッションに会話を保存する。
    """

    session = get_active_session()

    session_id = session.get(
        "session_id"
    )

    # 念のため二重防御
    if not session_id:

        session = (
            create_new_session()
        )

        session_id = session[
            "session_id"
        ]

    history_file = os.path.join(
        CHAT_HISTORY_DIR,
        f"{session_id}.json"
    )

    history = load_json(
        history_file,
        []
    )

    if not isinstance(
        history,
        list
    ):
        history = []

    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": now_string(),
        "metadata": metadata or {},
    }

    history.append(
        message
    )

    save_json(
        history_file,
        history
    )

    update_session_activity()

    return message


# ============================================================
# 現在セッション会話取得
# ============================================================

def get_chat_history(
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    現在セッションの会話履歴を取得。
    """

    session = get_active_session()

    session_id = session.get(
        "session_id"
    )

    if not session_id:
        return []

    history_file = os.path.join(
        CHAT_HISTORY_DIR,
        f"{session_id}.json"
    )

    history = load_json(
        history_file,
        []
    )

    if not isinstance(
        history,
        list
    ):
        return []

    if limit <= 0:
        return history

    return history[-limit:]


# ============================================================
# 全セッション会話取得
# ============================================================

def get_all_chat_history(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    全セッションの会話履歴をまとめて取得する。
    """

    messages = []

    if not os.path.exists(
        CHAT_HISTORY_DIR
    ):
        return []

    for filename in os.listdir(
        CHAT_HISTORY_DIR
    ):

        if not filename.endswith(
            ".json"
        ):
            continue

        path = os.path.join(
            CHAT_HISTORY_DIR,
            filename
        )

        history = load_json(
            path,
            []
        )

        if not isinstance(
            history,
            list
        ):
            continue

        session_id = (
            filename[:-5]
        )

        for message in history:

            if not isinstance(
                message,
                dict
            ):
                continue

            item = dict(message)

            item.setdefault(
                "session_id",
                session_id
            )

            messages.append(
                item
            )

    messages.sort(
        key=lambda item:
        item.get(
            "timestamp",
            ""
        )
    )

    if limit and limit > 0:
        return messages[-limit:]

    return messages


# ============================================================
# 会話履歴のみ削除
# ============================================================

def clear_chat_history() -> bool:
    """
    全チャット履歴を削除する。
    セッション自体は残す。
    """

    try:

        if os.path.exists(
            CHAT_HISTORY_DIR
        ):

            for filename in os.listdir(
                CHAT_HISTORY_DIR
            ):

                path = os.path.join(
                    CHAT_HISTORY_DIR,
                    filename
                )

                if os.path.isfile(path):
                    os.remove(path)

        session = get_active_session()

        session[
            "message_count"
        ] = 0

        session[
            "last_active"
        ] = now_string()

        save_json(
            ACTIVE_SESSION_FILE,
            session
        )

        return True

    except Exception as error:

        print(
            "❌ 会話履歴削除失敗"
        )

        print(error)

        return False


# ============================================================
# プロジェクト記憶保存
# ============================================================

def save_project_memory(
    project_name: str,
    key: str,
    value: Any
):
    """
    プロジェクト単位のMemoryを保存。
    """

    safe_name = (
        project_name
        .replace("/", "_")
        .replace("\\", "_")
    )

    project_file = os.path.join(
        PROJECT_MEMORY_DIR,
        f"{safe_name}.json"
    )

    memory = load_json(
        project_file,
        {}
    )

    if not isinstance(
        memory,
        dict
    ):
        memory = {}

    memory[key] = value

    memory[
        "project_name"
    ] = project_name

    memory[
        "updated_at"
    ] = now_string()

    save_json(
        project_file,
        memory
    )

    return memory


# ============================================================
# プロジェクト記憶取得
# ============================================================

def get_project_memory(
    project_name: str
) -> Dict[str, Any]:
    """
    プロジェクトMemory取得。
    """

    safe_name = (
        project_name
        .replace("/", "_")
        .replace("\\", "_")
    )

    project_file = os.path.join(
        PROJECT_MEMORY_DIR,
        f"{safe_name}.json"
    )

    memory = load_json(
        project_file,
        {}
    )

    if not isinstance(
        memory,
        dict
    ):
        return {}

    return memory


# ============================================================
# プロジェクト一覧
# ============================================================

def get_all_project_memories() -> List[
    Dict[str, Any]
]:
    """
    全プロジェクト記憶を取得。
    """

    projects = []

    if not os.path.exists(
        PROJECT_MEMORY_DIR
    ):
        return projects

    for filename in os.listdir(
        PROJECT_MEMORY_DIR
    ):

        if not filename.endswith(
            ".json"
        ):
            continue

        path = os.path.join(
            PROJECT_MEMORY_DIR,
            filename
        )

        data = load_json(
            path,
            {}
        )

        if not isinstance(
            data,
            dict
        ):
            continue

        if data:

            data.setdefault(
                "project_name",
                filename[:-5]
            )

            projects.append(
                data
            )

    projects.sort(
        key=lambda item:
        item.get(
            "updated_at",
            ""
        ),
        reverse=True
    )

    return projects


# ============================================================
# 長期記憶保存
# ============================================================

def save_long_term_memory(
    category: str,
    text: str,
    tags: Optional[
        List[str]
    ] = None,
    title: Optional[str] = None,
    metadata: Optional[
        Dict[str, Any]
    ] = None
) -> Dict[str, Any]:
    """
    AIの長期記憶を保存する。

    category例:
    preference
    likes
    schedule
    challenge
    architecture
    decision
    project
    person
    note
    """

    memory_id = str(
        uuid.uuid4()
    )

    memory_data = {
        "id": memory_id,
        "category": category,
        "title": title,
        "text": text,
        "tags": tags or [],
        "metadata": metadata or {},
        "created_at": now_string(),
        "updated_at": now_string(),
    }

    output_file = os.path.join(
        LONG_TERM_MEMORY_DIR,
        f"{memory_id}.json"
    )

    save_json(
        output_file,
        memory_data
    )

    return memory_data


# ============================================================
# 長期記憶更新
# ============================================================

def update_long_term_memory(
    memory_id: str,
    updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    指定した長期記憶を更新する。
    """

    path = os.path.join(
        LONG_TERM_MEMORY_DIR,
        f"{memory_id}.json"
    )

    data = load_json(
        path,
        {}
    )

    if not isinstance(
        data,
        dict
    ) or not data:

        return None

    # IDは変更不可
    updates.pop(
        "id",
        None
    )

    data.update(
        updates
    )

    data[
        "updated_at"
    ] = now_string()

    save_json(
        path,
        data
    )

    return data


# ============================================================
# 長期記憶削除
# ============================================================

def delete_long_term_memory(
    memory_id: str
) -> bool:
    """
    長期記憶を1件削除。
    """

    path = os.path.join(
        LONG_TERM_MEMORY_DIR,
        f"{memory_id}.json"
    )

    if not os.path.exists(path):
        return False

    try:

        os.remove(path)

        return True

    except Exception as error:

        print(
            f"❌ 長期記憶削除失敗: {memory_id}"
        )

        print(error)

        return False


# ============================================================
# 全長期記憶取得
# ============================================================

def get_all_long_term_memories() -> List[
    Dict[str, Any]
]:
    """
    全長期記憶取得。
    """

    results = []

    if not os.path.exists(
        LONG_TERM_MEMORY_DIR
    ):
        return results

    for filename in os.listdir(
        LONG_TERM_MEMORY_DIR
    ):

        if not filename.endswith(
            ".json"
        ):
            continue

        path = os.path.join(
            LONG_TERM_MEMORY_DIR,
            filename
        )

        data = load_json(
            path,
            {}
        )

        if isinstance(
            data,
            dict
        ) and data:

            results.append(
                data
            )

    results.sort(
        key=lambda item:
        item.get(
            "updated_at",
            item.get(
                "created_at",
                ""
            )
        ),
        reverse=True
    )

    return results


# ============================================================
# 長期記憶キーワード検索
# ============================================================

def search_long_term_memory(
    keyword: str
) -> List[Dict[str, Any]]:
    """
    長期記憶を文字列検索する。
    """

    results = []

    query = keyword.lower()

    for data in (
        get_all_long_term_memories()
    ):

        text = str(
            data.get(
                "text",
                ""
            )
        )

        title = str(
            data.get(
                "title",
                ""
            )
        )

        category = str(
            data.get(
                "category",
                ""
            )
        )

        tags = " ".join(
            str(tag)
            for tag in data.get(
                "tags",
                []
            )
        )

        target = (
            f"{title} "
            f"{text} "
            f"{category} "
            f"{tags}"
        ).lower()

        if query in target:

            results.append(
                data
            )

    return results


# ============================================================
# カテゴリ別長期記憶
# ============================================================

def get_long_term_memories_by_categories(
    categories: List[str],
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    categoryを複数指定して長期記憶を取得。
    """

    normalized = {
        category.lower()
        for category in categories
    }

    results = []

    for item in (
        get_all_long_term_memories()
    ):

        category = str(
            item.get(
                "category",
                ""
            )
        ).lower()

        if category in normalized:

            results.append(
                item
            )

    if limit and limit > 0:
        return results[:limit]

    return results


# ============================================================
# 好きなこと / 興味
# ============================================================

def get_preferences(
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    好み・興味系Memory。
    """

    return (
        get_long_term_memories_by_categories(
            [
                "preference",
                "preferences",
                "like",
                "likes",
                "favorite",
                "favorites",
                "interest",
                "interests",
                "hobby",
                "hobbies",
            ],
            limit
        )
    )


# ============================================================
# 予定
# ============================================================

def get_schedules(
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    予定 / イベント / 締切系Memory。
    """

    return (
        get_long_term_memories_by_categories(
            [
                "schedule",
                "schedules",
                "event",
                "events",
                "appointment",
                "appointments",
                "deadline",
                "deadlines",
                "plan",
                "plans",
            ],
            limit
        )
    )


# ============================================================
# 大きな課題
# ============================================================

def get_challenges(
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    課題 / 問題 / リスク系Memory。
    """

    return (
        get_long_term_memories_by_categories(
            [
                "challenge",
                "challenges",
                "issue",
                "issues",
                "problem",
                "problems",
                "risk",
                "risks",
                "blocker",
                "blockers",
            ],
            limit
        )
    )


# ============================================================
# 最近の長期記憶
# ============================================================

def get_recent_memories(
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    最近作成・更新された長期記憶。
    """

    memories = (
        get_all_long_term_memories()
    )

    return memories[:limit]


# ============================================================
# タスク保存
# ============================================================

def save_task(
    task_name: str,
    details: str,
    status: str = "pending",
    due_date: Optional[str] = None,
    priority: str = "normal",
    tags: Optional[
        List[str]
    ] = None
) -> Dict[str, Any]:
    """
    タスク保存。
    """

    task_id = str(
        uuid.uuid4()
    )

    task_data = {
        "id": task_id,
        "task_name": task_name,
        "details": details,
        "status": status,
        "priority": priority,
        "due_date": due_date,
        "tags": tags or [],
        "created_at": now_string(),
        "updated_at": now_string(),
    }

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    save_json(
        task_file,
        task_data
    )

    return task_data


# ============================================================
# タスク取得
# ============================================================

def get_task(
    task_id: str
) -> Optional[Dict[str, Any]]:
    """
    タスクを1件取得。
    """

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    data = load_json(
        task_file,
        {}
    )

    if not isinstance(
        data,
        dict
    ) or not data:

        return None

    return data


# ============================================================
# タスク状態更新
# ============================================================

def update_task_status(
    task_id: str,
    status: str
) -> bool:
    """
    タスク状態更新。
    """

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    task_data = load_json(
        task_file,
        {}
    )

    if not isinstance(
        task_data,
        dict
    ) or not task_data:

        return False

    task_data[
        "status"
    ] = status

    task_data[
        "updated_at"
    ] = now_string()

    save_json(
        task_file,
        task_data
    )

    return True


# ============================================================
# タスク削除
# ============================================================

def delete_task(
    task_id: str
) -> bool:
    """
    タスク1件削除。
    """

    task_file = os.path.join(
        TASK_MEMORY_DIR,
        f"{task_id}.json"
    )

    if not os.path.exists(
        task_file
    ):
        return False

    try:

        os.remove(
            task_file
        )

        return True

    except Exception as error:

        print(
            f"❌ タスク削除失敗: {task_id}"
        )

        print(error)

        return False


# ============================================================
# タスク一覧
# ============================================================

def get_all_tasks() -> List[
    Dict[str, Any]
]:
    """
    全タスク取得。
    """

    tasks = []

    if not os.path.exists(
        TASK_MEMORY_DIR
    ):
        return tasks

    for filename in os.listdir(
        TASK_MEMORY_DIR
    ):

        if not filename.endswith(
            ".json"
        ):
            continue

        path = os.path.join(
            TASK_MEMORY_DIR,
            filename
        )

        data = load_json(
            path,
            {}
        )

        if isinstance(
            data,
            dict
        ) and data:

            tasks.append(
                data
            )

    tasks.sort(
        key=lambda item:
        item.get(
            "updated_at",
            item.get(
                "created_at",
                ""
            )
        ),
        reverse=True
    )

    return tasks


# ============================================================
# プロジェクト分析保存
# ============================================================

def save_project_analysis(
    project_name: str,
    analysis: Dict[str, Any]
):
    """
    プロジェクト分析結果保存。
    """

    safe_name = (
        project_name
        .replace("/", "_")
        .replace("\\", "_")
    )

    analysis_dir = os.path.join(
        PROJECT_MEMORY_DIR,
        safe_name
    )

    os.makedirs(
        analysis_dir,
        exist_ok=True
    )

    output_file = os.path.join(
        analysis_dir,
        "analysis.json"
    )

    analysis[
        "project_name"
    ] = project_name

    analysis[
        "updated_at"
    ] = now_string()

    save_json(
        output_file,
        analysis
    )


# ============================================================
# プロジェクト分析取得
# ============================================================

def load_project_analysis(
    project_name: str
) -> Dict[str, Any]:
    """
    プロジェクト分析取得。
    """

    safe_name = (
        project_name
        .replace("/", "_")
        .replace("\\", "_")
    )

    path = os.path.join(
        PROJECT_MEMORY_DIR,
        safe_name,
        "analysis.json"
    )

    data = load_json(
        path,
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return {}

    return data


# ============================================================
# 最近触ったファイル保存
# ============================================================

def remember_recent_file(
    project_name: str,
    file_path: str
):
    """
    最近触ったファイルを最大20件保存。
    """

    project_memory = (
        get_project_memory(
            project_name
        )
    )

    recent_files = (
        project_memory.get(
            "recent_files",
            []
        )
    )

    if not isinstance(
        recent_files,
        list
    ):
        recent_files = []

    if file_path in recent_files:

        recent_files.remove(
            file_path
        )

    recent_files.insert(
        0,
        file_path
    )

    recent_files = (
        recent_files[:20]
    )

    save_project_memory(
        project_name,
        "recent_files",
        recent_files
    )


# ============================================================
# 最近触ったファイル取得
# ============================================================

def get_recent_files(
    project_name: str
) -> List[str]:
    """
    プロジェクトの最近触ったファイル取得。
    """

    memory = get_project_memory(
        project_name
    )

    recent_files = memory.get(
        "recent_files",
        []
    )

    if not isinstance(
        recent_files,
        list
    ):
        return []

    return recent_files


# ============================================================
# 汎用Memory
# ============================================================

def load_memory() -> Dict[str, Any]:
    """
    general_memory.json 読込。
    """

    memory = load_json(
        GENERAL_MEMORY_FILE,
        {}
    )

    if not isinstance(
        memory,
        dict
    ):
        return {}

    return memory


# ============================================================
# 汎用Memory保存
# ============================================================

def save_memory(
    key: str,
    value: Any
):
    """
    general_memory.json 保存。
    """

    memory = load_memory()

    memory[
        key
    ] = value

    memory[
        "updated_at"
    ] = now_string()

    save_json(
        GENERAL_MEMORY_FILE,
        memory
    )


# ============================================================
# 汎用Memory削除
# ============================================================

def delete_memory_key(
    key: str
) -> bool:
    """
    general_memory.jsonのキー削除。
    """

    memory = load_memory()

    if key not in memory:
        return False

    del memory[key]

    memory[
        "updated_at"
    ] = now_string()

    save_json(
        GENERAL_MEMORY_FILE,
        memory
    )

    return True


# ============================================================
# Memory統計
# ============================================================

def get_memory_statistics() -> Dict[
    str,
    Any
]:
    """
    Memory全体の統計。
    """

    chat_sessions = 0

    if os.path.exists(
        CHAT_HISTORY_DIR
    ):

        chat_sessions = len([
            filename
            for filename in os.listdir(
                CHAT_HISTORY_DIR
            )
            if filename.endswith(
                ".json"
            )
        ])

    messages = (
        get_all_chat_history()
    )

    long_term_memories = (
        get_all_long_term_memories()
    )

    tasks = get_all_tasks()

    projects = (
        get_all_project_memories()
    )

    pending_tasks = len([
        task
        for task in tasks
        if task.get(
            "status"
        ) not in {
            "completed",
            "done"
        }
    ])

    return {
        "chat_sessions":
            chat_sessions,

        "chat_messages":
            len(messages),

        "long_term_memories":
            len(
                long_term_memories
            ),

        "tasks":
            len(tasks),

        "pending_tasks":
            pending_tasks,

        "projects":
            len(projects),

        "preferences":
            len(
                get_preferences(
                    limit=100000
                )
            ),

        "schedules":
            len(
                get_schedules(
                    limit=100000
                )
            ),

        "challenges":
            len(
                get_challenges(
                    limit=100000
                )
            ),
    }


# ============================================================
# Memory全体要約
# ============================================================

def build_memory_summary() -> str:
    """
    AI向けMemoryサマリー文字列を生成。
    """

    stats = (
        get_memory_statistics()
    )

    session = (
        get_active_session()
    )

    summary = f"""
🧠 AI Memory Summary

Current Project:
{session.get("project_name")}

Session ID:
{session.get("session_id")}

Message Count:
{session.get("message_count", 0)}

Chat Sessions:
{stats.get("chat_sessions", 0)}

Chat Messages:
{stats.get("chat_messages", 0)}

Long Term Memories:
{stats.get("long_term_memories", 0)}

Preferences:
{stats.get("preferences", 0)}

Tasks:
{stats.get("tasks", 0)}

Pending Tasks:
{stats.get("pending_tasks", 0)}

Schedules:
{stats.get("schedules", 0)}

Challenges:
{stats.get("challenges", 0)}

Projects:
{stats.get("projects", 0)}
""".strip()

    return summary


# ============================================================
# Memory Overview
# ============================================================

def get_memory_overview(
    conversation_limit: int = 30,
    recent_memory_limit: int = 10
) -> Dict[str, Any]:
    """
    MemoryPage / MemoryManager.jsx 用の
    一括取得データ。

    GET /api/memory/overview
    からこの関数を呼び出す想定。
    """

    session = (
        get_active_session()
    )

    project_name = (
        session.get(
            "project_name",
            "default_project"
        )
    )

    return {
        "session":
            session,

        "recent_memories":
            get_recent_memories(
                recent_memory_limit
            ),

        "preferences":
            get_preferences(
                20
            ),

        "tasks":
            get_all_tasks(),

        "schedules":
            get_schedules(
                20
            ),

        "conversations":
            get_chat_history(
                conversation_limit
            ),

        "challenges":
            get_challenges(
                20
            ),

        "long_term_memories":
            get_all_long_term_memories(),

        "recent_files":
            get_recent_files(
                project_name
            ),

        "projects":
            get_all_project_memories(),

        "general_memory":
            load_memory(),

        "statistics":
            get_memory_statistics(),
    }


# ============================================================
# Memoryエクスポート
# ============================================================

def export_all_memory(
    output_path: str = "./memory_export.json"
) -> Dict[str, Any]:
    """
    Memory全体を1つのJSONにエクスポート。
    """

    export_data = {
        "exported_at":
            now_string(),

        "session":
            get_active_session(),

        "history":
            get_all_chat_history(),

        "tasks":
            get_all_tasks(),

        "long_term_memories":
            get_all_long_term_memories(),

        "projects":
            get_all_project_memories(),

        "general_memory":
            load_memory(),

        "statistics":
            get_memory_statistics(),
    }

    save_json(
        output_path,
        export_data
    )

    print(
        f"📦 Memory Exported: {output_path}"
    )

    return export_data


# ============================================================
# ディレクトリの中身削除
# ============================================================

def clear_directory(
    directory: str
):
    """
    指定Memoryディレクトリ内を空にする。
    """

    if not os.path.exists(
        directory
    ):
        return

    for name in os.listdir(
        directory
    ):

        path = os.path.join(
            directory,
            name
        )

        try:

            if os.path.isdir(path):

                shutil.rmtree(
                    path
                )

            else:

                os.remove(
                    path
                )

        except Exception as error:

            print(
                f"⚠ 削除失敗: {path}"
            )

            print(error)


# ============================================================
# 全記憶削除
# ============================================================

def clear_all_memory(
    create_session_after_clear: bool = True
) -> Dict[str, Any]:
    """
    AI Memoryを全削除する。

    削除対象:
    - chat_history
    - projects
    - long_term
    - tasks
    - general_memory.json
    - active_session.json

    ディレクトリ構造そのものは再生成する。

    create_session_after_clear=True の場合、
    削除後に新しい空セッションを生成する。
    """

    print(
        "🗑 AI Memory 全削除開始"
    )

    errors = []

    # ----------------------------------------
    # 各Memoryディレクトリを空にする
    # ----------------------------------------

    for directory in [
        CHAT_HISTORY_DIR,
        PROJECT_MEMORY_DIR,
        LONG_TERM_MEMORY_DIR,
        TASK_MEMORY_DIR,
    ]:

        try:

            clear_directory(
                directory
            )

        except Exception as error:

            errors.append(
                {
                    "path":
                        directory,

                    "error":
                        str(error),
                }
            )

    # ----------------------------------------
    # 単体Memoryファイル
    # ----------------------------------------

    for path in [
        GENERAL_MEMORY_FILE,
        ACTIVE_SESSION_FILE,
    ]:

        if not os.path.exists(
            path
        ):
            continue

        try:

            os.remove(
                path
            )

        except Exception as error:

            errors.append(
                {
                    "path":
                        path,

                    "error":
                        str(error),
                }
            )

    # ----------------------------------------
    # tmpファイルやbroken JSONも削除
    # ----------------------------------------

    try:

        if os.path.exists(
            MEMORY_DIR
        ):

            for filename in os.listdir(
                MEMORY_DIR
            ):

                if (
                    ".broken_" in filename
                    or filename.endswith(
                        ".tmp"
                    )
                ):

                    path = os.path.join(
                        MEMORY_DIR,
                        filename
                    )

                    if os.path.isfile(
                        path
                    ):

                        os.remove(
                            path
                        )

    except Exception as error:

        errors.append(
            {
                "path":
                    MEMORY_DIR,

                "error":
                    str(error),
            }
        )

    # ----------------------------------------
    # フォルダ再生成
    # ----------------------------------------

    ensure_memory_directories()

    # ----------------------------------------
    # 新セッション
    # ----------------------------------------

    new_session = None

    if create_session_after_clear:

        new_session = (
            create_new_session(
                "default_project"
            )
        )

    success = (
        len(errors) == 0
    )

    result = {
        "success":
            success,

        "message":
            (
                "全記憶を削除しました。"
                if success
                else
                "一部の記憶削除に失敗しました。"
            ),

        "errors":
            errors,

        "session":
            new_session,
    }

    print(
        "✅ AI Memory 全削除完了"
        if success
        else
        "⚠ AI Memory 一部削除失敗"
    )

    return result


# ============================================================
# Memory初期化
# ============================================================

def initialize_memory_system():
    """
    起動時に呼び出しておくと安全。

    Memoryディレクトリ確認と
    active_session.json の自動復旧を行う。
    """

    ensure_memory_directories()

    session = (
        get_active_session()
    )

    print(
        "🧠 AI Memory initialized"
    )

    print(
        f"   Session : {session.get('session_id')}"
    )

    print(
        f"   Project : {session.get('project_name')}"
    )

    return session


# ============================================================
# テスト
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        "🧠 Memory Manager Test"
    )

    print(
        "=" * 60
    )

    # ----------------------------------------
    # 初期化
    # ----------------------------------------

    session = (
        initialize_memory_system()
    )

    print(
        "\n[SESSION]"
    )

    print(
        session
    )

    # ----------------------------------------
    # チャット
    # ----------------------------------------

    save_chat_message(
        role="user",
        content="MemoryManagerのテストです"
    )

    save_chat_message(
        role="assistant",
        content="正常に保存されました"
    )

    # ----------------------------------------
    # 好きなこと
    # ----------------------------------------

    save_long_term_memory(
        category="preference",
        title="技術の好み",
        text="ReactやPythonを使ったアプリ開発に興味がある",
        tags=[
            "React",
            "Python"
        ]
    )

    # ----------------------------------------
    # 予定
    # ----------------------------------------

    save_long_term_memory(
        category="schedule",
        title="Memory機能改善",
        text="MemoryPageの表示機能を完成させる",
        tags=[
            "memory"
        ]
    )

    # ----------------------------------------
    # 大きな課題
    # ----------------------------------------

    save_long_term_memory(
        category="challenge",
        title="Memory JSON破損対策",
        text="active_session.jsonが破損しても自動復旧できるようにする",
        tags=[
            "bug",
            "memory"
        ]
    )

    # ----------------------------------------
    # タスク
    # ----------------------------------------

    task = save_task(
        task_name="Memory API実装",
        details="/api/memory/overview と /api/memory/all を実装する",
        status="pending",
        priority="high"
    )

    print(
        "\n[TASK]"
    )

    print(
        task
    )

    # ----------------------------------------
    # Overview
    # ----------------------------------------

    print(
        "\n[OVERVIEW]"
    )

    print(
        json.dumps(
            get_memory_overview(),
            ensure_ascii=False,
            indent=2
        )
    )

    # ----------------------------------------
    # Summary
    # ----------------------------------------

    print(
        "\n[SUMMARY]"
    )

    print(
        build_memory_summary()
    )
