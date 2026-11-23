"""
backend/engine/orchestrator/chat_orchestrator/orchestrator.py

分割されたサブモジュール（handler_registry, signal_state_store, knowledge_pipeline, routing_dispatcher）を
束ねるスリムな ChatOrchestrator 本体。
エレベーターシステム（JSON直接階数指定 / モデル限界値からの自動階層分割）、
保存済みエレベーターの直接ロード（[source:...]）、および JSON→日本語フォールバック整形を統合管理する。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

from engine.orchestrator.chat_orchestrator.handler_registry import (
    OcrRecruitHandler,
    PROJECT_BUILDER_AVAILABLE,
    PROJECT_BUILDER_IMPORT_ERROR,
    ProjectBuilderHandler,
    build_default_handlers,
)
from engine.orchestrator.chat_orchestrator.knowledge_pipeline import KnowledgePipelineMixin
from engine.orchestrator.chat_orchestrator.routing_dispatcher import (
    attach_debug_block,
    build_routing_debug_block,
    is_offline_error_response,
    resolve_forced_handler_name,
    score_and_sort_handlers,
)
from engine.orchestrator.chat_orchestrator.signal_state_store import SignalStateStore


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

NEXT_FLOOR_COMMANDS = {
    "続けて",
    "つづけて",
    "続き",
    "つづき",
    "次",
    "つぎ",
    "次へ",
    "上の階",
    "上へ",
    "next",
}

PREV_FLOOR_COMMANDS = {
    "戻って",
    "もどって",
    "戻る",
    "前の階",
    "前へ",
    "下の階",
    "下へ",
    "back",
    "prev",
}

# JSONの英語キーを自然な日本語見出しへ変換する辞書（未登録キーもそのまま見出し化して取りこぼさない）
JSON_KEY_LABELS_JA: Dict[str, str] = {
    "title": "タイトル",
    "name": "名称",
    "summary": "概要",
    "description": "説明",
    "overview": "全体像",
    "conclusion": "結論",
    "answer": "答え",
    "guideline": "ガイドライン・要点",
    "phenomenon": "起きている現象",
    "why_it_happens": "なぜ起きるのか",
    "comparison_note": "比較・開発者の視点",
    "practical_tips": "実践のコツ",
    "ideas": "設計コラム・アイデア",
    "limit_note": "最上階メモ",
    "cooking_time": "焼き時間・目安",
    "grill_time": "焼き時間",
    "time": "時間・目安",
    "duration": "所要時間",
    "temperature": "温度・火加減",
    "heat": "火加減",
    "fire": "火加減",
    "ingredients": "材料",
    "preparation": "下ごしらえ",
    "prep": "準備・下ごしらえ",
    "steps": "手順",
    "procedure": "進め方",
    "method": "方法",
    "how_to": "やり方",
    "tips": "コツ・ポイント",
    "points": "ポイント",
    "key_points": "重要ポイント",
    "check_points": "焼き上がり・確認の目安",
    "doneness": "焼き上がりの目安",
    "warnings": "注意点",
    "caution": "気をつけること",
    "notes": "補足",
    "examples": "具体例",
    "seasoning": "味付け",
    "serving": "盛り付け・食べ方",
    "faq": "よくある質問",
    "references": "参考情報",
}

JSON_SKIP_KEYS = {
    "id",
    "source_path",
    "content_type",
    "keywords",
    "tags",
    "aliases",
    "triggers",
    "message_examples",
    "elevator",
    "floors",
    "schema_version",
    "version",
    "domain",
    "category",
    "metadata",
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
        self.last_elevator: Optional[Dict[str, Any]] = None
        self.last_elevator_plan: Optional[Dict[str, Any]] = None

        # モデル1ターンあたりの文字数限界値（JSONに階数指定がない場合の自動分割基準）
        cfg_limit = (
            config.get("elevator_char_limit")
            if isinstance(config, dict)
            else getattr(config, "elevator_char_limit", None)
        )
        env_limit = os.environ.get("TO_ELEVATOR_CHAR_LIMIT")
        try:
            self.elevator_char_limit = int(cfg_limit or env_limit or 450)
        except (TypeError, ValueError):
            self.elevator_char_limit = 450

        # 親フォルダをたどり、backend/ と plugins/project_builder/knowledge/ の
        # 両方を直下に持つ本当のプロジェクトルート (To/) を確実に特定する
        # ※ To/backend/ 自身に backend/ や plugins/ が残っているケースを除外
        here = Path(__file__).resolve()
        discovered_root: Optional[Path] = None
        for parent in here.parents:
            if parent.name.lower() == "backend":
                continue
            if (parent / "backend").is_dir() and (
                parent / "plugins" / "project_builder" / "knowledge"
            ).is_dir():
                discovered_root = parent
                break

        if discovered_root is None:
            for parent in here.parents:
                if parent.name.lower() == "backend":
                    continue
                if (parent / "backend").is_dir() and (parent / "plugins").is_dir():
                    discovered_root = parent
                    break

        if discovered_root is None:
            discovered_root = (
                here.parents[4] if len(here.parents) >= 5 else Path(os.getcwd()).resolve()
            )

        self.project_root = discovered_root
        self.knowledge_dir = (
            self.project_root / "plugins" / "project_builder" / "knowledge"
        ).resolve()

        print(f"🏠 [ChatOrchestrator] project_root={self.project_root}")
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
            # base_dir は project_root (To/) を渡す（backend だと plugins/ が範囲外エラーになるため）
            self.knowledge_manager = KnowledgeManager(
                base_dir=self.project_root,
                knowledge_dirs=[self.knowledge_dir],
            )
            self._preload_plugin_titles()
        except Exception as e:
            print(f"❌ [ChatOrchestrator] KnowledgeManager初期化失敗: {e}")
            traceback.print_exc()
            self.knowledge_manager = None

        # Handlers 一括構築

        # Handlers 一括構築
        if callable(build_default_handlers):
            self.handlers = build_default_handlers(
                project_root=self.project_root,
                knowledge_dir=self.knowledge_dir,
                reload_callback=self._reload_knowledge_system,
            )
        else:
            self.handlers = []
            print("⚠️ [ChatOrchestrator] build_default_handlers が利用できません。")
    def _init_default_reports(self) -> None:
        self.last_elevator = None
        self.last_elevator_plan = None
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
        self.last_elevator = None
        self.last_elevator_plan = None
        return clean_signals

    def _get_feedback_bonus(self, message: str, handler_name: str) -> int:
        return self.signal_store.get_feedback_bonus(handler_name)

    # ========================================================
    # エレベーターシステム & JSON→日本語レンダリング
    # ========================================================

    def _store_elevator_context(self, plan: Optional[Dict[str, Any]]) -> None:
        """Pydantic の ChatRequest に未定義フィールドを setattr せず、signals 経由で安全に共有する"""
        self.last_elevator_plan = plan
        if plan is None:
            self.last_elevator = None
            return

        elevator_meta = {
            "topic": plan["title"],
            "title": plan["title"],
            "knowledge_id": plan["knowledge_id"],
            "source_path": plan["source_path"],
            "mode": plan["mode"],
            "current_floor": plan["current_floor"],
            "max_floor": plan["max_floor"],
            "has_next": plan["has_next"],
            "has_prev": plan["has_prev"],
            "next_floor_number": plan.get("next_floor_number"),
            "previous_floor_number": plan.get("previous_floor_number"),
            "floors": plan["floors"],
        }
        self.last_elevator = elevator_meta

        if isinstance(getattr(self, "current_signals", None), dict):
            self.current_signals["elevator_floor"] = plan["current_floor"]
            self.current_signals["elevator_meta"] = elevator_meta

    @staticmethod
    def _label_ja(key: str) -> str:
        return JSON_KEY_LABELS_JA.get(key.lower(), key.replace("_", " "))

    @classmethod
    def _render_json_value_ja(cls, value: Any, indent: int = 0) -> str:
        """任意のJSON値（str / list / dict）を読みやすい日本語Markdownへ再帰変換する"""
        prefix = "  " * indent
        if value is None or value == "":
            return ""
        if isinstance(value, bool):
            return f"{prefix}{'はい' if value else 'いいえ'}"
        if isinstance(value, (str, int, float)):
            return f"{prefix}{value}"
        if isinstance(value, list):
            lines: List[str] = []
            for idx, item in enumerate(value, start=1):
                if item in (None, "", [], {}):
                    continue
                if isinstance(item, dict):
                    item_title = item.get("title") or item.get("name") or item.get("step")
                    sub = cls._render_json_value_ja(item, indent + 1)
                    if sub:
                        if item_title:
                            lines.append(f"{prefix}- **{idx}. {item_title}**\n{sub}")
                        else:
                            lines.append(f"{prefix}- **{idx}.**\n{sub}")
                else:
                    lines.append(f"{prefix}- {item}")
            return "\n".join(lines)
        if isinstance(value, dict):
            lines = []
            for k, v in value.items():
                if k in JSON_SKIP_KEYS or v in (None, "", [], {}):
                    continue
                if isinstance(v, (dict, list)):
                    sub = cls._render_json_value_ja(v, indent + 1)
                    if sub:
                        lines.append(f"{prefix}**{cls._label_ja(k)}**\n{sub}")
                else:
                    lines.append(f"{prefix}- **{cls._label_ja(k)}**: {v}")
            return "\n".join(lines)
        return f"{prefix}{value}"

    def _build_elevator_plan(
        self,
        knowledge_item: Dict[str, Any],
        target_floor: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Knowledgeアイテムからエレベーター階層プランを構築する。
        - モードA (explicit_json): elevator.floors + content["1F_..."] / floors を優先
        - モードB (auto_model_limit): 階数指定がない場合は self.elevator_char_limit ごとに自動分割
        """
        raw_content = knowledge_item.get("content")
        # JSONルートが配列 [{...}] の場合は先頭要素を展開
        if isinstance(raw_content, list) and raw_content and isinstance(raw_content[0], dict):
            data = raw_content[0]
        elif isinstance(raw_content, dict):
            data = raw_content
        else:
            data = knowledge_item

        body_source = data.get("content") if isinstance(data.get("content"), dict) else data

        elevator_cfg = (
            data.get("elevator")
            if isinstance(data, dict) and isinstance(data.get("elevator"), dict)
            else (
                knowledge_item.get("elevator")
                if isinstance(knowledge_item.get("elevator"), dict)
                else (self.last_elevator if isinstance(self.last_elevator, dict) else {})
            )
        ) or {}

        title = str(
            elevator_cfg.get("topic")
            or elevator_cfg.get("title")
            or elevator_cfg.get("name")
            or (data.get("name") if isinstance(data, dict) else None)
            or (data.get("title") if isinstance(data, dict) else None)
            or knowledge_item.get("title")
            or knowledge_item.get("id")
            or "知識ノート"
        )
        source_path = str(
            knowledge_item.get("source_path")
            or knowledge_item.get("path")
            or knowledge_item.get("id")
            or ""
        )

        floors: List[Dict[str, Any]] = []
        mode = "auto_model_limit"

        # content 内の "1F_..." / "2F_..." / "floor_2" / "2_..." キーを階数番号に紐づけるマップ
        floor_content_map: Dict[int, Dict[str, Any]] = {}
        if isinstance(body_source, dict):
            for ck, cv in body_source.items():
                m = re.match(r"^(?:floor_?)?(\d+)(?:[fF階]|_|$)", str(ck))
                if m and isinstance(cv, dict):
                    floor_content_map[int(m.group(1))] = cv

        # モードA: JSONに直接 elevator.floors または floors が書かれている場合
        explicit_floors = None
        if isinstance(elevator_cfg, dict) and elevator_cfg.get("floors"):
            explicit_floors = elevator_cfg.get("floors")
        elif isinstance(data, dict) and data.get("floors"):
            explicit_floors = data.get("floors")

        def floor_materials(*sources: Any) -> Dict[str, str]:
            materials: Dict[str, str] = {}
            for source in sources:
                entries = source.get("materials") if isinstance(source, dict) else None
                if isinstance(entries, dict):
                    materials.update(
                        (name, text) for name, text in entries.items()
                        if isinstance(name, str) and name.strip()
                        and isinstance(text, str) and text.strip()
                    )
            return materials

        if isinstance(explicit_floors, dict) and explicit_floors:
            mode = "explicit_json"

            def _floor_sort_key(kv: Tuple[str, Any]) -> Tuple[int, str]:
                m = re.search(r"\d+", str(kv[0]))
                return (int(m.group(0)) if m else 999, str(kv[0]))

            for idx, (f_key, f_val) in enumerate(
                sorted(explicit_floors.items(), key=_floor_sort_key), start=1
            ):
                m_num = re.search(r"\d+", str(f_key))
                f_num = int(m_num.group(0)) if m_num else idx
                f_label = f"{f_num}F"

                meta_title = f_val.get("title") if isinstance(f_val, dict) else None
                meta_summary = f_val.get("summary") if isinstance(f_val, dict) else None

                detail_block = floor_content_map.get(f_num)
                f_title = str(
                    (detail_block.get("title") if isinstance(detail_block, dict) else None)
                    or meta_title
                    or f_label
                )
                f_summary = str(meta_summary or f"{title} の {f_label} コンテンツ")

                body_parts: List[str] = []
                if isinstance(meta_summary, str) and meta_summary.strip():
                    body_parts.append(f"> {meta_summary.strip()}")

                if isinstance(detail_block, dict):
                    detail_without_title = {
                        k: v for k, v in detail_block.items() if k not in ("title", "materials")
                    }
                    rendered_detail = self._render_json_value_ja(detail_without_title)
                    if rendered_detail:
                        body_parts.append(rendered_detail)
                elif isinstance(f_val, dict):
                    extra_dict = {
                        k: v
                        for k, v in f_val.items()
                        if k not in ("title", "label", "floor", "summary", "materials")
                    }
                    if extra_dict:
                        body_parts.append(self._render_json_value_ja(extra_dict))
                else:
                    body_parts.append(self._render_json_value_ja(f_val))

                floors.append(
                    {
                        "floor": f_num,
                        "label": f_label,
                        "title": f_title,
                        "summary": f_summary,
                        "text": "\n\n".join(p for p in body_parts if p).strip(),
                        "materials": floor_materials(f_val, detail_block),
                    }
                )

        elif isinstance(explicit_floors, list) and explicit_floors:
            mode = "explicit_json"
            for idx, f_val in enumerate(explicit_floors, start=1):
                if isinstance(f_val, dict):
                    f_num = int(f_val.get("floor", idx))
                    f_label = str(f_val.get("label") or f"{f_num}F")
                    detail_block = floor_content_map.get(f_num)
                    f_title = str(
                        (detail_block.get("title") if isinstance(detail_block, dict) else None)
                        or f_val.get("title")
                        or f_label
                    )
                    f_summary = str(f_val.get("summary") or f"{title} の {f_label} コンテンツ")
                    if isinstance(detail_block, dict):
                        f_text = self._render_json_value_ja(
                            {k: v for k, v in detail_block.items() if k not in ("title", "materials")}
                        )
                    else:
                        f_text = self._render_json_value_ja(
                            {k: v for k, v in f_val.items() if k not in ("floor", "label", "title", "materials")}
                        )
                else:
                    f_num = idx
                    f_label = f"{idx}F"
                    f_title = f_label
                    f_summary = f"{title} の {f_label} コンテンツ"
                    f_text = self._render_json_value_ja(f_val)

                floors.append(
                    {
                        "floor": f_num,
                        "label": f_label,
                        "title": f_title,
                        "summary": f_summary,
                        "text": f_text.strip(),
                        "materials": floor_materials(f_val, floor_content_map.get(f_num)),
                    }
                )

        elif floor_content_map:
            mode = "explicit_json"
            for f_num in sorted(floor_content_map.keys()):
                detail_block = floor_content_map[f_num]
                f_title = str(detail_block.get("title") or f"{f_num}F")
                detail_without_title = {
                    k: v for k, v in detail_block.items() if k not in ("title", "materials")
                }
                floors.append(
                    {
                        "floor": f_num,
                        "label": f"{f_num}F",
                        "title": f_title,
                        "summary": f"{title} の {f_num}F：{f_title}",
                        "text": self._render_json_value_ja(detail_without_title).strip(),
                        "materials": floor_materials(detail_block),
                    }
                )

        # モードB: 階数指定がない場合 → モデルの限界文字数で自動分割
        if not floors:
            mode = "auto_model_limit"
            sections: List[str] = []
            if isinstance(body_source, dict):
                for k, v in body_source.items():
                    if k in JSON_SKIP_KEYS or v in (None, "", [], {}):
                        continue
                    body = self._render_json_value_ja(v)
                    if body:
                        sections.append(f"#### {self._label_ja(k)}\n{body}")
            elif isinstance(raw_content, str) and raw_content.strip():
                sections.append(raw_content.strip())

            char_limit = max(200, int(self.elevator_char_limit))
            buf: List[str] = []
            buf_len = 0
            for sec in sections:
                if buf and buf_len + len(sec) > char_limit:
                    idx = len(floors) + 1
                    floors.append(
                        {
                            "floor": idx,
                            "label": f"{idx}F",
                            "title": f"ステップ {idx}",
                            "summary": f"{title} のステップ {idx}",
                            "text": "\n\n".join(buf).strip(),
                        }
                    )
                    buf = [sec]
                    buf_len = len(sec)
                else:
                    buf.append(sec)
                    buf_len += len(sec)
            if buf:
                idx = len(floors) + 1
                floors.append(
                    {
                        "floor": idx,
                        "label": f"{idx}F",
                        "title": f"ステップ {idx}",
                        "summary": f"{title} のステップ {idx}",
                        "text": "\n\n".join(buf).strip(),
                    }
                )

        if not floors:
            floors = [
                {
                    "floor": 1,
                    "label": "1F",
                    "title": title,
                    "summary": f"{title} の概要",
                    "text": "（このナレッジJSONには表示可能な本文が見つかりませんでした）",
                }
            ]

        floors = sorted({entry["floor"]: entry for entry in floors}.values(), key=lambda entry: entry["floor"])
        configured_floor = elevator_cfg.get("current_floor")
        selected_floor = target_floor if target_floor is not None else configured_floor
        current_index = next(
            (index for index, entry in enumerate(floors) if entry["floor"] == selected_floor),
            next((index for index, entry in enumerate(floors) if entry["floor"] == configured_floor), 0),
        )
        current_entry = floors[current_index]
        current_floor = current_entry["floor"]
        max_floor = floors[-1]["floor"]
        previous_floor = floors[current_index - 1]["floor"] if current_index > 0 else None
        next_floor = floors[current_index + 1]["floor"] if current_index + 1 < len(floors) else None

        return {
            "title": title,
            "knowledge_id": str(data.get("id") or knowledge_item.get("id") or title),
            "source_path": source_path,
            "mode": mode,
            "char_limit": self.elevator_char_limit,
            "current_floor": current_floor,
            "max_floor": max_floor,
            "next_floor_number": next_floor,
            "previous_floor_number": previous_floor,
            "has_next": next_floor is not None,
            "has_prev": previous_floor is not None,
            "current_entry": current_entry,
            "floors": [
                {
                    "floor": f["floor"],
                    "label": f["label"],
                    "title": f["title"],
                    "summary": f.get("summary", ""),
                }
                for f in floors
            ],
            "formatted_floor_markdown": self._format_elevator_floor_markdown(
                title=title,
                current_entry=current_entry,
                current_floor=current_floor,
                max_floor=max_floor,
                mode=mode,
                previous_floor=previous_floor,
                next_floor=next_floor,
            ),
        }

    @staticmethod
    def _format_elevator_floor_markdown(
        title: str,
        current_entry: Dict[str, Any],
        current_floor: int,
        max_floor: int,
        mode: str,
        previous_floor: Optional[int] = None,
        next_floor: Optional[int] = None,
    ) -> str:
        label = current_entry.get("label") or f"{current_floor}F"
        floor_title = current_entry.get("title") or ""
        body = current_entry.get("text") or ""

        header = f"### 🛗 {title} 【{label} / {max_floor}F】"
        if floor_title and floor_title not in (label, title):
            header += f" — {floor_title}"

        nav_parts: List[str] = []
        if next_floor is not None:
            nav_parts.append(f"次の階（{next_floor}F）へ進むには **『続けて』**")
        if previous_floor is not None:
            nav_parts.append(f"前の階（{previous_floor}F）へ戻るには **『戻って』**")

        mode_note = "JSON階数指定" if mode == "explicit_json" else "モデル限界値自動分割"
        if nav_parts:
            footer = f"\n\n---\n🛗 {' / '.join(nav_parts)} と入力してください。（{mode_note}）"
        else:
            footer = f"\n\n---\n✅ 最後の階（{max_floor}F）まで完了しました。（{mode_note}）"

        return f"{header}\n\n{body}{footer}"

    def _load_knowledge_item_from_path(self, source_path: str) -> Optional[Dict[str, Any]]:
        """指定または前回ヒットしたKnowledgeファイルを安全に再ロードする"""
        if not source_path:
            return None

        candidates = [
            Path(source_path),
            self.knowledge_dir / source_path,
            self.project_root / source_path,
        ]
        knowledge_root = self.knowledge_dir.resolve()
        target_file = None
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except (OSError, RuntimeError):
                continue
            if resolved.is_relative_to(knowledge_root) and resolved.is_file():
                target_file = resolved
                break
        if target_file is None:
            return None

        try:
            raw_text = target_file.read_text(encoding="utf-8-sig")
            content: Any = (
                json.loads(raw_text)
                if target_file.suffix.lower() == ".json"
                else raw_text
            )
            try:
                rel_id = str(
                    target_file.resolve().relative_to(self.knowledge_dir).with_suffix("")
                ).replace(os.sep, "/")
            except ValueError:
                rel_id = target_file.stem

            first_obj = (
                content[0]
                if isinstance(content, list) and content and isinstance(content[0], dict)
                else (content if isinstance(content, dict) else {})
            )
            return {
                "id": str(first_obj.get("id") or rel_id),
                "title": str(first_obj.get("name") or first_obj.get("title") or target_file.stem),
                "source_path": str(target_file.resolve()),
                "content_type": "json" if isinstance(content, (dict, list)) else "text",
                "content": content,
            }
        except Exception as e:
            print(f"⚠️ [ChatOrchestrator] エレベーター用Knowledge再読込失敗 ({source_path}): {e}")
            return None

    def _resolve_elevator_navigation(self, current_signals: Dict[str, Any]) -> bool:
        """
        保存済みエレベーターの [source:...] 指定や『続けて』『戻って』『2F』『3階』を検知し、
        エレベータープランを確定して current_signals へ安全に保存する。
        戻り値: エレベーター移動コマンドによる即返却対象なら True
        """
        msg = self.message.strip()
        msg_lower = msg.lower()
        prev_state = (
            current_signals.get("elevator_state")
            if isinstance(current_signals, dict)
            else None
        )

        floor_match = re.search(r"([1-9][0-9]?)\s*[fF階]", msg)
        requested_floor: Optional[int] = int(floor_match.group(1)) if floor_match else None
        is_next = msg in NEXT_FLOOR_COMMANDS or msg_lower in NEXT_FLOOR_COMMANDS
        is_prev = msg in PREV_FLOOR_COMMANDS or msg_lower in PREV_FLOOR_COMMANDS
        rephrase_match = re.fullmatch(
            r"(?:(?:(?P<number>[1-9][0-9]?)\s*(?P<unit>[fF階回])|今の階|この階|さっきの説明)"
            r"\s*(?:を|について)?\s*)?(?:もう少し\s*)?"
            r"(?:わかりやすく|分かりやすく|簡単に|やさしく)\s*"
            r"(?:(?:解説|説明|教え)(?:して|て)?\s*(?:ほしい|欲しい|ください)?)?[。！!？?]*",
            msg,
        )
        is_rephrase = False
        if rephrase_match and isinstance(prev_state, dict):
            number = rephrase_match.group("number")
            floor = int(number) if number else prev_state.get("current_floor", 1)
            # 「3回」を階として読むのは、説明対象が現在の3階と一致するときだけ。
            if rephrase_match.group("unit") != "回" or floor == prev_state.get("current_floor"):
                is_rephrase = True
                requested_floor = floor
        is_material_request = isinstance(prev_state, dict) and bool(re.fullmatch(
            r"(?:(?:今の階|この階|ここ)の\s*)?"
            r"(?:(?:資料(?:一覧)?|(?:フォルダ(?:ー)?|ディレクトリ)構成|構成|コード(?:の全文)?|全文|全部)"
            r"\s*(?:を\s*全(?:部|文))?\s*を?\s*)?"
            r"(?:見せて|表示して|全文を書いて)\s*(?:ください)?[。！!？?]*",
            msg,
        ))
        if is_material_request:
            requested_floor = prev_state.get("current_floor", 1)
        is_elevator_command = is_next or is_prev or is_rephrase or is_material_request or (requested_floor is not None)

        # 最優先: 保存済みエレベーターやモーダルからの [source:...] 明示指定
        source_match = re.search(r"\[source:([^\]]+)\]", msg)
        if source_match:
            explicit_path = source_match.group(1).strip()
            reloaded = self._load_knowledge_item_from_path(explicit_path)
            if reloaded is not None:
                plan = self._build_elevator_plan(reloaded, target_floor=requested_floor or 1)
                self._store_elevator_context(plan)
                setattr(self.request, "loaded_knowledge", [reloaded])
                if hasattr(self.prompt_builder, "set_active_knowledge"):
                    self.prompt_builder.set_active_knowledge([reloaded])
                else:
                    self.prompt_builder.active_knowledge = [reloaded]
                print(
                    f"🛗 [ChatOrchestrator] 保存済みエレベーター直接移動: "
                    f"{plan['title']} ({plan['current_floor']}F/{plan['max_floor']}F)"
                )
                return True

        loaded = getattr(self.request, "loaded_knowledge", [])
        real_knowledge = [
            item
            for item in loaded
            if isinstance(item, dict)
            and not str(item.get("id", "")).startswith("system/")
        ]

        target_item: Optional[Dict[str, Any]] = None
        target_floor = requested_floor
        moved_from_prev = False

        if isinstance(prev_state, dict) and is_elevator_command:
            prev_path = str(prev_state.get("source_path") or "")
            prev_floor = int(prev_state.get("current_floor", 1))

            if is_next or is_prev:
                key = "next_floor_number" if is_next else "previous_floor_number"
                if key in prev_state:
                    target_floor = prev_state[key] or prev_floor
                else:
                    max_floor = int(prev_state.get("max_floor", 1))
                    target_floor = min(prev_floor + 1, max_floor) if is_next else max(prev_floor - 1, 1)

            reloaded = self._load_knowledge_item_from_path(prev_path)
            if reloaded is not None:
                target_item = reloaded
                moved_from_prev = True
                setattr(self.request, "loaded_knowledge", [reloaded])
                if hasattr(self.prompt_builder, "set_active_knowledge"):
                    self.prompt_builder.set_active_knowledge([reloaded])
                else:
                    self.prompt_builder.active_knowledge = [reloaded]
                print(
                    f"🛗 [ChatOrchestrator] エレベーター移動: {reloaded.get('id')} -> {target_floor}F"
                )

        if target_item is None and real_knowledge:
            target_item = real_knowledge[0]

        if target_item is not None:
            plan = self._build_elevator_plan(target_item, target_floor=target_floor)
            if is_rephrase and moved_from_prev:
                plan["show_materials"] = False
            if is_rephrase and moved_from_prev and plan["mode"] == "explicit_json":
                entry = plan["current_entry"]
                summary = entry.get("summary", "").strip()
                if summary and summary != f"{plan['title']} の {entry['label']} コンテンツ":
                    plan["formatted_floor_markdown"] = self._format_elevator_floor_markdown(
                        title=plan["title"],
                        current_entry={**entry, "text": summary},
                        current_floor=plan["current_floor"],
                        max_floor=plan["max_floor"],
                        mode=plan["mode"],
                        previous_floor=plan["previous_floor_number"],
                        next_floor=plan["next_floor_number"],
                    )
            self._store_elevator_context(plan)
            print(
                f"🛗 [ChatOrchestrator] elevator_plan確定: {plan['title']} "
                f"({plan['current_floor']}F/{plan['max_floor']}F, mode={plan['mode']})"
            )
            return moved_from_prev or is_elevator_command

        return False

    @staticmethod
    def _is_empty_knowledge_note_reply(message_text: str) -> bool:
        """
        ChatHandler(explanation_formatter)がJSON本文を取りこぼし、
        見出し＋「知識ノートを整理しました！」の定型文だけ返した状態のみ判定する。
        """
        if not message_text or "知識ノートを整理しました！" not in message_text:
            return False
        head = message_text.split("---")[0]
        content_lines = [
            line.strip()
            for line in head.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return len(content_lines) == 0

    ELEVATOR_ENABLED_HANDLERS = {
        "ChatHandler",
        "ChatHandler (Local Fallback)",
        "ElevatorNavigator",
        "ShareHandler",
    }

    def _load_share_elevator(self) -> None:
        """共有の入力に対応するナレッジがない場合、既存のTo Shareナレッジを開く。"""
        for filename in ("to_share_digital_signature.json", "to_share_2_session.json"):
            item = self._load_knowledge_item_from_path(
                str(self.knowledge_dir / "share_to_qr" / filename)
            )
            if item is None:
                continue
            try:
                plan = self._build_elevator_plan(item)
            except (TypeError, ValueError) as exc:
                print(f"⚠️ [ChatOrchestrator] 共有エレベーターの階層設定エラー ({filename}): {exc}")
                continue
            self._store_elevator_context(plan)
            return

    def _attach_elevator_metadata(
        self,
        res_content: Any,
        handler_name: Optional[str] = None,
    ) -> Any:
        active_handler = handler_name or self.last_used_handler
        # APICollectHandler（CKAN等）やコード・DB系ハンドラーの結果には干渉しない
        if active_handler not in self.ELEVATOR_ENABLED_HANDLERS:
            return res_content

        if active_handler == "ShareHandler":
            if (
                not isinstance(res_content, dict)
                or res_content.get("response_type") != "link_navigator"
            ):
                return res_content
            if self.last_elevator is None:
                self._load_share_elevator()

        plan = self.last_elevator_plan
        elevator = self.last_elevator

        if not elevator:
            loaded = getattr(self.request, "loaded_knowledge", [])
            if isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict) and isinstance(item.get("elevator"), dict):
                        elevator = item["elevator"]
                        break
                    if (
                        isinstance(item, dict)
                        and isinstance(item.get("content"), dict)
                        and isinstance(item["content"].get("elevator"), dict)
                    ):
                        elevator = item["content"]["elevator"]
                        break

        if elevator and isinstance(res_content, str):
            res_content = {"message": res_content, "blocks": []}

        if isinstance(res_content, dict):
            if plan and self._is_empty_knowledge_note_reply(str(res_content.get("message", ""))):
                res_content["message"] = plan["formatted_floor_markdown"]

            message = res_content.get("message", "")
            if (
                plan and active_handler != "ShareHandler" and plan.get("show_materials", True)
                and isinstance(message, str)
            ):
                materials = plan["current_entry"].get("materials", {})
                if materials:
                    sections = [f"#### {name}\n\n{text}" for name, text in materials.items()]
                    res_content["message"] = "\n\n".join(
                        [message, *sections] if message else sections
                    )

            if elevator and "elevator" not in res_content:
                res_content["elevator"] = elevator

        # 次ターンの「続けて」「2F」用に現在階を永続化
        if elevator and isinstance(getattr(self, "current_signals", None), dict):
            self.current_signals["elevator_state"] = {
                "title": elevator.get("topic") or elevator.get("title"),
                "knowledge_id": elevator.get("knowledge_id"),
                "source_path": elevator.get("source_path"),
                "current_floor": elevator.get("current_floor", 1),
                "max_floor": elevator.get("max_floor", 1),
                "next_floor_number": elevator.get("next_floor_number"),
                "previous_floor_number": elevator.get("previous_floor_number"),
                "mode": elevator.get("mode", "auto_model_limit"),
            }
            self._save_signals(self.current_signals)

        return res_content

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
                    if not os.path.isdir(search_dir):
                        continue
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

        # 追加検索で初めて実ナレッジが見つかった場合にもエレベータープランを構築
        if self.last_elevator_plan is None:
            real_items = [
                k for k in combined_knowledge
                if isinstance(k, dict) and not str(k.get("id", "")).startswith("system/")
            ]
            if real_items:
                current_floor = int((self.current_signals or {}).get("elevator_floor", 1) or 1)
                plan = self._build_elevator_plan(real_items[0], target_floor=current_floor)
                self._store_elevator_context(plan)

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

    async def _invoke_with_knowledge_fallback(self, handler: Any) -> Any:
        try:
            return await self._invoke_handler(handler)
        except NameError as exc:
            intent = self.message.casefold()
            has_url = "http://" in intent or "https://" in intent
            is_qr_request = has_url and ("qr" in intent or "ｑｒ" in intent)
            if (
                handler.__class__.__name__ != "ChatHandler"
                or exc.name != "_handle_text_url_to_qr"
                or is_qr_request
                or self.last_elevator_plan is None
            ):
                raise
            print(
                "⚠️ [ChatOrchestrator] ChatHandler のQR関数が未定義です。"
                "読み込み済みの階層本文を返します。"
            )
            return "text", {
                "message": self.last_elevator_plan["formatted_floor_markdown"],
                "blocks": [],
            }

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

        # 3. KnowledgeRouter & エレベーター階層解決
        self._route_and_attach_knowledge(current_signals)
        is_elevator_move = self._resolve_elevator_navigation(current_signals)

        # 3.5 エレベーター移動（2F / 3F / 続けて / 戻って / 保存済み [source:...]）は即返却
        if is_elevator_move and self.last_elevator_plan is not None:
            res_content: Dict[str, Any] = {
                "message": self.last_elevator_plan["formatted_floor_markdown"],
                "blocks": [],
            }
            res_content = self._attach_elevator_metadata(res_content, handler_name="ElevatorNavigator")
            self.last_used_handler = "ElevatorNavigator"
            self._save_assistant_response_and_state(res_content)
            return ("text", res_content)

        # 4. Image fast path
        image_data = getattr(self.request, "image_base64", None)
        if image_data:
            try:
                from backend.api.services.tools.QR.link_qr_tool import handle_qr_image_base64
            except ModuleNotFoundError:
                from services.tools.QR.link_qr_tool import handle_qr_image_base64

            qr_res = handle_qr_image_base64(image_data)
            if qr_res:
                self.last_used_handler = "LinkQRTool"
                self._save_assistant_response_and_state(qr_res)
                return ("link_navigator", qr_res)
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
                    result = await self._invoke_with_knowledge_fallback(target_handler)
                except Exception as e:
                    print(f"⚠️ {forced_handler_name} 実行中に例外 ({e}) -> スコアリングへ移行")
                    result = None

                if result is not None and not is_offline_error_response(result):
                    res_type, res_content = result
                    res_content = self._attach_elevator_metadata(res_content, handler_name=forced_handler_name)
                    self.last_used_handler = forced_handler_name
                    self._save_assistant_response_and_state(res_content)
                    return (res_type, res_content)

                print(
                    f"🔄 {forced_handler_name} が未応答またはオフラインのため、ローカルHandler群へフォールバックします。"
                )
            else:
                print(
                    f"⚠️ 指定された {forced_handler_name} は見つかりません。通常のスコアリングへ移行します。"
                )

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
                result = await self._invoke_with_knowledge_fallback(cand_handler)
            except Exception as e:
                print(f"⚠️ {cand_name} で例外発生 ({e}) -> 次の候補Handlerを試行します")
                continue

            if is_offline_error_response(result):
                print(
                    f"🔄 {cand_name} がオフラインまたは未応答のため、次のローカルHandlerへ委譲します"
                )
                continue

            res_type, res_content = result
            res_content = self._attach_elevator_metadata(res_content, handler_name=cand_name)
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
            res_type, res_content = await self._invoke_with_knowledge_fallback(chat_fallback)
            res_content = self._attach_elevator_metadata(res_content)
            self._save_assistant_response_and_state(res_content)
            return (res_type, attach_debug_block(res_content))

        return (
            "text",
            {
                "message": "どのエージェントも処理できませんでした。",
                "blocks": [debug_block],
            },
        )
