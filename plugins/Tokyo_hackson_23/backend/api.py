#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/api.py
──────
フロントエンド（Web画面）からの非同期リクエストに応じ、
23区のスコア一覧や、区をクリックした際の「詳細内訳」データを配信する FastAPI サーバー。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# プロジェクトルート & DBパスの自動判定
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "opendata_queue.db"

# orchestrator/opendata_workflow.py と共通の23区公式統計データ（一次情報）
WARD_DEMOGRAPHICS = {
    "千代田区": {"population_10k": 6.80,  "area_sqkm": 11.66, "children_0_5": 3500,  "population_10k_5y_ago": 6.80},
    "中央区":   {"population_10k": 17.50, "area_sqkm": 10.21, "children_0_5": 11000, "population_10k_5y_ago": 17.50},
    "港区":     {"population_10k": 26.00, "area_sqkm": 20.37, "children_0_5": 13500, "population_10k_5y_ago": 26.00},
    "新宿区":   {"population_10k": 35.00, "area_sqkm": 18.22, "children_0_5": 14000, "population_10k_5y_ago": 35.00},
    "文京区":   {"population_10k": 24.20, "area_sqkm": 11.29, "children_0_5": 11500, "population_10k_5y_ago": 24.20},
    "台東区":   {"population_10k": 21.50, "area_sqkm": 10.11, "children_0_5": 9000,  "population_10k_5y_ago": 21.50},
    "墨田区":   {"population_10k": 28.00, "area_sqkm": 13.77, "children_0_5": 12500, "population_10k_5y_ago": 28.00},
    "江東区":   {"population_10k": 53.00, "area_sqkm": 43.01, "children_0_5": 26000, "population_10k_5y_ago": 53.00},
    "品川区":   {"population_10k": 42.00, "area_sqkm": 22.84, "children_0_5": 20000, "population_10k_5y_ago": 42.00},
    "目黒区":   {"population_10k": 28.80, "area_sqkm": 14.67, "children_0_5": 12000, "population_10k_5y_ago": 28.80},
    "大田区":   {"population_10k": 74.50, "area_sqkm": 61.86, "children_0_5": 31000, "population_10k_5y_ago": 74.50},
    "世田谷区": {"population_10k": 94.00, "area_sqkm": 58.05, "children_0_5": 41000, "population_10k_5y_ago": 94.00},
    "渋谷区":   {"population_10k": 24.50, "area_sqkm": 15.11, "children_0_5": 10500, "population_10k_5y_ago": 24.50},
    "中野区":   {"population_10k": 34.50, "area_sqkm": 15.59, "children_0_5": 13500, "population_10k_5y_ago": 34.50},
    "杉並区":   {"population_10k": 58.00, "area_sqkm": 34.06, "children_0_5": 24000, "population_10k_5y_ago": 58.00},
    "豊島区":   {"population_10k": 30.00, "area_sqkm": 13.01, "children_0_5": 11500, "population_10k_5y_ago": 30.00},
    "北区":     {"population_10k": 35.50, "area_sqkm": 20.61, "children_0_5": 15000, "population_10k_5y_ago": 35.50},
    "荒川区":   {"population_10k": 22.00, "area_sqkm": 10.16, "children_0_5": 10000, "population_10k_5y_ago": 22.00},
    "板橋区":   {"population_10k": 58.50, "area_sqkm": 32.22, "children_0_5": 25000, "population_10k_5y_ago": 58.50},
    "練馬区":   {"population_10k": 74.50, "area_sqkm": 48.08, "children_0_5": 32000, "population_10k_5y_ago": 74.50},
    "足立区":   {"population_10k": 69.50, "area_sqkm": 53.25, "children_0_5": 31000, "population_10k_5y_ago": 69.50},
    "葛飾区":   {"population_10k": 45.50, "area_sqkm": 34.80, "children_0_5": 19000, "population_10k_5y_ago": 45.50},
    "江戸川区": {"population_10k": 69.00, "area_sqkm": 49.90, "children_0_5": 31500, "population_10k_5y_ago": 69.00},
}

app = FastAPI(
    title="オープンデータ内訳表示 Web API Server",
    description="23区のスコア一覧および、クリック時の詳細内訳（オープンデータ・施設一覧・指標根拠）を提供します",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    # Render等の環境変数からURLを取得
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL が設定されていません。環境変数を確認してください。"
        )
    # PostgreSQL (Supabase/Render) に接続
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn

# ──────────────────────────────────────────────
# Pydantic レスポンススキーマ定義
# ──────────────────────────────────────────────
class WardScoreSummary(BaseModel):
    city_name: str
    total_score: float
    quality_score: float
    richness_score: float
    raw_count: int


class FacilityDetail(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_json: Optional[Dict[str, Any]] = None


class DatasetResourceDetail(BaseModel):
    id: str
    title: str
    format: str
    url: str
    status: str
    has_coordinates: bool


class DatasetEvidenceItem(BaseModel):
    dataset_id: str
    title: str
    url: str
    format: str
    status: str
    license_status: str
    facility_count: int


class FacilityEvidenceItem(BaseModel):
    facility_id: str
    facility_name: str
    address: Optional[str] = None
    matched_field: Optional[str] = None
    matched_raw_value: Optional[str] = None
    metric_value: float
    dataset_id: str
    dataset_title: str
    dataset_url: str


class WardEvidenceSummary(BaseModel):
    metric_label: str
    facility_count: int
    metric_sum: float
    confidence_score: Optional[float] = None
    datasets: List[DatasetEvidenceItem]
    sample_facilities: List[FacilityEvidenceItem]


class WardDetailResponse(BaseModel):
    theme: str
    city_name: str
    demographics: Dict[str, Any]
    score_breakdown: Dict[str, Any]
    datasets: List[DatasetResourceDetail]
    facilities: List[FacilityDetail]
    evidence: Optional[WardEvidenceSummary] = None


# ──────────────────────────────────────────────
# API エンドポイント
# ──────────────────────────────────────────────

@app.get("/", summary="ヘルスチェック")
def read_root():
    return {"status": "ok", "message": "OpenData API is running."}


@app.get("/api/scores", response_model=List[WardScoreSummary], summary="23区のスコアランキング取得")
def get_ward_scores(theme: str = Query(..., description="テーマ識別子 (例: childcare, park, aed)")):
    """一覧画面やグラフ描画で使う全23区のスコアランキングを返します。"""
    conn = get_db_connection()
    try:
        # psycopg2の場合は cursor を取得してから execute を実行する
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT city_name, total_score, quality_score, richness_score, raw_count
                FROM ward_scores
                WHERE theme = %s
                ORDER BY total_score DESC
                """,
                (theme,)  # psycopg2ではプレースホルダーが ? ではなく %s になります
            )
            rows = cur.fetchall()
            return [
                WardScoreSummary(
                    city_name=r["city_name"],
                    total_score=r["total_score"],
                    quality_score=r["quality_score"],
                    richness_score=r["richness_score"],
                    raw_count=r["raw_count"],
                )
                for r in rows
            ]
    finally:
        conn.close()


def _build_ward_evidence(theme: str, ward_name: str) -> Optional[WardEvidenceSummary]:
    try:
        from Tokyo_hackson_23.backend.engines.evidence_engine import get_ward_evidence
    except ImportError:
        logger.warning("engines/evidence_engine.py が見つかりません。evidence は null で返します。")
        return None

    try:
        ev = get_ward_evidence(db_path=str(DB_PATH), theme=theme, city_name=ward_name)
    except Exception as e:
        logger.warning(f"[{theme}/{ward_name}] evidence 計算に失敗しました: {e}")
        return None

    # 施設数が0でもエビデンス（オープンデータ情報など）はフロントエンドに返す
    sample_facs = []
    if ev.facility_count > 0:
        sample_facs = [FacilityEvidenceItem(**asdict(f)) for f in ev.sample_facilities]

    return WardEvidenceSummary(
        metric_label=ev.metric_label,
        facility_count=ev.facility_count,
        metric_sum=ev.metric_sum,
        confidence_score=ev.confidence_score,
        datasets=[DatasetEvidenceItem(**asdict(d)) for d in ev.datasets],
        sample_facilities=sample_facs,
    )

@app.get("/api/wards/{ward_name}", response_model=WardDetailResponse, summary="クリック時の「詳細内訳」取得")
def get_ward_detail(
    ward_name: str,
    theme: str = Query(..., description="テーマ識別子 (例: childcare, park)"),
):
    conn = get_db_connection()
    try:
        # 1. 人口・統計データの取得
        demo = WARD_DEMOGRAPHICS.get(ward_name)
        if not demo:
            raise HTTPException(status_code=404, detail=f"指定された区が存在しません: {ward_name}")

        with conn.cursor() as cur:
            # 2. スコア内訳の取得
            cur.execute(
                """
                SELECT raw_count, quality_score, richness_score, total_score, calculated_at
                FROM ward_scores
                WHERE theme = %s AND city_name = %s
                """,
                (theme, ward_name),
            )
            score_row = cur.fetchone()
            score_breakdown = dict(score_row) if score_row else {
                "raw_count": 0, "quality_score": 0.0, "richness_score": 0.0, "total_score": 0.0
            }

            # 3. 収集済みオープンデータセット（CKANリンク集）
            cur.execute(
                """
                SELECT id, title, format, url, status, has_coordinates
                FROM opendata_queue
                WHERE theme = %s AND municipality = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (theme, ward_name),
            )
            datasets = [
                DatasetResourceDetail(
                    id=r["id"],
                    title=r["title"] or "名称未設定",
                    format=r["format"] or "UNKNOWN",
                    url=r["url"] or "",
                    status=r["status"] or "UNASSESSED",
                    has_coordinates=bool(r["has_coordinates"]),
                )
                for r in cur.fetchall()
            ]

            # 4. 正規化済み施設リスト
            cur.execute(
                """
                SELECT id, name, address, latitude, longitude, raw_json
                FROM normalized_facilities
                WHERE theme = %s AND municipality = %s
                ORDER BY name ASC
                LIMIT 500
                """,
                (theme, ward_name),
            )
            
            facilities = []
            for r in cur.fetchall():
                # psycopg2のJSONB型は自動でdictになりますが、テキスト型で入っている場合に備えて安全に変換します
                raw_json = r["raw_json"]
                if isinstance(raw_json, str):
                    try:
                        raw_json = json.loads(raw_json)
                    except json.JSONDecodeError:
                        raw_json = None
                
                facilities.append(
                    FacilityDetail(
                        id=str(r["id"]),
                        name=r["name"],
                        address=r["address"],
                        latitude=r["latitude"],
                        longitude=r["longitude"],
                        raw_json=raw_json,
                    )
                )

        # 5. スコアの根拠（evidence_engine）
        evidence = _build_ward_evidence(theme, ward_name)

        return WardDetailResponse(
            theme=theme,
            city_name=ward_name,
            demographics=demo,
            score_breakdown=score_breakdown,
            datasets=datasets,
            facilities=facilities,
            evidence=evidence,
        )

    finally:
        conn.close()


@app.get("/api/facilities", response_model=List[FacilityDetail], summary="施設検索（地図表示用）")
def search_facilities(
    theme: str = Query(..., description="テーマ識別子"),
    municipality: Optional[str] = Query(None, description="区名でフィルタ（省略時は全区）"),
    limit: int = Query(500, le=2000, description="最大取得件数"),
):
    """地図上に施設ピンをまとめて表示する用途向けのエンドポイント。"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = "SELECT id, name, address, latitude, longitude, raw_json FROM normalized_facilities WHERE theme = %s"
            params: list = [theme]
            
            if municipality:
                query += " AND municipality = %s"
                params.append(municipality)
                
            query += " LIMIT %s"
            params.append(limit)

            cur.execute(query, tuple(params))
            
            facilities = []
            for r in cur.fetchall():
                raw_json = r["raw_json"]
                if isinstance(raw_json, str):
                    try:
                        raw_json = json.loads(raw_json)
                    except json.JSONDecodeError:
                        raw_json = None

                facilities.append(
                    FacilityDetail(
                        id=str(r["id"]),
                        name=r["name"],
                        address=r["address"],
                        latitude=r["latitude"],
                        longitude=r["longitude"],
                        raw_json=raw_json,
                    )
                )
            return facilities
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    # サーバー起動 (http://localhost:8000)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)