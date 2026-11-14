"""
backend/engine/orchestrator/chat_orchestrator/handler_registry.py

全Handlerの安全なimportと初期化リストの構築を担当するモジュール。
新しいHandler（SecurityAuditHandler等）を追加する際はこのファイルのみを編集すればよい。
"""
from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Callable, List

from api.services.handlers.Python.PythonCodeHandler import PythonCodeHandler
from api.services.handlers.project.repomix_Handler import RepomixHandler
from api.services.handlers.analysis.ocr_recruit_handler import OcrRecruitHandler
from api.services.handlers.github_handler import GithubHandler
from api.services.handlers.recruit_handler import RecruitHandler
from api.services.handlers.weather_handler import WeatherHandler
from api.services.handlers.database_handler import DatabaseHandler
from api.services.handlers.ollama_handler import OllamaHandler
from api.services.handlers.offline_handler import OfflineFallbackHandler
from api.services.handlers.Scraping_Handler import ScrapingHandler
from api.services.handlers.DesignHandler import DesignHandler
from api.services.handlers.code.HtmlHandler import HTMLHandler
from api.services.handlers.project.DeploymentHandler import DeploymentHandler
from api.services.handlers.ChatHandler import ChatHandler
from api.services.handlers.KnowledgeHealthHandler import KnowledgeHealthHandler
from api.services.handlers.KnowledgeReloadHandler import KnowledgeReloadHandler
from api.services.handlers.code.ConversionJsonHandler import ConversionJsonHandler
from api.services.handlers.code.PHPHandler import PhpHandler
from api.services.handlers.Ckan_API_Collect_handler import APICollectHandler
from api.services.handlers.code.Decompositionhandler import DecompositionHandler
from api.services.handlers.Github_guide_handler import GithubGuideHandler
from api.services.handlers.LineFormatHandler import LineFormatHandler
from api.services.handlers.perserhandler import ParserHandler
from api.services.handlers.Math_Handler.MathHandler import MathHandler
from api.services.handlers.GagHandler.GagHandler import GagHandler

# VSCode Handler / Tool の安全なインポート
try:
    from api.services.handlers.VSCode.VSCodeHandler import VSCodeHandler as VSCodeTool
except ImportError:
    try:
        from api.services.handlers.VSCode.VSCodeHandler import VSCodeTool
    except ImportError:
        VSCodeTool = None

# SecurityAuditHandler の安全なインポート
try:
    from api.services.handlers.SecurityAuditHandler import SecurityAuditHandler
except ImportError:
    try:
        from backend.api.services.handlers.SecurityAuditHandler import SecurityAuditHandler
    except ImportError:
        SecurityAuditHandler = None

# ProjectBuilderHandler のみ隔離インポート（失敗してもChat API全体を止めない）
PROJECT_BUILDER_AVAILABLE = False
PROJECT_BUILDER_IMPORT_ERROR = None
ProjectBuilderHandler = None

try:
    from api.services.handlers.project.ProjectBuilderHandler import (
        ProjectBuilderHandler,
    )
    PROJECT_BUILDER_AVAILABLE = True
except Exception as e:
    PROJECT_BUILDER_IMPORT_ERROR = e
    print("⚠️ [ChatOrchestrator] ProjectBuilderHandlerのimportに失敗しました。")
    print(f"⚠️ [ChatOrchestrator] 理由: {type(e).__name__}: {e}")
    print("⚠️ [ChatOrchestrator] Chat API自体は起動を続行します。")


def build_default_handlers(
    project_root: Path,
    knowledge_dir: Path,
    reload_callback: Callable[[], Any],
) -> List[Any]:
    """オーケストレーターに登録する全Handlerインスタンスのリストを生成する。"""
    default_knowledge_dirs: list[str | Path] = [knowledge_dir / "domains"]
    default_manager_base_dir = knowledge_dir

    handlers: List[Any] = []

    # 1. 最優先：ローカル静的解析・APIセキュリティ監査ハンドラー
    if SecurityAuditHandler is not None:
        try:
            handlers.append(SecurityAuditHandler(project_root=project_root))
            print("✅ [ChatOrchestrator] SecurityAuditHandler登録成功")
        except Exception as e:
            print(f"⚠️ [ChatOrchestrator] SecurityAuditHandler初期化失敗: {e}")

    # 2. コア開発・知識ハンドラー群
    handlers.extend(
        [
            PythonCodeHandler(),
            MathHandler(),
            KnowledgeReloadHandler(reload_callback=reload_callback),
            KnowledgeHealthHandler(),
            DecompositionHandler(),
            GithubGuideHandler(),
            APICollectHandler(),
            RepomixHandler(),
        ]
    )

    # 3. ProjectBuilderHandler（利用可能な場合のみ）
    if PROJECT_BUILDER_AVAILABLE and ProjectBuilderHandler is not None:
        try:
            handlers.append(ProjectBuilderHandler(project_root=str(project_root)))
            print("✅ [ChatOrchestrator] ProjectBuilderHandler登録成功")
        except Exception as e:
            print(f"❌ [ChatOrchestrator] ProjectBuilderHandler初期化失敗: {e}")
            traceback.print_exc()
    else:
        print("⚠️ [ChatOrchestrator] ProjectBuilderHandlerは無効です。")
        if PROJECT_BUILDER_IMPORT_ERROR:
            print(f"⚠️ [ChatOrchestrator] import error={PROJECT_BUILDER_IMPORT_ERROR}")

    # 4. 各種専門ハンドラー＆オフラインフォールバック群
    handlers.extend(
        [
            PhpHandler(),
            ConversionJsonHandler(),
            DeploymentHandler(
                knowledge_dirs=default_knowledge_dirs,
                manager_base_dir=default_manager_base_dir,
                cache_enabled=True,
            ),
        ]
    )

    if VSCodeTool is not None:
        try:
            handlers.append(VSCodeTool())
        except Exception as e:
            print(f"⚠️ [ChatOrchestrator] VSCodeTool初期化スキップ: {e}")

    handlers.extend(
        [
            ChatHandler(),
            GagHandler(),
            LineFormatHandler(),
            HTMLHandler(),
            GithubHandler(),
            RecruitHandler(),
            ScrapingHandler(),
            DesignHandler(),
            WeatherHandler(),
            DatabaseHandler(),
            OllamaHandler(),
            OfflineFallbackHandler(),
            ParserHandler(),
        ]
    )

    return handlers


__all__ = [
    "OcrRecruitHandler",
    "PROJECT_BUILDER_AVAILABLE",
    "PROJECT_BUILDER_IMPORT_ERROR",
    "ProjectBuilderHandler",
    "build_default_handlers",
]
