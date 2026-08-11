from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RequirementItem:
    category: str
    name: str
    description: str
    priority: int = 1
    exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RequirementsPlanner:
    """
    プロジェクト完成に必要なファイル・知識・設定を推定する。
    """

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)

    # -------------------------------------------------
    # 期待構成
    # -------------------------------------------------

    def expected_items(self) -> list[RequirementItem]:
        return [
            RequirementItem(
                category="frontend",
                name="frontend/src/hooks/useAiChat.js",
                description="チャット送受信の中心",
                priority=1,
            ),
            RequirementItem(
                category="backend",
                name="backend/api/routes_chat.py",
                description="AIチャットAPI",
                priority=1,
            ),
            RequirementItem(
                category="memory",
                name="plugins/ai_memory/memory_manager.py",
                description="長期記憶の保存",
                priority=1,
            ),
            RequirementItem(
                category="editor",
                name="plugins/ai_editor/approval_service.py",
                description="生成コードの承認管理",
                priority=2,
            )
        ]
        return questions