from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Task
from .priority_engine import PriorityEngine


@dataclass
class RoadmapPhase:
    name: str
    tasks: list[Task]

    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def completed(self) -> int:
        return sum(1 for task in self.tasks if task.status == "done")

    @property
    def progress(self) -> float:
        if self.total == 0:
            return 0.0
        return self.completed / self.total

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total": self.total,
            "completed": self.completed,
            "progress": round(self.progress, 3),
            "tasks": [task.to_dict() for task in self.tasks],
        }


class RoadmapPlanner:
    """タスク一覧から開発ロードマップを生成する。"""

    DEFAULT_PHASES = {
        "01_基盤構築": ["setup", "config", "models", "database"],
        "02_メモリ機能": ["memory", "conversation", "task", "notes"],
        "03_AI制御": ["priority", "focus", "approval", "orchestrator"],
        "04_UI表示": ["page", "panel", "sidebar", "dashboard"],
        "05_外部連携": ["unity", "blender", "vscode", "github"],
    }

    def __init__(
        self,
        priority_engine: PriorityEngine | None = None,
    ) -> None:
        self.priority_engine = priority_engine or PriorityEngine()
        }