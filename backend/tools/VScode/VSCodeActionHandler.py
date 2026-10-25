# tools/VSCodeActionHandler.py
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VSCodeActionHandler:
    """
    KnowledgeManagerが引き当てたVS Code知識を表示するだけでなく、
    最適な `code` CLIコマンドや設定ファイル生成を直接代行するハンドラー。
    """

    # セキュリティのため、自動実行を許可するVS Code CLIサブコマンドを限定
    ALLOWED_ARGS = {
        "--install-extension",
        "--uninstall-extension",
        "--list-extensions",
        "--diff",
        "--goto",
        "--new-window",
        "--reuse-window",
        "--status",
        "--version",
    }

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        # OS環境から `code` コマンドのパスを自動検出
        self.code_bin = shutil.which("code") or "code"

    def handle(
        self,
        resolved_items: list[dict[str, Any]],
        auto_execute: bool = False,
    ) -> dict[str, Any]:
        """
        KnowledgeManager.resolve().items を受け取り、UI表示用データと実行結果を返す。
        """
        cards: list[dict[str, Any]] = []
        executed_logs: list[str] = []

        for doc in resolved_items:
            items = doc.get("items", [doc]) if isinstance(doc, dict) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                cards.append(item)

                # 自動実行フラグがONかつ、アイテムにCLIコマンドが定義されている場合
                cli_args = item.get("cli_args")
                if auto_execute and isinstance(cli_args, list) and cli_args:
                    res = self.run_code_cli(cli_args)
                    executed_logs.append(res["message"])

        return {
            "status": "success",
            "template": "tools/HTML/vscode_assistant.html",
            "cards": cards,
            "executed_logs": executed_logs,
        }

    def run_code_cli(self, args: list[str]) -> dict[str, Any]:
        """
        VS Codeの `code` コマンドを安全に非同期・高速実行する。
        例: args = ["--install-extension", "MS-CEINTL.vscode-language-pack-ja"]
        """
        if not args or args[0] not in self.ALLOWED_ARGS:
            return {
                "status": "blocked",
                "message": f"許可されていないオプションです: {args}",
            }

        cmd = [self.code_bin, *args]
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=15,
                shell=(shutil.which("code") is None),  # WindowsのPATH対策
            )
            if completed.returncode == 0:
                return {
                    "status": "success",
                    "command": " ".join(cmd),
                    "output": completed.stdout.strip(),
                    "message": f"実行完了: {' '.join(cmd)}",
                }
            return {
                "status": "error",
                "command": " ".join(cmd),
                "message": completed.stderr.strip() or "コマンド実行エラー",
            }
        except Exception as exc:
            logger.error("VS Code CLI実行失敗: %s", exc)
            return {"status": "error", "message": str(exc)}