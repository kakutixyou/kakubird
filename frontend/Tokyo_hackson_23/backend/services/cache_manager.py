#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/cache_manager.py
──────────────────────────
HTTPレスポンス（CKAN検索結果・ダウンロードしたCSV/JSON本文など）を
SQLiteに一定時間（デフォルト24時間）キャッシュし、同じリクエストを
毎回サーバに投げに行かないようにするためのキャッシュ層。

依頼人の意向でDBはSQLite方針のため、キャッシュのためだけにRedis等の
別ミドルウェアを増やさず、既存の opendata_queue.db にテーブルを
1つ追加するだけで完結させている。

■ 位置づけ（マナー対策）
以前、collectors/opendata_collector.py や orchestrator/opendata_workflow.py
の run_download は、実行するたびに毎回ライブでHTTPを叩いていた。
同じテーマに対して collect → download を試行錯誤しながら何度も
実行すると、その分だけ東京都のサーバへの負荷が増える。
ここでキャッシュすることで「同じ検索・同じダウンロードURLは
24時間以内なら再取得しない」を徹底できる。

■ 使い方
    cache = CacheManager(db_path="data/opendata_queue.db", ttl_hours=24)
    key = cache.make_key(url, params)
    hit = cache.get(key)
    if hit is None:
        body = do_http_request()
        cache.set(key, url, body)
    else:
        body = hit
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 24.0


def ensure_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS http_cache (
            cache_key TEXT PRIMARY KEY,
            url TEXT,
            body TEXT,
            fetched_at TIMESTAMP,
            expires_at TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_http_cache_expires_at ON http_cache(expires_at)")
    conn.commit()


class CacheManager:
    """SQLiteベースの単純なTTLキャッシュ。同じ(url, params)の組み合わせへの
    再取得を防ぎ、オープンデータAPIへの負荷を減らす。
    """

    def __init__(self, db_path: str, ttl_hours: float = DEFAULT_TTL_HOURS):
        self.db_path = db_path
        self.ttl_hours = ttl_hours

    @staticmethod
    def make_key(url: str, params: Optional[dict] = None) -> str:
        """url + paramsから一意なキャッシュキーを作る。
        paramsはキー順を正規化してからハッシュ化するので、
        辞書の順序が違っても同じキーになる。
        """
        normalized = json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
        raw = f"{url}?{normalized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[str]:
        """有効期限内ならキャッシュ済みbodyを返す。無い/期限切れならNone。"""
        conn = sqlite3.connect(self.db_path)
        try:
            ensure_cache_table(conn)
            cur = conn.execute(
                "SELECT body, expires_at FROM http_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            body, expires_at = row
            if self._is_expired(expires_at):
                return None
            return body
        finally:
            conn.close()

    def set(self, cache_key: str, url: str, body: str) -> None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.ttl_hours)
        conn = sqlite3.connect(self.db_path)
        try:
            ensure_cache_table(conn)
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO http_cache (cache_key, url, body, fetched_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key, url, body,
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
        finally:
            conn.close()

    def purge_expired(self) -> int:
        """期限切れのキャッシュ行を削除する。定期実行やCLIから呼ぶ想定。"""
        conn = sqlite3.connect(self.db_path)
        try:
            ensure_cache_table(conn)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with conn:
                cur = conn.execute("DELETE FROM http_cache WHERE expires_at < ?", (now_str,))
                deleted = cur.rowcount
            logger.info("期限切れキャッシュを %d 件削除しました", deleted)
            return deleted
        finally:
            conn.close()

    @staticmethod
    def _is_expired(expires_at: str) -> bool:
        try:
            expires_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return True
        return datetime.now(timezone.utc) >= expires_dt