#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/api.py
──────
フロントエンド（Web画面）からの非同期リクエストに応じ、
23区のスコア一覧や、区をクリックした際の「詳細内訳」データを配信する FastAPI サーバー。

主な機能:
- GET /api/scores               : 指定テーマにおける23区のスコアランキング一覧
- GET /api/wards/{ward_name}    : クリック時の「詳細内訳」（デモグラフィック、スコア根拠、収集データセット、施設一覧、証跡）
- GET /api/facilities           : 地図表示等で使える正規化済み施設検索 API

--- パッチ履歴 ---
- WardDetailResponse に `evidence` を追加。engines/evidence_engine.py を使って
  「このスコアはどのデータセットの、どの行の、どの列由来か」まで
  内訳画面から辿れるようにした（scoreの根拠追跡）。
  evidence の計算に失敗しても（normalize_schema/metrics未実行など）、
  ward detail 自体は今まで通り返す（evidence だけ null になる）。
  
  
  1. APIの条件緩和（一番手軽な改善）
現在、api.py の内部には以下のコードがあります。

Python
if ev.facility_count == 0:
    return None
施設が0件だとエビデンス情報全体を「無かったこと（None）」にしてしまうため、フロントエンドで参照元データすら表示できなくなっています。
これを削除し、「施設数は0件だけど、このオープンデータ（CSVなど）を元に点数をつけているよ」とフロントエンドへしっかり返すように改善します。

2. データ正規化（normalize_schema.py）の強化
ここが根本的な解決策になります。カタログからダウンロードしたCSVファイルには、「緯度」「経度」「lat」「lon」「X座標」「Y座標」など、自治体によって列名に激しいバラつきがあります。
Python側でこの「列名の揺れ」を吸収する辞書（マッピングルール）を強化することで、弾かれていたデータが normalized_facilities テーブル（SQLiteデータベース）に正しく書き込まれるようになり、0件だった表示が実際の件数へと変わっていきます。

3. 全スコアの計算基準を「実際の施設数」へ移行
現在は「オープンデータのファイルが存在するかどうか」で基礎点数がついてしまっています。
今回「娯楽施設」で実装したような、「normalized_facilities に登録された実際の施設数と区の面積を使って計算するロジック」を、公園や防災など他のすべてのテーマにも適用します。これにより、データの中身を伴った真のスコアが算出されるようになります。

4. フロントエンドでの「状態」の可視化
UX（ユーザー体験）の観点からの改善です。単に「0件」と表示するのではなく、バックエンドから送られてくるステータスを活用して表示を切り替えます。

データはあるが座標がない場合 👉 「データ形式変換中」 または 「マップ表示非対応データ」

本当にデータがない場合 👉 「自治体からのデータ公開なし」

このように表示を分けることで、ユーザーに「バグかな？」と思わせず、行政のデータ公開度のリアルな現状として伝えることができます。

SQLiteデータベースの構造やPythonでのデータ処理の仕組みを活かして、さらに精度の高いシステムへと進化させていけそうですね。まずはこの中で、どの改善から手をつけてみたいですか？
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# プロジェクトルート & DBパスの自動判定
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "opendata_queue.db"

# orchestrator/opendata_workflow.py と共通の23区公式統計データ（一次情報）
#
# [population_10k_5y_ago について]
# orchestrator/opendata_workflow.py の WARD_DEMOGRAPHICS と同様、人口推移
# （増加率）スコア用の「5年前の人口（万人単位）」列。⚠️ 現状は仮置きで
# population_10k と同値（増加率0%扱い）。実データに手動で置き換えること。
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

# CORS対応（フロントエンドWeb画面からの非同期fetchを許可）
# ⚠️ allow_origins="*" と allow_credentials=True は仕様上併用不可（ブラウザに拒否される）。
#    認証(Cookie等)を使わない前提なので allow_credentials=False に修正。
#    将来Cookie認証等を導入する場合は allow_origins を実ドメインに限定すること。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"データベースが存在しません ({DB_PATH})。先に "
                   f"`python orchestrator/opendata_workflow.py collect --theme <theme名>` を実行してください。",
        )
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
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
    id: str          # ← int から str に変更（CKANのresource_idはUUID/MD5文字列のため）
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
    """engines/evidence_engine.py の DatasetEvidence に対応"""
    dataset_id: str
    title: str
    url: str
    format: str
    status: str
    license_status: str
    facility_count: int  # このデータセット由来の施設が何件正規化されているか


class FacilityEvidenceItem(BaseModel):
    """engines/evidence_engine.py の FacilityEvidence に対応。
    matched_field/matched_raw_value が「このスコアはどのCSVのどの列由来か」を示す。
    """
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
    """区の合計スコアの「根拠」。sample_facilities は代表数件のみ（全件は重いため）。"""
    metric_label: str
    facility_count: int
    metric_sum: float
    # このスコアがどれだけ信頼できそうかを表す0〜100の数値
    # (座標カバー率・データの鮮度・件数の十分さ・データセットの多様性から算出)。
    # metrics アクション未実行のテーマでは null。
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
    # [パッチ] スコアの根拠追跡。normalize_schema/metricsが未実行のテーマでは
    # None になる（内訳画面側は null を「詳細未計算」として扱う想定）。
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
        cur = conn.execute(
            """
            SELECT city_name, total_score, quality_score, richness_score, raw_count
            FROM ward_scores
            WHERE theme = ?
            ORDER BY total_score DESC
            """,
            (theme,),
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
    """
    engines/evidence_engine.py を呼んで根拠情報を組み立てる。
    """
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

    # 🎯【修正】施設数が0でもエビデンスは返す。ただし、サンプルの施設リストは空配列にする
    sample_facs = []
    if ev.facility_count > 0:
        sample_facs = [FacilityEvidenceItem(**asdict(f)) for f in ev.sample_facilities]

    return WardEvidenceSummary(
        metric_label=ev.metric_label,
        facility_count=ev.facility_count,
        metric_sum=ev.metric_sum,
        confidence_score=ev.confidence_score,
        datasets=[DatasetEvidenceItem(**asdict(d)) for d in ev.datasets],
        sample_facilities=sample_facs, # 👈 ここを安全に処理した変数に置き換え
    )

@app.get("/api/wards/{ward_name}", response_model=WardDetailResponse, summary="クリック時の「詳細内訳」取得")
def get_ward_detail(
    ward_name: str,
    theme: str = Query(..., description="テーマ識別子 (例: childcare, park)"),
):
    """
    💡 メイン機能: 画面で区をクリックしたときに呼ばれる内訳APIです。
    以下をすべてまとめて返却します。
      1. 一次公的統計（人口、面積、0-5歳児数など）
      2. スコア内訳（データ品質、地域充実度、データ件数）
      3. 収集元オープンデータリソース（CKANのURLや形式）
      4. normalize_schema.py で構造化された施設一覧（normalized_facilities）
      5. スコアの根拠（evidence_engine）：どのデータセットの、どの列由来かの追跡
    """
    conn = get_db_connection()
    try:
        # 1. 人口・統計データの取得
        demo = WARD_DEMOGRAPHICS.get(ward_name)
        if not demo:
            raise HTTPException(status_code=404, detail=f"指定された区が存在しません: {ward_name}")

        # 2. スコア内訳の取得
        cur = conn.execute(
            """
            SELECT raw_count, quality_score, richness_score, total_score, calculated_at
            FROM ward_scores
            WHERE theme = ? AND city_name = ?
            """,
            (theme, ward_name),
        )
        score_row = cur.fetchone()
        score_breakdown = dict(score_row) if score_row else {
            "raw_count": 0, "quality_score": 0.0, "richness_score": 0.0, "total_score": 0.0
        }

        # 3. 収集済みオープンデータセット（CKANリンク集）
        #    ※ 件数上限を追加（LIMIT無しだと大量データセット時にレスポンスが肥大化するため）
        cur = conn.execute(
            """
            SELECT id, title, format, url, status, has_coordinates
            FROM opendata_queue
            WHERE theme = ? AND municipality = ?
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

        # 4. 正規化済み施設リスト (normalize_schema.py の normalize_and_persist_facilities で格納)
        cur = conn.execute(
            """
            SELECT id, name, address, latitude, longitude, raw_json
            FROM normalized_facilities
            WHERE theme = ? AND municipality = ?
            ORDER BY name ASC
            LIMIT 500
            """,
            (theme, ward_name),
        )
        facilities = [
            FacilityDetail(
                id=str(r["id"]),
                name=r["name"],
                address=r["address"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                raw_json=json.loads(r["raw_json"]) if r["raw_json"] else None,
            )
            for r in cur.fetchall()
        ]

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
        query = "SELECT id, name, address, latitude, longitude, raw_json FROM normalized_facilities WHERE theme = ?"
        params: list = [theme]
        if municipality:
            query += " AND municipality = ?"
            params.append(municipality)
        query += " LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        return [
            FacilityDetail(
                id=str(r["id"]),
                name=r["name"],
                address=r["address"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                raw_json=json.loads(r["raw_json"]) if r["raw_json"] else None,
            )
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    # サーバー起動 (http://localhost:8000)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)