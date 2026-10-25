from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkspaceFileService:
    """
    パス検証・書き込み・上書き制御・バックアップ/ロールバックを担うサービス。
    将来的なアプリ開発（複数ファイル生成）や一部コード修正時の非破壊バックアップに対応する。
    """

    ALLOWED_EXTENSIONS = {
        ".json",
        ".code-workspace",
        ".md",
        ".txt",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".css",
        ".html",
        ".yaml",
        ".yml",
    }

    def __init__(
        self,
        base_dir: Path,
        knowledge_manager: Optional[Any] = None,
        backup_dir_name: str = ".vscode/.ai_backups",
    ) -> None:
        self.base_dir = base_dir.resolve()
        self.km = knowledge_manager
        self.backup_root = (self.base_dir / backup_dir_name).resolve()

    def validate_safe_path(self, relative_path: str) -> Optional[Path]:
        """ワークスペース外へのパストラバーサル（../ 等）と不正拡張子を防止する。"""
        if not relative_path:
            return None
        clean_rel = relative_path.strip().replace("\\", "/")
        if ".." in Path(clean_rel).parts:
            return None

        candidate = (self.base_dir / clean_rel).resolve()
        try:
            candidate.relative_to(self.base_dir)
        except ValueError:
            return None

        if candidate.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            return None
        return candidate

    def create_backup(self, target_file: Path) -> Optional[Path]:
        """既存ファイルを書き換える前にタイムスタンプ付きバックアップを作成する。"""
        if not target_file.exists():
            return None
        try:
            self.backup_root.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{target_file.stem}.{timestamp}{target_file.suffix}.bak"
            backup_path = self.backup_root / backup_name
            shutil.copy2(target_file, backup_path)
            return backup_path
        except Exception as exc:
            logger.warning("Backup creation failed for %s: %s", target_file, exc)
            return None

    def rollback_file(self, relative_path: str, backup_file_path: Optional[str] = None) -> Dict[str, Any]:
        """バックアップから対象ファイルを復元する。"""
        target = self.validate_safe_path(relative_path)
        if target is None:
            return {"success": False, "message": f"不正なファイルパスです: {relative_path}"}

        backup_candidate: Optional[Path] = None
        if backup_file_path:
            bp = Path(backup_file_path).resolve()
            if bp.exists():
                backup_candidate = bp
        elif self.backup_root.exists():
            matches = sorted(
                self.backup_root.glob(f"{target.stem}.*{target.suffix}.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if matches:
                backup_candidate = matches[0]

        if backup_candidate is None or not backup_candidate.exists():
            return {"success": False, "message": f"{relative_path} の復元用バックアップが見つかりません。"}

        try:
            shutil.copy2(backup_candidate, target)
            return {
                "success": True,
                "file_path": relative_path,
                "backup_used": str(backup_candidate),
                "message": f"{relative_path} をバックアップ ({backup_candidate.name}) から復元しました。",
            }
        except Exception as exc:
            return {"success": False, "message": f"復元中にエラーが発生しました: {exc}"}

    def write_files(
        self,
        files_to_write: List[Dict[str, Any]],
        allow_overwrite: bool = True,
        create_backups: bool = True,
    ) -> Dict[str, List[str]]:
        report: Dict[str, List[str]] = {
            "success": [],
            "failed": [],
            "skipped": [],
            "backups": [],
        }

        for item in files_to_write:
            rel_path = str(item.get("path") or "").strip()
            content = item.get("content", "")
            target = self.validate_safe_path(rel_path)

            if target is None:
                report["failed"].append(f"{rel_path} (不正なパスまたは許可されていない拡張子)")
                continue

            if target.exists() and not allow_overwrite:
                report["skipped"].append(f"{rel_path} (既存ファイル保護のためスキップ)")
                continue

            try:
                if target.exists() and create_backups:
                    bak = self.create_backup(target)
                    if bak:
                        report["backups"].append(str(bak))

                target.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, (dict, list)):
                    text_content = json.dumps(content, indent=2, ensure_ascii=False)
                else:
                    text_content = str(content)
                target.write_text(text_content, encoding="utf-8")
                report["success"].append(rel_path)
            except Exception as exc:
                logger.warning("Failed to write %s: %s", rel_path, exc)
                report["failed"].append(f"{rel_path} ({exc})")

        return report