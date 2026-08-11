# task_memory.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Task


class TaskMemory:
    """タスク一覧を JSON ファイルに保存する。"""

    def __init__(
        self,
        storage_path: str | Path = ".ai_memory/tasks.json",
    ) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.storage_path.exists():
            self._save([])

    # =========================================================
    # Public API
    # =========================================================

    def get_tasks(self) -> list[Task]:
        raw = self._load()
        tasks: list[Task] = []

        for item in raw:
            try:
                tasks.append(Task.from_dict(item))
            except Exception:
                continue

        return tasks

    def get_task(self, title: str) -> Task | None:
        for task in self.get_tasks():
            if task.title == title:
                return task
        return None

    def add_task(self, task: Task) -> None:
        tasks = self.get_tasks()

        # 同名タスクがあれば上書き
        for i, existing in enumerate(tasks):
            if existing.title == task.title:
                tasks[i] = task
                self._save_tasks(tasks)
                return

        tasks.append(task)
        self._save([task.to_dict() for task in tasks])