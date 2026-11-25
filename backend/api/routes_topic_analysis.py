from __future__ import annotations

import os
import re
from collections import Counter
from typing import Literal

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
TIMEOUT_SECONDS = 12

ALIASES = {
    "りんご": ["りんご", "リンゴ", "林檎", "apple"],
    "apple": ["apple", "りんご", "リンゴ", "林檎"],
    "株": ["株", "株式", "株価", "投資", "stock"],
    "株式": ["株式", "株", "株価", "投資", "stock"],
    "株価": ["株価", "株", "株式", "投資", "stock"],
    "投資": ["投資", "株", "株式", "株価", "stock"],
}
CATEGORY_TERMS = {
    "料理": ["料理", "レシピ", "recipe", "cook"],
    "料金": ["料金", "価格", "値段", "price", "cost"],
    "美味しさ": ["美味しい", "おいしい", "味", "taste", "delicious"],
    "検索": [],
    "株価": ["株価", "株", "stock", "price"],
    "売買理由": ["理由", "なぜ", "損益", "利益", "損失", "売買", "trade", "reason"],
}
STOCK_TERMS = ("株", "株式", "株価", "投資", "stock", "trading")
WIN_TERMS = ("勝ち", "勝った", "利益", "儲", "プラス", "profit", "gain", "win")
LOSS_TERMS = ("負け", "負けた", "損失", "損", "マイナス", "loss", "lose")
REASON_TERMS = ("理由", "なぜ", "原因", "根拠", "分析", "reason", "because", "因為")


class TopicAnalysisRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    category: str = "すべて"
    sources: list[Literal["qiita", "github", "youtube"]] = Field(default_factory=lambda: ["qiita", "github", "youtube"], max_length=3)


def _terms(query: str) -> list[str]:
    normalized = query.strip()
    terms = ALIASES.get(normalized.lower(), ALIASES.get(normalized, [normalized]))
    # Keep user intent while including common Japanese/English variants for the common ambiguous topics.
    return list(dict.fromkeys([normalized, *terms]))[:6]


def _search_query(query: str, category: str) -> str:
    terms = _terms(query)
    category_terms = CATEGORY_TERMS.get(category, []) if category != "すべて" else []
    # Search APIs treat spaces as AND; use a readable query rather than an unsafe raw query expression.
    return " ".join([terms[0], *category_terms[:2]])


def _text(item: dict) -> str:
    return " ".join(str(item.get(key) or "") for key in ("title", "description", "body", "snippet"))


def _stock_summary(results: list[dict]) -> dict | None:
    if not any(term in " ".join(_text(item) for item in results).lower() for term in STOCK_TERMS):
        return None
    text = " ".join(_text(item) for item in results).lower()
    count = lambda terms: sum(text.count(term.lower()) for term in terms)
    return {
        "win_mentions": count(WIN_TERMS),
        "loss_mentions": count(LOSS_TERMS),
        "reason_mentions": count(REASON_TERMS),
        "note": "検索結果のタイトル・概要に含まれる語句の出現回数です。勝敗金額や実際の取引件数ではなく、個々の結果を開いて内容を確認してく���さい。投資判断を示すものではありません。",
    }


def _youtube_search(query: str, category: str) -> list[dict]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY が未設定のため、YouTube検索をスキップしました。")
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "q": _search_query(query, category), "type": "video", "maxResults": 10, "key": api_key},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    output = []
    for item in response.json().get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        output.append({
            "source": "youtube", "title": snippet.get("title", "YouTube動画"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": snippet.get("description", "")[:500], "category": category,
            "published_at": snippet.get("publishedAt"),
            "moments": [{"seconds": seconds, "url": f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"} for seconds in (10, 20, 30)],
        })
    return output


def _qiita_search(query: str, category: str) -> list[dict]:
    response = requests.get(
        "https://qiita.com/api/v2/items",
        params={"page": 1, "per_page": 10, "query": _search_query(query, category)},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return [{
        "source": "qiita", "title": item.get("title", "Qiita記事"), "url": item.get("url", ""),
        "description": re.sub(r"\s+", " ", item.get("body", ""))[:350], "category": category,
        "published_at": item.get("created_at"), "metrics": {"いいね": item.get("likes_count", 0)},
    } for item in response.json()]


def _github_search(query: str, category: str) -> list[dict]:
    response = requests.get(
        "https://api.github.com/search/repositories",
        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        params={"q": _search_query(query, category), "sort": "stars", "order": "desc", "per_page": 10},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return [{
        "source": "github", "title": item.get("full_name", "GitHub repository"), "url": item.get("html_url", ""),
        "description": item.get("description") or "説明はありません。", "category": category,
        "published_at": item.get("updated_at"),
        "metrics": {"stars": item.get("stargazers_count", 0), "言語": item.get("language") or "不明"},
    } for item in response.json().get("items", [])]


@router.post("/api/topic-analysis")
def analyze_topic(request: TopicAnalysisRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="検索テーマを入力してください。")
    category = request.category if request.category in CATEGORY_TERMS else "すべて"
    results: list[dict] = []
    warnings: list[str] = []
    searches = {"qiita": _qiita_search, "github": _github_search, "youtube": _youtube_search}
    for source in request.sources:
        try:
            results.extend(searches[source](query, category))
        except Exception as exc:
            # Keep partial results from the remaining sources if one API is unavailable.
            warnings.append(f"{source}: {str(exc)[:240]}")
    corpus = " ".join(_text(item) for item in results).lower()
    evidence_terms = ("勝ち", "利益", "負け", "損失", "理由", "なぜ", "根拠", "おいしい", "美味しい", "レシピ", "料金", "価格")
    for item in results:
        item["evidence"] = [term for term in evidence_terms if term.lower() in _text(item).lower()][:5]
    categories = [name for name, terms in CATEGORY_TERMS.items() if not terms or any(term.lower() in corpus for term in terms)]
    if not categories:
        categories = [category] if category != "すべて" else ["検索"]
    return {
        "query": query,
        "normalized_terms": _terms(query),
        "categories": categories,
        "stock_analysis": _stock_summary(results),
        "results": results,
        "warnings": warnings,
    }
