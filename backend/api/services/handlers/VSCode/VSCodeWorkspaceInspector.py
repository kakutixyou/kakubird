# Vscodeworkspaceinspector
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FileDiagnosticsResult:
    """単一ファイルの構文・型チェック（VS Code Problems パネル相当）結果。"""

    file: str
    language: str
    checked: bool
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VSCodeWorkspaceInspector:
    """
    VS Code 側（CLI・ワークスペース設定・Git未コミット差分・直近編集ファイル・
    バックアップ履歴・静的診断チェック）から現在の状態を検査・取得するクラス。

    主な用途:
    1. ユーザーがファイル名を省略して「今開いているファイルを一部修正して」と言った際の対象ファイル推定
    2. `ProjectBuilderHandler` による1部分修正（Surgical Patch）や機能追加後の構文エラー自動検証
    3. `.vscode/tasks.json` や `settings.json` の現在の設定内容と導入済み拡張機能の整合性チェック
    4. フロントエンドの `VSCodeBlock` に表示するワークスペース診断カード（ステータスカード）の生成
    """

    SOURCE_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".c": "cpp",
        ".cpp": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".json": "json",
    }

    IGNORE_DIRS = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".ai_backups",
        "generated_zips",
    }

    def __init__(
        self,
        base_dir: Path,
        backup_dir_name: str = ".vscode/.ai_backups",
    ) -> None:
        self.base_dir = base_dir.resolve()
        self.backup_root = (self.base_dir / backup_dir_name).resolve()

    @staticmethod
    def resolve_code_binary() -> Optional[str]:
        return (
            shutil.which("code")
            or shutil.which("code.cmd")
            or shutil.which("code-insiders")
        )

    # ==================================================================
    # 1. 一括インスペクション & UIカード変換
    # ==================================================================

    def inspect_all(
        self,
        *,
        include_cli_status: bool = False,
        include_extensions: bool = False,
        target_files: Optional[List[str]] = None,
        run_diagnostics: bool = True,
    ) -> Dict[str, Any]:
        """VS Code とワークスペースの状態を一括診断して辞書で返す。"""
        recent = self.get_recently_modified_files(limit=8)
        git_info = self.get_git_working_status()

        # 診断対象ファイルの決定（指定がなければ直近編集ファイル上位3件）
        files_to_check = list(target_files or [])
        if not files_to_check:
            files_to_check = [item["path"] for item in recent[:3]]

        diagnostics: List[Dict[str, Any]] = []
        if run_diagnostics:
            for rel_path in files_to_check[:5]:
                diag = self.run_quick_diagnostics(rel_path)
                diagnostics.append(diag.to_dict())

        return {
            "base_dir": str(self.base_dir),
            "cli_available": self.resolve_code_binary() is not None,
            "active_candidate_file": self.infer_active_file(
                explicit_files=target_files,
                git_status=git_info,
                recent_files=recent,
            ),
            "workspace_config": self.get_workspace_config_status(),
            "git_status": git_info,
            "recent_files": recent,
            "backups": self.get_available_backups(target_files=target_files),
            "diagnostics": diagnostics,
            "vscode_status": self.get_vscode_cli_status() if include_cli_status else None,
            "installed_extensions": (
                self.get_installed_extensions() if include_extensions else None
            ),
        }

    def build_status_cards(
        self,
        report: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """`inspect_all()` の結果を `VSCodeBlock` 表示用のカードリストに変換する。"""
        data = report or self.inspect_all(run_diagnostics=True)
        cards: List[Dict[str, Any]] = []

        # 1) アクティブ推定ファイル & Git変更状況カード
        active_file = data.get("active_candidate_file") or "未検出"
        git_mod = data.get("git_status", {}).get("modified_files", [])
        cards.append(
            {
                "id": "inspector_active_context",
                "category": "🔍 Workspace Inspector (作業コンテキスト)",
                "title": f"推定アクティブファイル: {active_file}",
                "shortcut_win": "Ctrl + P",
                "description": (
                    f"未コミット変更: {len(git_mod)}件 "
                    f"({', '.join(git_mod[:4]) if git_mod else '変更なし'})"
                ),
                "trivia": "ファイル名を省略して『この関数だけ修正して』と指示した場合、このアクティブ候補が優先されます。",
            }
        )

        # 2) .vscode 設定ファイル状態カード
        ws_files = data.get("workspace_config", {}).get("files", {})
        existing_configs = [k for k, v in ws_files.items() if v.get("exists")]
        cards.append(
            {
                "id": "inspector_vscode_configs",
                "category": "⚙️ .vscode Configuration",
                "title": (
                    f"検出された設定: {', '.join(existing_configs)}"
                    if existing_configs
                    else ".vscode 設定ファイルはまだ作成されていません"
                ),
                "shortcut_win": "Ctrl + Shift + P",
                "description": "tasks.json / settings.json / launch.json の有無とタスク定義数を監視しています。",
                "trivia": "『tasks.jsonを書き込んで』と指示すると、現在の言語に合わせた設定を自動注入します。",
            }
        )

        # 3) 構文・診断チェック (Problems 相当) カード
        diags = data.get("diagnostics") or []
        failed_diags = [d for d in diags if d.get("checked") and not d.get("passed")]
        if failed_diags:
            first_err = failed_diags[0]
            err_msg = "; ".join(first_err.get("errors", [])[:2])
            cards.append(
                {
                    "id": "inspector_diagnostics_error",
                    "category": "⚠️ Problems / Diagnostics",
                    "title": f"{len(failed_diags)}件のファイルで構文エラーを検出 ({first_err.get('file')})",
                    "shortcut_win": "Ctrl + Shift + M",
                    "description": err_msg or "構文チェックに失敗しました。",
                    "trivia": "『エラー箇所だけ部分修正して』と送ると ProjectBuilderHandler がピンポイント修復します。",
                }
            )
        elif diags:
            cards.append(
                {
                    "id": "inspector_diagnostics_ok",
                    "category": "✅ Problems / Diagnostics",
                    "title": f"直近ファイル {len(diags)}件の構文チェック OK",
                    "shortcut_win": "Ctrl + Shift + M",
                    "description": "対象ファイルに構文エラーは検出されませんでした。",
                    "trivia": "1部分修正（Surgical Patch）適用後も自動でこの診断が走ります。",
                }
            )

        # 4) バックアップ履歴カード
        backups = data.get("backups") or []
        if backups:
            cards.append(
                {
                    "id": "inspector_backups",
                    "category": "🛡️ Safety Backups (.vscode/.ai_backups)",
                    "title": f"復元可能なバックアップ: {len(backups)}件 (最新: {backups[0].get('backup_name')})",
                    "shortcut_win": "code --diff",
                    "description": "『元に戻して（ロールバック）』と指示すると直前の状態へ即座に復元できます。",
                }
            )

        return cards

    # ==================================================================
    # 2. アクティブファイル推定（ファイル名省略時の補完用）
    # ==================================================================

    def infer_active_file(
        self,
        *,
        explicit_files: Optional[List[str]] = None,
        git_status: Optional[Dict[str, Any]] = None,
        recent_files: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        ユーザーが「今開いているファイルを一部修正して」のようにファイル名を省略した際、
        1) 明示指定ファイル -> 2) Git変更中の最新ファイル -> 3) ワークスペース内の直近更新ファイル
        の優先順位で対象ファイルを特定する。
        """
        if explicit_files:
            for f in explicit_files:
                if (self.base_dir / f).is_file():
                    return f
            return explicit_files[0]

        git_info = git_status or self.get_git_working_status()
        modified = git_info.get("modified_files") or []
        if modified:
            # 変更ファイルの中で最も更新日時が新しいものを返す
            best_file = None
            best_mtime = -1.0
            for rel in modified:
                p = self.base_dir / rel
                if p.is_file() and p.suffix.lower() in self.SOURCE_EXTENSIONS:
                    try:
                        mt = p.stat().st_mtime
                        if mt > best_mtime:
                            best_mtime = mt
                            best_file = rel
                    except OSError:
                        continue
            if best_file:
                return best_file

        recent = recent_files or self.get_recently_modified_files(limit=3)
        if recent:
            return str(recent[0].get("path") or "")
        return None

    # ==================================================================
    # 3. VS Code CLI / 拡張機能 / .vscode 設定確認
    # ==================================================================

    def get_vscode_cli_status(self, timeout: float = 4.0) -> Dict[str, Any]:
        """`code --status` を実行し、開いているウィンドウ・フォルダ情報を取得する。"""
        code_bin = self.resolve_code_binary()
        if not code_bin:
            return {"available": False, "reason": "VS Code CLI ('code') が PATH に見つかりません。"}

        try:
            proc = subprocess.run(
                [code_bin, "--status"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            raw = (proc.stdout or "").strip()
            open_windows = [
                line.strip()
                for line in raw.splitlines()
                if "|" in line or "Window (" in line or "Folder (" in line
            ]
            return {
                "available": True,
                "returncode": proc.returncode,
                "open_windows": open_windows[:15],
                "raw_excerpt": raw[:1000],
            }
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    def get_installed_extensions(self, timeout: float = 4.0) -> List[str]:
        """`code --list-extensions` で導入済み拡張機能一覧を取得する。"""
        code_bin = self.resolve_code_binary()
        if not code_bin:
            return []
        try:
            proc = subprocess.run(
                [code_bin, "--list-extensions"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        except Exception:
            return []

    def get_workspace_config_status(self) -> Dict[str, Any]:
        """`.vscode/` 内の tasks.json / settings.json / launch.json の有無とタスク定義数を確認する。"""
        vscode_dir = self.base_dir / ".vscode"
        result: Dict[str, Any] = {
            "vscode_dir_exists": vscode_dir.is_dir(),
            "files": {},
            "defined_task_labels": [],
        }
        for name in ("tasks.json", "settings.json", "launch.json", "extensions.json"):
            f = vscode_dir / name
            if f.is_file():
                info: Dict[str, Any] = {"exists": True, "size_bytes": f.stat().st_size}
                if name == "tasks.json":
                    try:
                        parsed = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                        tasks = parsed.get("tasks") if isinstance(parsed, dict) else []
                        if isinstance(tasks, list):
                            labels = [
                                str(t.get("label"))
                                for t in tasks
                                if isinstance(t, dict) and t.get("label")
                            ]
                            info["task_count"] = len(labels)
                            result["defined_task_labels"] = labels
                    except Exception:
                        info["task_count"] = 0
                result["files"][name] = info
            else:
                result["files"][name] = {"exists": False, "size_bytes": 0}
        return result

    # ==================================================================
    # 4. Git差分 / 直近編集ファイル / バックアップ一覧
    # ==================================================================

    def get_git_working_status(self, timeout: float = 3.0) -> Dict[str, Any]:
        """VS Code で編集中の未コミット変更ファイル（`git status --porcelain`）を取得する。"""
        git_bin = shutil.which("git")
        if not git_bin:
            return {"modified_files": [], "untracked_files": []}

        try:
            proc = subprocess.run(
                [git_bin, "status", "--porcelain"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            modified: List[str] = []
            untracked: List[str] = []
            for line in (proc.stdout or "").splitlines():
                if len(line) < 4:
                    continue
                status_code = line[:2]
                rel_path = line[3:].strip().strip('"')
                if "?" in status_code:
                    untracked.append(rel_path)
                else:
                    modified.append(rel_path)
            return {
                "modified_files": modified[:25],
                "untracked_files": untracked[:25],
            }
        except Exception:
            return {"modified_files": [], "untracked_files": []}

    def get_recently_modified_files(self, limit: int = 8) -> List[Dict[str, Any]]:
        """ワークスペース内で直近更新されたソースファイルを新しい順に取得する。"""
        candidates: List[tuple[float, Path]] = []
        try:
            for root, dirs, files in os.walk(self.base_dir):
                dirs[:] = [
                    d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".git")
                ]
                root_path = Path(root)
                for fname in files:
                    fpath = root_path / fname
                    if fpath.suffix.lower() in self.SOURCE_EXTENSIONS:
                        try:
                            candidates.append((fpath.stat().st_mtime, fpath))
                        except OSError:
                            continue
        except Exception:
            pass

        candidates.sort(key=lambda item: item[0], reverse=True)
        result: List[Dict[str, Any]] = []
        for mtime, fpath in candidates[:limit]:
            try:
                rel = str(fpath.relative_to(self.base_dir)).replace("\\", "/")
            except ValueError:
                rel = str(fpath)
            result.append(
                {
                    "path": rel,
                    "language": self.SOURCE_EXTENSIONS.get(fpath.suffix.lower(), "general"),
                    "mtime": round(mtime, 2),
                }
            )
        return result

    def get_available_backups(
        self,
        target_files: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """`.vscode/.ai_backups/` 内の復元可能バックアップ一覧を新しい順に返す。"""
        if not self.backup_root.is_dir():
            return []

        backups = sorted(
            self.backup_root.glob("*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        target_stems = {Path(f).stem for f in (target_files or [])}
        items: List[Dict[str, str]] = []

        for b in backups[:15]:
            if target_stems and not any(b.name.startswith(stem + ".") for stem in target_stems):
                continue
            items.append(
                {
                    "backup_name": b.name,
                    "backup_path": str(b),
                }
            )
        return items

    # ==================================================================
    # 5. Problems パネル相当の高速構文・診断チェック
    # ==================================================================

    def run_quick_diagnostics(
        self,
        relative_path: str,
        timeout: float = 5.0,
    ) -> FileDiagnosticsResult:
        """
        指定されたファイルに対して軽量な構文チェックを実行し、エラー有無を返す。
        - Python (`.py`): `python -m py_compile`
        - JSON (`.json`): `json.loads`
        - C/C++ (`.c`, `.cpp`): `gcc -fsyntax-only`
        """
        clean_rel = relative_path.strip().replace("\\", "/")
        target = (self.base_dir / clean_rel).resolve()
        ext = target.suffix.lower()
        lang = self.SOURCE_EXTENSIONS.get(ext, "general")

        if not target.is_file():
            return FileDiagnosticsResult(
                file=clean_rel,
                language=lang,
                checked=False,
                passed=False,
                errors=[f"ファイルが存在しません: {clean_rel}"],
            )

        # JSON の構文チェック
        if ext == ".json":
            try:
                json.loads(target.read_text(encoding="utf-8"))
                return FileDiagnosticsResult(
                    file=clean_rel,
                    language="json",
                    checked=True,
                    passed=True,
                    command="json.loads",
                )
            except Exception as exc:
                return FileDiagnosticsResult(
                    file=clean_rel,
                    language="json",
                    checked=True,
                    passed=False,
                    errors=[str(exc)],
                    command="json.loads",
                )

        cmd: Optional[List[str]] = None
        if ext == ".py":
            py_bin = shutil.which("python") or shutil.which("python3") or "python"
            cmd = [py_bin, "-m", "py_compile", str(target)]
        elif ext in {".c", ".cpp"} and shutil.which("gcc"):
            cmd = ["gcc", "-fsyntax-only", "-Wall", str(target)]

        if not cmd:
            return FileDiagnosticsResult(
                file=clean_rel,
                language=lang,
                checked=False,
                passed=True,
            )

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            output = (proc.stderr or proc.stdout or "").strip()
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            passed = proc.returncode == 0
            return FileDiagnosticsResult(
                file=clean_rel,
                language=lang,
                checked=True,
                passed=passed,
                errors=[] if passed else lines,
                warnings=lines if passed and lines else [],
                command=" ".join(cmd),
            )
        except Exception as exc:
            return FileDiagnosticsResult(
                file=clean_rel,
                language=lang,
                checked=False,
                passed=False,
                errors=[str(exc)],
                command=" ".join(cmd),
            )