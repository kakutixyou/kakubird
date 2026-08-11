#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engines/evidence_engine.py
────────────────────────────
スコア → 区 → データセット → 行 → セル、まで遡れるようにする「証跡」エンジン。

ward_scores / ward_metrics の背後にある実データ
（normalized_facilities.raw_json、opendata_queue のデータセット情報）を辿り、
「このスコアはどのデータセットの、どの行の、どの列由来か」を返す。
api.py の /api/wards/{ward_name} で「なぜこの区がこの順位なのか」を
説明する内訳表示のために使う想定。

依存関係: services/field_mapper.py の extract_numeric_field_with_source を
使って、実際にヒットしたカラム名・セルの生の値まで追跡する。
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from services.field_mapper import get_metric_field_candidates, extract_numeric_field_with_source
from engines.normalize_engine import normalize_numeric_string


@dataclass
class DatasetEvidence:
    dataset_id: str
    title: str
    url: str
    format: str
    status: str
    license_status: str
    facility_count: int  # このデータセット由来の施設が何件 normalized_facilities に入っているか


@dataclass
class FacilityEvidence:
    facility_id: str
    facility_name: str
    address: Optional[str]
    matched_field: Optional[str]     # 実際にヒットしたカラム名（例: "面積"）。見つからなければNone
    matched_raw_value: Optional[str]  # そのセルの生の値（例: "1,200"）。見つからなければNone
    metric_value: float               # 数値化した後の値（見つからなければdefaultの1.0）
    dataset_id: str
    dataset_title: str
    dataset_url: str


@dataclass
class WardEvidence:
    theme: str
    city_name: str
    metric_label: str
    facility_count: int
    metric_sum: float
    confidence_score: Optional[float] = None  # engines/metrics_engine.py の信頼度(0〜100)。metrics未実行ならNone
    datasets: list[DatasetEvidence] = field(default_factory=list)
    sample_facilities: list[FacilityEvidence] = field(default_factory=list)


def get_ward_evidence(
    db_path: str,
    theme: str,
    city_name: str,
    cfg: Optional[dict] = None,
    sample_limit: int = 20,
) -> WardEvidence:
    """
    区・テーマを指定して、スコアの根拠となった施設データとデータセット一覧を返す。
    sample_limit は施設一覧を全件返すと重くなるための上限（デフォルト20件）。
    """
    metric_field_candidates = get_metric_field_candidates(theme, cfg)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT nf.id AS facility_id, nf.name, nf.address, nf.raw_json, nf.source_dataset_id,
                   oq.title AS dataset_title, oq.url AS dataset_url, oq.format AS dataset_format,
                   oq.status AS dataset_status, oq.license_status AS dataset_license_status
            FROM normalized_facilities nf
            LEFT JOIN opendata_queue oq
                   ON oq.theme = nf.theme AND oq.id = nf.source_dataset_id
            WHERE nf.theme = ? AND nf.municipality = ?
            ORDER BY nf.name ASC
            """,
            (theme, city_name),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    facility_count = len(rows)
    metric_sum = 0.0
    dataset_map: dict[str, DatasetEvidence] = {}
    sample_facilities: list[FacilityEvidence] = []
    metric_label = metric_field_candidates[0] if metric_field_candidates else "件数"

    for i, row in enumerate(rows):
        meta = json.loads(row["raw_json"] or "{}")
        value, matched_key, matched_raw = extract_numeric_field_with_source(meta, metric_field_candidates)
        if matched_key:
            # [パッチ] "1.2ha"のような単位混在の生値も、集計時と同じ換算(m²等)で
            # 一致させる。matched_raw_value には元の表記("1.2ha")をそのまま残し、
            # metric_value だけ正規化後の値にする。
            converted = normalize_numeric_string(matched_raw)
            if converted is not None:
                value = converted
        metric_sum += value

        dataset_id = row["source_dataset_id"] or ""
        if dataset_id not in dataset_map:
            dataset_map[dataset_id] = DatasetEvidence(
                dataset_id=dataset_id,
                title=row["dataset_title"] or "名称未設定",
                url=row["dataset_url"] or "",
                format=row["dataset_format"] or "UNKNOWN",
                status=row["dataset_status"] or "UNASSESSED",
                license_status=row["dataset_license_status"] or "unknown",
                facility_count=0,
            )
        dataset_map[dataset_id].facility_count += 1

        if i < sample_limit:
            sample_facilities.append(FacilityEvidence(
                facility_id=row["facility_id"],
                facility_name=row["name"],
                address=row["address"],
                matched_field=matched_key,
                matched_raw_value=matched_raw,
                metric_value=value,
                dataset_id=dataset_id,
                dataset_title=row["dataset_title"] or "名称未設定",
                dataset_url=row["dataset_url"] or "",
            ))

    # [パッチ] 信頼度(confidence_score)は engines/metrics_engine.py が
    # ward_metrics テーブルに保存済みの値をそのまま読む（ここで再計算はしない
    # ＝計算式が2箇所でズレるのを防ぐ）。metrics アクションが未実行なら None。
    confidence_score = None
    try:
        from engines.metrics_engine import get_ward_metrics
        ward_metrics = get_ward_metrics(db_path=db_path, theme=theme)
        wm = ward_metrics.get(city_name)
        if wm:
            confidence_score = wm.confidence_score
    except ImportError:
        pass

    return WardEvidence(
        theme=theme,
        city_name=city_name,
        metric_label=metric_label,
        facility_count=facility_count,
        metric_sum=round(metric_sum, 2),
        confidence_score=confidence_score,
        datasets=list(dataset_map.values()),
        sample_facilities=sample_facilities,
    )


def get_dataset_evidence(db_path: str, theme: str, dataset_id: str, limit: int = 100) -> list[FacilityEvidence]:
    """
    1つのデータセット(dataset_id)由来の施設行を一覧表示したい場合のドリルダウン用。
    「このデータセットから正規化された施設はどれか」を返す（matched_field等は付与しない軽量版）。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT nf.id AS facility_id, nf.name, nf.address, nf.raw_json,
                   oq.title AS dataset_title, oq.url AS dataset_url
            FROM normalized_facilities nf
            LEFT JOIN opendata_queue oq
                   ON oq.theme = nf.theme AND oq.id = nf.source_dataset_id
            WHERE nf.theme = ? AND nf.source_dataset_id = ?
            ORDER BY nf.name ASC
            LIMIT ?
            """,
            (theme, dataset_id, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [
        FacilityEvidence(
            facility_id=row["facility_id"],
            facility_name=row["name"],
            address=row["address"],
            matched_field=None,
            matched_raw_value=None,
            metric_value=0.0,
            dataset_id=dataset_id,
            dataset_title=row["dataset_title"] or "名称未設定",
            dataset_url=row["dataset_url"] or "",
        )
        for row in rows
    ]