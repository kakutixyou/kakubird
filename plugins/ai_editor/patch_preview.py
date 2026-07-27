from __future__ import annotations

"""
patch_preview.py

Unified Diff を UI/API 向けに整形する。

主な責務:
- diff_generator が生成した差分を受け取る
- 追加行数 / 削除行数を集計
- 変更ファイル情報をまとめる
- フロントエンドでそのまま表示できる JSON を生成する
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .diff_generator import (
    count_changes,
    generate_diff,
    get_diff_stats,
)


# ---------------------------------------------------------
# Data Models
# ---------------------------------------------------------

@dataclass(slots=True)
class PatchPreview:
    """
    UI/API 用のプレビュー情報。
    """

    file: str
    added: int
    removed: int
    changed: bool
    diff: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------
# Service
# ---------------------------------------------------------

class PatchPreviewService:
    """
    差分プレビュー生成サービス。
    """

    def create_preview(
        self,
        *,
        file_path: str | Path,
        old_text: str,
        new_text: str,
        description: str = "",
    ) -> PatchPreview:
        """
        旧内容と新内容から PatchPreview を生成する。
        """
        diff_text = generate_diff(
            old_text=old_text,
            new_text=new_text,
            file_path=file_path,
        )

        stats = get_diff_stats(diff_text)

        return PatchPreview(
            file=str(file_path),
            added=stats.added,
            removed=stats.removed,
            changed=stats.changed,
            diff=diff_text,
            description=description,
        )

    def create_from_diff(
        self,
        *,
        file_path: str | Path,
        diff_text: str,
        description: str = "",
    ) -> PatchPreview:
        """
        既存の diff 文字列から PatchPreview を生成する。
        """
        added, removed = count_changes(diff_text)

        return PatchPreview(
            file=str(file_path),
            added=added,
            removed=removed,
            changed=(added > 0 or removed > 0),
            diff=diff_text,
            description=description,
        )

    def create_from_files(
        self,
        *,
        file_path: str | Path,
        old_file: str | Path,
        new_file: str | Path,
        description: str = "",
        encoding: str = "utf-8",
    ) -> PatchPreview:
        """
        2つのファイルを読み込んでプレビューを生成する。
        """
        old_text = Path(old_file).read_text(encoding=encoding)
        new_text = Path(new_file).read_text(encoding=encoding)

        return self.create_preview(
            file_path=file_path,
            old_text=old_text,
            new_text=new_text,
            description=description,
        )


# ---------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------

def create_patch_preview(
    *,
    file_path: str | Path,
    old_text: str,
    new_text: str,
    description: str = "",
) -> dict[str, Any]:
    """
    辞書形式のプレビューを生成する。
    """
    service = PatchPreviewService()
    preview = service.create_preview(
        file_path=file_path,
        old_text=old_text,
        new_text=new_text,
        description=description,
    )
    return preview.to_dict()


# ---------------------------------------------------------
# Example Usage
# ---------------------------------------------------------

if __name__ == "__main__":
    old = 'print("hello")\n'
    new = 'print("Hello, world!")\n'

    service = PatchPreviewService()

    preview = service.create_preview(
        file_path="app.py",
        old_text=old,
        new_text=new,
        description="Greeting message update",
    )

    print(preview.to_dict())