from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class VSCodeLauncher:
    """
    VS Code の起動と実行結果の管理を行うクラス。
    - 通常ファイルオープン (`code --reuse-window -g <file>:<line>`)
    - 1部分修正後の Diff 比較オープン (`code --reuse-window --diff <backup> <target>`)
    - アプリ開発時のプロジェクトフォルダオープン (`code --reuse-window <folder>`)
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()

    @staticmethod
    def resolve_code_binary() -> Optional[str]:
        return shutil.which("code") or shutil.which("code.cmd") or shutil.which("code-insiders")

    def open_file(
        self,
        relative_or_abs_path: Path | str,
        line: int = 1,
        column: int = 1,
    ) -> Dict[str, Any]:
        code_bin = self.resolve_code_binary()
        target = self._resolve_target(relative_or_abs_path)

        if not code_bin:
            return {
                "launched": False,
                "mode": "goto",
                "reason": "VS Code CLI ('code') が PATH に見つかりません。",
                "target": str(target),
                "command": f"code --reuse-window -g {target}:{line}:{column}",
            }

        cmd = [code_bin, "--reuse-window", "-g", f"{target}:{max(1, line)}:{max(1, column)}"]
        return self._spawn(cmd, mode="goto", target=str(target), line=line)

    def open_diff(
        self,
        before_path: Path | str,
        after_path: Path | str,
    ) -> Dict[str, Any]:
        code_bin = self.resolve_code_binary()
        before_abs = self._resolve_target(before_path)
        after_abs = self._resolve_target(after_path)

        if not code_bin:
            return {
                "launched": False,
                "mode": "diff",
                "reason": "VS Code CLI ('code') が PATH に見つかりません。",
                "target": str(after_abs),
                "command": f'code --reuse-window --diff "{before_abs}" "{after_abs}"',
            }

        cmd = [code_bin, "--reuse-window", "--diff", str(before_abs), str(after_abs)]
        return self._spawn(cmd, mode="diff", target=str(after_abs))

    def open_workspace_folder(self, folder_path: Optional[Path | str] = None) -> Dict[str, Any]:
        code_bin = self.resolve_code_binary()
        target_dir = self._resolve_target(folder_path) if folder_path else self.base_dir

        if not code_bin:
            return {
                "launched": False,
                "mode": "folder",
                "reason": "VS Code CLI ('code') が PATH に見つかりません。",
                "target": str(target_dir),
            }

        cmd = [code_bin, "--reuse-window", str(target_dir)]
        return self._spawn(cmd, mode="folder", target=str(target_dir))

    def _resolve_target(self, path_val: Path | str) -> Path:
        p = Path(path_val)
        return p.resolve() if p.is_absolute() else (self.base_dir / p).resolve()

    def _spawn(self, cmd: list[str], *, mode: str, target: str, line: int = 1) -> Dict[str, Any]:
        try:
            subprocess.Popen(
                cmd,
                cwd=str(self.base_dir),
                shell=False,
            )
            return {
                "launched": True,
                "mode": mode,
                "target": target,
                "line": line,
                "command": " ".join(cmd),
            }
        except Exception as exc:
            return {
                "launched": False,
                "mode": mode,
                "reason": str(exc),
                "target": target,
                "command": " ".join(cmd),
            }