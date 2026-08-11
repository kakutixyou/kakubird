#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/field_mapper.py
─────────────────────────
自治体ごと・提供元ごとにバラつくCSV/JSONのカラム名を、テーマ横断で
統一的に読み取るためのマッピングテーブルと抽出ヘルパー。

■ 今までの重複
- orchestrator/normalize_schema.py の _extract_facility_fields()
  → name/address/緯度/経度の候補カラム名がハードコード
- engines/metrics_engine.py の THEME_METRIC_FIELD_CANDIDATES
  → テーマ別の数値項目（面積・定員等）の候補カラム名がハードコード
この2つが別々の場所に別々の書式で存在していたのを、ここに一本化する。

■ テーマYAMLでの上書き
themes/*.yaml に `metric_fields:` を書くと、そのテーマだけデフォルト候補
より優先して検索される。
    # themes/park.yaml
    metric_fields:
      - 公園面積
      - 面積

metric_fields を書かなければ、このモジュールのデフォルト候補
（DEFAULT_THEME_METRIC_FIELD_CANDIDATES）がそのまま使われる。
"""

from __future__ import annotations

from typing import Optional


# ──────────────────────────────────────────────
# 施設共通フィールド（name/address/緯度/経度）の候補カラム名
# ──────────────────────────────────────────────
FACILITY_FIELD_CANDIDATES: dict[str, list[str]] = {
    "name": ["施設名", "name", "名称"],
    "address": ["住所", "address", "所在地"],
    "latitude": ["緯度", "latitude", "lat"],
    "longitude": ["経度", "longitude", "lng", "lon"],
}

# ──────────────────────────────────────────────
# テーマ別の数値指標フィールド候補（デフォルト）
# ──────────────────────────────────────────────
# engines/metrics_engine.py の richness_score 計算や、
# orchestrator/normalize_schema.py の extract_metric() が使う。
# 未定義のテーマ（aed / library / sports / wifi 等）は「施設1件=1」として
# 単純にカウントする（候補なし=[]）。
DEFAULT_THEME_METRIC_FIELD_CANDIDATES: dict[str, list[str]] = {
    "childcare": ["定員", "capacity", "定員数"],
    "park": ["面積", "area", "面積(㎡)", "面積（㎡）"],
    "disaster": ["収容人数", "capacity"],
}

DEFAULT_METRIC_VALUE = 1.0


# ──────────────────────────────────────────────
# 候補解決
# ──────────────────────────────────────────────
def get_metric_field_candidates(theme: str, cfg: Optional[dict] = None) -> list[str]:
    """
    テーマの数値指標フィールド候補を返す。
    cfg（テーマYAMLの読み込み結果）に metric_fields があれば、
    デフォルト候補より優先した順序で連結する（重複は除去）。
    """
    yaml_candidates = list((cfg or {}).get("metric_fields") or [])
    default_candidates = DEFAULT_THEME_METRIC_FIELD_CANDIDATES.get(theme, [])

    merged: list[str] = []
    for c in yaml_candidates + default_candidates:
        if c not in merged:
            merged.append(c)
    return merged


def get_facility_field_candidates(field: str) -> list[str]:
    """name/address/latitude/longitude の候補カラム名を返す。"""
    return FACILITY_FIELD_CANDIDATES.get(field, [])


# ──────────────────────────────────────────────
# 抽出ヘルパー
# ──────────────────────────────────────────────
def extract_field(raw_json: dict, candidates: list[str]) -> Optional[str]:
    """候補カラム名の中から最初に見つかった非空の値をそのまま返す。"""
    for key in candidates:
        val = raw_json.get(key)
        if val is not None and str(val).strip():
            return val
    return None


def extract_numeric_field(raw_json: dict, candidates: list[str], default: float = DEFAULT_METRIC_VALUE) -> float:
    """
    候補カラム名から数値を読み取る。
    "1,200" や "800㎡" のようなカンマ・単位混じりの表記にも対応する。
    候補が空、または値が見つからない/数値化できない場合は default を返す
    （＝「面積が分からなければ1件としてカウントする」というfacility_count用途を想定）。
    """
    value, _matched_key, _raw_value = extract_numeric_field_with_source(raw_json, candidates, default)
    return value


def extract_numeric_field_with_source(
    raw_json: dict, candidates: list[str], default: float = DEFAULT_METRIC_VALUE
) -> tuple[float, Optional[str], Optional[str]]:
    """
    extract_numeric_field と同じ数値抽出をしつつ、
    「実際にヒットしたカラム名」と「そのセルの生の値」も一緒に返す。
    engines/evidence_engine.py が「このスコアはどの列由来か」を
    追跡するために使う。
    戻り値: (数値, ヒットしたカラム名 or None, 生の値の文字列 or None)
    """
    if not candidates:
        return default, None, None
    for key in candidates:
        val = raw_json.get(key)
        if val is None:
            continue
        cleaned = str(val).replace(",", "").strip()
        numeric = "".join(c for c in cleaned if c.isdigit() or c in ".-")
        if numeric and numeric not in ("-", "."):
            try:
                return float(numeric), key, str(val)
            except ValueError:
                continue
    return default, None, None


def extract_float_field(raw_json: dict, candidates: list[str]) -> Optional[float]:
    """
    緯度経度など「見つからなければNoneにしたい」数値フィールド用。
    extract_numeric_field と違い default へのフォールバックはしない。
    """
    for key in candidates:
        val = raw_json.get(key)
        if val is None:
            continue
        try:
            return float(str(val).strip())
        except (ValueError, TypeError):
            continue
    return None


def extract_facility_core_fields(
    raw_json: dict, fallback_title: Optional[str] = None
) -> tuple[str, Optional[str], Optional[float], Optional[float]]:
    """
    施設の name / address / latitude / longitude をまとめて抽出する。
    normalize_schema.py の _extract_facility_fields から移設したもの。
    """
    name = extract_field(raw_json, FACILITY_FIELD_CANDIDATES["name"]) or fallback_title or "名称不明"
    address = extract_field(raw_json, FACILITY_FIELD_CANDIDATES["address"])
    lat = extract_float_field(raw_json, FACILITY_FIELD_CANDIDATES["latitude"])
    lon = extract_float_field(raw_json, FACILITY_FIELD_CANDIDATES["longitude"])
    return name, address, lat, lon