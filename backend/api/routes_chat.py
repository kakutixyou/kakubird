# backend/api/routes_chat.py
import traceback
import json
import os
import threading # ✅ asyncioから変更：FastAPIの別スレッドに安全に任せるため
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Header, Request, BackgroundTasks
from pydantic import BaseModel, Field

from api.services.chat_service import ChatService
from model.chat_models import (
    ChatMessage,
    ChatRequest,
    ChatContext,
    ChatResponse,
    OrchestratorResponse,
)
from core.memory_manager import get_chat_history, save_chat_message

# =========================================================
# ✅ 1. 各オーケストレーターのインポート
# =========================================================
# ※実際にはご自身のパスに合わせてインポートしてください

from engine.orchestrator.chat_orchestrator import ChatOrchestrator          # 通常チャット
from engine.orchestrator.agent_orchestrator import AgentOrchestrator        # 自律エージェント
from engine.orchestrator.copilot_orchestrator import CopilotOrchestrator    # コード生成・補完
from engine.orchestrator.custom_sql_orchestrator import CustomSqlOrchestrator  # SQL Builder
# from engine.orchestrator.project_orchestrator import ProjectOrchestrator    # プロジェクト解析
# from engine.orchestrator.builder_orchestrator import BuilderOrchestrator    # アプリ・画面生成
# from engine.orchestrator.deployment_orchestrator import DeploymentOrchestrator  # フォルダー・空ファイル生成
# from engine.orchestrator.plugin_orchestrator import PluginOrchestrator      # Plugin管理
# from engine.orchestrator.memory_orchestrator import MemoryOrchestrator      # Memory管理
# from engine.orchestrator.github_orchestrator import GithubOrchestrator      # GitHub解析
# from engine.orchestrator.scraping_orchestrator import ScrapingOrchestrator  # スクレイピング
# from engine.orchestrator.knowledge_orchestrator import KnowledgeOrchestrator # Knowledge管理
# from engine.orchestrator.html_orchestrator import HtmlOrchestrator          # HTML/UI解析
# from engine.orchestrator.unity_orchestrator import UnityOrchestrator        # Unity支援
# from engine.orchestrator.video_orchestrator import VideoOrchestrator        # 動画編集支援
# from engine.orchestrator.json_orchestrator import JsonOrchestrator          # JSON生成・修正
# from engine.orchestrator.template_orchestrator import TemplateOrchestrator  # テンプレート生成
# from engine.orchestrator.workflow_orchestrator import WorkflowOrchestrator  # ワークフロー管理
# from engine.orchestrator.debug_orchestrator import DebugOrchestrator        # エラー解析
# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/api/chat",
    tags=["AI Chat & Multimodal Router"]
)

# =========================================================
# 信号（Signals）管理用の裏側処理（バックグラウンドタスク）
# =========================================================
SIGNALS_FILE = "backend/.ai_memory/user_signals.json"
signal_lock = threading.Lock() # ✅ async不要の標準Lockに変更

# ✅ async def ではなく、ただの def に変更（FastAPIが自動的に別スレッドで処理してくれます）
def update_signals_in_background(updates: dict):
    """ユーザーに応答を返したあとに、裏側で安全に user_signals.json を書き換えるタスク"""
    with signal_lock: # ✅ async with ではなく with に変更
        current = {}
        if os.path.exists(SIGNALS_FILE):
            try:
                with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                pass
                
        current.update(updates)
        
        try:
            os.makedirs(os.path.dirname(SIGNALS_FILE), exist_ok=True)
            with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
            print(f"🤫 [Background] 信号を更新しました: {updates}")
        except Exception as e:
            print(f"⚠️ [Background] 信号の保存エラー: {e}")


# =========================================================
# ✅ 2. ファクトリーパターンの実装 (Orchestrator Factory)
# =========================================================
class OrchestratorFactory:
    """リクエストのモードに応じて適切なオーケストレーターを生成・返却するファクトリー"""
    @staticmethod
    def get_orchestrator(mode: str, project_root: str = "."):
        # 辞書マッピングで分岐をスマートに管理
        orchestrators = {
            "gemini": ChatOrchestrator,      # 通常のチャット用
            "agent": AgentOrchestrator,      # 自律型エージェント用
            "copilot": CopilotOrchestrator,  # コード生成用
            # "custom_sql": CustomSqlOrchestrator # 旧エンドポイントのCustom AI相当
        }
        
        # モードが見つからなければデフォルト（ChatOrchestrator）を返す
        orchestrator_class = orchestrators.get(mode, ChatOrchestrator)
        print(f"🏭 [Factory] '{mode}' モードに対して {orchestrator_class.__name__} を生成しました")
        
        return orchestrator_class(project_root=project_root)


# =========================================================
# Endpoints
# =========================================================

# --- ① 旧式のエンドポイント（将来的に②に統合していく想定） ---
# (※コードが長くなるため省略しますが、そのまま残して問題ありません)

# ---------------------------------------------------------
# ② 新しいエンドポイント（ファクトリーを利用するルート）
# ---------------------------------------------------------
@router.post("")
@router.post("/", response_model=OrchestratorResponse, include_in_schema=False)
async def handle_ai_chat(request: ChatRequest, background_tasks: BackgroundTasks):
    print("🔥 handle_ai_chat に入りました", flush=True)
    try:
        # 1. ユーザー入力のDB保存
        save_chat_message(role="user", content=request.message)

        # 2. ファクトリーを使って適切なオーケストレーターを生成
        mode = getattr(request, "mode", "gemini") 
        orchestrator = OrchestratorFactory.get_orchestrator(mode, project_root=".")

        # 3. ChatServiceの生成と実行（前処理・実行・フォールバックはすべてサービスにお任せ）
        chat_service = ChatService(project_root=".")
        response_type, content = await chat_service.execute_chat(request, orchestrator, background_tasks)

        # 4. AIの返答をDBに保存
        ai_reply_text = content if isinstance(content, str) else content.get("message", "処理が完了しました")
        save_chat_message(
            role="assistant",
            content=ai_reply_text,
            metadata={"source": mode, "type": response_type}
        )

        # 5. バックグラウンド状態保存（ChatServiceが回収した状態を保存）
        updates_to_save = {}
        # ★ orchestratorではなく、chat_service から状態を受け取るのがポイント
        if chat_service.last_used_handler:
            updates_to_save["last_used_handler"] = chat_service.last_used_handler
        if chat_service.active_context:
            updates_to_save["active_context"] = chat_service.active_context
            
        if updates_to_save:
            background_tasks.add_task(update_signals_in_background, updates_to_save)

        # 6. クライアントへ返却
        return {
            "status": "success",
            "response_type": response_type,
            "content": content
        }

    except Exception as e:
        print("🚨🚨🚨 エラー発生 🚨🚨🚨", flush=True)
        error_details = traceback.format_exc()
        print(f"💥 エラーの正体:\n{error_details}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))