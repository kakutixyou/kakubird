from http import client

import httpx
from tools.base import BaseTool
from typing import Any, Dict

# tools/github_search.py
class GithubSearchTool(BaseTool):
    @property
    def name(self) -> str: return "github_search"
    
    @property
    def description(self) -> str: return "GitHubからリポジトリを検索します。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索キーワード（例: 'AI agent python'）"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    async def execute(self, query: str = "", **kwargs) -> Dict[str, Any]:
    # ここに先ほどの GitHub API 呼び出しロジックを書く
# async with httpx.AsyncClient() as client:
        res = await client.get(f"https://api.github.com/search/repositories?q={query}") # type: ignore
        data = res.json()
        return {"status": "success", "total_count": data.get("total_count")}