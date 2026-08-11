# from __future__ import annotations

# import logging
# from pathlib import Path
# from typing import Any, Optional, Tuple

# from ......plugins.project_builder.base_handler import BaseHandler
# from api.services.inspectors.IntentInSpector import IntentInspector

# from engine.KnowledgeRouter import KnowledgeRouter
# from engine.KnowledgeSearchEngine import KnowledgeSearchEngine
# from engine.orchestrator.knowledge_orchestra import KnowledgeOrchestra
# # ▼ 1. knowledge_orchestra のクラスをインポート（※パスやクラス名は実際の環境に合わせてください）
# # from backend.engine.orchestrator.knowledge_orchestra import KnowledgeOrchestra

# logger = logging.getLogger(__name__)

# DEPLOYMENT_COMMANDS = {"/deploy", "/deployment", "/project"}



# class DeploymentHandler(BaseHandler):
#     def __init__(
#         self,
#         knowledge_dirs: list[str | Path],
#         manager_base_dir: str | Path = ".",
#         manager_target_dirs: Optional[list[str]] = None,
#         threshold: int = 1,
#         top_k: int | None = 8,
#         cache_enabled: bool = True,
#     ):
#         self.knowledge_dirs = [Path(p).resolve() for p in knowledge_dirs]
#         if not self.knowledge_dirs:
#             raise ValueError("knowledge_dirs is empty")

#         self.router = KnowledgeRouter(
#             knowledge_dir=str(self.knowledge_dirs[0]),
#             threshold=threshold,
#             top_k=top_k,
#         )

#         self.search_engine = KnowledgeSearchEngine(
#             knowledge_dirs=self.knowledge_dirs,
#             cache_enabled=cache_enabled,
#             manager_base_dir=manager_base_dir,
#             manager_target_dirs=manager_target_dirs or [],
#             default_limit=5,
#         )

#         self.detected_surface: Optional[str] = None
#         self.detected_theme: Optional[str] = None
        
#         self.knowledge_orchestra = KnowledgeOrchestra(
#             base_dir=str(manager_base_dir)
#         )
#         # ▼ 3. self.knowledge_orchestra を定義する
#         # self.knowledge_orchestra = knowledge_orchestra or KnowledgeOrchestra()

#     # ... (_get_text, estimate_size, can_handle, calculate_score は変更なしのため省略) ...

#     async def handle(self, message: Any) -> Tuple[str, Any]:
#         user_text = self._get_text(message)

#         try:
#             # 1) Router候補
#             route_result = self.router.route(
#                 user_text,
#                 signals={"active_context": self.detected_theme or self.detected_surface},
#             )

#             if not route_result.file_paths:
#                 return "text", "関連するナレッジが見つかりませんでした。"

#             # 2) SearchEngine統合実行
#             prompt = self.search_engine.search(
#                 message=user_text,
#                 file_paths=route_result.file_paths,
#                 use_manager_prefilter=True,
#                 manager_force_rebuild=False,
#                 limit=5,
#             )

#             # ▼▼▼ 4. ここにCopilotのガード処理を追加 ▼▼▼
#             blocked, guard_message = self.knowledge_orchestra.guard_before_finalize(
#                 relative_dir_path="analyzed_results",
#                 force_rebuild=False,
#                 latest_only=True,
#             )
#             if blocked:
#                 # ブロックされた場合はガードメッセージを返す
#                 return "text", guard_message
#             return "text", prompt

#         except Exception as e:
#             logger.exception("DeploymentHandler error: %s", e)
#             return "text", f"DeploymentHandler error: {e}"
        
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

from api.services.handlers.base_handler import BaseHandler
from api.services.inspectors.IntentInSpector import IntentInspector

from engine.KnowledgeRouter import KnowledgeRouter
from engine.KnowledgeSearchEngine import KnowledgeSearchEngine
from engine.orchestrator.knowledge_orchestra import KnowledgeOrchestra


logger = logging.getLogger(__name__)


# =========================================================
# Deployment command
# =========================================================

DEPLOYMENT_COMMANDS = {
    "/deploy",
    "/deployment",
    "/project",
}


# =========================================================
# DeploymentHandler
# =========================================================

class DeploymentHandler(BaseHandler):
    """
    DeploymentHandler

    役割
    ---------------------------------------------------------
    ・プロジェクト/デプロイ関連の要求を検出
    ・KnowledgeRouterによる関連ナレッジ探索
    ・KnowledgeSearchEngineによる詳細検索
    ・KnowledgeOrchestraによる最終ガード
    ・DecompositionHandlerなど上位Handlerへ解析結果を返す

    注意
    ---------------------------------------------------------
    このHandler自身はJS生成やフォルダー生成を担当しない。

    それらはDecompositionHandler / ProjectBuilderHandler
    などの責務とする。

    DeploymentHandlerは
    「デプロイ・プロジェクト関連情報の解析担当」
    として動作する。
    """

    def __init__(
        self,
        knowledge_dirs: list[str | Path],
        manager_base_dir: str | Path = ".",
        manager_target_dirs: Optional[list[str]] = None,
        threshold: int = 1,
        top_k: int | None = 8,
        cache_enabled: bool = True,
    ):
        super().__init__()

        # -----------------------------------------------------
        # Knowledge directory
        # -----------------------------------------------------

        self.knowledge_dirs = [
            Path(p).resolve()
            for p in knowledge_dirs
        ]

        if not self.knowledge_dirs:
            raise ValueError(
                "knowledge_dirs is empty"
            )

        # -----------------------------------------------------
        # Knowledge Router
        # -----------------------------------------------------

        self.router = KnowledgeRouter(
            knowledge_dir=str(
                self.knowledge_dirs[0]
            ),
            threshold=threshold,
            top_k=top_k,
        )

        # -----------------------------------------------------
        # Knowledge Search Engine
        # -----------------------------------------------------

        self.search_engine = KnowledgeSearchEngine(
            knowledge_dirs=self.knowledge_dirs,
            cache_enabled=cache_enabled,
            manager_base_dir=manager_base_dir,
            manager_target_dirs=(
                manager_target_dirs or []
            ),
            default_limit=5,
        )

        # -----------------------------------------------------
        # Knowledge Orchestra
        # -----------------------------------------------------

        self.knowledge_orchestra = KnowledgeOrchestra(
            base_dir=str(manager_base_dir)
        )

        # -----------------------------------------------------
        # Runtime state
        # -----------------------------------------------------

        self.detected_surface: Optional[str] = None
        self.detected_theme: Optional[str] = None
        self.detected_mode: Optional[str] = None

    # =========================================================
    # Message utility
    # =========================================================

    def _get_text(self, message: Any) -> str:
        """
        どんな入力形式でも安全に文字列へ変換する。
        """

        if isinstance(message, str):
            return message

        if isinstance(message, dict):
            return str(
                message.get(
                    "message",
                    message.get(
                        "text",
                        message.get(
                            "content",
                            message,
                        ),
                    ),
                )
            )

        if hasattr(message, "message"):
            return str(message.message)

        if hasattr(message, "text"):
            return str(message.text)

        if hasattr(message, "content"):
            return str(message.content)

        return str(message)

    # =========================================================
    # Estimate size
    # =========================================================

    def estimate_size(self, message: Any) -> int:
        """
        Handler処理量の概算。

        ChatOrchestratorの競合判定で使用する。
        """

        text = self._get_text(message)

        base_size = 3000

        if len(text) > 1000:
            base_size += 3000

        if len(text) > 5000:
            base_size += 5000

        return base_size

    # =========================================================
    # can_handle
    # =========================================================

    async def can_handle(self, message: Any) -> bool:
        """
        Deployment / project 系の要求か簡易判定する。
        """

        text = self._get_text(message)
        lower = text.lower().strip()

        # -----------------------------------------------------
        # 明示的コマンド
        # -----------------------------------------------------

        if any(
            command in lower
            for command in DEPLOYMENT_COMMANDS
        ):
            return True

        # -----------------------------------------------------
        # Deployment系キーワード
        # -----------------------------------------------------

        keywords = [
            "deploy",
            "deployment",
            "デプロイ",
            "公開",
            "本番環境",
            "公開する",
            "公開したい",
            "デプロイしたい",
            "プロジェクトを配置",
            "プロジェクトを公開",
        ]

        if any(
            keyword in lower
            for keyword in keywords
        ):
            return True

        return False

    # =========================================================
    # calculate_score
    # =========================================================

    async def calculate_score(
        self,
        message: Any,
        signals: Optional[dict] = None,
    ) -> int:
        """
        ChatOrchestrator用のHandlerスコア。

        IntentInspectorの結果を利用しつつ、
        Deployment固有の要求だけを高く評価する。
        """

        text = self._get_text(message)
        lower = text.lower().strip()

        # -----------------------------------------------------
        # IntentInspector
        # -----------------------------------------------------

        try:
            inspector = IntentInspector(text)
            analysis = inspector.inspect()

            self.detected_mode = analysis.get(
                "mode"
            )

            # IntentInspectorが明示的に別Handlerを
            # 指定している場合はDeploymentを横取りしない。
            forced_handler = analysis.get(
                "forced_handler"
            )

            if (
                forced_handler
                and forced_handler
                != "DeploymentHandler"
            ):
                return 0

        except Exception as e:
            logger.warning(
                "IntentInspector failed: %s",
                e,
            )

        # -----------------------------------------------------
        # 明示的Deployment command
        # -----------------------------------------------------

        if any(
            command in lower
            for command in DEPLOYMENT_COMMANDS
        ):
            return 100

        # -----------------------------------------------------
        # 強いDeployment keyword
        # -----------------------------------------------------

        strong_keywords = [
            "デプロイ",
            "deploy",
            "本番環境",
            "公開する",
            "公開したい",
            "デプロイする",
            "デプロイしたい",
        ]

        if any(
            keyword in lower
            for keyword in strong_keywords
        ):
            return 90

        # -----------------------------------------------------
        # Cloud / Hosting
        # -----------------------------------------------------

        cloud_keywords = [
            "cloudflare",
            "workers",
            "pages",
            "vercel",
            "netlify",
            "docker",
            "hosting",
            "サーバーへ配置",
            "サーバーに配置",
        ]

        if any(
            keyword in lower
            for keyword in cloud_keywords
        ):
            return 80

        # -----------------------------------------------------
        # Project deployment
        # -----------------------------------------------------

        project_keywords = [
            "プロジェクトを配置",
            "プロジェクトを公開",
            "アプリを公開",
            "アプリをデプロイ",
        ]

        if any(
            keyword in lower
            for keyword in project_keywords
        ):
            return 80

        return 0

    # =========================================================
    # handle
    # =========================================================

    async def handle(
        self,
        message: Any,
    ) -> Tuple[str, Any]:
        """
        Deployment / Project解析を実行する。
        """

        user_text = self._get_text(message)

        logger.info(
            "🚀 DeploymentHandler 発動: %s",
            user_text[:100],
        )

        try:
            # -------------------------------------------------
            # 1. Knowledge Router
            # -------------------------------------------------

            route_result = self.router.route(
                user_text,
                signals={
                    "active_context": (
                        self.detected_theme
                        or self.detected_surface
                    )
                },
            )

            # -------------------------------------------------
            # Router結果の安全な取得
            # -------------------------------------------------

            file_paths = getattr(
                route_result,
                "file_paths",
                None,
            )

            if file_paths is None:
                file_paths = []

            if not file_paths:
                logger.info(
                    "🔍 DeploymentHandler: "
                    "関連ナレッジが見つかりませんでした"
                )

                return "text", {
                    "message":
                        "デプロイ・プロジェクト関連のナレッジが見つかりませんでした。",
                    "blocks": [],
                }

            # -------------------------------------------------
            # 2. Knowledge Search
            # -------------------------------------------------

            prompt = self.search_engine.search(
                message=user_text,
                file_paths=file_paths,
                use_manager_prefilter=True,
                manager_force_rebuild=False,
                limit=5,
            )

            # -------------------------------------------------
            # 3. Knowledge Orchestra Guard
            # -------------------------------------------------

            blocked, guard_message = (
                self.knowledge_orchestra
                .guard_before_finalize(
                    relative_dir_path="analyzed_results",
                    force_rebuild=False,
                    latest_only=True,
                )
            )

            if blocked:
                logger.warning(
                    "🛡️ DeploymentHandler: "
                    "KnowledgeOrchestraによりブロックされました"
                )

                return "text", {
                    "message": str(
                        guard_message
                    ),
                    "blocks": [],
                }

            # -------------------------------------------------
            # 4. Response
            # -------------------------------------------------

            content = {
                "message": str(prompt),
                "blocks": [
                    {
                        "type": "DeploymentAnalysisBlock",
                        "props": {
                            "handler":
                                "DeploymentHandler",
                            "fileCount":
                                len(file_paths),
                            "files":
                                [
                                    str(path)
                                    for path in file_paths
                                ],
                        },
                    }
                ],
            }

            return "ui_code", content

        except Exception as e:
            logger.exception(
                "DeploymentHandler error"
            )

            return "text", {
                "message":
                    f"DeploymentHandler error: {e}",
                "blocks": [],
            }