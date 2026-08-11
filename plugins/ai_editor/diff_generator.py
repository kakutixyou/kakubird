from __future__ import annotations

"""
diff_generator.py

2つのテキストの差分を Unified Diff 形式で生成するユーティリティ。

主な用途:
- AI が提案したコード変更の差分生成
- 変更行数の集計
- 変更有無の判定
- approval_service / patch_preview / patch_validator の入力生成
"""

from dataclasses import dataclass
import difflib
from pathlib import Path


@dataclass(slots=True)
class DiffStats:
    """
    差分の統計情報。
    """

    added: int
    removed: int
    changed: bool


def _normalize_text(text: str) -> list[str]:
    """
    テキストを行単位のリストへ変換する。
    行末の改行文字を保持する。
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")

    return text.splitlines(keepends=True)


def generate_diff(
    old_text: str,
    new_text: str,
    file_path: str | Path,
    context_lines: int = 3,
) -> str:
    """
    Unified Diff を生成する。

    Parameters
    ----------
    old_text:
        元のファイル内容
    new_text:
        新しいファイル内容
    file_path:
        対象ファイルのパス
    context_lines:
        前後の文脈行数

    Returns
    -------
    str
        Unified Diff 文字列
    """
    path = str(file_path)

    old_lines = _normalize_text(old_text)
    new_lines = _normalize_text(new_text)

    diff_lines = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context_lines,
        lineterm="",
    )

    return "\n".join(diff_lines)


def has_changes(diff_text: str) -> bool:
    """
    差分に実際の変更が含まれているか判定する。
    """
    if not diff_text.strip():
        return False

    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+") or line.startswith("-"):
            return True

    return False


def count_changes(diff_text: str) -> tuple[int, int]:
    """
    追加行数・削除行数を返す。

    Returns
    -------
    tuple[int, int]
        (added, removed)
    """
    added = 0
    removed = 0

    for line in diff_text.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("---"):
            continue
        if line.startswith("@@"):
            continue

        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1

    return added, removed


def get_diff_stats(diff_text: str) -> DiffStats:
    """
    差分統計を取得する。
    """
    added, removed = count_changes(diff_text)

    return DiffStats(
        added=added,
        removed=removed,
        changed=(added > 0 or removed > 0),
    )


def generate_file_diff(
    old_file: str | Path,
    new_file: str | Path,
    *,
    display_path: str | None = None,
    context_lines: int = 3,
    encoding: str = "utf-8",
) -> str:
    """
    2つのファイルを読み込んで Unified Diff を生成する。
    """
    old_path = Path(old_file)
    new_path = Path(new_file)

    old_text = old_path.read_text(encoding=encoding)
    new_text = new_path.read_text(encoding=encoding)

    path_for_display = display_path or str(new_path)

    return generate_diff(
        old_text=old_text,
        new_text=new_text,
        file_path=path_for_display,
        context_lines=context_lines,
    )


def create_diff_payload(
    file_path: str | Path,
    old_text: str,
    new_text: str,
) -> dict:
    """
    UI/API 用の差分ペイロードを生成する。

    Returns
    -------
    dict
        {
            "file": "...",
            "added": 3,
            "removed": 1,
            "changed": True,
            "diff": "..."
        }
    """
    diff_text = generate_diff(
        old_text=old_text,
        new_text=new_text,
        file_path=file_path,
    )

    stats = get_diff_stats(diff_text)

    return {
        "file": str(file_path),
        "added": stats.added,
        "removed": stats.removed,
        "changed": stats.changed,
        "diff": diff_text,
    }


if __name__ == "__main__":
    old = 'print("hello")\n'
    new = 'print("Hello, world!")\n'

    payload = create_diff_payload(
        file_path="app.py",
        old_text=old,
        new_text=new,
    )

    print(payload["diff"])
    print(
        f"added={payload['added']}, "
        f"removed={payload['removed']}, "
        f"changed={payload['changed']}"
    )