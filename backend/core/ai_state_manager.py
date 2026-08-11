# =========================================================
# ai_state_manager.py
# AIの状態・記憶・現在タスクを管理する中枢
# =========================================================

import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional

# =========================================================
# 保存先ディレクトリ設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")

ACTIVE_CONTEXT_FILE = os.path.join(AI_MEMORY_DIR, "active_context.json")
WORKSPACE_STATE_FILE = os.path.join(AI_MEMORY_DIR, "workspace_state.json")
CURRENT_TASK_FILE = os.path.join(AI_MEMORY_DIR, "current_task.json")
PROJECT_MAP_FILE = os.path.join(AI_MEMORY_DIR, "project_map.json")
DEPENDENCY_GRAPH_FILE = os.path.join(AI_MEMORY_DIR, "dependency_graph.json")
CURRENT_STATE_FILE = os.path.join(AI_MEMORY_DIR, "current_state.json")
# =========================================================
# ディレクトリ自動生成
# =========================================================

os.makedirs(AI_MEMORY_DIR, exist_ok=True)

# =========================================================
# スレッド安全用ロック
# =========================================================

_lock = threading.Lock()

# =========================================================
# 共通JSON操作
# =========================================================

def _load_json(path: str, default: Any):
    """
    JSONファイルを安全に読み込む
    """
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"❌ JSON読み込み失敗: {path}")
        print(e)
        return default


def _save_json(path: str, data: Any):
    """
    JSONファイルを安全に保存
    """
    try:
        with _lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ JSON保存失敗: {path}")
        print(e)

# =========================================================
# 初期状態生成
# =========================================================

DEFAULT_ACTIVE_CONTEXT = {
    "active_project": None,
    "focused_file": None,
    "focused_component": None,
    "mode": "normal_chat",
    "last_updated": None
}

DEFAULT_WORKSPACE_STATE = {
    "loaded_projects": [],
    "indexed_files": [],
    "known_languages": [],
    "known_frameworks": [],
    "last_scan": None
}

DEFAULT_CURRENT_TASK = {
    "task": None,
    "status": "idle",
    "progress": 0,
    "details": ""
}

# =========================================================
# 初回起動時のファイル生成
# =========================================================

def initialize_ai_state():
    """
    必要なJSONファイルを生成
    """

    if not os.path.exists(ACTIVE_CONTEXT_FILE):
        _save_json(ACTIVE_CONTEXT_FILE, DEFAULT_ACTIVE_CONTEXT)

    if not os.path.exists(WORKSPACE_STATE_FILE):
        _save_json(WORKSPACE_STATE_FILE, DEFAULT_WORKSPACE_STATE)

    if not os.path.exists(CURRENT_TASK_FILE):
        _save_json(CURRENT_TASK_FILE, DEFAULT_CURRENT_TASK)

    if not os.path.exists(PROJECT_MAP_FILE):
        _save_json(PROJECT_MAP_FILE, {})

    if not os.path.exists(DEPENDENCY_GRAPH_FILE):
        _save_json(DEPENDENCY_GRAPH_FILE, {})

# =========================================================
# Active Context
# =========================================================

def get_active_context() -> Dict[str, Any]:
    return _load_json(ACTIVE_CONTEXT_FILE, DEFAULT_ACTIVE_CONTEXT)


def update_active_context(updates: Dict[str, Any]) -> Dict[str, Any]:
    context = get_active_context()

    context.update(updates)

    context["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _save_json(ACTIVE_CONTEXT_FILE, context)

    return context


def clear_active_context():
    _save_json(ACTIVE_CONTEXT_FILE, DEFAULT_ACTIVE_CONTEXT)
def save_current_state(state_data: dict):
    _save_json(CURRENT_STATE_FILE, state_data)
# =========================================================
# 状態読込
# =========================================================

def load_current_state():
    return _load_json(CURRENT_STATE_FILE, {})
# =========================================================
# Workspace State
# =========================================================

def get_workspace_state() -> Dict[str, Any]:
    return _load_json(WORKSPACE_STATE_FILE, DEFAULT_WORKSPACE_STATE)


def update_workspace_state(updates: Dict[str, Any]) -> Dict[str, Any]:
    state = get_workspace_state()

    state.update(updates)

    state["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _save_json(WORKSPACE_STATE_FILE, state)

    return state

# =========================================================
# Current Task
# =========================================================

def get_current_task() -> Dict[str, Any]:
    return _load_json(CURRENT_TASK_FILE, DEFAULT_CURRENT_TASK)


def set_current_task(
    task: str,
    status: str = "running",
    progress: int = 0,
    details: str = ""
):
    current = {
        "task": task,
        "status": status,
        "progress": progress,
        "details": details,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    _save_json(CURRENT_TASK_FILE, current)

    return current


def update_task_progress(progress: int, details: Optional[str] = None):
    current = get_current_task()

    current["progress"] = progress

    if details is not None:
        current["details"] = details

    current["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _save_json(CURRENT_TASK_FILE, current)

    return current


def finish_current_task(details: str = "完了"):
    current = get_current_task()

    current["status"] = "completed"
    current["progress"] = 100
    current["details"] = details

    current["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _save_json(CURRENT_TASK_FILE, current)

    return current

# =========================================================
# Project Map
# =========================================================

def get_project_map() -> Dict[str, Any]:
    return _load_json(PROJECT_MAP_FILE, {})


def save_project_map(project_map: Dict[str, Any]):
    _save_json(PROJECT_MAP_FILE, project_map)

# =========================================================
# Dependency Graph
# =========================================================

def get_dependency_graph() -> Dict[str, Any]:
    return _load_json(DEPENDENCY_GRAPH_FILE, {})


def save_dependency_graph(graph: Dict[str, Any]):
    _save_json(DEPENDENCY_GRAPH_FILE, graph)

# =========================================================
# AI状態サマリー
# =========================================================

def get_ai_system_summary() -> Dict[str, Any]:
    """
    AI全体状態をまとめて返す
    """

    return {
        "active_context": get_active_context(),
        "workspace_state": get_workspace_state(),
        "current_task": get_current_task(),
        "project_map_exists": os.path.exists(PROJECT_MAP_FILE),
        "dependency_graph_exists": os.path.exists(DEPENDENCY_GRAPH_FILE)
    }

# =========================================================
# 自己分析用（将来拡張）
# =========================================================

def analyze_self_state() -> Dict[str, Any]:
    """
    AI自身の状態を簡易分析
    """

    workspace = get_workspace_state()
    project_map = get_project_map()
    dependency_graph = get_dependency_graph()

    indexed_count = len(workspace.get("indexed_files", []))

    frontend_files = []
    backend_files = []

    for key in project_map.keys():
        if "frontend" in key.lower():
            frontend_files.append(key)

        if "backend" in key.lower():
            backend_files.append(key)

    return {
        "indexed_files": indexed_count,
        "frontend_sections": len(frontend_files),
        "backend_sections": len(backend_files),
        "dependency_nodes": len(dependency_graph.keys()),
        "active_mode": get_active_context().get("mode"),
        "current_task": get_current_task().get("task")
    }

# =========================================================
# 初期化実行
# =========================================================

initialize_ai_state()

print("🧠 AI State Manager initialized.")