"""
CloudFlareAdviceHandler.py
==================================================

Cloudflare専用Advice Handler

役割
--------------------------------------------------
1. ユーザーのCloudflare相談を受け取る
2. Cloudflare関連Knowledgeを検索する
3. 貼り付けられたCloudflare画面テキストを認識する
4. 現在のUI状態を判定する
5. 次に何をすべきかをKnowledgeから取得する
6. 使用したKnowledgeの情報源を返す
7. ChatOrchestrator / ConversationManagerから
   利用しやすい結果形式にまとめる

想定フロー
--------------------------------------------------

ChatOrchestrator
      ↓
IntentInspector
      ↓
CloudFlareAdviceHandler
      ↓
KnowledgeRouter
      ↓
KnowledgeSearchEngine
      ↓
KnowledgeLoader
      ↓
Cloudflare Knowledge JSON
      ↓
UI State Recognition
      ↓
Cloudflare Advice Result

重要
--------------------------------------------------
Cloudflareの画面名・メニュー名は将来変更される可能性がある。

そのため、

    if "Deploy a tunnel" in text:

のようなCloudflare固有のUI判定を大量にPythonへ
ハードコードしない。

UI認識ルールはKnowledge JSON側に置く。

例:

{
    "recognition": {
        "required_text_any": [
            "Cloudflare One"
        ],
        "supporting_text_any": [
            "Recommendations",
            "Deploy a tunnel"
        ]
    }
}

Pythonはこのルールを解釈するだけにする。
==================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


class CloudFlareAdviceHandler:
    """
    Cloudflare相談専用Handler。

    想定:
        handler = CloudFlareAdviceHandler(...)
        result = handler.handle("Cloudflareのこの画面どうすればいい？")

    または:

        result = await handler.handle_async(...)
    """

    # =========================================================
    # 初期化
    # =========================================================

    def __init__(
        self,
        knowledge_dirs: Optional[list[str | Path]] = None,
        manager_base_dir: str | Path = ".",
        manager_target_dirs: Optional[list[str]] = None,
        search_limit: int = 5,
    ):
        """
        Parameters
        ----------
        knowledge_dirs:
            KnowledgeRouter / KnowledgeSearchEngine が検索する
            Knowledgeディレクトリ。

        manager_base_dir:
            KnowledgeManagerのbase_dir。

        manager_target_dirs:
            KnowledgeManagerに渡す相対ディレクトリ。

        search_limit:
            KnowledgeSearchEngineから取得するKnowledge数。
        """

        self.search_limit = search_limit

        # -----------------------------------------------------
        # デフォルトKnowledgeディレクトリ
        # -----------------------------------------------------
        if knowledge_dirs is None:
            project_root = Path(__file__).resolve().parents[3]

            knowledge_dirs = [
                project_root / "backend" / "engine" / "knowledge",
                project_root / "plugin" / "knowledge",
            ]

        self.knowledge_dirs = [
            Path(path).resolve()
            for path in knowledge_dirs
        ]

        self.manager_base_dir = Path(manager_base_dir).resolve()

        self.manager_target_dirs = (
            manager_target_dirs or []
        )

        # -----------------------------------------------------
        # KnowledgeRouter
        # -----------------------------------------------------
        self.router = None

        try:
            from engine.KnowledgeRouter import KnowledgeRouter

            self.router = KnowledgeRouter(
                knowledge_dirs=self.knowledge_dirs
            )

            logger.info(
                "CloudFlareAdviceHandler: KnowledgeRouter initialized"
            )

        except Exception as e:
            logger.warning(
                "KnowledgeRouter initialization failed: %s",
                e
            )

        # -----------------------------------------------------
        # KnowledgeSearchEngine
        # -----------------------------------------------------
        self.search_engine = None

        try:
            from engine.KnowledgeSearchEngine import (
                KnowledgeSearchEngine
            )

            self.search_engine = KnowledgeSearchEngine(
                knowledge_dirs=self.knowledge_dirs,
                manager_base_dir=self.manager_base_dir,
                manager_target_dirs=self.manager_target_dirs,
                default_limit=self.search_limit,
            )

            logger.info(
                "CloudFlareAdviceHandler: "
                "KnowledgeSearchEngine initialized"
            )

        except Exception as e:
            logger.warning(
                "KnowledgeSearchEngine initialization failed: %s",
                e
            )

    # =========================================================
    # Public API
    # =========================================================

    def handle(
        self,
        message: str,
        *,
        screen_text: Optional[str] = None,
        intent: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Cloudflare相談を処理する。

        Parameters
        ----------
        message:
            ユーザーの質問。

        screen_text:
            Cloudflare画面からコピーしたテキスト。
            ユーザーが画面を貼り付けた場合はこちらへ渡す。

        intent:
            IntentInspectorから渡される意図情報。

        context:
            ContextManager等から渡される会話コンテキスト。

        Returns
        -------
        dict
            Handler結果。
        """

        message = self._normalize_text(message)

        if not message:
            return self._error_result(
                "Cloudflareへの質問内容が空です。"
            )

        # -----------------------------------------------------
        # 1. 検索対象テキストを作る
        # -----------------------------------------------------

        combined_text = message

        if screen_text:
            combined_text += "\n\n[Cloudflare Screen]\n"
            combined_text += screen_text

        # -----------------------------------------------------
        # 2. Cloudflare Knowledgeを検索
        # -----------------------------------------------------

        knowledge_result = self._search_knowledge(
            combined_text
        )

        # -----------------------------------------------------
        # 3. UI状態を判定
        # -----------------------------------------------------

        ui_state = self._detect_ui_state(
            screen_text=screen_text,
            knowledge_items=knowledge_result.get(
                "items",
                []
            ),
        )

        # -----------------------------------------------------
        # 4. 次のアクションを抽出
        # -----------------------------------------------------

        next_action = self._extract_next_action(
            ui_state
        )

        # -----------------------------------------------------
        # 5. 回答用Promptを生成
        # -----------------------------------------------------

        prompt = self._build_advice_prompt(
            message=message,
            screen_text=screen_text,
            intent=intent,
            context=context,
            knowledge_items=knowledge_result.get(
                "items",
                []
            ),
            ui_state=ui_state,
            next_action=next_action,
        )

        # -----------------------------------------------------
        # 6. 情報源を保存可能な形にする
        # -----------------------------------------------------

        sources = self._build_sources(
            knowledge_result.get(
                "items",
                []
            ),
            ui_state,
        )

        # -----------------------------------------------------
        # 7. Result
        # -----------------------------------------------------

        return {
            "status": "success",

            "handler": "CloudFlareAdviceHandler",

            "domain": "cloudflare",

            "message": message,

            "prompt": prompt,

            "ui_state": ui_state,

            "next_action": next_action,

            "knowledge_sources": sources,

            "knowledge_errors": knowledge_result.get(
                "errors",
                []
            ),

            "meta": {
                "knowledge_count": len(
                    knowledge_result.get(
                        "items",
                        []
                    )
                ),
                "screen_text_provided": bool(
                    screen_text
                ),
                "intent": intent or {},
            },
        }

    # =========================================================
    # Async
    # =========================================================

    async def handle_async(
        self,
        message: str,
        *,
        screen_text: Optional[str] = None,
        intent: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:

        return await asyncio.to_thread(
            self.handle,
            message,
            screen_text=screen_text,
            intent=intent,
            context=context,
        )

    # =========================================================
    # Knowledge Search
    # =========================================================

    def _search_knowledge(
        self,
        message: str,
    ) -> dict[str, Any]:
        """
        KnowledgeRouter → KnowledgeSearchEngine
        の検索を行う。

        現在のKnowledgeSearchEngine.search()は
        Prompt文字列を返す実装なので、

        1. Routerで候補ファイルを取得
        2. SearchEngineでPrompt生成
        3. Loaderで実ファイルを取得

        の3段階にしている。

        これにより、最終的に
        knowledge_sourcesを取得できる。
        """

        result = {
            "prompt": "",
            "items": [],
            "errors": [],
            "paths": [],
        }

        # -----------------------------------------------------
        # Routerが利用できない場合
        # -----------------------------------------------------

        if self.router is None:
            logger.warning(
                "KnowledgeRouter is not available."
            )

            return result

        try:

            route_result = self.router.route(
                message
            )

            file_paths = list(
                getattr(
                    route_result,
                    "file_paths",
                    []
                )
                or []
            )

            result["paths"] = file_paths

            logger.info(
                "Cloudflare Knowledge candidates: %d",
                len(file_paths)
            )

            if not file_paths:
                return result

            # -------------------------------------------------
            # SearchEngine
            # -------------------------------------------------

            if self.search_engine is not None:

                try:

                    result["prompt"] = (
                        self.search_engine.search(
                            message,
                            file_paths,
                            limit=self.search_limit,
                        )
                    )

                except Exception as e:

                    logger.exception(
                        "KnowledgeSearchEngine error"
                    )

                    result["errors"].append(
                        {
                            "type": "search_error",
                            "message": str(e),
                        }
                    )

            # -------------------------------------------------
            # Loader
            # -------------------------------------------------

            loader = getattr(
                self.search_engine,
                "loader",
                None,
            )

            if loader is None:

                try:
                    from engine.KnowledgeLoader import (
                        KnowledgeLoader
                    )

                    loader = KnowledgeLoader(
                        knowledge_dirs=self.knowledge_dirs
                    )

                except Exception as e:

                    logger.warning(
                        "KnowledgeLoader initialization failed: %s",
                        e
                    )

                    return result

            try:

                load_result = loader.load(
                    file_paths
                )

                result["items"] = list(
                    getattr(
                        load_result,
                        "items",
                        []
                    )
                    or []
                )

                for error in getattr(
                    load_result,
                    "errors",
                    []
                ):

                    result["errors"].append(
                        {
                            "path": getattr(
                                error,
                                "path",
                                ""
                            ),
                            "reason": getattr(
                                error,
                                "reason",
                                ""
                            ),
                            "detail": getattr(
                                error,
                                "detail",
                                ""
                            ),
                        }
                    )

            except Exception as e:

                logger.exception(
                    "KnowledgeLoader error"
                )

                result["errors"].append(
                    {
                        "type": "loader_error",
                        "message": str(e),
                    }
                )

        except Exception as e:

            logger.exception(
                "Cloudflare Knowledge routing error"
            )

            result["errors"].append(
                {
                    "type": "routing_error",
                    "message": str(e),
                }
            )

        return result

    # =========================================================
    # UI State Detection
    # =========================================================

    def _detect_ui_state(
        self,
        screen_text: Optional[str],
        knowledge_items: list[Any],
    ) -> dict[str, Any]:
        """
        Knowledge JSON内のrecognition設定を使って
        Cloudflare UI状態を判定する。

        Python側にCloudflare UI名をハードコードしない。

        JSON側:

        recognition:
            required_text_any:
            supporting_text_any:
            negative_text_any:

        を利用する。
        """

        if not screen_text:
            return {
                "detected": False,
                "state_id": None,
                "label": None,
                "confidence": 0.0,
                "matched_sources": [],
                "matched_text": [],
                "reason": "screen_text_not_provided",
            }

        normalized_screen = self._normalize_for_match(
            screen_text
        )

        candidates = []

        for item in knowledge_items:

            content = getattr(
                item,
                "content",
                None
            )

            path = getattr(
                item,
                "path",
                ""
            )

            if not isinstance(
                content,
                dict
            ):
                continue

            # -------------------------------------------------
            # recognition取得
            # -------------------------------------------------

            recognition = content.get(
                "recognition",
                {}
            )

            if not isinstance(
                recognition,
                dict
            ):
                continue

            required = self._as_string_list(
                recognition.get(
                    "required_text_any",
                    []
                )
            )

            supporting = self._as_string_list(
                recognition.get(
                    "supporting_text_any",
                    []
                )
            )

            negative = self._as_string_list(
                recognition.get(
                    "negative_text_any",
                    []
                )
            )

            # -------------------------------------------------
            # Match
            # -------------------------------------------------

            required_matches = self._find_matches(
                normalized_screen,
                required
            )

            supporting_matches = self._find_matches(
                normalized_screen,
                supporting
            )

            negative_matches = self._find_matches(
                normalized_screen,
                negative
            )

            # -------------------------------------------------
            # 必須条件がある場合
            # -------------------------------------------------

            if required:

                if not required_matches:
                    continue

            # -------------------------------------------------
            # Negativeがある場合は状態候補から除外
            # -------------------------------------------------

            if negative_matches:
                continue

            # -------------------------------------------------
            # Confidence
            # -------------------------------------------------

            score = 0.0

            if required:
                score += 0.60

            if supporting_matches:
                score += min(
                    0.30,
                    0.05 * len(
                        supporting_matches
                    )
                )

            # Requiredが無く、supportingだけの場合
            if not required and supporting_matches:
                score = min(
                    0.75,
                    0.15 * len(
                        supporting_matches
                    )
                )

            if score <= 0:
                continue

            # -------------------------------------------------
            # State情報
            # -------------------------------------------------

            state = content.get(
                "state",
                {}
            )

            if not isinstance(
                state,
                dict
            ):
                state = {}

            interpretation = content.get(
                "interpretation",
                {}
            )

            if not isinstance(
                interpretation,
                dict
            ):
                interpretation = {}

            candidates.append(
                {
                    "state_id": state.get(
                        "id",
                        content.get(
                            "id",
                            path
                        )
                    ),

                    "label": state.get(
                        "label",
                        content.get(
                            "name",
                            path
                        )
                    ),

                    "status": state.get(
                        "status"
                    ),

                    "confidence": round(
                        min(score, 1.0),
                        3
                    ),

                    "matched_sources": [
                        path
                    ],

                    "matched_text": (
                        required_matches
                        + supporting_matches
                    ),

                    "required_matches": (
                        required_matches
                    ),

                    "supporting_matches": (
                        supporting_matches
                    ),

                    "interpretation": interpretation,

                    "content": content,
                }
            )

        # -----------------------------------------------------
        # 候補なし
        # -----------------------------------------------------

        if not candidates:

            return {
                "detected": False,
                "state_id": None,
                "label": None,
                "confidence": 0.0,
                "matched_sources": [],
                "matched_text": [],
                "reason": "no_ui_state_matched",
            }

        # -----------------------------------------------------
        # Confidence順
        # -----------------------------------------------------

        candidates.sort(
            key=lambda x: x[
                "confidence"
            ],
            reverse=True
        )

        best = candidates[0]

        return {
            "detected": True,

            "state_id": best[
                "state_id"
            ],

            "label": best[
                "label"
            ],

            "status": best.get(
                "status"
            ),

            "confidence": best[
                "confidence"
            ],

            "matched_sources": best[
                "matched_sources"
            ],

            "matched_text": best[
                "matched_text"
            ],

            "required_matches": best[
                "required_matches"
            ],

            "supporting_matches": best[
                "supporting_matches"
            ],

            "interpretation": best[
                "interpretation"
            ],

            "candidate_count": len(
                candidates
            ),
        }

    # =========================================================
    # Next Action
    # =========================================================

    def _extract_next_action(
        self,
        ui_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        UI Stateから次に何をすべきかを取得する。
        """

        if not ui_state.get(
            "detected",
            False
        ):
            return {
                "available": False,
                "action": None,
                "reason": "ui_state_not_detected",
            }

        interpretation = ui_state.get(
            "interpretation",
            {}
        )

        if not isinstance(
            interpretation,
            dict
        ):
            interpretation = {}

        next_action = interpretation.get(
            "next_recommended_action"
        )

        user_action_required = interpretation.get(
            "user_action_required"
        )

        waiting_required = interpretation.get(
            "waiting_required"
        )

        return {
            "available": bool(
                next_action
                or user_action_required
                or waiting_required
            ),

            "action": next_action,

            "user_action_required": (
                user_action_required
            ),

            "waiting_required": (
                waiting_required
            ),

            "parallel_action": interpretation.get(
                "parallel_action"
            ),

            "meaning": interpretation.get(
                "meaning"
            ),
        }

    # =========================================================
    # Prompt Builder
    # =========================================================

    def _build_advice_prompt(
        self,
        *,
        message: str,
        screen_text: Optional[str],
        intent: Optional[dict[str, Any]],
        context: Optional[dict[str, Any]],
        knowledge_items: list[Any],
        ui_state: dict[str, Any],
        next_action: dict[str, Any],
    ) -> str:
        """
        最終AIに渡すためのCloudflare専用Promptを作る。

        ここではAI自身にUI状態を推測させるのではなく、
        Handlerで判定した状態を明示する。
        """

        lines = []

        lines.append(
            "あなたはCloudflare設定を支援するアシスタントです。"
        )

        lines.append(
            "以下のKnowledgeとUI状態を根拠として回答してください。"
        )

        lines.append(
            "Knowledgeに存在しない設定状況を断定しないでください。"
        )

        lines.append(
            "CloudflareのUI名称が変更されている可能性があるため、"
            "文字列そのものだけでなく画面の意味を優先してください。"
        )

        lines.append("")

        # -----------------------------------------------------
        # User
        # -----------------------------------------------------

        lines.append(
            "【ユーザーの質問】"
        )

        lines.append(
            message
        )

        # -----------------------------------------------------
        # Intent
        # -----------------------------------------------------

        if intent:

            lines.append("")
            lines.append(
                "【IntentInspectorの判定】"
            )

            lines.append(
                self._safe_json(
                    intent
                )
            )

        # -----------------------------------------------------
        # Screen
        # -----------------------------------------------------

        if screen_text:

            lines.append("")
            lines.append(
                "【Cloudflare画面テキスト】"
            )

            # あまりにも巨大な画面テキストが
            # Promptを圧迫しないように制限
            lines.append(
                screen_text[:12000]
            )

        # -----------------------------------------------------
        # UI State
        # -----------------------------------------------------

        lines.append("")
        lines.append(
            "【検出されたUI状態】"
        )

        lines.append(
            self._safe_json(
                {
                    "detected": ui_state.get(
                        "detected"
                    ),
                    "state_id": ui_state.get(
                        "state_id"
                    ),
                    "label": ui_state.get(
                        "label"
                    ),
                    "status": ui_state.get(
                        "status"
                    ),
                    "confidence": ui_state.get(
                        "confidence"
                    ),
                    "matched_text": ui_state.get(
                        "matched_text"
                    ),
                }
            )
        )

        # -----------------------------------------------------
        # Next Action
        # -----------------------------------------------------

        lines.append("")
        lines.append(
            "【推奨される次の操作】"
        )

        lines.append(
            self._safe_json(
                next_action
            )
        )

        # -----------------------------------------------------
        # Knowledge
        # -----------------------------------------------------

        lines.append("")
        lines.append(
            "【関連Knowledge】"
        )

        for index, item in enumerate(
            knowledge_items,
            start=1
        ):

            path = getattr(
                item,
                "path",
                ""
            )

            description = getattr(
                item,
                "description",
                ""
            )

            content = getattr(
                item,
                "content",
                None
            )

            lines.append(
                f"\n--- Knowledge {index} ---"
            )

            lines.append(
                f"source: {path}"
            )

            if description:

                lines.append(
                    f"description: {description}"
                )

            lines.append(
                self._safe_json(
                    content
                )
            )

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        if context:

            lines.append("")
            lines.append(
                "【会話コンテキスト】"
            )

            lines.append(
                self._safe_json(
                    context
                )
            )

        # -----------------------------------------------------
        # Answer policy
        # -----------------------------------------------------

        lines.append("")
        lines.append(
            "【回答ルール】"
        )

        lines.append(
            "1. 現在の状態を最初に簡潔に説明する。"
        )

        lines.append(
            "2. 次に何をすればよいかを具体的に説明する。"
        )

        lines.append(
            "3. 画面上に実際に存在する文言を使える場合は引用する。"
        )

        lines.append(
            "4. 設定完了を確認できない場合は「完了」と断定しない。"
        )

        lines.append(
            "5. DNS浸透など待機状態なら、"
            "不要な操作を勧めず待つべきことを説明する。"
        )

        lines.append(
            "6. Knowledgeにない情報は推測で補完しない。"
        )

        return "\n".join(
            lines
        )

    # =========================================================
    # Source Tracking
    # =========================================================

    def _build_sources(
        self,
        knowledge_items: list[Any],
        ui_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Conversation JSONへ保存できる
        knowledge_sourcesを生成する。
        """

        sources = []

        matched_paths = set(
            ui_state.get(
                "matched_sources",
                []
            )
        )

        for item in knowledge_items:

            path = getattr(
                item,
                "path",
                ""
            )

            if not path:
                continue

            source_type = (
                "ui_state"
                if path in matched_paths
                else "knowledge"
            )

            sources.append(
                {
                    "path": path,

                    "domain": getattr(
                        item,
                        "domain_label",
                        ""
                    ),

                    "content_type": getattr(
                        item,
                        "content_type",
                        ""
                    ),

                    "description": getattr(
                        item,
                        "description",
                        ""
                    ),

                    "used": True,

                    "source_type": source_type,
                }
            )

        return sources

    # =========================================================
    # Text Utilities
    # =========================================================

    @staticmethod
    def _normalize_text(
        text: str
    ) -> str:

        return str(
            text or ""
        ).strip()

    @staticmethod
    def _normalize_for_match(
        text: str
    ) -> str:
        """
        UI判定用の正規化。

        大文字小文字・全角半角などの差を
        できるだけ吸収する。
        """

        text = str(
            text or ""
        )

        text = text.replace(
            "\u3000",
            " "
        )

        text = text.lower()

        # 連続空白を統一
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    @staticmethod
    def _as_string_list(
        value: Any
    ) -> list[str]:

        if value is None:
            return []

        if isinstance(
            value,
            str
        ):
            return [value]

        if isinstance(
            value,
            (list, tuple, set)
        ):
            return [
                str(x)
                for x in value
                if x is not None
            ]

        return []

    def _find_matches(
        self,
        normalized_text: str,
        patterns: list[str],
    ) -> list[str]:
        """
        JSONの認識候補のうち、
        実際に画面テキストに存在したものを返す。
        """

        matches = []

        for pattern in patterns:

            normalized_pattern = (
                self._normalize_for_match(
                    pattern
                )
            )

            if not normalized_pattern:
                continue

            if normalized_pattern in normalized_text:

                matches.append(
                    pattern
                )

        return matches

    # =========================================================
    # JSON Utility
    # =========================================================

    @staticmethod
    def _safe_json(
        value: Any
    ) -> str:

        try:

            return json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        except Exception:

            return str(value)

    # =========================================================
    # Error
    # =========================================================

    @staticmethod
    def _error_result(
        message: str
    ) -> dict[str, Any]:

        return {
            "status": "error",

            "handler": (
                "CloudFlareAdviceHandler"
            ),

            "domain": "cloudflare",

            "message": message,

            "prompt": "",

            "ui_state": {
                "detected": False,
                "state_id": None,
                "confidence": 0.0,
            },

            "next_action": {
                "available": False,
                "action": None,
            },

            "knowledge_sources": [],

            "knowledge_errors": [],
        }


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s: "
            "%(message)s"
        ),
    )

    # ---------------------------------------------------------
    # テスト用Cloudflare画面
    # ---------------------------------------------------------

    sample_screen = """
    Overview

    Cloudflare One

    Connect and secure your users, networks, agents, and data
    with Zero Trust security.

    Recommendations

    Deploy a tunnel

    Plan

    Zero Trust Free

    Team name

    sweet-voice-81a1
    """

    handler = CloudFlareAdviceHandler()

    result = handler.handle(
        "このCloudflare Oneの画面についてどうすればいい？",
        screen_text=sample_screen,
        intent={
            "type": "cloudflare_setup",
            "target": "tunnel",
        },
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "CloudFlareAdviceHandler Test"
    )

    print(
        "=" * 70
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )