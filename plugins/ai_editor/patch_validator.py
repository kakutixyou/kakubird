from __future__ import annotations

"""
patch_validator.py

AI が生成した変更案 (diff/new_content) を安全に適用できるか検証する。

主なチェック:
- 変更が存在するか
- 対象パスが許可されているか
- 危険なパス (.git, node_modules など) ではないか
- 削除行数・追加行数が上限を超えていないか
- Python ファイルの場合、構文エラーがないか
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import ast

from .diff_generator import (
    count_changes,
    has_changes,
)


# ---------------------------------------------------------
# Data Models
# ---------------------------------------------------------

@dataclass(slots=True)
class ValidationResult:
    """
    検証結果。
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    added: int = 0
    removed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------
# Service
# ---------------------------------------------------------

class PatchValidator:
    """
    パッチ検証サービス。
    """

    DEFAULT_BLOCKED_PARTS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
    }

    def __init__(
        self,
        *,
        max_added_lines: int = 5000,
        max_removed_lines: int = 5000,
        blocked_path_parts: set[str] | None = None,
        allowed_roots: list[str | Path] | None = None,
    ) -> None:
        self.max_added_lines = max_added_lines
        self.max_removed_lines = max_removed_lines
        self.blocked_path_parts = (
            blocked_path_parts or self.DEFAULT_BLOCKED_PARTS
        )
        self.allowed_roots = (
            [Path(p).resolve() for p in allowed_roots]
            if allowed_roots
            else None
        )

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def validate(
        self,
        *,
        file_path: str | Path,
        diff_text: str,
        new_content: str,
    ) -> ValidationResult:
        """
        パッチを検証する。
        """
        result = ValidationResult(valid=True)

        path = Path(file_path)

        # 変更有無
        if not has_changes(diff_text):
            result.valid = False
            result.errors.append("変更がありません。")
            return result

        # 行数集計
        added, removed = count_changes(diff_text)
        result.added = added
        result.removed = removed

        # 上限チェック
        if added > self.max_added_lines:
            result.valid = False
            result.errors.append(
                f"追加行数が上限を超えています: "
                f"{added} > {self.max_added_lines}"
            )

        if removed > self.max_removed_lines:
            result.valid = False
            result.errors.append(
                f"削除行数が上限を超えています: "
                f"{removed} > {self.max_removed_lines}"
            )

        # パス検証
        self._validate_path(path, result)

        # Python 構文チェック
        if path.suffix == ".py":
            self._validate_python_syntax(new_content, result)

        # 空ファイル警告
        if not new_content.strip():
            result.warnings.append("新しいファイル内容が空です。")

        return result

    # -----------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------

    def _validate_path(
        self,
        path: Path,
        result: ValidationResult,
    ) -> None:
        """
        対象パスの安全性を検証する。
        """
        # 禁止ディレクトリ
        for part in path.parts:
            if part in self.blocked_path_parts:
                result.valid = False
                result.errors.append(
                    f"禁止されたパスです: {path}"
                )
                return

        # 許可ルート
        if self.allowed_roots:
            try:
                resolved = path.resolve()
            except Exception:
                result.valid = False
                result.errors.append(
                    f"パス解決に失敗しました: {path}"
                )
                return

            if not any(
                str(resolved).startswith(str(root))
                for root in self.allowed_roots
            ):
                result.valid = False
                result.errors.append(
                    f"許可されたディレクトリ外です: {path}"
                )

    def _validate_python_syntax(
        self,
        source: str,
        result: ValidationResult,
    ) -> None:
        """
        Python の構文チェック。
        """
        try:
            ast.parse(source)
        except SyntaxError as e:
            result.valid = False
            result.errors.append(
                f"Python構文エラー: line {e.lineno}: {e.msg}"
            )


# ---------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------

def validate_patch(
    *,
    file_path: str | Path,
    diff_text: str,
    new_content: str,
) -> dict[str, Any]:
    """
    辞書形式で検証結果を返す。
    """
    validator = PatchValidator()
    result = validator.validate(
        file_path=file_path,
        diff_text=diff_text,
        new_content=new_content,
    )
    return result.to_dict()


# ---------------------------------------------------------
# Example Usage
# ---------------------------------------------------------

if __name__ == "__main__":
    diff_text = """--- a/test.py
+++ b/test.py
@@ -1 +1 @@
-print("hello")
+print("Hello")
"""

    new_content = 'print("Hello")\n'

    validator = PatchValidator(
        allowed_roots=["."]
    )

    result = validator.validate(
        file_path="test.py",
        diff_text=diff_text,
        new_content=new_content,
    )

    print(result.to_dict())