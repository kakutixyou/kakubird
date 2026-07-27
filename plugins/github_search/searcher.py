"""
GitHub Search Plugin - searcher.py
自然言語メッセージを受け取り、GitHubリポジトリを検索して返す
使用方法: python3 searcher.py "GitHubで似たようなものを作ろうとしている人がいるか探したい"
"""

import sys
import json
import urllib.request
import urllib.parse
import re
from typing import Optional


# ----------------------------------------------------------------
# 1. 自然言語 → GitHub検索クエリ変換
# ----------------------------------------------------------------

# よく使われる日本語キーワードと対応する英語技術用語
KEYWORD_MAP = {
    # 技術スタック
    "python": "python", "ython": "python",
    "javascript": "javascript", "js": "javascript",
    "typescript": "typescript", "ts": "typescript",
    "react": "react", "vue": "vue", "svelte": "svelte",
    "fastapi": "fastapi", "django": "django", "flask": "flask",
    "機械学習": "machine-learning", "ml": "machine-learning",
    "深層学習": "deep-learning", "딥러닝": "deep-learning",
    "ai": "ai", "人工知能": "artificial-intelligence",
    "チャット": "chat", "チャットボット": "chatbot",
    "プラグイン": "plugin", "拡張": "plugin",
    "sql": "sql", "データベース": "database", "db": "database",
    "api": "api", "rest": "rest-api",
    "ゲーム": "game", "blender": "blender", "unity": "unity",
    "スクレイピング": "scraping", "crawler": "crawler",
    "認証": "authentication", "auth": "authentication",
    "マルチテナント": "multi-tenant", "saas": "saas",
    "検索": "search", "ベクター": "vector", "埋め込み": "embedding",
    "php": "php", "laravel": "laravel",
    "electron": "electron", "デスクトップ": "desktop",
    "メモリ": "memory", "記憶": "memory",
}

def build_query(message: str) -> str:
    """
    自然言語メッセージからGitHub検索クエリを生成する
    例: "GitHubで似たようなAIを作ろうとしている人" → "ai plugin system"
    """
    msg_lower = message.lower()
    found_keywords = []

    for jp_key, en_value in KEYWORD_MAP.items():
        if jp_key in msg_lower and en_value not in found_keywords:
            found_keywords.append(en_value)

    # キーワードが見つからない場合はメッセージから英単語を抽出
    if not found_keywords:
        english_words = re.findall(r'[a-zA-Z]{3,}', message)
        found_keywords = [w.lower() for w in english_words[:4]]

    # それでも空なら汎用クエリ
    if not found_keywords:
        found_keywords = ["ai", "plugin"]

    # "github" 単体は除外（ノイズになるため）
    found_keywords = [k for k in found_keywords if k != "github"]
    if not found_keywords:
        found_keywords = ["ai", "plugin"]

    return " ".join(found_keywords[:4])  # GitHub APIは長すぎるクエリが苦手なので4語まで


# ----------------------------------------------------------------
# 2. GitHub API 呼び出し
# ----------------------------------------------------------------

GITHUB_API = "https://api.github.com/search/repositories"

def search_github(query: str, per_page: int = 5) -> dict:
    params = urllib.parse.urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
    })

    url = f"{GITHUB_API}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-search-plugin/1.0",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API error: {e.code} {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Network error: {str(e)}")


# ----------------------------------------------------------------
# 3. 結果を整形
# ----------------------------------------------------------------

def format_results(raw: dict, query: str, original_message: str) -> dict:
    items = raw.get("items", [])
    total = raw.get("total_count", 0)

    repos = []
    for item in items:
        repos.append({
            "name": item.get("full_name"),
            "url": item.get("html_url"),
            "description": item.get("description") or "説明なし",
            "stars": item.get("stargazers_count", 0),
            "language": item.get("language") or "不明",
            "updated_at": item.get("updated_at", "")[:10],  # YYYY-MM-DD
            "topics": item.get("topics", []),
        })

    return {
        "success": True,
        "original_message": original_message,
        "query_used": query,
        "total_count": total,
        "repositories": repos,
        "search_url": f"https://github.com/search?q={urllib.parse.quote(query)}&type=repositories",
    }


# ----------------------------------------------------------------
# 4. エントリーポイント
# ----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "メッセージ引数が必要です"}))
        sys.exit(1)

    message = sys.argv[1]

    try:
        query = build_query(message)
        raw = search_github(query)
        result = format_results(raw, query, message)
        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "original_message": message,
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()