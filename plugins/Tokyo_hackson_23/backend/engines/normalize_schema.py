#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orchestrator/normalize_schema.py
──────────────────────────────
① opendata_queue の raw_metadata を対象に、ライセンス判定・メトリクス抽出・
   施設データへの正規化を行い、normalized_facilities テーブルへ永続化する。

処理の流れ:
  backfill_license_status()       … raw_metadataからlicense_status/license_idを判定してDB反映
  normalize_and_persist_facilities() … license_status='OK'なitemを施設データとしてDBへ書き込み
  build_theme_snapshot()          … JSON出力用の%内訳スナップショットを生成（DBには書かない）

--- パッチ履歴 ---
- カラム名の候補リスト（name/address/緯度/経度、テーマ別数値項目）が
  engines/metrics_engine.py と別々にハードコードされていたのを
  services/field_mapper.py に一本化。テーマYAMLの `metric_fields` も
  ここ経由で反映されるようになった（cfg引数を渡した場合のみ）。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Callable, Optional

from Tokyo_hackson_23.backend.services.field_mapper import (
    get_metric_field_candidates,
    extract_facility_core_fields,
)
from .normalize_engine import normalize_numeric_string

# ──────────────────────────────────────────────
# ライセンス判定
# ──────────────────────────────────────────────
LICENSE_OK_IDS = {
    "cc-by", "cc-by-4.0", "cc-by-sa-4.0", "cc-zero", "cc0-1.0",
    "notspecified",  # 東京都データはnotspecifiedでも規約上は二次利用可のケースが多いため要運用判断
}
LICENSE_NG_KEYWORDS = ["禁止", "許可が必要", "no-commercial", "non-commercial"]


def judge_license(meta: dict) -> tuple[str, Optional[str]]:
    """raw_metadataからライセンスOK/NG/unknownを判定する"""
    license_id = (meta.get("license_id") or "").strip().lower()
    license_title = (meta.get("license_title") or "")

    if any(kw in license_title for kw in LICENSE_NG_KEYWORDS):
        return "NG", license_id or None

    if license_id in LICENSE_OK_IDS:
        return "OK", license_id or None

    if license_id:
        return "unknown", license_id
    return "unknown", None


def get_usable_items(db_path: str, theme: str) -> list[dict]:
    """ライセンス判定でOKになったitemだけを対象にする"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT * FROM opendata_queue
        WHERE theme = ? AND status = 'DOWNLOADED' AND license_status = 'OK'
        """,
        (theme,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def backfill_license_status(db_path: str, theme: str) -> int:
    """DOWNLOADED済みだがlicense_status未判定のitemに対して判定を実行しDB反映する"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT theme, id, raw_metadata FROM opendata_queue
        WHERE theme = ? AND status = 'DOWNLOADED' AND license_status = 'unknown'
        """,
        (theme,),
    )
    rows = cur.fetchall()
    updated = 0
    for row in rows:
        meta = json.loads(row["raw_metadata"] or "{}")
        status, license_id = judge_license(meta)
        conn.execute(
            "UPDATE opendata_queue SET license_status=?, license_id=? WHERE theme=? AND id=?",
            (status, license_id, row["theme"], row["id"]),
        )
        updated += 1
    conn.commit()
    conn.close()
    return updated


# ──────────────────────────────────────────────
# テーマ別メトリクス抽出
# ──────────────────────────────────────────────
# [パッチ] 候補カラム名は services/field_mapper.py、単位換算・表記ゆれ吸収は
# engines/normalize_engine.py に統合済み。cfg（テーマYAMLの読み込み結果）を
# 渡すと `metric_fields` が優先される。
def extract_metric(theme: str, meta: dict, cfg: Optional[dict] = None) -> float:
    candidates = get_metric_field_candidates(theme, cfg)
    for key in candidates:
        val = meta.get(key)
        if val is None:
            continue
        parsed = normalize_numeric_string(val)
        if parsed is not None:
            return parsed
    return 1.0


# ──────────────────────────────────────────────
# ② 施設データの正規化 → DB永続化（今回の本題）
# ──────────────────────────────────────────────
def normalize_and_persist_facilities(db_path: str, theme: str) -> dict:
    """
    license_status='OK' かつ status='DOWNLOADED' のitemを
    施設データとして normalized_facilities テーブルへ書き込む。

    戻り値: {"inserted": 件数, "skipped_no_coords": 件数} の集計dict
      → 位置情報が取れなかった件数もここで可視化し、②の精度把握に使う
    """
    items = get_usable_items(db_path, theme)
    if not items:
        return {"inserted": 0, "skipped_no_coords": 0, "total_candidates": 0}

    conn = sqlite3.connect(db_path)
    inserted = 0
    skipped_no_coords = 0

    with conn:
        for item in items:
            meta = json.loads(item["raw_metadata"] or "{}")
            # [パッチ] services/field_mapper.py の共通ヘルパーへ移設
            name, address, lat, lon = extract_facility_core_fields(meta, fallback_title=item.get("title"))

            if lat is None or lon is None:
                skipped_no_coords += 1  # 位置情報なしでも一覧表示用に登録自体は行う（地図表示だけ不可）

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO normalized_facilities
                    (id, theme, municipality, name, address, latitude, longitude, raw_json, source_dataset_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"], theme, item.get("municipality"),
                        name, address, lat, lon,
                        json.dumps(meta, ensure_ascii=False),
                        item["id"],
                    ),
                )
                inserted += 1
            except sqlite3.Error:
                continue

    conn.close()
    return {
        "inserted": inserted,
        "skipped_no_coords": skipped_no_coords,
        "total_candidates": len(items),
    }


# ──────────────────────────────────────────────
# JSON出力用スナップショット（DBには書き込まない）
# ──────────────────────────────────────────────
# [パッチ] 実装は engines/snapshot_engine.py に統合済み。永続化（タイムスタンプ付き
# 保存）が必要な場合は engines.snapshot_engine.capture_snapshot を使うこと。
# ここでは後方互換のため同名関数を薄いラッパーとして残す。
def build_snapshot_entry(item: dict, metric_key: str, cfg: Optional[dict] = None) -> dict:
    from Tokyo_hackson_23.backend.engines.snapshot_engine import build_snapshot_entry as _build_snapshot_entry
    return _build_snapshot_entry(item, metric_key, cfg=cfg)


def build_theme_snapshot(db_path: str, theme: str, metric_key: str, cfg: Optional[dict] = None) -> list[dict]:
    from Tokyo_hackson_23.backend.engines.snapshot_engine import build_theme_snapshot as _build_theme_snapshot
    return _build_theme_snapshot(db_path, theme, metric_key=metric_key, cfg=cfg)