#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workflow.py
───────────
オープンデータの収集(collect)・ファイル取得＆JSON変換(download)・
23区公式統計に基づくスコアリング(score)・スキーマ正規化フック(normalize_schema)を
一元管理するメインワークフローエンジン。

主な特長:
- 既存DBへの自動カラム追加・インデックス作成などの安全なマイグレーション
- CSVファイルをダウンロード時にオンメモリでDict形式のJSONへ自動変換
- CKAN等の収集途中で失敗した場合でも取得済みデータを破棄せずにDBへ反映
- theme_schema.py および 23区一次統計データ(WARD_DEMOGRAPHICS)との完全連動

--- パッチ履歴 ---
- OpenDataQueueDB.__init__ 内で未定義の `cols` を参照していたバグを修正
  （license_status/license_id 追加マイグレーションを _init_db() 内に移動）
- normalized_facilities テーブルの CREATE TABLE が欠落していたバグを修正
  （api.py / normalize_schema.py はこのテーブルへの読み書きに依存している）
- run_collect が cfg（テーマYAML）の queries[1:] / formats / group / rows /
  max_packages を無視していたバグを修正（cfg駆動に変更し、複数queryをマージ）
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import yaml

# theme_schema.py からバリデーション関数をインポート
try:
    from theme_schema import validate_theme_config, ThemeConfigError
except ImportError:
    validate_theme_config = None

# プロジェクトルートのパス解決
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 23区 基礎デモグラフィックデータ（一次情報・公式統計値）
# ──────────────────────────────────────────────
#
# [population_10k_5y_ago について]
# 人口推移（増加率）スコア用に追加した「5年前の人口（万人単位）」の列。
# ⚠️ ここでは暫定的に population_10k と同じ値を仮置きしている（＝増加率0%扱い）。
# 実際のスコアが正しく機能するには、東京都の統計（住民基本台帳人口・国勢調査等、
# 例: https://www.tokyo-23city.or.jp/chosa/tokei/joho/ ）から実際の5年前の値に
# 手動で置き換える必要がある。23件だけなので手打ちで問題ない。
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


# ──────────────────────────────────────────────
# 堅牢なDB管理層 (マイグレーション対応)
# ──────────────────────────────────────────────
class OpenDataQueueDB:
    def __init__(self, db_path: str = "data/opendata_queue.db"):
        self.db_path = Path(db_path)
        if not self.db_path.is_absolute():
            self.db_path = BASE_DIR / self.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _table_exists(self, name: str) -> bool:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        )
        return cur.fetchone() is not None

    def _get_columns(self, table_name: str) -> set[str]:
        cur = self.conn.execute(f"PRAGMA table_info({table_name})")
        return {row["name"] for row in cur.fetchall()}

    def _init_db(self):
        """テーブル作成および既存DBの自動マイグレーション"""
        # 1. opendata_queue テーブル
        if not self._table_exists("opendata_queue"):
            self.conn.execute(
                """
                CREATE TABLE opendata_queue (
                    theme TEXT NOT NULL,
                    id TEXT NOT NULL,
                    url TEXT,
                    title TEXT,
                    municipality TEXT,
                    format TEXT,
                    raw_metadata TEXT,
                    has_coordinates INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'UNASSESSED',  -- UNASSESSED, DOWNLOADED, ERROR
                    mapping_rule TEXT,
                    error_msg TEXT,
                    license_status TEXT DEFAULT 'unknown',
                    license_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (theme, id)
                )
                """
            )
        else:
            # 既存テーブルへの不整合防止マイグレーション
            cols = self._get_columns("opendata_queue")
            if "theme" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN theme TEXT")
                self.conn.execute("UPDATE opendata_queue SET theme='default' WHERE theme IS NULL OR theme=''")
            if "has_coordinates" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN has_coordinates INTEGER DEFAULT 0")
            if "status" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN status TEXT DEFAULT 'UNASSESSED'")
            if "mapping_rule" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN mapping_rule TEXT")
            if "error_msg" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN error_msg TEXT")
            if "created_at" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "updated_at" not in cols:
                self.conn.execute("ALTER TABLE opendata_queue ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            # [パッチ] 以前は __init__ 直下にあって `cols` が未定義のため NameError になっていた箇所。
            # ここ（_init_db内・cols定義後）に移動して修正。
            if "license_status" not in cols:
                self.conn.execute(
                    "ALTER TABLE opendata_queue ADD COLUMN license_status TEXT DEFAULT 'unknown'"
                )
            if "license_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE opendata_queue ADD COLUMN license_id TEXT"
                )

            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_opendata_queue_theme_id ON opendata_queue(theme, id)"
            )

        # 2. ward_scores (採点結果テーブル)
        if not self._table_exists("ward_scores"):
            self.conn.execute(
                """
                CREATE TABLE ward_scores (
                    theme TEXT NOT NULL,
                    city_name TEXT NOT NULL,
                    raw_count INTEGER DEFAULT 0,
                    quality_score REAL DEFAULT 0.0,
                    richness_score REAL DEFAULT 0.0,
                    total_score REAL DEFAULT 0.0,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (theme, city_name)
                )
                """
            )

        # 3. normalized_facilities (正規化済み施設一覧テーブル)
        # [パッチ] api.py の /api/wards/{ward_name} と /api/facilities、
        # normalize_schema.py の normalize_and_persist_facilities() が
        # このテーブルに依存しているが、CREATE TABLE がどこにも無く
        # 「no such table: normalized_facilities」で落ちていたため追加。
        if not self._table_exists("normalized_facilities"):
            self.conn.execute(
                """
                CREATE TABLE normalized_facilities (
                    id TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    municipality TEXT,
                    name TEXT,
                    address TEXT,
                    latitude REAL,
                    longitude REAL,
                    raw_json TEXT,
                    source_dataset_id TEXT,
                    PRIMARY KEY (theme, id)
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_normalized_facilities_municipality "
                "ON normalized_facilities(theme, municipality)"
            )

        self.conn.commit()

    def insert_unassessed_items(self, theme: str, items: list[dict]) -> int:
        inserted_count = 0
        with self.conn:
            for item in items:
                raw_data = json.dumps(item.get("raw_metadata", {}), ensure_ascii=False)
                item_id = (item.get("id") or "").strip()
                url = (item.get("url") or "").strip()
                if not item_id or not url:
                    continue
                try:
                    self.conn.execute(
                        """
                        INSERT INTO opendata_queue
                        (theme, id, url, title, municipality, format, raw_metadata, has_coordinates, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'UNASSESSED')
                        """,
                        (
                            theme,
                            item_id,
                            url,
                            item.get("title", ""),
                            item.get("municipality", ""),
                            item.get("format", ""),
                            raw_data,
                            1 if item.get("has_coordinates") else 0,
                        ),
                    )
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    pass  # 重複登録はスキップ
        return inserted_count

    def get_unassessed_items(self, theme: str, limit: int = 100) -> list[dict]:
        cur = self.conn.execute(
            """
            SELECT * FROM opendata_queue
            WHERE theme = ? AND status = 'UNASSESSED'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (theme, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def update_status(self, theme: str, item_id: str, status: str, error_msg: str = ""):
        with self.conn:
            self.conn.execute(
                """
                UPDATE opendata_queue
                SET status = ?, error_msg = ?, updated_at = CURRENT_TIMESTAMP
                WHERE theme = ? AND id = ?
                """,
                (status, error_msg, theme, item_id),
            )

    def save_ward_score(self, theme: str, city_name: str, raw_count: int, quality_score: float, richness_score: float, total_score: float):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO ward_scores
                (theme, city_name, raw_count, quality_score, richness_score, total_score, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (theme, city_name, raw_count, quality_score, richness_score, total_score),
            )

    def get_stats(self, theme: str) -> dict:
        cur = self.conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM opendata_queue
            WHERE theme = ?
            GROUP BY status
            """,
            (theme,),
        )
        return {row["status"]: row["count"] for row in cur.fetchall()}


# ──────────────────────────────────────────────
# メインワークフロー
# ──────────────────────────────────────────────
@dataclass
class OpenDataWorkflowConfig:
    db_path: str = "data/opendata_queue.db"
    themes_dir: str = "themes"
    request_timeout: int = 20
    sleep_sec: float = 1.0


class OpenDataWorkflow:
    def __init__(self, config: Optional[OpenDataWorkflowConfig] = None):
        self.config = config or OpenDataWorkflowConfig()
        self.db = OpenDataQueueDB(db_path=self.config.db_path)
        self.themes_dir = BASE_DIR.parent / self.config.themes_dir
    def _load_theme_cfg(self, theme_name: str) -> dict:
        """YAMLから設定を読み込み、schema検証を実施"""
        yaml_path = self.themes_dir / f"{theme_name}.yaml"
        if not yaml_path.exists():
            logger.warning(f"テーマYAML未検出: {yaml_path}。デフォルト設定で動作します。")
            return {"name": theme_name, "label": theme_name, "denominator": "population_10k", "weight": 1.0}

        with yaml_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        if validate_theme_config:
            validate_theme_config(theme_name, cfg)
        return cfg

    # ------------------------------------------------------------------
    # 1. 収集 (collect)
    # ------------------------------------------------------------------
    def run_collect(
        self,
        theme: str,
        query: Optional[str] = None,
        format_type: Optional[str] = None,
        group: Optional[str] = None,
        rows: Optional[int] = None,
        max_packages: Optional[int] = None,
    ):
        """
        [パッチ] 以前は format_type/group/rows/max_packages が関数デフォルト値
        （常にCSV/all/200/2000）で固定され、テーマYAMLの設定が無視されていた。
        また queries は cfg["queries"][0] の1件しか使われていなかった。
        今回、各引数は「Noneならcfgの値を使う・指定されればcfgより優先して上書きする」
        方式にし、queriesは全件ループしてマージするよう修正。
        """
        cfg = self._load_theme_cfg(theme)
        
        queries = [query] if query else (cfg.get("queries") or [""])
        effective_format = format_type if format_type is not None else ",".join(cfg.get("formats", ["CSV"]))
        effective_group = group if group is not None else cfg.get("group", "all")
        effective_rows = rows if rows is not None else cfg.get("rows", 200)
        effective_max_packages = max_packages if max_packages is not None else cfg.get("max_packages", 2000)

        logger.info(
            "[Workflow/Collect] 開始 theme=%s queries=%r format=%s group=%s rows=%d max_packages=%d",
            theme, queries, effective_format, effective_group, effective_rows, effective_max_packages
        )

        try:
            from collectors.opendata_collector import OpenDataCollector, CKANCollectionError
        except ImportError:
            logger.error("collectors/opendata_collector.py が見つかりません。")
            return

        collector = OpenDataCollector(timeout=self.config.request_timeout)

        # (id, url) キーで重複排除しつつ、複数queryの結果をマージする
        merged: dict[tuple[str, str], dict] = {}
        collect_failed = False

        for q in queries:
            try:
                results = collector.search_ckan(
                    query=q,
                    format_type=effective_format,
                    group=effective_group,
                    rows=effective_rows,
                    max_packages=effective_max_packages,
                )
            except CKANCollectionError as e:
                logger.error("❌ query=%r でCKAN検索が途中で失敗。取得済み部分データで継続します: %s", q, e)
                results = e.partial_results
                collect_failed = True
            except Exception as e:
                logger.error("❌ query=%r で予期せぬエラー: %s", q, e)
                collect_failed = True
                continue

            for item in results:
                key = (item.get("id", ""), item.get("url", ""))
                merged[key] = item

        results = list(merged.values())

        if not results:
            logger.warning("⚠️ 追加対象となる新規データセットがありませんでした。")
            self._print_db_stats(theme)
            return

        inserted = self.db.insert_unassessed_items(theme=theme, items=results)
        status_note = "（一部query失敗あり）" if collect_failed else ""
        logger.info("🎉 DB反映完了: %d 件追加 / 集計%d件%s (theme=%s)", inserted, len(results), status_note, theme)
        self._print_db_stats(theme)

    # ------------------------------------------------------------------
    # 2. ダウンロード & 自動JSON変換 (download)
    # ------------------------------------------------------------------
    def run_download(self, theme: str, output_dir: Optional[str] = None, batch_size: Optional[int] = None):
        cfg = self._load_theme_cfg(theme)
        effective_output_dir = output_dir or cfg.get("output_dir") or "output/opendata_jsons"
        effective_batch_size = batch_size if batch_size is not None else cfg.get("batch_size", 100)

        logger.info("[Workflow/Download] 開始 theme=%s batch_size=%d", theme, effective_batch_size)

        out_path = Path(effective_output_dir)
        if not out_path.is_absolute():
            out_path = BASE_DIR / out_path
        out_path.mkdir(parents=True, exist_ok=True)

        items = self.db.get_unassessed_items(theme=theme, limit=effective_batch_size)
        if not items:
            logger.info("✅ ダウンロード待ちデータはありません。")
            self._print_db_stats(theme)
            return

        success_count, error_count = 0, 0

        for item in items:
            url = item.get("url", "")
            item_id = item.get("id", "")
            title = item.get("title", f"dataset_{item_id}")
            fmt = (item.get("format") or "").upper()

            safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in title).strip() or "untitled"
            file_name = f"{safe_title}_{item_id}.json"
            file_path = out_path / file_name

            logger.info("📥 取得中: %s (URL: %s)", title, url)

            try:
                resp = requests.get(url, timeout=self.config.request_timeout)
                resp.raise_for_status()

                # 文字コード補正
                resp.encoding = resp.apparent_encoding or resp.encoding
                raw_text = resp.text

                json_data = []
                # CSVフォーマットの自動構造化判定
                if fmt == "CSV" or url.lower().endswith(".csv"):
                    f = io.StringIO(raw_text)
                    reader = csv.DictReader(f)
                    for row in reader:
                        json_data.append(row)
                else:
                    try:
                        json_data = resp.json()
                    except json.JSONDecodeError:
                        json_data = {"raw_text": raw_text}

                # JSON出力
                with file_path.open("w", encoding="utf-8") as wf:
                    json.dump(json_data, wf, ensure_ascii=False, indent=2)

                self.db.update_status(theme=theme, item_id=item_id, status="DOWNLOADED", error_msg="")
                success_count += 1
                logger.info("  └─ ✅ 保存成功: %s", file_path)

            except Exception as e:
                logger.error("  └─ ❌ エラー発生: %s", e)
                self.db.update_status(theme=theme, item_id=item_id, status="ERROR", error_msg=str(e))
                error_count += 1

            time.sleep(self.config.sleep_sec)

        logger.info("🎉 処理完了 - 成功: %d 件 | エラー: %d 件", success_count, error_count)
        self._print_db_stats(theme)

    # ------------------------------------------------------------------
    # 3. 採点・評価 (score)
    # ------------------------------------------------------------------
    
    def run_score(self, theme: str):
        """23区公式統計(WARD_DEMOGRAPHICS)をもとにスコア計算"""
        cfg = self._load_theme_cfg(theme)
        denominator_type = cfg.get("denominator", "population_10k")
        weight = float(cfg.get("weight", 1.0))

        logger.info(f"[{theme}] スコア計算中 (正規化単位: {denominator_type}, 重み: {weight})...")

        cur = self.db.conn.execute(
            """
            SELECT municipality,
                   COUNT(*) as raw_count,
                   AVG(has_coordinates) as coord_rate,
                   SUM(CASE WHEN format IN ('CSV', 'JSON') THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as open_rate
            FROM opendata_queue
            WHERE theme = ? AND municipality IS NOT NULL AND municipality != ''
            GROUP BY municipality
            """,
            (theme,),
        )
        records = cur.fetchall()

        if not records:
            logger.warning(f"[{theme}] 採点対象の自治体データがDB内にありません。")
            return

        for row in records:
            city_name = row["municipality"]
            raw_count = row["raw_count"]
            coord_rate = row["coord_rate"] or 0.0
            open_rate = row["open_rate"] or 0.0

            # 軸1: データ品質 (100点満点)
            quality_score = (coord_rate * 50.0) + (open_rate * 50.0)

            # 軸2: 地域充実度 (公式統計による正規化)
            demo = WARD_DEMOGRAPHICS.get(city_name, {"population_10k": 10.0, "area_sqkm": 10.0, "children_0_5": 10000})
            denom_val = demo.get(denominator_type, 1.0)

            density = raw_count / denom_val if denom_val > 0 else 0
            richness_score = min(100.0, density * 10.0)

            # 総合スコア
            total_score = round(((quality_score * 0.5) + (richness_score * 0.5)) * weight, 1)

            # DB保存
            self.db.save_ward_score(theme, city_name, raw_count, quality_score, richness_score, total_score)

        logger.info(f"🎉 [{theme}] 全自治体のスコア計算・DB保存が完了しました。")

    # ------------------------------------------------------------------
    # 4.5 人口推移スコア (population_score)
    # ------------------------------------------------------------------
    def run_population_score(self, theme: str = "population"):
        """
        人口推移（増加率）専用のスコア計算。

        他テーマの run_score() は opendata_queue の COUNT(*)（=カタログの
        データセット件数）を richness_score の元にしているが、人口推移は
        「人口関連データが何件公開されているか」ではなく「実際に人口が
        何%増減したか」を測るべき指標なので、そもそも共通の run_score()
        とは別ロジックが必要（denominatorで正規化するdensity方式は使わない）。

        WARD_DEMOGRAPHICS の population_10k（現在）と population_10k_5y_ago
        （5年前）から増加率を算出し、ward_scores に保存する。
        themes/population.yaml があれば label/weight の定義に使う
        （queries 等はここでは未使用。将来 import_csv 等で人口関連データセットを
        集めるときのフィルタ用に残してある）。

        保存内容（ward_scores テーブルの汎用カラムを流用）:
          - raw_count      : 未使用（0固定）
          - richness_score : 増加率そのもの（%、マイナスもあり得る）
          - quality_score  : 5年前データが未入力（population_10k と同値のまま）の
                             場合は 0.0（＝仮値のため信頼できない、という合図）、
                             実データが入っていれば 100.0
          - total_score    : 増加率を0-100のスコアに変換した値
                             （0%成長=50点を中心に、±10%成長で0/100点に張り付く）
        """
        cfg = self._load_theme_cfg(theme)
        weight = float(cfg.get("weight", 1.0))

        logger.info(f"[{theme}] 人口推移スコアを計算中...")

        for city_name, demo in WARD_DEMOGRAPHICS.items():
            pop_now = demo.get("population_10k")
            pop_prev = demo.get("population_10k_5y_ago")

            if pop_now is None or pop_prev is None or pop_prev == 0:
                logger.warning(f"[{theme}] {city_name}: 人口データが不足しているためスキップします。")
                continue

            growth_rate_pct = (pop_now - pop_prev) / pop_prev * 100.0

            # 仮置き値（5年前=現在のまま未入力）の区は信頼度0として明示する
            is_placeholder = abs(pop_now - pop_prev) < 1e-9
            quality_score = 0.0 if is_placeholder else 100.0

            # ±10%成長で0点/100点に張り付く形で0-100スコア化。中心(0%成長)は50点。
            total_score = round(max(0.0, min(100.0, 50.0 + growth_rate_pct * 5.0)) * weight, 1)

            self.db.save_ward_score(
                theme, city_name,
                raw_count=0,
                quality_score=quality_score,
                richness_score=round(growth_rate_pct, 2),
                total_score=total_score,
            )

        logger.info(f"🎉 [{theme}] 人口推移スコア計算・DB保存が完了しました。")

    # ------------------------------------------------------------------
    # 4. スキーマ正規化フック (normalize_schema)
    # ------------------------------------------------------------------
    def run_normalize_schema(self, theme: str):
        """
        normalize_schema.py の実処理（backfill_license_status →
        normalize_and_persist_facilities）を実際に呼び出す。
        以前はログを出すだけのフックで、正規化処理そのものが
        呼ばれていなかった。
        """
        logger.info(f"[{theme}] normalize_schema を開始します")
        try:
            from normalize_schema import backfill_license_status, normalize_and_persist_facilities
        except ImportError:
            logger.error("orchestrator/normalize_schema.py が見つかりません。")
            return

        db_path = str(self.db.db_path)
        updated = backfill_license_status(db_path=db_path, theme=theme)
        logger.info(f"[{theme}] ライセンス判定を更新: {updated} 件")

        result = normalize_and_persist_facilities(db_path=db_path, theme=theme)
        logger.info(
            f"[{theme}] 施設正規化完了: 登録 {result['inserted']} 件 / "
            f"座標なし {result['skipped_no_coords']} 件 / "
            f"候補総数 {result['total_candidates']} 件"
        )

    def _print_db_stats(self, theme: str):
        stats = self.db.get_stats(theme=theme)
        logger.info(
            "📊 DB状況(theme=%s): ダウンロード済 %d 件 | 未処理 %d 件 | エラー %d 件",
            theme,
            stats.get("DOWNLOADED", 0),
            stats.get("UNASSESSED", 0),
            stats.get("ERROR", 0),
        )

    def run_import_catalog(self, theme: str, csv_url: str):
        """
        東京都のオープンデータカタログCSV等を一括で読み込み、
        API制限を回避して直接DBのキュー(UNASSESSED)に流し込む。
        """
        import hashlib

        logger.info(f"[Workflow/Import] カタログCSVの一括インポートを開始: {csv_url}")

        try:
            resp = requests.get(csv_url, timeout=self.config.request_timeout)
            resp.raise_for_status()

            # 文字コードの自動補正（Shift-JISやCP932が使われている場合への対応）
            resp.encoding = resp.apparent_encoding or 'utf-8'

            f = io.StringIO(resp.text)
            reader = csv.DictReader(f)

            # 🛠️ デバッグ用に追加: 実際のCSVのカラム名を出力して確認する
            logger.info(f"🔍 CSVの実際のカラム一覧: {reader.fieldnames}")
            cfg = self._load_theme_cfg(theme)
            keywords = cfg.get("queries", [])
            items = []
            for row in reader:
                # 典型的カラム名のフォールバック対応
                dataset_name = row.get("データセット_タイトル") or row.get("データセット名") or row.get("title") or "名称不明"
                resource_name = row.get("ファイルタイトル") or row.get("リソース名") or row.get("name") or ""
                full_title = f"{dataset_name} - {resource_name}" if resource_name else dataset_name
                if keywords and not any(kw in full_title for kw in keywords):
                    continue
                org_name = row.get("地方公共団体名") or row.get("組織名") or row.get("organization") or "不明"

                municipality = org_name
                for ward in ["千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"]:
                    if ward in org_name:
                        municipality = ward
                        break

                format_type = (row.get("ファイル形式") or row.get("フォーマット") or row.get("format") or "UNKNOWN").upper()

                download_url = (
                    row.get("ファイル_ダウンロードURL")
                    or row.get("ファイル_アクセスURL")
                    or row.get("ダウンロードURL")
                    or row.get("URL")
                    or row.get("url")
                    or row.get("リソースURL")
                    or ""
                )
                if not download_url:
                    # URLが空欄の行はスキップ
                    continue

                # リソースIDがない場合はURLからハッシュを生成して一意に保つ
                item_id = row.get("リソースID") or row.get("id")
                if not item_id:
                    item_id = hashlib.md5(download_url.encode('utf-8')).hexdigest()

                # 位置情報の有無を推測
                has_coords = format_type in ("GEOJSON", "KML", "SHP", "TOPOJSON") or "緯度" in str(row) or "経度" in str(row)

                # 🎉 ここがポイント: CSVの1行分(row)をそのまま raw_metadata に入れる
                # これにより、row["ライセンス"] などが全てDBに保存されます
                items.append({
                    "id": item_id,
                    "url": download_url,
                    "title": full_title,
                    "municipality": municipality,
                    "format": format_type,
                    "has_coordinates": has_coords,
                    "raw_metadata": row,
                })

            if not items:
                logger.warning("インポート可能なデータがCSVから見つかりませんでした。")
                return

            inserted = self.db.insert_unassessed_items(theme=theme, items=items)
            logger.info(f"🎉 カタログインポート完了: {len(items)}件中、{inserted}件を新規登録しました（theme={theme}）")
            self._print_db_stats(theme)

        except Exception as e:
            logger.error(f"❌ カタログCSVのインポートに失敗しました: {e}")
    # ------------------------------------------------------------------
    # 4.6 娯楽施設アクセススコア (entertainment_score)
    # ------------------------------------------------------------------
    def run_entertainment_score(self, theme: str = "entertainment"):
        """
        娯楽施設（遊園地、動物園、博物館など）専用のスコア計算。
        「近さのみ」で評価するため、区の面積(area_sqkm)と実際の施設数(normalized_facilities)から
        「平均的な施設までの距離」を算出し、100点満点でスコアをつける。
        """
        cfg = self._load_theme_cfg(theme)
        weight = float(cfg.get("weight", 1.0))

        logger.info(f"[{theme}] 娯楽施設へのアクセス（近さ）スコアを計算中...")

        # キューではなく、正規化済みの「実際の施設数」をカウントする
        cur = self.db.conn.execute(
            """
            SELECT municipality, COUNT(*) as raw_count
            FROM normalized_facilities
            WHERE theme = ? AND municipality IS NOT NULL AND municipality != ''
            GROUP BY municipality
            """,
            (theme,)
        )
        records = cur.fetchall()

        if not records:
            logger.warning(f"[{theme}] 採点対象の施設データが normalized_facilities 内にありません。")
            return

        for row in records:
            city_name = row["municipality"]
            raw_count = row["raw_count"]

            demo = WARD_DEMOGRAPHICS.get(city_name)
            if not demo or raw_count == 0:
                self.db.save_ward_score(theme, city_name, raw_count, 0.0, 0.0, 0.0)
                continue

            area = demo["area_sqkm"]

            # 平均距離の概算（km） = 0.5 * √(面積 / 施設数)
            avg_distance_km = 0.5 * ((area / raw_count) ** 0.5)

            # 距離からスコアへ変換（近さのみで点数化）
            if avg_distance_km <= 0.5:
                score = 100.0  # 500m以内
            elif avg_distance_km <= 1.0:
                score = 80.0   # 1km以内
            elif avg_distance_km <= 2.0:
                score = 60.0   # 2km以内
            elif avg_distance_km <= 4.0:
                score = 40.0   # 4km以内
            else:
                score = 20.0   # それ以上

            total_score = round(score * weight, 1)

            # データベースに保存（品質スコアは0固定、確認用にrichnessに距離を保存）
            self.db.save_ward_score(
                theme, city_name,
                raw_count=raw_count,
                quality_score=0.0,
                richness_score=round(avg_distance_km, 2),
                total_score=total_score
            )

        logger.info(f"🎉 [{theme}] 娯楽施設（近さ重視）のスコア計算・DB保存が完了しました。")

# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="オープンデータ統合ワークフロー")
    parser.add_argument("action", choices=["collect", "download", "score", "population_score", "entertainment_score", "normalize_schema", "import_csv"], help="実行するアクション")

    parser.add_argument("--theme", type=str, default="default", help="テーマ識別子 (例: childcare, park, aed)")
    parser.add_argument("--query", type=str, default=None, help="検索クエリ (未指定時はYAMLのqueries全件を使用)")
    parser.add_argument("--format", type=str, default=None, help="収集フォーマット (未指定時はYAMLのformatsを使用)")
    parser.add_argument("--group", type=str, default=None, help="組織グループ (未指定時はYAMLのgroupを使用)")
    parser.add_argument("--rows", type=int, default=None, help="1ページあたりの件数 (未指定時はYAMLのrowsを使用)")
    parser.add_argument("--max-packages", type=int, default=None, help="収集する最大パッケージ数 (未指定時はYAMLのmax_packagesを使用)")
    parser.add_argument("--batch-size", type=int, default=None, help="ダウンロードの1回あたり処理件数 (未指定時はYAMLのbatch_sizeを使用)")
    parser.add_argument("--output-dir", type=str, default=None, help="JSON出力フォルダ (未指定時はYAMLのoutput_dirを使用)")
    parser.add_argument("--db-path", type=str, default="data/opendata_queue.db", help="SQLite DBパス")
    parser.add_argument("--timeout", type=int, default=20, help="HTTPタイムアウト秒")

    # CSVインポート用の引数
    parser.add_argument("--csv-url", type=str, default=None, help="一括インポートするカタログCSVのURL (import_csv時のみ)")

    return parser


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args()

    cfg = OpenDataWorkflowConfig(
        db_path=args.db_path,
        request_timeout=args.timeout,
    )
    workflow = OpenDataWorkflow(config=cfg)

    if args.action == "collect":
        workflow.run_collect(
            theme=args.theme,
            query=args.query,
            format_type=args.format,
            group=args.group,
            rows=args.rows,
            max_packages=args.max_packages,
        )
    elif args.action == "download":
        workflow.run_download(
            theme=args.theme,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
        )
    elif args.action == "score":
        workflow.run_score(theme=args.theme)
    elif args.action == "population_score":
        workflow.run_population_score(theme=args.theme)
    elif args.action == "entertainment_score":
        workflow.run_entertainment_score(theme=args.theme)
    elif args.action == "normalize_schema":
        workflow.run_normalize_schema(theme=args.theme)
    elif args.action == "import_csv":
        if not args.csv_url:
            logger.error("⚠️ import_csv を実行するには --csv-url でCSVのURLを指定してください。")
        else:
            workflow.run_import_catalog(theme=args.theme, csv_url=args.csv_url)


if __name__ == "__main__":
    main()