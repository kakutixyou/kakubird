# ===
# context_builder.py
# AIへ渡す「現在必要な文脈(Context)」を構築する
# ===

import os
import json
from typing import Dict, Any, List

# ===
# 内部モジュール
# ===

from core.ai_state_manager import (
    get_active_context,
    get_workspace_state,
    get_current_task,
    get_project_map,
    get_dependency_graph
)

from core.chunk_manager_chatgpt import (
    search_chunks_by_keyword
)

# ===
# 基本設定
# ===

MAX_HISTORY_MESSAGES = 8
MAX_RELATED_CHUNKS = 6
MAX_CHUNK_LENGTH = 1800

def build_ai_context() -> dict:
    return { "system_prompt": "You...", "recent_context": "..." }
# ===
# 基本設定
# ===

MAX_HISTORY_MESSAGES = 8
MAX_RELATED_CHUNKS = 6
MAX_CHUNK_LENGTH = 1800
MAX_PROMPT_LENGTH = 15000 # トークン溢れ防止用の安全装置
# ===
# テキスト整形
# ===

def safe_trim(text: str, limit: int = MAX_CHUNK_LENGTH) -> str:
    """
    長すぎるChunkを切り詰める
    """

    if len(text) <= limit:
        return text

    return text[:limit] + "\n...(truncated)"

# ===
# 会話履歴整理
# ===

def build_history_context(history: List[Dict[str, Any]]) -> str:
    """
    会話履歴をLLM向け文字列へ変換
    """

    if not history:
        return "履歴なし"

    recent_history = history[-MAX_HISTORY_MESSAGES:]

    lines = []

    for msg in recent_history:

        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        lines.append(f"[{role}] {content}")

    return "\n".join(lines)

# ===
# Active Context構築
# ===

def build_active_context_text() -> str:

    active = get_active_context()

    return (
        f"現在モード: {active.get('mode')}\n"
        f"現在プロジェクト: {active.get('active_project')}\n"
        f"注目ファイル: {active.get('focused_file')}\n"
        f"注目コンポーネント: {active.get('focused_component')}\n"
    )

# ===
# Workspace Context構築
# ===

def build_workspace_context_text() -> str:

    workspace = get_workspace_state()

    indexed_files = workspace.get("indexed_files", [])
    frameworks = workspace.get("known_frameworks", [])
    languages = workspace.get("known_languages", [])

    return (
        f"Indexed Files: {len(indexed_files)}\n"
        f"Frameworks: {', '.join(frameworks)}\n"
        f"Languages: {', '.join(languages)}\n"
    )

# ===
# Current Task Context
# ===

def build_current_task_text() -> str:

    task = get_current_task()

    return (
        f"Current Task: {task.get('task')}\n"
        f"Status: {task.get('status')}\n"
        f"Progress: {task.get('progress')}%\n"
        f"Details: {task.get('details')}\n"
    )

# ===
# Project Map Context
# ===

def build_project_map_text() -> str:

    project_map = get_project_map()

    if not project_map:
        return "Project Mapなし"

    lines = []

    for section, files in project_map.items():

        lines.append(f"\n[{section}]")

        if isinstance(files, list):
            for file in files[:20]:
                lines.append(f" - {file}")

    return "\n".join(lines)

# ===
# Dependency Context
# ===

def build_dependency_context(target_file: str = None) -> str:

    graph = get_dependency_graph()

    if not graph:
        return "Dependency Graphなし"

    lines = []

    # 特定ファイルのみ
    if target_file and target_file in graph:

        deps = graph[target_file]

        lines.append(f"[Dependencies for {target_file}]")

        for dep in deps[:20]:
            lines.append(f" -> {dep}")

        return "\n".join(lines)

    # 全体簡易
    for key, deps in list(graph.items())[:10]:

        lines.append(f"\n[{key}]")

        for dep in deps[:10]:
            lines.append(f" -> {dep}")

    return "\n".join(lines)

# ===
# 関連Chunk検索
# ===

def build_related_chunks_text(
    query: str,
    project_name: str = "default_project"
) -> str:
    """
    クエリに関連するChunkを検索
    """

    results = search_chunks_by_keyword(
        keyword=query,
        project_name=project_name
    )

    if not results:
        return "関連Chunkなし"

    lines = []

    for idx, chunk in enumerate(results[:MAX_RELATED_CHUNKS]):

        lines.append(
            f"""

Chunk #{idx + 1}
File: {chunk.get('file_name')}
Language: {chunk.get('language')}


{safe_trim(chunk.get('content', ''))}
"""
        )

    return "\n".join(lines)

# ===
# システム能力Context
# ===

def build_system_capabilities_text() -> str:

    return """
【AIシステム能力】

- ソースコード解析
- React/FastAPI構造理解
- RAG検索
- Chunk検索
- Dependency Graph解析
- Project Map解析
- GitHub検索
- 天気取得
- SQLite解析
- ZIPインポート解析

"""

# ===
# メインContext Builder
# ===

def build_full_context(
    user_message: str,
    history: List[Dict[str, Any]] = None,
    project_name: str = "default_project"
) -> Dict[str, Any]:
    """
    AIへ渡す完全Contextを構築
    """

    if history is None:
        history = []

    full_context_text = f"""
# =====
# AI SYSTEM CONTEXT
# =====

{build_system_capabilities_text()}

# =====
# ACTIVE CONTEXT
# =====

{build_active_context_text()}

# =====
# WORKSPACE STATE
# =====

{build_workspace_context_text()}

# =====
# CURRENT TASK
# =====

{build_current_task_text()}

# =====
# PROJECT MAP
# =====

{build_project_map_text()}

# =====
# DEPENDENCY GRAPH
# =====

{build_dependency_context()}

# =====
# RECENT CHAT HISTORY
# =====

{build_history_context(history)}

# =====
# RELATED KNOWLEDGE CHUNKS
# =====

{build_related_chunks_text(
    query=user_message,
    project_name=project_name
)}

# =====
# USER MESSAGE
# =====

{user_message}

"""

    return {
        "system_context": full_context_text,
        "active_context": get_active_context(),
        "workspace_state": get_workspace_state(),
        "current_task": get_current_task(),
        "project_map": get_project_map(),
        "dependency_graph": get_dependency_graph()
    }

# ===
# 軽量Context
# ===

def build_lightweight_context(
    user_message: str
) -> str:
    """
    高速応答向け軽量Context
    """

    active = get_active_context()

    return f"""
現在モード: {active.get('mode')}
現在プロジェクト: {active.get('active_project')}

ユーザー入力:
{user_message}
"""

# ===
# Debug表示
# ===

def debug_print_context(context: Dict[str, Any]):

    print("\n")
    print("🧠 AI Context Debug")
    print("")

    system_context = context.get("system_context", "")

    print(system_context[:3000])

    print("\n")

# ===
# JSON保存（デバッグ用）
# ===

def save_context_snapshot(
    context: Dict[str, Any],
    output_path: str = "./context_snapshot.json"
):

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)

        print(f"📦 Context Snapshot Saved: {output_path}")

    except Exception as e:
        print("❌ Context保存失敗")
        print(e)

# ===
# テスト
# ===

if __name__ == "__main__":

    sample_history = [
        {
            "role": "user",
            "content": "stream処理どこ？"
        },
        {
            "role": "assistant",
            "content": "useAiChat.jsです"
        }
    ]

    context = build_full_context(
        user_message="ZIPアップロード処理を解析して",
        history=sample_history,
        project_name="test_project"
    )

    debug_print_context(context)

    save_context_snapshot(context)