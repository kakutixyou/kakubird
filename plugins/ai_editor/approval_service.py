# jimdo_sutdio_replica/plugins/ai_editor/approval_service.py
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


# ---------------------------------------------
# Data Model
# ---------------------------------------------

@dataclass(slots=True)
class ApprovalRequest:
    id: str
    file_path: str
    status: str
    created_at: str
    updated_at: str
    diff: str
    new_content: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequest":
        return cls(**data)


# ---------------------------------------------
# Service
# ---------------------------------------------

class ApprovalService:
    """
    AI が生成した変更案の承認状態を管理する。
    """

    VALID_STATUSES = {
        "pending",
        "approved",
        "rejected",
        "applied",
        "expired",
    }

    def __init__(
        self,
        storage_dir: str | Path = ".ai_editor/approvals",
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------
    # Internal Helpers
    # -----------------------------------------

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _generate_id(self) -> str:
        return f"patch_{uuid4().hex[:12]}"

    def _get_path(self, request_id: str) -> Path:
        return self.storage_dir / f"{request_id}.json"

    def _save(self, request: ApprovalRequest) -> None:
        path = self._get_path(request.id)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                request.to_dict(),
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _load(self, request_id: str) -> ApprovalRequest:
        path = self._get_path(request_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Approval request not found: {request_id}"
            )

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return ApprovalRequest.from_dict(data)

    # -----------------------------------------
    # Public API
    # -----------------------------------------

    def create_request(
        self,
        *,
        file_path: str,
        diff: str,
        new_content: str,
        description: str = "",
    ) -> ApprovalRequest:
        """
        新しい承認リクエストを作成する。
        """
        now = self._now()

        request = ApprovalRequest(
            id=self._generate_id(),
            file_path=file_path,
            status="pending",
            created_at=now,
            updated_at=now,
            diff=diff,
            new_content=new_content,
            description=description,
        )

        self._save(request)
        return request

    def get_request(self, request_id: str) -> ApprovalRequest:
        """
        承認リクエストを取得する。
        """
        return self._load(request_id)

    def list_requests(self) -> list[ApprovalRequest]:
        """
        すべての承認リクエストを新しい順に取得する。
        """
        requests: list[ApprovalRequest] = []

        for path in self.storage_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                requests.append(ApprovalRequest.from_dict(data))
            except Exception:
                continue

        requests.sort(
            key=lambda r: r.created_at,
            reverse=True,
        )

        return requests

    def update_status(
        self,
        request_id: str,
        status: str,
    ) -> ApprovalRequest:
        """
        ステータスを更新する。
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        request = self._load(request_id)
        request.status = status
        request.updated_at = self._now()

        self._save(request)
        return request

    def approve(self, request_id: str) -> ApprovalRequest:
        return self.update_status(request_id, "approved")

    def reject(self, request_id: str) -> ApprovalRequest:
        return self.update_status(request_id, "rejected")

    def mark_applied(self, request_id: str) -> ApprovalRequest:
        return self.update_status(request_id, "applied")

    def expire(self, request_id: str) -> ApprovalRequest:
        return self.update_status(request_id, "expired")

    def delete_request(self, request_id: str) -> None:
        """
        承認リクエストを削除する。
        """
        path = self._get_path(request_id)

        if path.exists():
            path.unlink()

    def to_dict(self, request_id: str) -> dict[str, Any]:
        """
        API レスポンス用の辞書を返す。
        """
        return self.get_request(request_id).to_dict()


# ---------------------------------------------
# Example Usage
# ---------------------------------------------

if __name__ == "__main__":
    service = ApprovalService()

    request = service.create_request(
        file_path="plugins/ai_editor/approval_service.py",
        diff="--- old\n+++ new\n",
        new_content="print('hello')\n",
        description="approval_service.py を生成",
    )

    print("Created:", request.id)
    print("Status:", request.status)

    approved = service.approve(request.id)
    print("Approved:", approved.status)

    loaded = service.get_request(request.id)
    print("Loaded:", loaded.to_dict())