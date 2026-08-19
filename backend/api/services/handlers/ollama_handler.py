# api/services/handlers/ollama_handler.py
import os
from typing import Any, Tuple

from .base_handler import BaseHandler

# 必要なサービス群をインポート
from api.routes_system import discover_services
from core.context_builder import build_ai_context
from core.memory_manager import save_chat_message
from api.services.ollama_service import ask_ollama_with_tools
from api.services.github_service import execute_github_search
from api.services.weather_service import execute_weather_fetch

class OllamaHandler(BaseHandler):
    """
    Ollama (ローカルLLM) による推論と、Tool Calls（関数呼び出し）を担当するハンドラー
    """
    
    def __init__(self):
        self.DB_DIR = "./"

    async def can_handle(self, message: str) -> bool:
        """
        Ollamaは一般的なチャットの「メインエンジン」なので、
        他のハンドラーが処理しなかったものは、基本的にすべて引き受けます（常にTrue）。
        """
        return True
    
    async def calculate_score(self, message: str) -> int:
        """
        Ollamaの優先度スコアを計算します。

        通常のチャットは0点、明示的な指名があれば200点とします。

        通常のチャットは60点、明示的な指名があれば160点とします。

        """
        msg_lower = message.lower()
        
        # ユーザーが明示的に「Ollama」と入力した場合（絶対勝つスコア）

        if "ollama" in msg_lower:

                    return 200
            
        # 通常の会話のベーススコア
        # （元々は60点に設定）
        return 0

        # return 160
            
        # 通常の会話のベーススコア
        # （ScrapingHandlerの90点に負けるように、あえて60点に設定）
        # return 60

    # 🌟 追加ここまで
    async def handle(self, message: str) -> Tuple[str, Any] | None:
        """
        プロンプトを構築してOllamaに推論させ、テキストまたはツール実行結果を返す
        """
        print("🧠 Ollama Handler 発動: LLM推論を開始します")

        # 1. システム連携情報の取得
        system_services = await discover_services()
        context = build_ai_context()
        base_prompt = context.get("raw_prompt_context", "あなたは優秀なAIアシスタントです。")

        current_context = (
            f"{base_prompt}\n\n"
            f"【システムが提供可能なAPI機能一覧】\n"
            f"{system_services}\n"
        )

        # 2. SQLite DB情報の付与
        if os.path.exists(self.DB_DIR):
            active_databases = [
                f.replace(".db", "")
                for f in os.listdir(self.DB_DIR)
                if f.endswith(".db")
            ]
            if active_databases:
                current_context += (
                    "\n【現在システム内に実在するSQLiteデータベース】\n"
                    f"{', '.join(active_databases)}\n"
                )

        # 3. Ollamaへリクエスト送信
        ollama_res = await ask_ollama_with_tools(message, current_context)

        # オフライン（起動していない等）の場合は None を返して次のハンドラーへ処理を譲る
        if ollama_res.get("error"):
            print(" Ollamaがオフライン、またはエラーが発生しました。")
            return (
                "text",
                " Ollamaサーバーに接続できませんでした。"
            )

        response_msg = ollama_res.get("message", {})

        # 4. Tool Calls (Ollamaが自律的に関数を呼び出した場合)
        if "tool_calls" in response_msg and response_msg["tool_calls"]:
            for tool_call in response_msg["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"]["arguments"]

                # --- GitHub Search ツール ---
                if func_name == "github_search":
                    query = func_args.get("query", "AI agent")
                    result = await execute_github_search(query)
                    
                    save_chat_message(
                        "assistant", 
                        result["message"], 
                        metadata={"source": "ollama_tool"}
                    )
                    return "github_search", result

                # --- Weather Fetch ツール ---
                elif func_name == "weather_fetch":
                    city = func_args.get("city", "東京")
                    result = await execute_weather_fetch(city)
                    
                    save_chat_message(
                        "assistant", 
                        result["message"], 
                        metadata={"source": "ollama_tool"}
                    )
                    return "text", result["message"]

        # 5. 通常のテキストレスポンス
        if response_msg.get("content"):
            save_chat_message(
                "assistant", 
                response_msg["content"], 
                metadata={"source": "ollama"}
            )
            return "text", response_msg["content"]

        return None