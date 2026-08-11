#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engines/metrics_engine.py
─────────────────────────
normalized_facilities（正規化済み施設データ）から実際の数値
（面積・定員・収容人数など）を読み取り、区ごとの
「密度・カバー率・最新性」を集計するエンジン。

■ なぜ必要か
これまでの run_score() は opendata_queue の COUNT(*)
（＝その区がそのテーマで公開している"データセット（CSVファイル）の件数"）
を richness_score の元にしていた。しかし、これは実際の施設数・面積とは
無関係にブレる指標だった。
  例）A区が公園200件を1本のCSVにまとめて公開 → raw_count = 1
      B区が同じ200件を5本のCSVに分けて公開     → raw_count = 5
      → B区の方が「公園が充実している」スコアになってしまう

metrics_engine は、normalize_schema.py が作った normalized_facilities
（施設1件=1行）を実際に数えて・実際の数値項目（面積・定員等）を合算する
ことで、この歪みを取り除く。score_engine（run_score）はこちらの値を
優先して使うように差し替える。

■ 使い方
    from engines.metrics_engine import run_metrics
    run_metrics(db_path="data/opendata_queue.db", theme="park")

    # または CLI から:
    python orchestrator/opendata_workflow.py metrics --theme park
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from services.field_mapper import get_metric_field_candidates
from engines.normalize_engine import normalize_numeric_string

logger = logging.getLogger(__name__)


# [パッチ] 候補カラム名テーブルと数値抽出ロジックは services/field_mapper.py に
# 一本化した（normalize_schema.py 側の重複実装ともここで揃える）。
# テーマYAMLの `metric_fields:` はここを経由して反映される。

DEFAULT_METRIC_VALUE = 1.0


@dataclass
class WardMetrics:
    theme: str
    city_name: str
    facility_count: int
    metric_sum: float
    metric_label: str                    # 何を合計したか（"面積(㎡)"等、無ければ"件数"）
    coord_coverage: float                 # 緯度経度が取れている割合 (0.0〜1.0)
    freshness_days_avg: Optional[float]   # 元データセットの平均取得経過日数（None=不明）
    dataset_count: int                    # このスコアの根拠になっている独立データセットの数
    confidence_score: float               # このスコアの信頼度 (0〜100)
    calculated_at: str


# ──────────────────────────────────────────────
# テーブル管理
# ──────────────────────────────────────────────
def ensure_ward_metrics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ward_metrics (
            theme TEXT NOT NULL,
            city_name TEXT NOT NULL,
            facility_count INTEGER DEFAULT 0,
            metric_sum REAL DEFAULT 0.0,
            metric_label TEXT DEFAULT '件数',
            coord_coverage REAL DEFAULT 0.0,
            freshness_days_avg REAL,
            dataset_count INTEGER DEFAULT 0,
            confidence_score REAL DEFAULT 0.0,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (theme, city_name)
        )
        """
    )
    # 既存DBへの後方互換マイグレーション（旧バージョンで作られたテーブルに列を追加）
    cols = {row[1] for row in conn.execute("PRAGMA table_info(ward_metrics)").fetchall()}
    if "dataset_count" not in cols:
        conn.execute("ALTER TABLE ward_metrics ADD COLUMN dataset_count INTEGER DEFAULT 0")
    if "confidence_score" not in cols:
        conn.execute("ALTER TABLE ward_metrics ADD COLUMN confidence_score REAL DEFAULT 0.0")
    conn.commit()


# ──────────────────────────────────────────────
# 数値抽出ヘルパー
# ──────────────────────────────────────────────
def _extract_metric_value(candidates: list[str], raw_json: dict) -> float:
    """raw_json（施設1件分の元データ）から候補カラム名を使って数値を拾う。
    [パッチ] engines/normalize_engine.py 経由に変更。"1.2ha" のような
    面積単位混在の表記も m² に換算してから合算されるようになった。
    見つからない/数値化できない場合は 1.0（=1件としてカウント）にフォールバック。
    """
    for key in candidates:
        val = raw_json.get(key)
        if val is None:
            continue
        parsed = normalize_numeric_string(val)
        if parsed is not None:
            return parsed
    return DEFAULT_METRIC_VALUE


def _metric_label(candidates: list[str]) -> str:
    return candidates[0] if candidates else "件数"


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────
# 信頼度（confidence_score）
# ──────────────────────────────────────────────
# 4つの観点を均等（各25%）に重み付けして平均する、0〜100のスコア。
# 「表示されているスコアがどれだけ信頼できそうか」を一目で分かるようにする。
def _compute_confidence(
    coord_coverage: float,
    freshness_days_avg: Optional[float],
    facility_count: int,
    dataset_count: int,
) -> float:
    """
    - coverage_score: 座標が取れている施設の割合（位置情報の完全性）
    - freshness_score: 元データセット取得からの経過日数（新しいほど高評価、365日で0点）
    - sample_size_score: 施設件数の十分さ（1件だけの区は信頼度が低い。5件以上で満点）
    - diversity_score: 何種類の独立したデータセットに基づいているか
      （1本のCSVだけに依存していると、そのデータセット固有の欠陥や偏りに
      スコア全体が引きずられるため、複数データセットの方が信頼できる）
    """
    coverage_score = min(100.0, max(0.0, coord_coverage) * 100.0)

    if freshness_days_avg is None:
        freshness_score = 50.0  # 不明な場合は中立値（減点も加点もしない）
    else:
        freshness_score = max(0.0, min(100.0, 100.0 - (freshness_days_avg / 365.0) * 100.0))

    sample_size_score = min(100.0, facility_count * 20.0)  # 5件以上で満点
    diversity_score = min(100.0, dataset_count * 50.0)     # 2データセット以上で満点

    return round((coverage_score + freshness_score + sample_size_score + diversity_score) / 4.0, 1)


# ──────────────────────────────────────────────
# 集計本体
# ──────────────────────────────────────────────
def compute_ward_metrics(db_path: str, theme: str, cfg: Optional[dict] = None) -> list[WardMetrics]:
    """
    normalized_facilities を区ごとに集計し、WardMetrics のリストを返す
    （DB保存は persist_ward_metrics() 側で行う。副作用なしで呼べる）。

    normalized_facilities から見て、元データセットの updated_at（取得日時）を
    opendata_queue と JOIN して「鮮度（何日前のデータか）」も併せて計算する。

    cfg（テーマYAMLの読み込み結果）を渡すと、`metric_fields` があれば
    services/field_mapper.py のデフォルト候補より優先して使われる。
    """
    metric_field_candidates = get_metric_field_candidates(theme, cfg)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.execute(
            """
            SELECT nf.municipality, nf.raw_json, nf.latitude, nf.longitude,
                   nf.source_dataset_id, oq.updated_at AS source_updated_at
            FROM normalized_facilities nf
            LEFT JOIN opendata_queue oq
                   ON oq.theme = nf.theme AND oq.id = nf.source_dataset_id
            WHERE nf.theme = ? AND nf.municipality IS NOT NULL AND nf.municipality != ''
            """,
            (theme,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning(
            f"[{theme}] normalized_facilities にデータがありません。"
            f"先に `normalize_schema` アクションを実行してください。"
        )
        return []

    by_ward: dict[str, dict] = {}
    now = datetime.now(timezone.utc)

    for row in rows:
        ward = row["municipality"]
        bucket = by_ward.setdefault(ward, {
            "facility_count": 0,
            "metric_sum": 0.0,
            "with_coords": 0,
            "freshness_days": [],
            "dataset_ids": set(),
        })

        meta = json.loads(row["raw_json"] or "{}")
        bucket["facility_count"] += 1
        bucket["metric_sum"] += _extract_metric_value(metric_field_candidates, meta)

        if row["source_dataset_id"]:
            bucket["dataset_ids"].add(row["source_dataset_id"])

        if row["latitude"] is not None and row["longitude"] is not None:
            bucket["with_coords"] += 1

        ts = _parse_timestamp(row["source_updated_at"])
        if ts:
            bucket["freshness_days"].append((now - ts).days)

    metric_label = _metric_label(metric_field_candidates)
    calculated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    results: list[WardMetrics] = []

    for ward, bucket in by_ward.items():
        count = bucket["facility_count"]
        coord_coverage = (bucket["with_coords"] / count) if count else 0.0
        freshness_list = bucket["freshness_days"]
        freshness_avg = (sum(freshness_list) / len(freshness_list)) if freshness_list else None
        dataset_count = len(bucket["dataset_ids"])
        confidence_score = _compute_confidence(coord_coverage, freshness_avg, count, dataset_count)

        results.append(WardMetrics(
            theme=theme,
            city_name=ward,
            facility_count=count,
            metric_sum=round(bucket["metric_sum"], 2),
            metric_label=metric_label,
            coord_coverage=round(coord_coverage, 4),
            freshness_days_avg=round(freshness_avg, 1) if freshness_avg is not None else None,
            dataset_count=dataset_count,
            confidence_score=confidence_score,
            calculated_at=calculated_at,
        ))

    return results


def persist_ward_metrics(db_path: str, metrics: list[WardMetrics]) -> int:
    """compute_ward_metrics() の結果を ward_metrics テーブルへ保存する。"""
    if not metrics:
        return 0

    conn = sqlite3.connect(db_path)
    ensure_ward_metrics_table(conn)
    with conn:
        for m in metrics:
            conn.execute(
                """
                INSERT OR REPLACE INTO ward_metrics
                (theme, city_name, facility_count, metric_sum, metric_label,
                 coord_coverage, freshness_days_avg, dataset_count, confidence_score, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    m.theme, m.city_name, m.facility_count, m.metric_sum,
                    m.metric_label, m.coord_coverage, m.freshness_days_avg,
                    m.dataset_count, m.confidence_score, m.calculated_at,
                ),
            )
    conn.close()
    return len(metrics)


def get_ward_metrics(db_path: str, theme: str) -> dict[str, WardMetrics]:
    """score_engine 等から読む用のヘルパー。{区名: WardMetrics} の辞書を返す。
    ward_metrics テーブルが存在しない/空の場合は空dictを返す（例外は投げない）。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_ward_metrics_table(conn)
    cur = conn.execute("SELECT * FROM ward_metrics WHERE theme = ?", (theme,))
    rows = cur.fetchall()
    conn.close()

    return {
        r["city_name"]: WardMetrics(
            theme=r["theme"],
            city_name=r["city_name"],
            facility_count=r["facility_count"],
            metric_sum=r["metric_sum"],
            metric_label=r["metric_label"],
            coord_coverage=r["coord_coverage"],
            freshness_days_avg=r["freshness_days_avg"],
            dataset_count=r["dataset_count"] or 0,
            confidence_score=r["confidence_score"] or 0.0,
            calculated_at=r["calculated_at"],
        )
        for r in rows
    }


def run_metrics(db_path: str, theme: str, cfg: Optional[dict] = None) -> list[WardMetrics]:
    """orchestrator/CLIから呼ぶエントリポイント。計算して保存し、結果を返す。
    cfg（テーマYAMLの読み込み結果）を渡すと `metric_fields` が反映される。
    """
    metrics = compute_ward_metrics(db_path=db_path, theme=theme, cfg=cfg)
    saved = persist_ward_metrics(db_path=db_path, metrics=metrics)
    logger.info(f"[{theme}] ward_metrics 保存完了: {saved} 区分")
    for m in sorted(metrics, key=lambda x: x.metric_sum, reverse=True):
        logger.info(
            f"  {m.city_name}: {m.metric_label}={m.metric_sum} "
            f"(施設{m.facility_count}件, 座標カバー率{m.coord_coverage:.0%}, "
            f"鮮度平均{m.freshness_days_avg}日)"
        )
    return metrics