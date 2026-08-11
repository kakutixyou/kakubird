

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engines/snapshot_engine.py
────────────────────────────
根拠データ（メタデータ・ダウンロードURL・カタログページ等）を
タイムスタンプ付きで永続化するスナップショット機構。

■ なぜ必要か
evidence_engine.py はDBの「現在の状態」から根拠を辿るが、元データは
自治体側の都合でいつでも更新・削除されうる。「あるスコアが表示された
時点で、実際にはどの数値・どのライセンス状態だったか」を後から
検証できるようにするには、都度の状態をイミュータブルに記録しておく
必要がある。これが snapshot_engine の役目。

■ theme_schema.py との連動
themes/*.yaml の `enable_snapshot` / `snapshot_targets` は、以前は
バリデーションされるだけで、実際にはどこからも参照されていなかった
（宣言されているのに使われていない設定）。この engine が初めてそれを
実際に読み、スナップショットの対象範囲を決める。

  snapshot_targets の意味:
    - "metadata"     : タイトル・フォーマット・ライセンス状態・自治体名など
    - "download_url" : データセットの実ダウンロードURL
    - "web_page"      : CKANカタログの当該データセットページURL（可能な場合のみ）

■ 使い方
    # JSON出力用（DBには書かない。今まで通りの build_theme_snapshot 相当）
    entries = build_theme_snapshot(db_path, theme, cfg=cfg)

    # 永続化（DBに1回分のスナップショットとして書き込む。履歴は追記のみで消さない）
    inserted = capture_snapshot(db_path, theme, cfg=cfg)

    # 過去のスナップショット履歴を取得
    history = get_snapshot_history(db_path, theme, city_name="世田谷区")
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from services.field_mapper import get_metric_field_candidates
from engines.normalize_engine import normalize_numeric_string
from orchestrator.theme_schema import resolve_effective_metric_key

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT_TARGETS = ["metadata"]
DEFAULT_CATALOG_BASE_URL = "https://catalog.data.metro.tokyo.lg.jp"


# ──────────────────────────────────────────────
# テーブル管理
# ──────────────────────────────────────────────
def ensure_snapshot_table(conn: sqlite3.Connection) -> None:
    """
    追記専用（append-only）のテーブル。INSERT OR REPLACE はしない。
    「同じitemを2回スナップショットしたら2行になる」ことで、
    時系列の証跡（タイムスタンプ保持）としての意味を持つ。
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS theme_snapshots (
            snapshot_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL,
            city_name TEXT,
            item_id TEXT NOT NULL,
            metric_key TEXT,
            payload_json TEXT NOT NULL,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_theme_snapshots_lookup "
        "ON theme_snapshots(theme, city_name, captured_at)"
    )
    conn.commit()


# ──────────────────────────────────────────────
# 対象データの取得（normalize_schema.get_usable_items と同じ条件）
# ──────────────────────────────────────────────
def _get_usable_items(db_path: str, theme: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT * FROM opendata_queue
            WHERE theme = ? AND status = 'DOWNLOADED' AND license_status = 'OK'
            """,
            (theme,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _derive_web_page_url(meta: dict, catalog_base_url: str) -> Optional[str]:
    """
    CKANのリソース情報から、可能であればカタログのデータセットページURLを
    推測する。多くのCKANサイトは /dataset/{package_id or name} で
    アクセスできるが、収集時に resource 単位の情報しか保存していないため
    package_id が無ければ None を返す（＝ web_page ターゲットは
    「取れる時だけ取る」ベストエフォート実装）。

    [既知の制約] collectors/opendata_collector.py は現状、
    resource（id/url/format等）だけを raw_metadata として保存しており、
    パッケージ名（カタログURLのスラッグ）は保持していない。
    正確な web_page を毎回取りたい場合は、収集時に
    pkg.get("name") も raw_metadata に含めるよう opendata_collector.py 側の
    拡張が必要。
    """
    package_id = meta.get("package_id")
    if package_id:
        return f"{catalog_base_url.rstrip('/')}/dataset/{package_id}"
    return None


# ──────────────────────────────────────────────
# 1件分のスナップショットペイロード構築
# ──────────────────────────────────────────────
def build_snapshot_entry(
    item: dict,
    metric_key: str,
    cfg: Optional[dict] = None,
    snapshot_targets: Optional[list[str]] = None,
    catalog_base_url: str = DEFAULT_CATALOG_BASE_URL,
) -> dict:
    """
    1データセット分のスナップショットペイロードを組み立てる。
    snapshot_targets（"metadata"/"download_url"/"web_page"）に応じて
    含める情報を変える。指定が無ければ ["metadata"] のみ。
    """
    meta = json.loads(item["raw_metadata"] or "{}")
    targets = snapshot_targets if snapshot_targets is not None else DEFAULT_SNAPSHOT_TARGETS

    theme = item["theme"]
    candidates = get_metric_field_candidates(theme, cfg)
    raw_value = 1.0
    for key in candidates:
        val = meta.get(key)
        if val is None:
            continue
        parsed = normalize_numeric_string(val)
        if parsed is not None:
            raw_value = parsed
            break

    entry: dict = {
        "district": item.get("municipality") or "不明",
        "metricKey": metric_key,
        "rawValue": raw_value,
        "unit": "",
        "datasetTitle": item["title"],
        "fetchedAt": item["updated_at"],
        "license": item.get("license_id", ""),
        "licenseStatus": item.get("license_status", "unknown"),
    }

    if "metadata" in targets:
        entry["metadata"] = {
            "format": item.get("format"),
            "status": item.get("status"),
            "municipality": item.get("municipality"),
        }
    if "download_url" in targets:
        entry["downloadUrl"] = item.get("url", "")
    if "web_page" in targets:
        entry["webPageUrl"] = _derive_web_page_url(meta, catalog_base_url)

    return entry


def build_theme_snapshot(
    db_path: str,
    theme: str,
    metric_key: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> list[dict]:
    """
    テーマ全体のスナップショット一覧を生成する（district別の生値リスト）。
    DBには書き込まない、JSON出力用の従来どおりの関数（normalize_schema.py の
    同名関数から移設）。metric_key を省略した場合は resolve_effective_metric_key
    （cfgのmetric_keyかテーマ名）を使う。
    """
    resolved_metric_key = metric_key or resolve_effective_metric_key(theme, cfg or {})
    snapshot_targets = (cfg or {}).get("snapshot_targets", DEFAULT_SNAPSHOT_TARGETS)
    items = _get_usable_items(db_path, theme)
    return [
        build_snapshot_entry(item, resolved_metric_key, cfg=cfg, snapshot_targets=snapshot_targets)
        for item in items
    ]


# ──────────────────────────────────────────────
# 永続化（本題: タイムスタンプ付きで残す）
# ──────────────────────────────────────────────
def capture_snapshot(
    db_path: str,
    theme: str,
    cfg: Optional[dict] = None,
    force: bool = False,
    catalog_base_url: str = DEFAULT_CATALOG_BASE_URL,
) -> int:
    """
    現時点の根拠データを theme_snapshots に追記する（既存行は消さない）。

    cfg["enable_snapshot"] が False（デフォルト）のテーマは、誤って
    毎回スナップショットを溜め続けないよう、明示的に force=True を
    渡さない限りスキップする。
    """
    cfg = cfg or {}
    if not cfg.get("enable_snapshot", False) and not force:
        logger.info(
            f"[{theme}] enable_snapshot が false のためスナップショットをスキップします。"
            f"強制的に実行するには force=True を指定してください。"
        )
        return 0

    metric_key = resolve_effective_metric_key(theme, cfg)
    snapshot_targets = cfg.get("snapshot_targets", DEFAULT_SNAPSHOT_TARGETS)
    items = _get_usable_items(db_path, theme)

    if not items:
        logger.warning(f"[{theme}] スナップショット対象のデータがありません（license_status='OK'かつDOWNLOADEDが必要）。")
        return 0

    conn = sqlite3.connect(db_path)
    ensure_snapshot_table(conn)
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    inserted = 0
    with conn:
        for item in items:
            payload = build_snapshot_entry(
                item, metric_key, cfg=cfg,
                snapshot_targets=snapshot_targets,
                catalog_base_url=catalog_base_url,
            )
            conn.execute(
                """
                INSERT INTO theme_snapshots
                (theme, city_name, item_id, metric_key, payload_json, captured_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    theme, item.get("municipality"), item["id"], metric_key,
                    json.dumps(payload, ensure_ascii=False), captured_at,
                ),
            )
            inserted += 1
    conn.close()

    logger.info(f"[{theme}] スナップショットを {inserted} 件、captured_at={captured_at} で保存しました。")
    return inserted


# ──────────────────────────────────────────────
# 履歴取得
# ──────────────────────────────────────────────
def get_snapshot_history(
    db_path: str,
    theme: str,
    city_name: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    過去のスナップショットを新しい順に返す。
    「このスコアは過去のどの時点のデータに基づいていたか」を
    振り返る用途（内訳画面の「更新履歴」表示など）を想定。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_snapshot_table(conn)
    try:
        query = "SELECT * FROM theme_snapshots WHERE theme = ?"
        params: list = [theme]
        if city_name:
            query += " AND city_name = ?"
            params.append(city_name)
        query += " ORDER BY captured_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for r in rows:
        row = dict(r)
        row["payload"] = json.loads(row.pop("payload_json") or "{}")
        results.append(row)
    return results