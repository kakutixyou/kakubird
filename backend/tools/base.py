from routes_chat import ChatRequest, ChatResponse
from tools.registry import registry
from tools.github_search import GithubSearchTool
# 必要に応じてWeatherToolなどもインポートして登録
# tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Ollama(OpenAI互換)に渡すためのFunction Schemaを定義"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]: pass
registry.register(GithubSearchTool())

# @router.post("/", response_model=ChatResponse)
# async def handle_ai_chat(request: ChatRequest):
#     # 1. AIに現在の能力を伝える（動的に全ツールの説明が入る）
#     available_tools_prompt = registry.get_all_descriptions()
    
#     # 2. ユーザーの意図を判定してツール名と引数を決める（本来はLLMに推論させる）
#     # ※ 仮にここで "github_search" を使うと判定されたとする
#     selected_tool = "github_search"
#     tool_args = {"query": "AI agent UI stars:>10"}

#     # 3. ツールを実行して結果を返す（if/elifの羅列が不要になる！）
#     try:
#         result = await registry.execute_tool(selected_tool, **tool_args)
#         return ChatResponse(
#             response_type=selected_tool,
#             content=result
#         )
#     except Exception as e:
#         # フォールバック処理へ
#         pass