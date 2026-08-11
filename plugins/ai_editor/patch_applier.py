from __future__ import annotations

"""
patch_applier.py

承認済みの変更案を実際のファイルへ適用する。

主な責務:
- ApprovalService から承認リクエストを取得
- rollback_manager にバックアップを作成させる
- new_content を対象ファイルへ書き込む
- ApprovalService の状態を "applied" に更新
- 適用結果を返す
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from .approval_service import ApprovalService, ApprovalRequest
from .rollback_manager import RollbackManager


# ---------------------------------------------------------
# Data Model
# ---------------------------------------------------------

@dataclass(slots=True)
class ApplyResult:
    """
    パッチ適用結果。
    """

    success: bool
    request_id: str
    file_path: str
    backup_id: str
    status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------
# Service
# ---------------------------------------------------------

class PatchApplier:
    """
    承認済みのパッチをファイルに適用する。
    """

    def __init__(
        self,
        approval_service: Optional[ApprovalService] = None,
        rollback_manager: Optional[RollbackManager] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.approval_service = approval_service or ApprovalService()
        self.rollback_manager = rollback_manager or RollbackManager()
        self.encoding = encoding

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def apply(self, request_id: str) -> ApplyResult:
        """
        承認済みの変更をファイルへ適用する。

        Parameters
        ----------
        request_id:
            Approval request ID

        Returns
        -------
        ApplyResult
        """
        request = self.approval_service.get_request(request_id)

        if request.status != "approved":
            raise ValueError(
                f"Request must be approved before apply. "
                f"Current status: {request.status}"
            )

        target_path = Path(request.file_path)

        # 親ディレクトリが存在しなければ作成
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 現在の内容を取得（新規ファイルなら空文字）
        old_content = self._read_existing_content(target_path)

        # バックアップ作成
        backup_id = self.rollback_manager.create_backup(
            file_path=target_path,
            content=old_content,
        )

        # 新しい内容を書き込み
        target_path.write_text(
            request.new_content,
            encoding=self.encoding,
        )

        # 承認状態を applied に更新
        self.approval_service.mark_applied(request_id)

        return ApplyResult(
            success=True,
            request_id=request.id,
            file_path=str(target_path),
            backup_id=backup_id,
            status="applied",
            message=f"Applied patch to {target_path}",
        )

    def apply_request(self, request: ApprovalRequest) -> ApplyResult:
        """
        ApprovalRequest オブジェクトを直接受け取って適用する。
        """
        return self.apply(request.id)

    # -----------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------

    def _read_existing_content(self, path: Path) -> str:
        """
        既存ファイルの内容を取得する。
        ファイルが存在しない場合は空文字を返す。
        """
        if not path.exists():
            return ""

        return path.read_text(encoding=self.encoding)


# ---------------------------------------------------------
# Example Usage
# ---------------------------------------------------------

if __name__ == "__main__":
    approval_service = ApprovalService()
    rollback_manager = RollbackManager()

    # 例: 承認リクエスト作成
    req = approval_service.create_request(
        file_path="example.py",
        diff="--- old\n+++ new\n",
        new_content='print("Hello from PatchApplier")\n',
        description="example.py を生成",
    )

    # 承認
    approval_service.approve(req.id)

    # 適用
    applier = PatchApplier(
        approval_service=approval_service,
        rollback_manager=rollback_manager,
    )

    result = applier.apply(req.id)
    print(result.to_dict())