from typing import Dict, Any
from tools.base import BaseTool
from tools.registry import registry
from tools.github_search import GithubSearchTool
from tools.weather_fetch import WeatherFetchTool

registry.register(GithubSearchTool())
registry.register(WeatherFetchTool()) # 👈 これを1行追加するだけ！
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """ツールを登録する"""
        self._tools[tool.name] = tool

    def get_all_descriptions(self) -> str:
        """LLMに『今使えるツール一覧』を教えるための文字列を生成"""
        return "\n".join([f"- {name}: {t.description}" for name, t in self._tools.items()])

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """指定されたツールを実行する"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        return await self._tools[tool_name].execute(**kwargs)

# シングルトンとしてインスタンス化
registry = ToolRegistry()