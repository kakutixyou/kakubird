from __future__ import annotations

import os
import re
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
# Only count wording that explicitly reports a realized or personal outcome. Generic words like
# 「上昇」「下落」 are intentionally excluded: price movement alone doesn't establish a trade result.
WIN_PHRASES = ("利益確定", "利確", "儲かった", "勝った", "勝ちました", "利益が出", "利益を出", "プラスにな", "profit", "gained", "made a profit")
LOSS_PHRASES = ("損切り", "損失", "負けた", "負けました", "損した", "損しました", "含み損", "マイナスにな", "loss", "lost money", "lost")
REASON_TERMS = ("理由", "なぜ", "原因", "根拠", "分析", "reason", "because")
FOLLOWING_TERMS = ("従って買", "従って株", "言う通りに買", "言われて買", "おすすめされて買", "推奨されて買", "紹介されて買", "following", "followed", "recommendation")
RISK_TERMS = {
    "損失・損切りへの言及": ("損失", "損切り", "負けた", "損した", "含み損", "loss"),
    "推奨に従った取引への言及": FOLLOWING_TERMS,
    "実績・根拠の確認が必要": ("勝率", "実績", "根拠", "バックテスト", "検証", "過去成績"),
    "広告・利益相反の確認が必要": ("広告", "pr", "アフィリエイト", "利益相反", "スポンサー", "有料サロン"),
}


class TopicAnalysisRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    category: str = "すべて"
    sources: list[Literal["qiita", "github", "youtube"]] = Field(default_factory=lambda: ["qiita", "github", "youtube"], max_length=3)


def _terms(query: str) -> list[str]:
    normalized = query.strip()
    terms = ALIASES.get(normalized.lower(), ALIASES.get(normalized, [normalized]))
    return list(dict.fromkeys([normalized, *terms]))[:6]


def _search_query(query: str, category: str) -> str:
    terms = _terms(query)
    category_terms = CATEGORY_TERMS.get(category, []) if category != "すべて" else []
    return " ".join([terms[0], *category_terms[:2]])


def _text(item: dict) -> str:
    return " ".join(str(item.get(key) or "") for key in ("title", "description", "body", "snippet"))


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(phrase.casefold() in normalized for phrase in phrases)


def _classify_reported_outcome(item: dict) -> tuple[str | None, list[str]]:
    text = _text(item)
    wins = [phrase for phrase in WIN_PHRASES if phrase.casefold() in text.casefold()]
    losses = [phrase for phrase in LOSS_PHRASES if phrase.casefold() in text.casefold()]
    # Ambiguous reports (both win and loss, such as a mixed portfolio) are not forced into either bucket.
    if bool(wins) == bool(losses):
        return None, []
    return ("win", wins) if wins else ("loss", losses)


def _stock_summary(results: list[dict]) -> dict | None:
    stock_results = [item for item in results if _contains_any(_text(item), STOCK_TERMS)]
    if not stock_results:
        return None

    classified = []
    following_posts = []
    risk_counts = {label: 0 for label in RISK_TERMS}
    for item in stock_results:
        text = _text(item)
        outcome, evidence = _classify_reported_outcome(item)
        if outcome:
            classified.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "outcome": outcome,
                "evidence": evidence,
            })
        if _contains_any(text, FOLLOWING_TERMS):
            following_posts.append({"title": item.get("title", ""), "url": item.get("url", ""), "source": item.get("source", "")})
        for label, terms in RISK_TERMS.items():
            if _contains_any(text, terms):
                risk_counts[label] += 1

    wins = sum(1 for item in classified if item["outcome"] == "win")
    losses = sum(1 for item in classified if item["outcome"] == "loss")
    sample_size = wins + losses
    return {
        "win_rate_percent": round(wins / sample_size * 100, 1) if sample_size else None,
        "wins": wins,
        "losses": losses,
        "sample_size": sample_size,
        "unclassified_posts": max(0, len(stock_results) - sample_size),
        "recommendation_following_posts": following_posts[:10],
        "risk_signals": [{"label": label, "count": count} for label, count in risk_counts.items() if count],
        "classified_posts": classified[:20],
        "note": "これは検索結果のタイトル・概要に、利益/損失を明示した投稿だけを1投稿=1件として数えた参考値です。全記事・全取引の勝率ではなく、投稿者や推奨者の実力、将来の成績を示しません。検索結果の抜粋による誤分類や、勝ちだけを公開する選択バイアスがあります。投資判断に使わず、元記事と取引条件を確認してください。",
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
