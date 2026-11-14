"""
backend/engine/orchestrator/chat_orchestrator/knowledge_pipeline.py

Knowledgeの正規化、マージ、ルーターからのロード、起動時監査、健全性監視、
およびプロジェクト進捗計算を担当するモジュール。
"""
from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any, Dict, List


class KnowledgePipelineMixin:
    """
    ChatOrchestrator に Knowledge 関連メソッド群を提供する Mixin クラス。
    既存の属性名（self.knowledge_router, self.last_knowledge_health 等）をそのまま維持する。
    """

    def _preload_plugin_titles(self) -> None:
        """Occupations と Historical Figures のメタデータをウォームアップ読み込みする。"""
        if self.knowledge_manager is None:
            return

        try:
            occupation_items = self.knowledge_manager.load_all_json_from_dir(
                self.occupations_dir
            )
            _ = [item["title"] for item in occupation_items if item.get("title")]
        except Exception as e:
            print(f"⚠️ 職業タイトル一覧の読み込みに失敗: {e}")

        try:
            history_items = self.knowledge_manager.load_all_json_from_dir(
                self.historical_figures_dir
            )
            for item in history_items:
                try:
                    data = item.data
                except Exception as e:
                    print(f"⚠️ 歴史人物データ読み込み失敗 ({item.rel_path}): {e}")
                    continue
                if not isinstance(data, dict):
                    continue
                hf = data.get("history_figures", {})
                if not isinstance(hf, dict):
                    continue
                for group in ("world_history", "japan_history"):
                    people = hf.get(group)
                    if not isinstance(people, list):
                        continue
                    for person in people:
                        if isinstance(person, dict) and person.get("name"):
                            _ = str(person["name"])
        except Exception as e:
            print(f"⚠️ 歴史人物タイトル一覧の読み込みに失敗: {e}")

    def _normalize_loaded_knowledge(self, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            values = list(value.values())
            if values and all(isinstance(item, dict) for item in values):
                return values
            return [value]
        return []

    def _merge_knowledge_lists(
        self,
        existing: list[dict[str, Any]],
        additional: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()

        for item in existing + additional:
            if not isinstance(item, dict):
                continue
            identity = item.get("id") or item.get("name") or item.get("title")
            if identity:
                identity_key = str(identity).strip()
            else:
                try:
                    identity_key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                except Exception:
                    identity_key = str(id(item))

            if identity_key in seen:
                continue
            seen.add(identity_key)
            merged.append(item)

        return merged

    def _load_router_knowledge(
        self,
        matched_paths: list[Any],
        user_message: str = "",
        signals: Dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        requested_paths = [
            str(path).strip() for path in matched_paths if str(path).strip()
        ]
        loaded: list[dict[str, Any]] = []

        if not requested_paths:
            self.last_knowledge_load_status = {
                "status": "empty",
                "requested_count": 0,
                "loaded_count": 0,
                "loaded_paths": [],
                "errors": [],
            }
            self.last_knowledge_selection = {
                "selected_domains": [],
                "dropped_domains": [],
                "estimated_chars": 0,
                "truncated": False,
                "decisions": [],
                "load_errors": [],
            }
            return loaded

        try:
            load_result = self.knowledge_loader.load(requested_paths)
        except Exception as exc:
            self.last_knowledge_load_status = {
                "status": "failed",
                "requested_count": len(requested_paths),
                "loaded_count": 0,
                "loaded_paths": [],
                "errors": [
                    {
                        "path": "*",
                        "reason": "loader_exception",
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                ],
            }
            print(f"❌ [ChatOrchestrator] KnowledgeLoader実行失敗: {exc}")
            traceback.print_exc()
            return loaded

        candidate_count = len(load_result.items)

        try:
            selection_result = self.knowledge_selector.select(
                user_message=user_message,
                load_result=load_result,
                signals=signals,
            )
            self.last_knowledge_selection = selection_result.to_dict()
            load_result = selection_result.as_load_result()
        except Exception as exc:
            self.last_knowledge_selection = {
                "selected_domains": [
                    str(getattr(item, "domain_label", ""))
                    for item in load_result.items
                ],
                "dropped_domains": [],
                "estimated_chars": 0,
                "truncated": False,
                "decisions": [],
                "load_errors": [],
                "status": "fallback",
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"⚠️ [ChatOrchestrator] Knowledge選別失敗。未選別で継続します: {exc}")

        loaded_paths: list[str] = []
        for item in load_result.items:
            item_path = str(getattr(item, "path", ""))
            domain_label = str(
                getattr(item, "domain_label", "") or item_path or "knowledge"
            )
            loaded.append(
                {
                    "id": domain_label,
                    "title": domain_label,
                    "source_path": item_path,
                    "content_type": str(getattr(item, "content_type", "unknown")),
                    "description": str(getattr(item, "description", "")),
                    "content": getattr(item, "content", None),
                }
            )
            loaded_paths.append(item_path)

        errors = [
            {
                "path": str(getattr(error, "path", "")),
                "reason": str(getattr(error, "reason", "unknown")),
                "detail": str(getattr(error, "detail", "")),
            }
            for error in load_result.errors
        ]

        if errors and loaded:
            status = "partial"
        elif errors:
            status = "failed"
        else:
            status = "ready"

        self.last_knowledge_load_status = {
            "status": status,
            "requested_count": len(requested_paths),
            "candidate_count": candidate_count,
            "loaded_count": len(loaded),
            "loaded_paths": loaded_paths,
            "selection": dict(self.last_knowledge_selection),
            "errors": errors,
        }

        print(
            "📚 [ChatOrchestrator] "
            f"KnowledgeLoader status={status} "
            f"requested={len(requested_paths)} "
            f"candidates={candidate_count} "
            f"loaded={len(loaded)} "
            f"errors={len(errors)}"
        )
        return loaded

    async def _reload_knowledge_system(self) -> Dict[str, Any]:
        """Router/Loaderを候補状態で再構築し、監査後に安全に切り替える。"""
        from engine.KnowledgeLoader import KnowledgeLoader
        from engine.KnowledgeRouter import KnowledgeRouter

        async with self.knowledge_reload_lock:
            domains_before = len(
                getattr(self.knowledge_router, "domains", []) or []
            )

            try:
                def rebuild():
                    candidate_router = KnowledgeRouter(
                        knowledge_dir=self.knowledge_dir,
                        threshold=1.0,
                        top_k=5,
                    )
                    candidate_loader = KnowledgeLoader(
                        knowledge_dirs=[self.knowledge_dir],
                        cache_enabled=True,
                    )
                    audit_report = self.knowledge_startup_auditor.run(
                        router=candidate_router,
                    )
                    return candidate_router, candidate_loader, audit_report

                candidate_router, candidate_loader, audit_report = await asyncio.to_thread(
                    rebuild
                )
            except Exception as exc:
                failed_audit = {
                    "status": "failed",
                    "summary": "Knowledge再読込の準備中に例外が発生しました",
                    "should_warn_user": True,
                    "counts": {},
                    "valid_paths": [],
                    "issues": [
                        {
                            "code": "knowledge_reload_exception",
                            "severity": "critical",
                            "message": "Knowledgeを再構築できませんでした",
                            "path": None,
                            "detail": f"{type(exc).__name__}: {exc}",
                        }
                    ],
                }
                self.knowledge_startup_report = failed_audit
                if hasattr(self, "request"):
                    setattr(self.request, "knowledge_startup_audit", dict(failed_audit))
                return {
                    "status": "failed",
                    "applied": False,
                    "summary": failed_audit["summary"],
                    "domains_before": domains_before,
                    "domains_after": domains_before,
                    "audit": failed_audit,
                }

            audit_data = audit_report.to_dict()
            self.knowledge_startup_report = audit_data
            domains_after = len(getattr(candidate_router, "domains", []) or [])
            applied = audit_report.status != "failed"

            if applied:
                self.knowledge_router = candidate_router
                self.knowledge_loader = candidate_loader
                self.last_knowledge_load_status = {
                    "status": "not_run_after_reload",
                    "requested_count": 0,
                    "candidate_count": 0,
                    "loaded_count": 0,
                    "loaded_paths": [],
                    "errors": [],
                }
                self.last_knowledge_selection = {
                    "selected_domains": [],
                    "dropped_domains": [],
                    "estimated_chars": 0,
                    "truncated": False,
                    "decisions": [],
                    "load_errors": [],
                }
                self.last_knowledge_health = {
                    "status": "not_checked",
                    "summary": "再読込後の最初の質問で診断します",
                    "should_warn_user": False,
                    "can_use_knowledge": False,
                    "expected": False,
                    "counts": {},
                    "loaded_paths": [],
                    "selected_domains": [],
                    "dropped_domains": [],
                    "issues": [],
                }
                if hasattr(self.prompt_builder, "set_active_knowledge"):
                    self.prompt_builder.set_active_knowledge([])
                else:
                    self.prompt_builder.active_knowledge = []

            if hasattr(self, "request"):
                setattr(self.request, "knowledge_startup_audit", dict(audit_data))
                if applied:
                    setattr(self.request, "loaded_knowledge", [])
                    setattr(
                        self.request,
                        "knowledge_load_status",
                        dict(self.last_knowledge_load_status),
                    )
                    setattr(
                        self.request,
                        "knowledge_selection",
                        dict(self.last_knowledge_selection),
                    )
                    setattr(
                        self.request,
                        "knowledge_health",
                        dict(self.last_knowledge_health),
                    )

            result_status = (
                "success" if audit_report.status == "healthy" else audit_report.status
            )
            return {
                "status": result_status,
                "applied": applied,
                "summary": audit_report.summary,
                "domains_before": domains_before,
                "domains_after": domains_after if applied else domains_before,
                "audit": audit_data,
            }

    def _run_knowledge_startup_audit(self) -> None:
        if self.knowledge_router is None:
            self.knowledge_startup_report = {
                "status": "failed",
                "summary": "KnowledgeRouterが利用できないため起動時監査を実行できません",
                "should_warn_user": True,
                "counts": {},
                "valid_paths": [],
                "issues": [
                    {
                        "code": "router_unavailable",
                        "severity": "critical",
                        "message": "KnowledgeRouterが利用できません",
                        "path": None,
                        "detail": "起動時監査を開始できませんでした",
                    }
                ],
            }
            print("❌ [ChatOrchestrator] Knowledge Startup Audit: router unavailable")
            return

        try:
            report = self.knowledge_startup_auditor.run(router=self.knowledge_router)
            self.knowledge_startup_report = report.to_dict()
        except Exception as exc:
            self.knowledge_startup_report = {
                "status": "failed",
                "summary": "Knowledge起動時監査で例外が発生しました",
                "should_warn_user": True,
                "counts": {},
                "valid_paths": [],
                "issues": [
                    {
                        "code": "startup_audit_exception",
                        "severity": "critical",
                        "message": "Knowledge起動時監査で例外が発生しました",
                        "path": None,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                ],
            }
            print(f"❌ [ChatOrchestrator] Knowledge Startup Audit失敗: {exc}")
            traceback.print_exc()

        print(
            "🔎 [ChatOrchestrator] "
            f"KnowledgeStartupAudit status={self.knowledge_startup_report.get('status')} "
            f"summary={self.knowledge_startup_report.get('summary')}"
        )

    def _analyze_knowledge_health(self, knowledge: list[dict[str, Any]]) -> str:
        signals = getattr(self.request, "current_signals", {})
        if not isinstance(signals, dict):
            signals = {}

        try:
            report = self.knowledge_health_monitor.evaluate(
                load_status=self.last_knowledge_load_status,
                selection=self.last_knowledge_selection,
                loaded_knowledge=knowledge,
            )
            health_data = report.to_dict()
            health_context = report.to_prompt_context()
        except Exception as exc:
            health_data = {
                "status": "failed",
                "summary": "Knowledge Health監視処理が失敗しました",
                "should_warn_user": True,
                "can_use_knowledge": False,
                "expected": True,
                "counts": {},
                "loaded_paths": [],
                "selected_domains": [],
                "dropped_domains": [],
                "issues": [
                    {
                        "code": "health_monitor_exception",
                        "severity": "critical",
                        "message": "Knowledge Health監視処理が失敗しました",
                        "stage": "health",
                        "path": None,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                ],
            }
            health_context = (
                "# Knowledge Health\n"
                "- 状態: failed\n"
                "- 監視処理自体が失敗しました。Knowledgeを正常に読めたと主張しないこと。"
            )
            print(f"❌ [ChatOrchestrator] Knowledge Health監視失敗: {exc}")
            traceback.print_exc()

        self.last_knowledge_health = health_data
        setattr(self.request, "knowledge_health", dict(health_data))
        setattr(self.request, "knowledge_health_context", health_context)
        setattr(
            self.request,
            "knowledge_startup_audit",
            dict(self.knowledge_startup_report),
        )
        signals["knowledge_health"] = dict(health_data)
        signals["knowledge_health_context"] = health_context
        setattr(self.request, "current_signals", signals)
        self.current_signals = signals

        print(
            "🩺 [ChatOrchestrator] "
            f"KnowledgeHealth status={health_data.get('status')} "
            f"warn={health_data.get('should_warn_user')}"
        )
        return health_context

    def _analyze_project_progress(self, knowledge: list[dict[str, Any]]) -> str:
        signals = getattr(self.request, "current_signals", {})
        if not isinstance(signals, dict):
            signals = {}

        try:
            report = self.project_progress_analyzer.analyze(
                user_message=self.message,
                knowledge=knowledge,
                signals=signals,
            )
            progress_data = report.to_dict()
            progress_context = report.to_prompt_context()
        except Exception as exc:
            progress_data = {
                "goal": None,
                "overall_status": "analysis_failed",
                "progress_percent": None,
                "confidence": "low",
                "current_phase": None,
                "counts": {},
                "tasks": [],
                "barriers": [],
                "next_actions": [],
                "evidence_sources": [],
                "warnings": [f"{type(exc).__name__}: {exc}"],
                "calculation": {},
            }
            progress_context = (
                "# プロジェクト進捗\n"
                "進捗解析に失敗したため、進捗率を推測しないこと。"
            )
            print(f"⚠️ [ChatOrchestrator] ProjectProgress解析失敗: {exc}")
            traceback.print_exc()

        self.last_project_progress = progress_data
        setattr(self.request, "project_progress", dict(progress_data))
        setattr(self.request, "project_progress_context", progress_context)

        signals["project_progress"] = dict(progress_data)
        signals["project_progress_context"] = progress_context
        setattr(self.request, "current_signals", signals)
        self.current_signals = signals

        print(
            "📊 [ChatOrchestrator] "
            f"ProjectProgress status={progress_data.get('overall_status')} "
            f"progress={progress_data.get('progress_percent')}"
        )
        return progress_context

    def _route_and_attach_knowledge(self, current_signals: Dict[str, Any]) -> None:
        """KnowledgeRouter を実行し、結果を self.request と prompt_builder にセットする。"""
        if not self.knowledge_router:
            self.last_knowledge_load_status = {
                "status": "router_unavailable",
                "requested_count": 0,
                "loaded_count": 0,
                "loaded_paths": [],
                "errors": [
                    {
                        "path": "*",
                        "reason": "router_unavailable",
                        "detail": "KnowledgeRouterが初期化されていません",
                    }
                ],
            }
            self.last_knowledge_selection = {
                "selected_domains": [],
                "dropped_domains": [],
                "estimated_chars": 0,
                "truncated": False,
                "decisions": [],
                "load_errors": [],
                "status": "router_unavailable",
            }
            setattr(
                self.request,
                "knowledge_load_status",
                dict(self.last_knowledge_load_status),
            )
            setattr(
                self.request,
                "knowledge_selection",
                dict(self.last_knowledge_selection),
            )
            return

        try:
            route_result = self.knowledge_router.route(self.message, current_signals)
            matched_paths: list[Any] = []

            if route_result is not None:
                if hasattr(route_result, "file_paths"):
                    matched_paths = list(route_result.file_paths)
                elif hasattr(route_result, "matched_files"):
                    matched_paths = list(route_result.matched_files)
                elif isinstance(route_result, list):
                    matched_paths = route_result
                elif hasattr(route_result, "__iter__") and not isinstance(
                    route_result, str
                ):
                    matched_paths = list(route_result)

            print(f"🧠 [ChatOrchestrator] matched_paths={matched_paths}")

            if hasattr(route_result, "matched_domains"):
                print(
                    f"🧠 [ChatOrchestrator] matched_domains={route_result.matched_domains}"
                )

            if hasattr(route_result, "scores"):
                route_scores = getattr(route_result, "scores")
                print(f"🧠 [ChatOrchestrator] knowledge_scores={route_scores}")
                if isinstance(route_scores, dict):
                    current_signals["knowledge_scores"] = route_scores

            loaded_knowledges = self._load_router_knowledge(
                matched_paths,
                user_message=self.message,
                signals=current_signals,
            )

            setattr(
                self.request,
                "knowledge_load_status",
                dict(self.last_knowledge_load_status),
            )
            setattr(
                self.request,
                "knowledge_selection",
                dict(self.last_knowledge_selection),
            )

            loaded_knowledge_ids = [
                item.get("id") or item.get("name") or item.get("title")
                for item in loaded_knowledges
                if item.get("id") or item.get("name") or item.get("title")
            ]

            print(
                f"🧠 [ChatOrchestrator] loaded_knowledge_count={len(loaded_knowledges)}"
            )
            print(f"🧠 [ChatOrchestrator] loaded_knowledge_ids={loaded_knowledge_ids}")

            setattr(self.request, "loaded_knowledge", loaded_knowledges)
            if hasattr(self.prompt_builder, "set_active_knowledge"):
                self.prompt_builder.set_active_knowledge(loaded_knowledges)
            else:
                self.prompt_builder.active_knowledge = loaded_knowledges

        except Exception as e:
            print(f"❌ [ChatOrchestrator] Knowledgeルーティング中にエラー: {e}")
            traceback.print_exc()
            setattr(self.request, "loaded_knowledge", [])
            self.last_knowledge_load_status = {
                "status": "failed",
                "requested_count": 0,
                "loaded_count": 0,
                "loaded_paths": [],
                "errors": [
                    {
                        "path": "*",
                        "reason": "routing_exception",
                        "detail": f"{type(e).__name__}: {e}",
                    }
                ],
            }
            self.last_knowledge_selection = {
                "selected_domains": [],
                "dropped_domains": [],
                "estimated_chars": 0,
                "truncated": False,
                "decisions": [],
                "load_errors": [],
                "status": "routing_failed",
            }
            setattr(
                self.request,
                "knowledge_load_status",
                dict(self.last_knowledge_load_status),
            )
            setattr(
                self.request,
                "knowledge_selection",
                dict(self.last_knowledge_selection),
            )
            if hasattr(self.prompt_builder, "set_active_knowledge"):
                self.prompt_builder.set_active_knowledge([])
            else:
                self.prompt_builder.active_knowledge = []
