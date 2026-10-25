from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from api.services.manager.KnowledgeManager import KnowledgeManager
except ImportError:
    KnowledgeManager = None  # type: ignore[assignment,misc]

from .VSCodeIntentParser import VSCodeIntent

logger = logging.getLogger(__name__)


class VSCodeKnowledgeService:
    """
    KnowledgeManager による検索とカードの取得を担当するサービス。
    JSON ナレッジが未作成の環境でも即座に返せる組み込みカードと、
    コード解析・部分修正・アプリ開発時のコンテキストカード補完を備える。
    """

    BUILTIN_CARDS: List[Dict[str, Any]] = [
        {
            "id": "builtin_gcc_task",
            "category": "Tasks (C言語 / GCC)",
            "title": "GCCコンパイルとエラー検出 (.vscode/tasks.json)",
            "shortcut_win": "Ctrl + Shift + B",
            "description": (
                "開いているCファイル(${file})をGCCでコンパイルし、出力されたwarning/errorを"
                "problemMatcherの正規表現で検出して「問題」パネルに表示します。"
            ),
            "trivia": "presentation.clear を true、showReuseMessage を false にすると、毎回綺麗なターミナルで結果だけを確認できます。",
        },
        {
            "id": "builtin_autodetect_off",
            "category": "Settings (高速化)",
            "title": "不要なタスク自動検出のOFF (.vscode/settings.json)",
            "shortcut_win": "Ctrl + ,",
            "description": "typescript.tsc / grunt / gulp / npm の autoDetect を off にしてタスク一覧のノイズを消します。",
            "trivia": "runOptions.runOn を 'folderOpen' に設定すると、フォルダを開いた瞬間にタスクを自動実行させることも可能です。",
        },
        {
            "id": "builtin_surgical_patch_workflow",
            "category": "Workflow (1部分修正 & Diff)",
            "title": "ピンポイント部分修正と VS Code Diff 確認",
            "shortcut_win": "code --diff <backup> <target>",
            "description": "ファイル全体を上書きせず対象関数・行範囲のみをパッチ適用し、バックアップとの差分を VS Code で即座に比較します。",
            "trivia": "問題があれば『元に戻して（ロールバック）』と指示するだけでバックアップから即時復元できます。",
        },
    ]

    def __init__(
        self,
        base_dir: Path,
        knowledge_manager: Optional[Any] = None,
        knowledge_dir: str = "tools/VScode/knowledge",
    ) -> None:
        self.base_dir = base_dir.resolve()
        self.target_k_dir = self.base_dir / knowledge_dir
        try:
            self.target_k_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if knowledge_manager is not None:
            self.km = knowledge_manager
        elif KnowledgeManager is not None:
            try:
                self.km = KnowledgeManager(
                    base_dir=self.base_dir,
                    knowledge_dirs=[self.target_k_dir],
                    threshold=1.0,
                    top_k=5,
                    cache_enabled=True,
                )
            except Exception as exc:
                logger.debug("KnowledgeManager init skipped: %s", exc)
                self.km = None
        else:
            self.km = None

    def search_cards(
        self,
        message: str,
        signals: Optional[Dict[str, Any]] = None,
        intent: Optional[VSCodeIntent] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        cards: List[Dict[str, Any]] = []
        files_to_write: List[Dict[str, Any]] = []
        matched_paths: List[str] = []

        if self.km is not None:
            try:
                resolved = self.km.resolve(
                    message=message,
                    intent_analysis=signals or {},
                    top_k=5,
                    threshold=1.0,
                )
                matched_paths = list(getattr(resolved, "matched_paths", []) or [])
                for doc in getattr(resolved, "items", []) or []:
                    if not isinstance(doc, dict):
                        continue
                    for item in doc.get("items", [doc]):
                        if isinstance(item, dict):
                            cards.append(item)
                            if isinstance(item.get("workspace_files"), list):
                                files_to_write.extend(item["workspace_files"])
            except Exception as exc:
                logger.debug("Knowledge resolve skipped: %s", exc)

        if intent and intent.mode == "code_analysis":
            cards.insert(
                0,
                {
                    "id": "vscode_package_architecture",
                    "category": "Architecture (VSCode Package)",
                    "title": "VSCode モジュラーパッケージ構成 (7クラス分離)",
                    "shortcut_win": "N/A",
                    "description": (
                        "VSCodeIntentParser / VSCodeKnowledgeService / VSCodeTaskBuilder / "
                        "WorkspaceFileService / VSCodeLauncher / VSCodeResponseBuilder / VSCodeHandler"
                    ),
                    "trivia": "アプリ開発や1部分修正は ProjectBuilderHandler とシームレスに連携します。",
                },
            )

        if not cards:
            cards = list(self.BUILTIN_CARDS)

        return cards, files_to_write, matched_paths