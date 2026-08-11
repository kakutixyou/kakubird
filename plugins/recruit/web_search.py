# plugin/recruit/web_search.py
from __future__ import annotations
import os
import httpx

SEARCH_API = "https://api.search.brave.com/res/v1/web/search"

def search_company(company_name: str) -> str:
    """
    Brave Search API で企業評判を検索し、
    スニペットをまとめて文字列で返す。
    """
    api_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
    if not api_key:
        return ""

    queries = [
        f"{company_name} 退職理由 口コミ",
        f"{company_name} 残業 激務 評判",
    ]

    snippets = []
    for q in queries:
        try:
            res = httpx.get(
                SEARCH_API,
                headers={"Accept": "application/json",
                         "X-Subscription-Token": api_key},
                params={"q": q, "count": 5, "lang": "ja"},
                timeout=10.0,
            )
            for item in res.json().get("web", {}).get("results", []):
                snippets.append(f"[{item['title']}] {item['description']}")
        except Exception:
            continue

    return "\n".join(snippets)