# plugins/
# └── ai_memory/
#     └── memory_manager.py
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

from .conversation_memory import ConversationMemory


class MemoryManager:
    """
    AI Memory 全体を管理する。

    管理対象:
    - conversation.json : 会話履歴
    - notes.json        : 重複なしメモ
    - tasks.json        : タスク一覧
    - files.json        : 関連ファイル一覧
    """
    # def record_interaction(
    #     self,
    #     user_message,
    #     assistant_message
    # ):
    #     self.conversation.add_message("user", user_message)
    #     self.conversation.add_message("assistant", assistant_message)

    def __init__(
        self,
        storage_dir: str | Path = ".ai_memory",
        max_messages: int = 200,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 会話履歴
        self.conversation = ConversationMemory(
            storage_path=self.storage_dir / "conversation.json",
            max_messages=max_messages,
        )

        # その他
        self.notes_path = self.storage_dir / "notes.json"
        self.tasks_path = self.storage_dir / "tasks.json"
        self.files_path = self.storage_dir / "files.json"

        # 初期ファイル生成
        self._ensure_json_file(self.notes_path, []) # type: ignore
        self._ensure_json_file(self.tasks_path, []) # type: ignore
        self._ensure_json_file(self.files_path, []) # type: ignore

    # =========================================================
    # Public API
    # =========================================================

def record_interaction(
    self,
    user_message: str,
    assistant_message: str,
    notes: list[str] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    files: list[dict[str, Any]] | None = None,
) -> None:
    """Record user and assistant interaction with optional metadata."""
    # 会話を記録
    self.conversation.add_message("user", user_message)
    self.conversation.add_message("assistant", assistant_message)

    # メモを記録
    if notes:
        self._append_to_json_file(self.notes_path, notes)

    # タスクを記録
    if tasks:
        self._append_to_json_file(self.tasks_path, tasks)

    # ファイルを記録
    if files:
        self._append_to_json_file(self.files_path, files)