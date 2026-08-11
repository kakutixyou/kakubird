"""
qiita_collector.py
==================
Qiita APIを利用して、特定のOSSや技術キーワードに関する記事を収集する。
前回の反省を活かし、「ノイズ（価値が低い記事）」を弾き、
「ポイント（価値が高い記事）」だけを構造化して抽出するフィルター機能を搭載。

入力: 検索クエリ (OSS名など)
出力: 価値の高い記事のリストと、除外された記事の統計を含むJSON辞書
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

REQUEST_INTERVAL = 1.0  # Qiita APIのレート制限対策

class QiitaCollector:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("QIITA_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def collect(self, query: str, max_pages: int = 2) -> dict:
        """
        指定したクエリで記事を検索し、価値の高低で仕分ける
        """
        logger.info(f"[Qiita] 収集開始: query='{query}'")
        
        all_items = self._fetch_items(query, max_pages)
        
        high_value_articles = []
        low_value_articles = []

        for item in all_items:
            # 記事を評価して仕分ける
            evaluation = self._evaluate_article(item)
            
            if evaluation["is_high_value"]:
                high_value_articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "lgtm_count": item.get("likes_count", 0),
                    "tags": [t["name"] for t in item.get("tags", [])],
                    "created_at": item.get("created_at"),
                    # 本文は長すぎるので、最初の500文字程度をプレビューとして保持
                    "body_preview": item.get("body", "")[:500].replace("\n", " "),
                    "reason": evaluation["reason"] # なぜ高評価と判断したか
                })
            else:
                low_value_articles.append({
                    "title": item.get("title"),
                    "lgtm_count": item.get("likes_count", 0),
                    "reason": evaluation["reason"] # なぜ低評価（ノイズ）と判断したか
                })

        logger.info(f"[Qiita] 収集完了: High={len(high_value_articles)}件, Low={len(low_value_articles)}件を除外")

        return {
            "query": query,
            "high_value_articles": sorted(high_value_articles, key=lambda x: x["lgtm_count"], reverse=True),
            "stats": {
                "total_fetched": len(all_items),
                "high_value_count": len(high_value_articles),
                "low_value_count": len(low_value_articles),
                "low_value_reasons": self._aggregate_reasons(low_value_articles)
            }
        }

    # ─────────────────────────────────────────────────────
    # 内部メソッド（フィルタリングロジック）
    # ─────────────────────────────────────────────────────

    def _evaluate_article(self, item: dict) -> dict:
        """
        記事の価値を判定する（前回の反省を活かしたルールベース判定）
        """
        lgtm = item.get("likes_count", 0)
        body = item.get("body", "")
        title = item.get("title", "").lower()
        tags = [t["name"].lower() for t in item.get("tags", [])]

        # 1. LGTM数が極端に少ないものは「価値が低い」とみなす（基準: 3未満）
        if lgtm < 3:
            return {"is_high_value": False, "reason": "LGTM_TOO_LOW"}

        # 2. 文字数が少なすぎるものは、単なるメモの可能性が高い
        if len(body) < 800:
            return {"is_high_value": False, "reason": "BODY_TOO_SHORT"}

        # 3. タイトルやタグによるノイズ判定（「備忘録」「ポエム」「エラーメモ」など）
        noise_keywords = ["備忘録", "メモ", "とりあえず", "やってみた", "エラー解決"]
        for word in noise_keywords:
            if word in title:
                # ただしLGTMが50以上あれば、良質な備忘録の可能性があるので救済
                if lgtm < 50:
                    return {"is_high_value": False, "reason": f"NOISE_KEYWORD_{word}"}

        # 4. コードブロック（```）が一切ない記事は技術的な具体性に欠ける
# 4. コードブロック（```）が一切ない記事は技術的な具体性に欠ける
            if "```" not in body and lgtm < 20:
                return {"is_high_value": False, "reason": "NO_CODE_BLOCKS"}

        # すべてのフィルターを通過したものを「ポイント（High Value）」とする
        return {"is_high_value": True, "reason": "PASSED_FILTERS"}

    def _fetch_items(self, query: str, max_pages: int) -> list[dict]:
        results = []
        for page in range(1, max_pages + 1):
            time.sleep(REQUEST_INTERVAL)
            try:
                # stocks（ストック数）順で検索することで、最初からある程度質の高いものを狙う
                url = f"https://qiita.com/api/v2/items?page={page}&per_page=20&query={query} sort:stock"
                resp = self.session.get(url, timeout=10)
                
                if resp.status_code == 403:
                    logger.warning("[Qiita] APIレート制限に到達しました。")
                    break
                resp.raise_for_status()
                
                items = resp.json()
                if not items:
                    break
                results.extend(items)
            except Exception as e:
                logger.error(f"[Qiita] API取得エラー: {e}")
                break
        return results

    def _aggregate_reasons(self, low_value_articles: list[dict]) -> dict:
        """どの理由でノイズが弾かれたかの統計を出す"""
        reasons = {}
        for a in low_value_articles:
            r = a["reason"]
            reasons[r] = reasons.get(r, 0) + 1
        return reasons