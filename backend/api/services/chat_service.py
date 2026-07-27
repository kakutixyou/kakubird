# chat_service.py
import logging
import traceback
from typing import Tuple, Any, Optional
from fastapi import BackgroundTasks

from api.services.knowledge_service import KnowledgeService
from plugins.project_builder.ChatHandler import ChatHandler 

from model.chat_models import ChatRequest, ChatContext

# ★変更点: 特定のOrchestratorではなく、すべてのOrchestratorが従う「型（基底クラス）」があればそれをインポートするのがベストです
from engine.orchestrator.base_orchestrator import BaseOrchestrator 

logger = logging.getLogger(__name__)

class ChatService:
    """
    ChatServiceは「Facade（窓口）」として機能します。
    ルーターから受け取ったオーケストレーターの実行前後の共通処理を担います。
    """
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.last_used_handler: Optional[str] = None
        self.active_context: Optional[ChatContext] = None

    # ★変更点: orchestrator を引数として受け取るようにしました
    async def execute_chat(self, request: ChatRequest, orchestrator: BaseOrchestrator, background_tasks: BackgroundTasks) -> Tuple[str, Any]:
        """
        チャット実行のメインフロー。
        """
        logger.info(f"💼 [ChatService] リクエスト受付: {request.message[:20]}...")
        print("🔥ChatService: execute_chat開始", flush=True)

        try:
            # ====================================================
            # 1 & 2. 外部コードと知識のロード (共通の前処理)
            # ====================================================
            world_knowledge = KnowledgeService.load_knowledge(self.project_root)
            request.world_knowledge = world_knowledge

            # ====================================================
            # 3. 司令塔へ委譲（ルーターから渡されたオーケストレーターを実行）
            # ====================================================
            print(f"  -> [{orchestrator.__class__.__name__}] に実行を委譲します")
            # ※メソッド名はオーケストレーター間で統一しておく必要があります（例: execute() や route_and_execute()）
            response_type, content = await orchestrator.route_and_execute(request)

            # 💡 [フォールバック判定]
            if response_type == "text" and "自己解析中にエラーが発生しました" in str(content):
                raise ValueError("Deployment parsing failed internally, falling back to chat.")

            # ====================================================
            # 4. 事後処理と記憶の更新
            # ====================================================
            self.last_used_handler = getattr(orchestrator, "last_used_handler", "Unknown")
            self.active_context = getattr(orchestrator, "active_context", None)

            logger.info(f"🏁 [ChatService] 実行完了。担当ハンドラー: {self.last_used_handler}")
            return response_type, content

        except Exception as e:
            # ====================================================
            # 🚨 最後の砦：フォールバック処理 (共通の後処理)
            # ====================================================
            print(f"⚠️ エラーが発生しました: {e}。ChatHandlerにフォールバックします。", flush=True)
            traceback.print_exc()
            
            try:
                self.last_used_handler = "ChatHandler (Fallback)"
                fallback_handler = ChatHandler()
                
                # フォールバック処理
                response_type, content = await fallback_handler.handle(request)
                
                logger.info("🏁 [ChatService] ChatHandlerへのフォールバックによる実行完了。")
                return response_type, content
                
            except Exception as fallback_error:
                print(f"🚨 [致命的] フォールバックハンドラーもクラッシュ: {fallback_error}", flush=True)
                return "text", "申し訳ありません。システムに一時的な問題が発生しました。時間をおいてもう一度お試しください。"