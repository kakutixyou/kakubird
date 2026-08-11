#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opendata_collector.py
────────────────────
CKAN API (東京都オープンデータカタログ) から、
テーマ条件に沿ってデータセット資源(resource)を収集するコレクタ。

--- パッチ履歴 ---
- 生HTTP部分（requestsセッション・リトライ設定・実際の呼び出し）を
  collectors/ckan_client.py の CKANClient に切り出した。
  OpenDataCollector はページング・組織フィルタ・座標判定・自治体名正規化
  といった「CKANレスポンスをどう解釈するか」のロジックに専念する。
- cache_db_path を渡すと services/cache_manager.py 経由で24時間キャッシュが
  有効になる（同じ検索を毎回サーバに投げに行かなくなる）。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Set, Tuple

from collectors.ckan_client import CKANClient
from services.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# search_catalog_server.py と整合する組織フィルタ
GROUP_FQ = {
    "都": "organization:(t000* OR t313360 OR t001001)",
    "区": "organization:t131*",
    "市町村": "organization:(t132* OR t133* OR t134*)",
}

# 東京23区リスト（自治体名正規化用）
TOKYO_23_WARDS = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区",
    "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区",
    "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"
]


class CKANCollectionError(Exception):
    """
    ページング途中でCKAN APIへの接続が失敗した場合に送出する例外。
    それまでに収集できた部分結果を partial_results に保持する。
    """
    def __init__(self, message: str, partial_results: List[Dict]):
        super().__init__(message)
        self.partial_results = partial_results


class OpenDataCollector:
    def __init__(
        self,
        base_url: str = "https://catalog.data.metro.tokyo.lg.jp",
        timeout: int = 20,
        user_agent: str = "opendata-collector/1.0",
        cache_db_path: Optional[str] = None,
        cache_ttl_hours: float = 24.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        cache = CacheManager(db_path=cache_db_path, ttl_hours=cache_ttl_hours) if cache_db_path else None
        self.client = CKANClient(
            base_url=self.base_url,
            timeout=timeout,
            user_agent=user_agent,
            cache=cache,
        )

    def _clean_municipality(self, raw_org_name: str) -> str:
        """組織名から23区名を抽出・正規化"""
        for ward in TOKYO_23_WARDS:
            if ward in raw_org_name:
                return ward
        return raw_org_name.strip()

    def _detect_coordinates(self, res_format: str, title: str, raw_metadata: dict) -> bool:
        """フォーマットやタイトル・属性から位置情報(緯度経度・GISデータ)の存在を判定"""
        fmt = res_format.upper()
        if fmt in ("GEOJSON", "KML", "SHP", "TOPOJSON"):
            return True

        text_to_check = f"{title} {raw_metadata.get('description', '')}".lower()
        coord_keywords = ["緯度", "経度", "lat", "lon", "location", "座標", "位置情報"]
        return any(kw in text_to_check for kw in coord_keywords)

    def search_ckan(
        self,
        query: str,
        format_type: Optional[str] = "CSV",
        group: str = "all",
        rows: int = 200,
        max_packages: int = 2000,
        sleep_sec: float = 0.2,
    ) -> List[Dict]:
        if rows <= 0:
            rows = 100
        if rows > 1000:
            logger.warning("rows=%d は上限1000に制限しました", rows)
        rows = min(rows, 1000)

        if max_packages <= 0:
            max_packages = rows

        logger.info(
            "CKAN検索開始 query=%r format=%r group=%r rows=%d max_packages=%d",
            query, format_type, group, rows, max_packages
        )

        collected: List[Dict] = []
        seen_resource_keys: Set[Tuple[str, str]] = set()
        start = 0
        total_count = None

        while start < max_packages:
            params = {
                "q": query or "",
                "rows": rows,
                "start": start,
            }
            if group in GROUP_FQ:
                params["fq"] = GROUP_FQ[group]

            try:
                data = self.client.package_search(params)
            except Exception as e:
                logger.error(
                    "ページ取得失敗 start=%d: %s ／ ここまでの収集結果 %d 件を保持して中断します",
                    start, e, len(collected)
                )
                raise CKANCollectionError(
                    f"CKAN検索が途中で失敗しました (start={start}, collected={len(collected)}件): {e}",
                    partial_results=collected,
                ) from e

            if not data.get("success"):
                logger.warning("CKAN success=false start=%d", start)
                break

            result = data.get("result", {})
            packages = result.get("results", [])
            total_count = result.get("count", 0)

            if not packages:
                logger.info("取得終了: packages が空 start=%d", start)
                break

            for pkg in packages:
                pkg_title = pkg.get("title") or pkg.get("name") or "untitled"
                raw_org = (pkg.get("organization") or {}).get("title", "不明")
                municipality = self._clean_municipality(raw_org)

                for res in pkg.get("resources", []):
                    res_id = (res.get("id") or "").strip()
                    res_url = (res.get("url") or "").strip()
                    res_name = (res.get("name") or "").strip()
                    res_format = (res.get("format") or "").strip().upper()

                    if not res_id or not res_url:
                        continue

                    if format_type:
                        targets = {t.strip().upper() for t in format_type.split(",") if t.strip()}
                        if res_format not in targets:
                            continue

                    key = (res_id, res_url)
                    if key in seen_resource_keys:
                        continue
                    seen_resource_keys.add(key)

                    res_full_title = f"{pkg_title} - {res_name}" if res_name else pkg_title
                    has_coords = self._detect_coordinates(res_format, res_full_title, res)

                    collected.append({
                        "id": res_id,
                        "url": res_url,
                        "title": res_full_title,
                        "municipality": municipality,
                        "format": res_format or "UNKNOWN",
                        "has_coordinates": has_coords,  # workflow.py スコア計算用フラグ
                        "raw_metadata": res,
                    })

            start += rows
            logger.info(
                "page完了 start=%d collected=%d total_count=%s",
                start, len(collected), total_count
            )

            if start >= (total_count or 0):
                break

            time.sleep(sleep_sec)

        logger.info("CKAN検索完了: collected=%d total_count=%s", len(collected), total_count)
        return collected