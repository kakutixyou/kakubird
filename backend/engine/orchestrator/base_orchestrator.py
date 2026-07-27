import logging
import traceback
from abc import ABC, abstractmethod
from typing import Tuple, Any, Optional, Dict

# モデルのインポート（プロジェクトの構成に合わせて調整してください）
from model.chat_models import ChatRequest, ChatContext

logger = logging.getLogger(__name__)
class BaseOrchestrator(ABC):
    """
    全オーケストレーターの親となる抽象基底クラス（ルールブック）。

    ChatOrchestrator
    AgentOrchestrator
    CopilotOrchestrator
    DeploymentOrchestrator
    GithubOrchestrator
    ...

    など全ての Orchestrator はこのクラスを継承します。
    """

    def __init__(
        self,
        project_root=None,
        config=None,
        services=None,
    ):
        # ==========================================
        # 共通設定
        # ==========================================
        self.project_root = project_root
        self.config = config
        self.services = services

        # ==========================================
        # 共通状態（State）
        # ==========================================
        self.orchestrator_name = self.__class__.__name__

        self.last_used_handler: Optional[str] = None
        self.active_context: Optional[ChatContext] = None

        self.execution_metadata: Dict[str, Any] = {}

    # ==========================================
    # 必須実装
    # ==========================================
    @abstractmethod
    async def route_and_execute(
        self,
        request: ChatRequest,
        **kwargs
    ) -> Tuple[str, Any]:
        """
        各 Orchestrator が必ず実装するメイン処理。

        Parameters
        ----------
        request : ChatRequest
            ChatServiceから渡されるリクエスト

        Returns
        -------
        Tuple[str, Any]
            (response_type, content)
        """
        raise NotImplementedError

    # ==========================================
    # 共通ログ
    # ==========================================
    def _log_start(self, task_description: str = ""):
        """処理開始ログ"""

        msg = f"[{self.orchestrator_name}] 処理開始"

        if task_description:
            msg += f" : {task_description}"

        logger.info(msg)
        print(f"▶️ {msg}", flush=True)

    def _log_end(self, status: str = "完了"):
        """処理終了ログ"""

        msg = (
            f"[{self.orchestrator_name}] "
            f"処理{status}"
            f" (Handler: {self.last_used_handler})"
        )

        logger.info(msg)
        print(f"⏹️ {msg}", flush=True)

    # ==========================================
    # 共通エラー処理
    # ==========================================
    def _handle_standard_error(
        self,
        error: Exception,
        context_info: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """共通エラー処理"""

        error_message = str(error)
        trace = traceback.format_exc()

        logger.error(
            f"[{self.orchestrator_name}] {error_message}"
        )

        logger.debug(trace)

        print(
            f"❌ [{self.orchestrator_name}] {error_message}",
            flush=True,
        )

        self.last_used_handler = (
            f"{self.orchestrator_name} (Error)"
        )

        return (
            "error_json",
            {
                "status": "error",
                "orchestrator": self.orchestrator_name,
                "message": "処理中にエラーが発生しました。",
                "details": error_message,
                "context": context_info,
                "traceback": trace,
            },
        )

    # ==========================================
    # 共通Context更新
    # ==========================================
    def _set_context(
        self,
        new_context: ChatContext,
    ):
        """現在のContextを更新"""

        self.active_context = new_context

        logger.debug(
            f"[{self.orchestrator_name}] Context Updated"
        )