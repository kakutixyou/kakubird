from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


from api.services.handlers.base_handler import BaseHandler


try:
    from api.services.handlers.ChatHandler.request_utils import (
        extract_message,
        extract_signals,
    )
except ImportError:
    def extract_message(request: Any) -> str:
        if isinstance(request, str):
            return request
        if isinstance(request, dict):
            return str(request.get("message") or request.get("text") or "")
        return str(getattr(request, "message", "") or "")

    def extract_signals(request: Any) -> Dict[str, Any]:
        if isinstance(request, dict):
            return dict(request.get("current_signals") or request.get("signals") or {})
        return dict(getattr(request, "current_signals", None) or getattr(request, "signals", None) or {})

from .VSCodeIntentParser import VSCodeIntent, VSCodeIntentParser
from .VSCodeKnowledgeService import VSCodeKnowledgeService
from .VSCodeLauncher import VSCodeLauncher
from .VSCodeResponseBuilder import VSCodeResponseBuilder
from .VSCodeTaskBuilder import VSCodeTaskBuilder
from .VSCodeWorkspaceInspector import VSCodeWorkspaceInspector
from .WorkspaceFileService import WorkspaceFileService

logger = logging.getLogger(__name__)


class VSCodeHandler(BaseHandler):
    """
    意図判定・処理の調整・共通レスポンスへの変換を担うオーケストレーター。
    - タスク生成 (.vscode/tasks.json)・設定注入・ショートカットナレッジ検索を処理
    - VSCodeWorkspaceInspector によるワークスペース状態確認・直近編集ファイル自動補完・構文診断を実行
    - 将来的な「アプリ開発」「一部コードの修正（Surgical Partial Patch）」「コード解析」は
      ProjectBuilderHandler とシームレスに連携・委譲できるよう設計
    """

    HANDLER_NAME = "VSCodeHandler"

    def __init__(
        self,
        knowledge_manager: Optional[Any] = None,
        project_builder_handler: Optional[Any] = None,
        knowledge_dir: str = "tools/VScode/knowledge",
        base_dir: Optional[Path] = None,
        enable_debug: bool = True,
    ) -> None:
        super().__init__()
        self.enable_debug = enable_debug
        self.project_builder_handler = project_builder_handler

        # VSCode/VSCodeHandler.py から見て To/backend を解決
        resolved_base = base_dir or self._resolve_base_dir()
        self.base_dir = resolved_base

        self.knowledge_service = VSCodeKnowledgeService(
            base_dir=resolved_base,
            knowledge_manager=knowledge_manager,
            knowledge_dir=knowledge_dir,
        )
        self.file_service = WorkspaceFileService(
            base_dir=resolved_base,
            knowledge_manager=self.knowledge_service.km,
        )
        self.launcher = VSCodeLauncher(base_dir=resolved_base)
        self.inspector = VSCodeWorkspaceInspector(base_dir=resolved_base)

    @staticmethod
    def _resolve_base_dir() -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if parent.name == "backend" or (parent / "api").is_dir():
                return parent
        return current.parents[3] if len(current.parents) > 3 else Path.cwd()

    def _debug(self, msg: str) -> None:
        if self.enable_debug:
            print(f"💻 [{self.HANDLER_NAME}] {msg}", flush=True)

    async def calculate_score(
        self,
        message: str,
        current_signals: Optional[dict] = None,
    ) -> int:
        if not getattr(self, "enabled", True):
            return 0

        signals = current_signals or {}
        routing = signals.get("routing") or {}

        intent = VSCodeIntentParser.parse(message, signals)

        # ★ コード解析要求（「VSCodeHandler.pyを解析して」等）、一般会話（「VSCodeについて教えて」）、
        # またはアプリ開発要求は VSCodeHandler が奪わずスコア 0 を返して LLM / ProjectBuilderHandler に譲る
        if (
            intent.should_pass_to_llm or intent.mode in ("code_analysis", "app_development")
        ) and signals.get("forced_handler") != self.HANDLER_NAME:
            self._debug(f"Yielding to LLM/ProjectBuilder (mode={intent.mode}) -> score=0")
            return 0

        if (
            signals.get("forced_handler") == self.HANDLER_NAME
            or signals.get("mode") in ("vscode", "vscode_assistant")
            or routing.get("is_vscode_tool") is True
            or intent.mode in ("task_build", "write_workspace", "vscode_action")
        ):
            return 100
        return 0

    def estimate_size(self, message: str) -> int:
        return 800

    async def handle(self, request: Any) -> Tuple[str, Any]:
        message = extract_message(request)
        signals = extract_signals(request)
        self._debug(f"handling message={message!r}")

        # 1. 意図解析
        intent: VSCodeIntent = VSCodeIntentParser.parse(message, signals)

        # ファイル名が省略されている場合、VSCodeWorkspaceInspector で直近編集/Git変更ファイルを推定補完
        if not intent.target_files and intent.mode in ("partial_patch", "vscode_action", "launch"):
            inferred = self.inspector.infer_active_file()
            if inferred:
                intent.target_files = [inferred]
                self._debug(f"Inferred active file from workspace: {inferred}")

        self._debug(
            f"intent: mode={intent.mode}, lang={intent.language}, "
            f"files={intent.target_files}, delegate_pb={intent.delegate_to_project_builder}"
        )

        # 2. 一部コード修正・アプリ開発・コード解析で ProjectBuilderHandler が接続されている場合は委譲
        if intent.delegate_to_project_builder and self.project_builder_handler is not None:
            self._debug(f"Delegating mode={intent.mode} to ProjectBuilderHandler")
            pb_result = await self.project_builder_handler.handle(request)
            if isinstance(pb_result, tuple) and len(pb_result) == 2:
                _, pb_meta = pb_result
                return str(pb_meta.get("message") or ""), pb_meta
            if isinstance(pb_result, dict):
                return str(pb_result.get("message") or ""), pb_result

        # 3. ワークスペース状態確認要求（「状態を確認」「診断」「インスペクト」等）の処理
        if any(k in message.lower() for k in ("状態", "確認", "診断", "inspect", "status", "差分")):
            inspect_report = self.inspector.inspect_all(
                include_cli_status=("status" in message.lower() or "ウィンドウ" in message),
                target_files=intent.target_files or None,
                run_diagnostics=True,
            )
            status_cards = self.inspector.build_status_cards(inspect_report)
            return VSCodeResponseBuilder.build(
                intent=intent,
                cards=status_cards,
                generated_task=None,
                written_report={"success": [], "failed": [], "skipped": []},
                matched_paths=[],
            )

        # 4. ロールバック要求の直接処理
        if intent.vscode_action == "vscode_rollback" and intent.target_files:
            rb_res = self.file_service.rollback_file(intent.target_files[0])
            cards = [
                {
                    "id": "rollback_result",
                    "category": "↩️ Rollback",
                    "title": rb_res.get("message", "ロールバック処理"),
                    "shortcut_win": "Ctrl + Z",
                    "description": f"対象ファイル: {intent.target_files[0]}",
                }
            ]
            written = {"success": [intent.target_files[0]] if rb_res.get("success") else [], "failed": [], "skipped": []}
            return VSCodeResponseBuilder.build(
                intent=intent,
                cards=cards,
                generated_task=None,
                written_report=written,
                matched_paths=[],
                error=None if rb_res.get("success") else rb_res.get("message"),
            )

        # 5. ナレッジ検索とカード取得
        cards, files_to_write, matched_paths = self.knowledge_service.search_cards(
            message=message,
            signals=signals,
            intent=intent,
        )

        # 6. 用途に応じた tasks.json の生成
        generated_task: Optional[Dict[str, Any]] = None
        if intent.mode in ("task_build", "write_workspace", "vscode_action"):
            generated_task = VSCodeTaskBuilder.build_task_from_intent(message, intent=intent)

        # 7. ワークスペースへの書き込みと VS Code 起動
        written_report: Dict[str, list[str]] = {"success": [], "failed": [], "skipped": []}
        launch_result: Optional[Dict[str, Any]] = None

        if intent.should_write:
            if not files_to_write and generated_task:
                files_to_write = [
                    {
                        "path": ".vscode/tasks.json",
                        "content": generated_task,
                    }
                ]
            written_report = self.file_service.write_files(
                files_to_write=files_to_write,
                allow_overwrite=intent.allow_overwrite,
            )

        if intent.should_launch:
            if written_report.get("success"):
                target_to_open = written_report["success"][0]
                launch_result = self.launcher.open_file(target_to_open, line=intent.start_line or 1)
            elif intent.target_files:
                launch_result = self.launcher.open_file(intent.target_files[0], line=intent.start_line or 1)

        # 8. 統一レスポンスへの変換
        embed_html = bool(signals.get("embed_vscode_payload", False))
        return VSCodeResponseBuilder.build(
            intent=intent,
            cards=cards,
            generated_task=generated_task,
            written_report=written_report,
            matched_paths=matched_paths,
            launch_result=launch_result,
            embed_html_payload=embed_html,
        )


class VSCodePreResponder:
    """
    ChatHandler の先頭に差し込む用 Responder。
    明確な VS Code タスク・設定操作のみを高速処理し、
    「VSCodeHandler.pyを解析して」「VSCodeについて教えて」「アプリを作って」「一部修正して」は
    横取りせず None を返して後続の LLM / ProjectBuilderHandler に渡す。
    """

    name = "VSCodePreResponder"

    EXPLICIT_TOOL_TRIGGER = (
        "tasks.json",
        "settings.json",
        "launch.json",
        "problemmatcher",
        "ショートカット",
        "マルチカーソル",
        "コマンドパレット",
    )

    def __init__(self, vscode_handler: Optional[VSCodeHandler] = None) -> None:
        self.handler = vscode_handler or VSCodeHandler()

    async def try_respond(self, ctx: Any) -> Optional[Tuple[str, Any]]:
        signals = getattr(ctx, "current_signals", {}) or {}
        routing = signals.get("routing") or {}
        analysis = getattr(ctx, "analysis", {}) or {}
        message = str(getattr(ctx, "message", ""))
        msg_lower = message.lower()

        intent = VSCodeIntentParser.parse(message, signals)
        if (
            intent.should_pass_to_llm
            or intent.delegate_to_project_builder
            or intent.mode in ("code_analysis", "app_development", "partial_patch")
        ) and signals.get("forced_handler") != "VSCodeHandler":
            return None

        is_vscode_tool = (
            signals.get("forced_handler") == "VSCodeHandler"
            or routing.get("is_vscode_tool") is True
            or analysis.get("mode") in ("vscode_tool", "vscode_task")
            or intent.mode in ("task_build", "write_workspace", "vscode_action")
            or any(kw in msg_lower for kw in self.EXPLICIT_TOOL_TRIGGER)
        )
        if not is_vscode_tool:
            return None

        return await self.handler.handle(ctx.request)