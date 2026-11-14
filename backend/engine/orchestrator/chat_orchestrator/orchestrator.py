"""
backend/engine/orchestrator/chat_orchestrator/orchestrator.py

分割されたサブモジュール（handler_registry, signal_state_store, knowledge_pipeline, routing_dispatcher）を
束ねるスリムな ChatOrchestrator 本体。
"""
from __future__ import annotations

import asyncio
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

from engine.context.ContextManager import ContextManager
from engine.prompt.PromptBuilder import PromptBuilder
from engine.KnowledgeContextSelector import KnowledgeContextSelector
from engine.KnowledgeLoader import KnowledgeLoader
from engine.KnowledgeRouter import KnowledgeRouter
from engine.KnowledgeStartupAudit import KnowledgeStartupAudit
from engine.ProjectProgressAnalyzer import ProjectProgressAnalyzer
from engine.knowledge_health import KnowledgeHealthMonitor
from engine.orchestrator.base_orchestrator import BaseOrchestrator

from api.services.inspectors.IntentInSpector import IntentInspector
from api.services.manager.KnowledgeManager import KnowledgeManager

from .handler_registry import (
    OcrRecruitHandler,
    PROJECT_BUILDER_AVAILABLE,
    PROJECT_BUILDER_IMPORT_ERROR,
    ProjectBuilderHandler,
    build_default_handlers,
)
from .knowledge_pipeline import KnowledgePipelineMixin
from .routing_dispatcher import (
    attach_debug_block,
    build_routing_debug_block,
    is_offline_error_response,
    resolve_forced_handler_name,
    score_and_sort_handlers,
)
from .signal_state_store import SignalStateStore


RESET_COMMANDS = {
    "メモリ消去",
    "メモリ削除",
    "記憶リセット",
    "記憶消去",
    "履歴削除",
    "リセット",
    "/reset",
    "/clear",
}


class ChatOrchestrator(KnowledgePipelineMixin, BaseOrchestrator):
    """
    分割パッケージ化されたスリムなメインオーケストレーター。
    外部からの呼び出しインターフェースは旧 chat_orchestrator.py と100%同一。
    """

    def __init__(
        self,
        project_root=None,
        config=None,
        services=None,
    ) -> None:
        super().__init__(
            project_root=project_root,
            config=config,
            services=services,
        )

        self.context_manager = ContextManager()
        self.intent_inspector = None
        self.prompt_builder = PromptBuilder()

        self.last_used_handler = "Unknown"
        self.active_context = None

        # このファイルは backend/engine/orchestrator/chat_orchestrator/orchestrator.py
        # parents[3] がプロジェクトルート (To/)
        here = Path(__file__).resolve()
        discovered_root = here.parents[3] if len(here.parents) >= 4 else Path(os.getcwd()).resolve()
        if not (discovered_root / "backend").is_dir() and (here.parents[2] / "backend").is_dir():
            discovered_root = here.parents[2]

        self.project_root = discovered_root
        self.knowledge_dir = (
            self.project_root / "plugins" / "project_builder" / "knowledge"
        ).resolve()

        print(f"📚 [ChatOrchestrator] Knowledge検索先={self.knowledge_dir}")

        self.knowledge_router = None
        self.knowledge_loader = KnowledgeLoader(
            knowledge_dirs=[self.knowledge_dir],
            cache_enabled=True,
        )
        self.knowledge_selector = KnowledgeContextSelector(
            max_items=4,
            max_chars=8_000,
            min_score=1.0,
            fallback_items=1,
        )
        self.project_progress_analyzer = ProjectProgressAnalyzer(
            max_tasks=100,
            max_barriers=30,
            max_next_actions=5,
            in_progress_credit=0.5,
        )
        self.knowledge_health_monitor = KnowledgeHealthMonitor(
            strict=False,
            max_issues=50,
            inspect_empty_content=True,
        )
        self.knowledge_startup_auditor = KnowledgeStartupAudit(
            knowledge_roots=[self.knowledge_dir],
            max_files=1_000,
            max_file_bytes=32 * 1024 * 1024,
            require_markdown_frontmatter=True,
            strict=False,
            cache_path=(
                self.project_root
                / "backend"
                / ".ai_memory"
                / "knowledge_audit_cache.json"
            ),
            use_cache=True,
        )
        self.knowledge_reload_lock = asyncio.Lock()
        self._init_default_reports()

        try:
            if self.knowledge_dir.is_dir():
                self.knowledge_router = KnowledgeRouter(
                    knowledge_dir=self.knowledge_dir,
                    threshold=1.0,
                    top_k=5,
                )
                print(
                    f"📚 [ChatOrchestrator] 登録Knowledge数={len(self.knowledge_router.domains)}"
                )
            else:
                print(
                    f"⚠️ [ChatOrchestrator] Knowledgeフォルダが見つかりません: {self.knowledge_dir}"
                )
        except Exception as e:
            print(f"❌ [ChatOrchestrator] KnowledgeRouter初期化失敗: {e}")
            traceback.print_exc()
            self.knowledge_router = None

        self._run_knowledge_startup_audit()

        # Memory & SignalStateStore
        self.memory_dir = str(self.project_root / "backend" / ".ai_memory")
        self.feedback_file = os.path.join(self.memory_dir, "feedback_scores.json")
        self.signals_file = os.path.join(self.memory_dir, "user_signals.json")
        self.signal_store = SignalStateStore(
            memory_dir=self.memory_dir,
            signals_file=self.signals_file,
            feedback_file=self.feedback_file,
        )

        # Plugin Knowledge & KnowledgeManager
        self.plugin_knowledge_dir = str(self.knowledge_dir)
        self.occupations_dir = os.path.join(
            self.plugin_knowledge_dir, "Claude_occupations"
        )
        self.historical_figures_dir = os.path.join(
            self.plugin_knowledge_dir, "Claude_historical_figures"
        )

        self.knowledge_manager = None
        try:
            self.knowledge_manager = KnowledgeManager(
                base_dir=(self.project_root / "backend")
            )
            self._preload_plugin_titles()
        except Exception as e:
            print(f"❌ [ChatOrchestrator] KnowledgeManager初期化失敗: {e}")
            traceback.print_exc()
            self.knowledge_manager = None

        # Handlers 一括構築
        self.handlers = build_default_handlers(
            project_root=self.project_root,
            knowledge_dir=self.knowledge_dir,
            reload_callback=self._reload_knowledge_system,
        )

    def _init_default_reports(self) -> None:
        self.knowledge_startup_report: Dict[str, Any] = {
            "status": "not_checked",
            "summary": "Knowledgeの起動時監査はまだ実行されていません",
            "should_warn_user": False,
            "counts": {},
            "valid_paths": [],
            "issues": [],
        }
        self.last_knowledge_health: Dict[str, Any] = {
            "status": "not_checked",
            "summary": "Knowledgeの読込処理はまだ実行されていません",
            "should_warn_user": False,
            "can_use_knowledge": False,
            "expected": False,
            "counts": {},
            "loaded_paths": [],
            "selected_domains": [],
            "dropped_domains": [],
            "issues": [],
        }
        self.last_project_progress: Dict[str, Any] = {
            "goal": None,
            "overall_status": "not_analyzed",
            "progress_percent": None,
            "confidence": "low",
            "current_phase": None,
            "counts": {},
            "tasks": [],
            "barriers": [],
            "next_actions": [],
            "evidence_sources": [],
            "warnings": [],
            "calculation": {},
        }
        self.last_knowledge_selection: Dict[str, Any] = {
            "selected_domains": [],
            "dropped_domains": [],
            "estimated_chars": 0,
            "truncated": False,
            "decisions": [],
            "load_errors": [],
        }
        self.last_knowledge_load_status: Dict[str, Any] = {
            "status": "not_run",
            "requested_count": 0,
            "loaded_count": 0,
            "loaded_paths": [],
            "errors": [],
        }

    # ========================================================
    # SignalStateStore への委譲メソッド（旧メソッド名互換）
    # ========================================================

    def _save_signals(self, signals_data: Dict[str, Any]) -> None:
        self.signal_store.save_signals(signals_data)

    def _get_current_signals(self) -> Dict[str, Any]:
        return self.signal_store.get_current_signals()

    def _update_signals_with_created_files(self, assistant_text: str) -> None:
        self.signal_store.update_signals_with_created_files(assistant_text)

    def _save_assistant_response_and_state(self, res_content: Any) -> None:
        self.signal_store.save_assistant_response_and_state(
            self.context_manager, res_content
        )

    def _reset_all_memory(self) -> Dict[str, Any]:
        clean_signals = self.signal_store.reset_all_memory(self.context_manager)
        self.current_signals = clean_signals
        self.active_context = None
        return clean_signals

    def _get_feedback_bonus(self, message: str, handler_name: str) -> int:
        return self.signal_store.get_feedback_bonus(handler_name)

    # ========================================================
    # Handler Invocation
    # ========================================================

    async def _invoke_handler(self, handler: Any) -> Any:
        handler_name = handler.__class__.__name__

        existing_knowledge = self._normalize_loaded_knowledge(
            getattr(self.request, "loaded_knowledge", [])
        )
        additional_knowledge: list[dict[str, Any]] = []

        if (
            hasattr(handler, "get_search_keywords")
            and self.knowledge_manager is not None
        ):
            try:
                keywords = handler.get_search_keywords(self.message)
            except Exception:
                keywords = []
                print(f"❌ {handler_name}.get_search_keywordsで例外")
                traceback.print_exc()

            if keywords:
                search_dirs = [
                    self.plugin_knowledge_dir,
                    self.occupations_dir,
                    self.historical_figures_dir,
                ]
                for search_dir in search_dirs:
                    try:
                        result = self.knowledge_manager.search_by_keywords(
                            search_dir, keywords
                        )
                        additional_knowledge.extend(
                            self._normalize_loaded_knowledge(result)
                        )
                    except Exception as e:
                        print(f"⚠️ Knowledge追加検索エラー ({search_dir}): {e}")
                        traceback.print_exc()

        combined_knowledge = self._merge_knowledge_lists(
            existing_knowledge, additional_knowledge
        )
        health_context = self._analyze_knowledge_health(combined_knowledge)
        progress_context = self._analyze_project_progress(combined_knowledge)

        combined_knowledge = self._merge_knowledge_lists(
            combined_knowledge,
            [
                {
                    "id": "system/knowledge_health",
                    "title": "Knowledge読込監視結果",
                    "source_path": "system/knowledge_health",
                    "content_type": "generated_context",
                    "description": "Knowledgeの読込失敗・件数不一致・空データの監視結果",
                    "content": health_context,
                },
                {
                    "id": "system/project_progress",
                    "title": "プロジェクト進捗",
                    "source_path": "system/project_progress",
                    "content_type": "generated_context",
                    "description": "選択済みJSONから決定的に計算した現在地・壁・次の行動",
                    "content": progress_context,
                },
            ],
        )

        setattr(self.request, "loaded_knowledge", combined_knowledge)

        if hasattr(self.prompt_builder, "set_active_knowledge"):
            self.prompt_builder.set_active_knowledge(combined_knowledge)
        else:
            self.prompt_builder.active_knowledge = combined_knowledge

        knowledge_ids = [
            item.get("id") or item.get("name") or item.get("title")
            for item in combined_knowledge
            if item.get("id") or item.get("name") or item.get("title")
        ]
        print(
            f"🧠 [ChatOrchestrator] {handler_name}へ渡すKnowledge件数={len(combined_knowledge)}"
        )
        print(f"🧠 [ChatOrchestrator] knowledge_ids={knowledge_ids}")

        return await handler.handle(self.request)

    # ========================================================
    # Main Route and Execute
    # ========================================================

    async def route_and_execute(self, request: Any, **kwargs: Any) -> Tuple[str, Any]:
        self.request = request
        self.message = str(getattr(request, "message", "") or "")

        # 0. メモリ消去コマンドの即時割り込み処理
        if self.message.strip() in RESET_COMMANDS:
            clean_signals = self._reset_all_memory()
            setattr(self.request, "current_signals", clean_signals)
            return (
                "text",
                {
                    "message": "🧹 会話履歴とプロジェクト記憶（Project Context）を完全にリセットしました！（Turn: 0 / History: 0）",
                    "blocks": [],
                    "update_signals": clean_signals,
                },
            )

        self.context_manager.add_chat_history("user", self.message)

        available_keys: list[str] = []
        if self.knowledge_router is not None and hasattr(
            self.knowledge_router, "domains"
        ):
            available_keys = [
                domain.name for domain in self.knowledge_router.domains
            ]

        self._init_default_reports()
        setattr(self.request, "loaded_knowledge", [])
        setattr(self.request, "knowledge_load_status", dict(self.last_knowledge_load_status))
        setattr(self.request, "knowledge_selection", dict(self.last_knowledge_selection))
        setattr(self.request, "knowledge_health", dict(self.last_knowledge_health))
        setattr(self.request, "knowledge_startup_audit", dict(self.knowledge_startup_report))
        setattr(self.request, "project_progress", dict(self.last_project_progress))

        if hasattr(self.prompt_builder, "set_active_knowledge"):
            self.prompt_builder.set_active_knowledge([])
        else:
            self.prompt_builder.active_knowledge = []

        # 1. IntentInspector
        try:
            inspector = IntentInspector(
                self.message,
                available_knowledge_keys=available_keys,
            )
        except TypeError:
            inspector = IntentInspector(self.message)
            print("⚠️ 古いIntentInspectorを検出。フォールバック初期化しました。")

        inspect_result = inspector.inspect()
        self.context_manager.apply_inspector_result(inspect_result)

        # 2. Signals & Mode 伝播
        current_signals = self._get_current_signals()
        current_signals["intent_analysis"] = inspect_result
        current_signals["active_mode"] = inspect_result.get("mode", "unknown")

        self.request.current_signals = current_signals
        self.request.intent_analysis = inspect_result
        setattr(self.request, "current_signals", current_signals)
        self.current_signals = current_signals
        self.active_context = current_signals.get("active_context")

        if current_signals:
            intent_summary = inspect_result if isinstance(inspect_result, dict) else {}
            print(
                "📡 [ChatOrchestrator] "
                f"mode={intent_summary.get('mode', 'unknown')} "
                f"intent={intent_summary.get('intent', 'unknown')} "
                f"forced_handler={intent_summary.get('forced_handler')} "
                f"knowledge_count={len(available_keys)}"
            )

        # 3. KnowledgeRouter
        self._route_and_attach_knowledge(current_signals)

        # 4. Image fast path
        image_data = getattr(self.request, "image_base64", None)
        if image_data:
            print("📸 画像データ受信！ OcrRecruitHandlerへ直接ルーティング")
            ocr_handler = OcrRecruitHandler()
            self.last_used_handler = "OcrRecruitHandler"
            self.active_context = None
            result = await ocr_handler.handle(self.message, image_data)
            if result:
                _, res_content = result
                self._save_assistant_response_and_state(res_content)
            return result

        # 4.5 司令塔による絶対君主制ルーティング (Forced Handler + オフライン耐性)
        forced_handler_name = resolve_forced_handler_name(self.message, inspect_result)
        if forced_handler_name:
            print(f"👑 [IntentInspector] 絶対命令: {forced_handler_name} を優先実行します")
            target_handler = next(
                (h for h in self.handlers if h.__class__.__name__ == forced_handler_name),
                None,
            )
            if target_handler:
                try:
                    result = await self._invoke_handler(target_handler)
                except Exception as e:
                    print(f"⚠️ {forced_handler_name} 実行中に例外 ({e}) -> スコアリングへ移行")
                    result = None

                if not is_offline_error_response(result):
                    res_type, res_content = result
                    self.last_used_handler = forced_handler_name
                    self._save_assistant_response_and_state(res_content)
                    return (res_type, res_content)

                print(f"🔄 {forced_handler_name} が未応答またはオフラインのため、ローカルHandler群へフォールバックします。")
            else:
                print(f"⚠️ 指定された {forced_handler_name} は見つかりません。通常のスコアリングへ移行します。")

        # 5 & 6. Handler Scoring & Sort
        scored_handlers = await score_and_sort_handlers(
            handlers=self.handlers,
            message=self.message,
            current_signals=current_signals,
            feedback_bonus_fn=lambda name: self._get_feedback_bonus(self.message, name),
        )

        if not scored_handlers:
            return (
                "text",
                {"message": "利用可能なHandlerがありません。", "blocks": []},
            )

        debug_block = build_routing_debug_block(scored_handlers)

        # 7. スコア上位から順番に実行（Ollamaオフライン時は次点のローカルHandlerへ自動委譲）
        for candidate in scored_handlers:
            if candidate["score"] <= 0:
                break
            cand_handler = candidate["handler"]
            cand_name = cand_handler.__class__.__name__
            print(f"🚀 [ChatOrchestrator] {cand_name} を実行します (Score: {candidate['score']})")

            try:
                result = await self._invoke_handler(cand_handler)
            except Exception as e:
                print(f"⚠️ {cand_name} で例外発生 ({e}) -> 次の候補Handlerを試行します")
                continue

            if is_offline_error_response(result):
                print(f"🔄 {cand_name} がオフラインまたは未応答のため、次のローカルHandlerへ委譲します")
                continue

            res_type, res_content = result
            self.last_used_handler = cand_name
            print(f"📦 [ChatOrchestrator] 実行完了 handler={cand_name} res_type={res_type}")
            self._save_assistant_response_and_state(res_content)
            return (res_type, attach_debug_block(res_content))

        # 8. すべてのスコア付き候補が未応答だった場合はローカルの ChatHandler で確実に応答
        chat_fallback = next(
            (h for h in self.handlers if h.__class__.__name__ == "ChatHandler"),
            None,
        )
        if chat_fallback is not None:
            self.last_used_handler = "ChatHandler (Local Fallback)"
            res_type, res_content = await self._invoke_handler(chat_fallback)
            self._save_assistant_response_and_state(res_content)
            return (res_type, attach_debug_block(res_content))

        return (
            "text",
            {
                "message": "どのエージェントも処理できませんでした。",
                "blocks": [debug_block],
            },
        )
