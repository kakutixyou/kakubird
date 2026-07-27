from __future__ import annotations

"""
rollback_manager.py

ファイル変更前のバックアップを保存し、
必要に応じて元の状態へ復元する。

保存先:
.ai_editor/backups/
    ├── backup_xxxxx.json
    └── ...

各バックアップには以下を保存する:
- backup_id
- file_path
- created_at
- content
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------
# Data Models
# ---------------------------------------------------------

@dataclass(slots=True)
class BackupRecord:
    """
    バックアップ情報。
    """

    backup_id: str
    file_path: str
    created_at: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupRecord":
        return cls(**data)


# ---------------------------------------------------------
# Service
# ---------------------------------------------------------

class RollbackManager:
    """
    ファイルのバックアップと復元を管理する。
    """

    def __init__(
        self,
        storage_dir: str | Path = ".ai_editor/backups",
        encoding: str = "utf-8",
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encoding = encoding

    # -----------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _generate_backup_id(self) -> str:
        return f"backup_{uuid4().hex[:12]}"

    def _get_path(self, backup_id: str) -> Path:
        return self.storage_dir / f"{backup_id}.json"

    def _save(self, record: BackupRecord) -> None:
        path = self._get_path(record.backup_id)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                record.to_dict(),
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _load(self, backup_id: str) -> BackupRecord:
        path = self._get_path(backup_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Backup not found: {backup_id}"
            )

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return BackupRecord.from_dict(data)

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def create_backup(
        self,
        *,
        file_path: str | Path,
        content: str,
    ) -> str:
        """
        バックアップを作成し、backup_id を返す。
        """
        record = BackupRecord(
            backup_id=self._generate_backup_id(),
            file_path=str(file_path),
            created_at=self._now(),
            content=content,
        )

        self._save(record)
        return record.backup_id

    def get_backup(self, backup_id: str) -> BackupRecord:
        """
        バックアップ情報を取得する。
        """
        return self._load(backup_id)

    def list_backups(self) -> list[BackupRecord]:
        """
        すべてのバックアップを新しい順で取得する。
        """
        records: list[BackupRecord] = []

        for path in self.storage_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append(BackupRecord.from_dict(data))
            except Exception:
                continue

        records.sort(
            key=lambda r: r.created_at,
            reverse=True,
        )

        return records

    def restore(self, backup_id: str) -> str:
        """
        バックアップからファイルを復元する。

        Returns
        -------
        str
            復元されたファイルパス
        """
        record = self._load(backup_id)

        target_path = Path(record.file_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_text(
            record.content,
            encoding=self.encoding,
        )

        return str(target_path)

    def delete_backup(self, backup_id: str) -> None:
        """
        バックアップファイルを削除する。
        """
        path = self._get_path(backup_id)

        if path.exists():
            path.unlink()

    def to_dict(self, backup_id: str) -> dict[str, Any]:
        """
        辞書形式で取得する。
        """
        return self.get_backup(backup_id).to_dict()


# ---------------------------------------------------------
# Example Usage
# ---------------------------------------------------------

if __name__ == "__main__":
    manager = RollbackManager()

    # バックアップ作成
    backup_id = manager.create_backup(
        file_path="example.py",
        content='print("before")\n',
    )

    print("Backup created:", backup_id)

    # 復元
    restored_path = manager.restore(backup_id)
    print("Restored:", restored_path)

    # 一覧表示
    for record in manager.list_backups():
        print(record.to_dict())