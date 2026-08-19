#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collectors/ckan_client.py
──────────────────────────
CKAN Action API (package_search 等) への薄いHTTPクライアント。

collectors/opendata_collector.py が今まで自前で持っていた
「requestsセッション・リトライ設定・実際のHTTP呼び出し」の部分だけを
切り出したもの。東京都のカタログサイト(catalog.data.metro.tokyo.lg.jp)
に限らず、他の自治体のCKANサイト(将来的な横浜市等)にも base_url を
変えるだけで対応できるようにするための土台。

services/cache_manager.py と組み合わせることで、同じ検索クエリを
24時間以内に繰り返し投げないようにできる（マナー対策）。
cache を渡さなければ今まで通りキャッシュなしで動く。
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from Tokyo_hackson_23.backend.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class CKANClient:
    def __init__(
        self,
        base_url: str,
        timeout: int = 20,
        user_agent: str = "opendata-collector/1.0",
        cache: Optional[CacheManager] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.search_endpoint = f"{self.base_url}/api/3/action/package_search"
        self.timeout = timeout
        self.cache = cache

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        # 429/5xx を自動リトライ（opendata_collector.py と同じ設定）
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def package_search(self, params: dict) -> dict:
        """
        package_search を叩く。self.cache が設定されていれば、
        同じ(url, params)の組み合わせを一定時間キャッシュから返す。
        """
        cache_key = None
        if self.cache:
            cache_key = self.cache.make_key(self.search_endpoint, params)
            cached_body = self.cache.get(cache_key)
            if cached_body is not None:
                logger.debug("cache hit: %s params=%r", self.search_endpoint, params)
                return json.loads(cached_body)

        data = self._request_json(self.search_endpoint, params=params)

        if self.cache and cache_key:
            self.cache.set(cache_key, self.search_endpoint, json.dumps(data, ensure_ascii=False))

        return data

    def _request_json(self, url: str, params: dict) -> dict:
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.exception("CKAN API request failed: %s", e)
            raise
        except ValueError as e:
            logger.exception("CKAN API json decode failed: %s", e)
            raise