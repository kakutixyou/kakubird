
# jimdo_studio_react/backend/api/services/github_service.py

import traceback
import urllib.parse
from typing import Dict, Any, List

import httpx


# =========================================================
# Constants
# =========================================================

GITHUB_SEARCH_API = (
    "https://api.github.com/search/repositories"
)

DEFAULT_TIMEOUT = 15.0

DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}


# =========================================================
# Helper Functions
# =========================================================

def build_search_url(query: str) -> str:
    """
    GitHub検索URL生成
    """

    encoded_query = urllib.parse.quote(query)

    return (
        f"https://github.com/search?q={encoded_query}"
    )


def normalize_repository(repo: Dict[str, Any]) -> Dict[str, Any]:
    """
    GitHub APIのrepository objectを
    frontend向けに整形
    """

    return {
        "id": str(repo.get("id")),

        "name": repo.get(
            "full_name",
            "unknown"
        ),

        "description": repo.get(
            "description",
            "No description"
        ),

        "stars": repo.get(
            "stargazers_count",
            0
        ),

        "language": (
            repo.get("language")
            or "Unknown"
        ),

        "url": repo.get(
            "html_url",
            ""
        ),

        "forks": repo.get(
            "forks_count",
            0
        ),

        "open_issues": repo.get(
            "open_issues_count",
            0
        ),

        "watchers": repo.get(
            "watchers_count",
            0
        ),

        "updated_at": repo.get(
            "updated_at",
            ""
        ),

        "owner": {
            "login": (
                repo.get("owner", {})
                .get("login", "unknown")
            ),

            "avatar_url": (
                repo.get("owner", {})
                .get("avatar_url", "")
            ),
        }
    }


# =========================================================
# GitHub Search
# =========================================================

async def execute_github_search(
    query: str,
    limit: int = 6
) -> Dict[str, Any]:
    """
    GitHub Repository Search

    Args:
        query:
            GitHub search query

        limit:
            最大取得件数

    Returns:
        Dict[str, Any]
    """

    try:

        encoded_query = urllib.parse.quote(
            query
        )

        github_api_url = (
            f"{GITHUB_SEARCH_API}"
            f"?q={encoded_query}"
            f"&sort=stars"
            f"&order=desc"
            f"&per_page={limit}"
        )

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT
        ) as client:

            response = await client.get(
                github_api_url,
                headers=DEFAULT_HEADERS,
            )

            response.raise_for_status()

            search_data = response.json()

        items = search_data.get(
            "items",
            []
        )

        total_count = search_data.get(
            "total_count",
            0
        )

        repositories = [
            normalize_repository(repo)
            for repo in items[:limit]
        ]

        return {
            "error": False,

            "message": (
                f"🤖 GitHubを検索し、"
                f"要件に合いそうなプロジェクトを "
                f"{total_count:,} 件見つけました！\n\n"
                f"*(検索クエリ: `{query}`)*"
            ),

            "query_used": query,

            "total_count": total_count,

            "repositories": repositories,

            "search_url": build_search_url(
                query
            ),
        }

    except httpx.TimeoutException:

        return {
            "error": True,
            "message":
                "GitHub検索がタイムアウトしました。"
        }

    except httpx.HTTPStatusError as e:

        print(f"GitHub HTTP Error: {e}")

        return {
            "error": True,
            "message":
                "GitHub APIエラーが発生しました。"
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": True,
            "message":
                "GitHub検索中に内部エラーが発生しました。"
        }


# =========================================================
# Trending Helper Queries
# =========================================================

async def search_ai_projects() -> Dict[str, Any]:
    """
    人気AIプロジェクト検索
    """

    query = (
        "AI agent stars:>100 "
        "pushed:>2025-01-01"
    )

    return await execute_github_search(
        query=query,
        limit=10
    )


async def search_math_visualization_projects() -> Dict[str, Any]:
    """
    数学可視化系プロジェクト検索
    """

    query = (
        "math visualization "
        "python OR react "
        "stars:>50"
    )

    return await execute_github_search(
        query=query,
        limit=10
    )


async def search_react_projects() -> Dict[str, Any]:
    """
    React UI系プロジェクト検索
    """

    query = (
        "react ui framework "
        "stars:>500"
    )

    return await execute_github_search(
        query=query,
        limit=10
    )


# =========================================================
# Repository Detail
# =========================================================

async def fetch_repository_detail(
    owner: str,
    repo: str
) -> Dict[str, Any]:
    """
    単一Repository詳細取得

    Example:
        owner="microsoft"
        repo="vscode"
    """

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}"
    )

    try:

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT
        ) as client:

            response = await client.get(
                url,
                headers=DEFAULT_HEADERS
            )

            response.raise_for_status()

            repo_data = response.json()

        normalized = normalize_repository(
            repo_data
        )

        normalized["readme_url"] = (
            f"https://github.com/"
            f"{owner}/{repo}"
            f"#readme"
        )

        return {
            "error": False,
            "repository": normalized
        }

    except Exception:

        traceback.print_exc()

        return {
            "error": True,
            "message":
                "Repository詳細取得に失敗しました。"
        }


# =========================================================
# Language Detection Helper
# =========================================================

def detect_search_category(
    message: str
) -> str:
    """
    ユーザーメッセージから
    検索カテゴリを推定
    """

    msg = message.lower()

    if any(
        k in msg
        for k in [
            "数学",
            "math",
            "visualization",
        ]
    ):
        return "math"

    if any(
        k in msg
        for k in [
            "ai",
            "agent",
            "llm",
        ]
    ):
        return "ai"

    if any(
        k in msg
        for k in [
            "react",
            "ui",
            "frontend",
        ]
    ):
        return "react"

    return "general"


# =========================================================
# Smart Search
# =========================================================

async def smart_github_search(
    user_message: str
) -> Dict[str, Any]:
    """
    メッセージ内容から
    自動検索
    """

    category = detect_search_category(
        user_message
    )

    if category == "math":

        return await search_math_visualization_projects()

    elif category == "ai":

        return await search_ai_projects()

    elif category == "react":

        return await search_react_projects()

    return await execute_github_search(
        query=user_message,
        limit=5
    )


# =========================================================
# Future Expansion Notes
# =========================================================

"""
将来的な拡張ポイント

1. GitHub Trending API
--------------------------------------------------------
トレンド分析

2. README Fetch
--------------------------------------------------------
README要約

3. Repository Embedding
--------------------------------------------------------
RAG検索

4. Topic Filtering
--------------------------------------------------------
topic:ai topic:agent

5. License Detection
--------------------------------------------------------
MIT / Apache etc

6. Security Analysis
--------------------------------------------------------
危険repo検知

7. Commit Activity
--------------------------------------------------------
活動量分析

8. AI Scoring
--------------------------------------------------------
コード品質評価

9. Plugin Integration
--------------------------------------------------------
plugin marketplace

10. Streaming Search
--------------------------------------------------------
リアルタイム検索
"""
