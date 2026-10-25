#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/github/repository_tool.py
旧 github_search.py のバグ（from http import client とコメントアウト問題）を修正し、
BaseTool 規格に統一した GitHub リポジトリ検索ツール。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import httpx
from tools.base_tool import BaseTool


class RepositoryTool(BaseTool):
    name = "github_search"
    aliases = ["github", "repo_search", "github_repository"]
    category = "github"
    description = "GitHubからキーワードに一致するリポジトリを検索し、上位リポジトリ情報を返します。"

    fast_route_enabled = False
    priority = 60
    mode = "github_operation"
    forced_handler = "GithubHandler"
    fast_route_score = 85

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if msg_lower.startswith("/github"):
            return True, "github_command"
        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索キーワード（例: 'AI agent python', 'stars:>100 language:python'）",
                },
                "limit": {
                    "type": "integer",
                    "description": "取得する最大件数（デフォルト: 5）",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "", limit: int = 5, **kwargs: Any) -> Dict[str, Any]:
        if not query.strip():
            return {"error": True, "message": "検索キーワード (query) を指定してください。"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "per_page": max(1, min(limit, 20))},
                    headers={"Accept": "application/vnd.github+json"},
                )
                res.raise_for_status()
                data = res.json()

            items = [
                {
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "stars": repo.get("stargazers_count"),
                    "url": repo.get("html_url"),
                    "language": repo.get("language"),
                }
                for repo in (data.get("items") or [])[:limit]
            ]

            return {
                "error": False,
                "status": "success",
                "message": f"🔍 GitHubで '{query}' に一致するリポジトリが {data.get('total_count', 0)} 件見つかりました。",
                "total_count": data.get("total_count", 0),
                "repositories": items,
            }
        except Exception as exc:
            return {"error": True, "message": f"GitHub API検索エラー: {exc}"}