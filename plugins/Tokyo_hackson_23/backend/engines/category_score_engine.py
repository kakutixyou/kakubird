#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
backend/engines/category_score_engine.py
────────────────────────────────────────

themes/*.yaml の設定を利用して、東京23区の各テーマを0〜100点で採点する。

主な処理:
1. themes/<theme>.yaml を読み込む
2. theme_schema.py で設定を検証
3. normalized_facilities から区別の実データを集計
4. denominator に従って人口・面積・子ども人口等で正規化
5. 23区内の相対評価を0〜100点へ変換
6. データ品質スコアを計算
7. ward_scores に保存

既存フロントエンド:
    GET /api/scores?theme=park
        ↓
    pillarMeta.js
        ↓
    calculateCategoryScore()

とそのまま接続できる。

対応 denominator:
    population_10k
    area_sqkm
    children_0_5
    none

将来的に国勢調査を導入した場合は、
data/census/normalized/*.json の値を優先する。
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ============================================================
# import
# ============================================================

try:
    from Tokyo_hackson_23.backend.orchestrator.theme_schema import (
        validate_theme_config,
        resolve_effective_metric_key,
        ThemeConfigError,
    )
except ImportError:
    from orchestrator.theme_schema import (
        validate_theme_config,
        resolve_effective_metric_key,
        ThemeConfigError,
    )


logger = logging.getLogger(__name__)


# ============================================================
# パス
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB_PATH = (
    BACKEND_DIR
    / "data"
    / "opendata_queue.db"
)

DEFAULT_THEMES_DIR = (
    BACKEND_DIR
    / "themes"
)

DEFAULT_CENSUS_DIR = (
    BACKEND_DIR
    / "data"
    / "census"
    / "normalized"
)


# ============================================================
# 一時フォールバック
#
# census_normalize_engine.py が完成するまではこちらを使用。
# censusデータが存在すればそちらを優先する。
# ============================================================

WARD_DEMOGRAPHICS_FALLBACK: Dict[str, Dict[str, float]] = {

    "千代田区": {
        "population_10k": 6.80,
        "area_sqkm": 11.66,
        "children_0_5": 3500,
    },

    "中央区": {
        "population_10k": 17.50,
        "area_sqkm": 10.21,
        "children_0_5": 11000,
    },

    "港区": {
        "population_10k": 26.00,
        "area_sqkm": 20.37,
        "children_0_5": 13500,
    },

    "新宿区": {
        "population_10k": 35.00,
        "area_sqkm": 18.22,
        "children_0_5": 14000,
    },

    "文京区": {
        "population_10k": 24.20,
        "area_sqkm": 11.29,
        "children_0_5": 11500,
    },

    "台東区": {
        "population_10k": 21.50,
        "area_sqkm": 10.11,
        "children_0_5": 9000,
    },

    "墨田区": {
        "population_10k": 28.00,
        "area_sqkm": 13.77,
        "children_0_5": 12500,
    },

    "江東区": {
        "population_10k": 53.00,
        "area_sqkm": 43.01,
        "children_0_5": 26000,
    },

    "品川区": {
        "population_10k": 42.00,
        "area_sqkm": 22.84,
        "children_0_5": 20000,
    },

    "目黒区": {
        "population_10k": 28.80,
        "area_sqkm": 14.67,
        "children_0_5": 12000,
    },

    "大田区": {
        "population_10k": 74.50,
        "area_sqkm": 61.86,
        "children_0_5": 31000,
    },

    "世田谷区": {
        "population_10k": 94.00,
        "area_sqkm": 58.05,
        "children_0_5": 41000,
    },

    "渋谷区": {
        "population_10k": 24.50,
        "area_sqkm": 15.11,
        "children_0_5": 10500,
    },

    "中野区": {
        "population_10k": 34.50,
        "area_sqkm": 15.59,
        "children_0_5": 13500,
    },

    "杉並区": {
        "population_10k": 58.00,
        "area_sqkm": 34.06,
        "children_0_5": 24000,
    },

    "豊島区": {
        "population_10k": 30.00,
        "area_sqkm": 13.01,
        "children_0_5": 11500,
    },

    "北区": {
        "population_10k": 35.50,
        "area_sqkm": 20.61,
        "children_0_5": 15000,
    },

    "荒川区": {
        "population_10k": 22.00,
        "area_sqkm": 10.16,
        "children_0_5": 10000,
    },

    "板橋区": {
        "population_10k": 58.50,
        "area_sqkm": 32.22,
        "children_0_5": 25000,
    },

    "練馬区": {
        "population_10k": 74.50,
        "area_sqkm": 48.08,
        "children_0_5": 32000,
    },

    "足立区": {
        "population_10k": 69.50,
        "area_sqkm": 53.25,
        "children_0_5": 31000,
    },

    "葛飾区": {
        "population_10k": 45.50,
        "area_sqkm": 34.80,
        "children_0_5": 19000,
    },

    "江戸川区": {
        "population_10k": 69.00,
        "area_sqkm": 49.90,
        "children_0_5": 31500,
    },
}


# ============================================================
# データクラス
# ============================================================

@dataclass
class WardMetric:
    city_name: str

    raw_count: int
    metric_sum: float

    dataset_count: int

    coordinate_count: int
    coord_coverage: float

    denominator_value: float
    density: float


@dataclass
class WardScore:
    theme: str
    metric_key: str

    city_name: str

    raw_count: int

    density: float

    richness_score: float
    quality_score: float
    total_score: float


# ============================================================
# テーマYAML
# ============================================================

def load_theme_config(
    theme: str,
    themes_dir: Path = DEFAULT_THEMES_DIR,
) -> Dict[str, Any]:

    path = themes_dir / f"{theme}.yaml"

    if not path.exists():

        raise FileNotFoundError(
            f"テーマYAMLがありません: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        cfg = yaml.safe_load(f) or {}

    if validate_theme_config:

        validate_theme_config(
            theme,
            cfg,
        )

    return cfg


# ============================================================
# DB
# ============================================================

def connect_db(
    db_path: Path | str,
) -> sqlite3.Connection:

    path = Path(
        db_path
    )

    if not path.exists():

        raise FileNotFoundError(
            f"DBがありません: {path}"
        )

    conn = sqlite3.connect(
        str(path)
    )

    conn.row_factory = sqlite3.Row

    return conn


def table_exists(
    conn: sqlite3.Connection,
    name: str,
) -> bool:

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (name,),
    ).fetchone()

    return row is not None


def ensure_ward_scores_table(
    conn: sqlite3.Connection,
) -> None:

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ward_scores (

            theme TEXT NOT NULL,

            city_name TEXT NOT NULL,

            raw_count INTEGER DEFAULT 0,

            quality_score REAL DEFAULT 0,

            richness_score REAL DEFAULT 0,

            total_score REAL DEFAULT 0,

            calculated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (
                theme,
                city_name
            )
        )
        """
    )

    conn.commit()


# ============================================================
# Census読込
# ============================================================

def load_census_normalized(
    census_dir: Path = DEFAULT_CENSUS_DIR,
) -> Dict[str, Dict[str, float]]:
    """
    census_normalize_engine.py の出力を読む。

    複数ファイルが存在する場合は、
    後から読み込んだ値で更新する。

    想定:

    {
        "wards": [
            {
                "ward_name": "足立区",
                "metrics": {
                    "population_total": 695043,
                    "population_0_14": ...
                }
            }
        ]
    }
    """

    result: Dict[
        str,
        Dict[str, float]
    ] = {}

    if not census_dir.exists():

        return result

    paths = sorted(
        census_dir.glob(
            "*.json"
        )
    )

    for path in paths:

        try:

            with path.open(
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(
                    f
                )

        except Exception as exc:

            logger.warning(
                "census読み込み失敗: %s : %s",
                path,
                exc,
            )

            continue

        wards = data.get(
            "wards",
            []
        )

        if not isinstance(
            wards,
            list,
        ):
            continue

        for ward in wards:

            if not isinstance(
                ward,
                dict,
            ):
                continue

            name = (
                ward.get(
                    "ward_name"
                )
                or ward.get(
                    "city_name"
                )
            )

            if not name:
                continue

            metrics = ward.get(
                "metrics",
                {}
            )

            if not isinstance(
                metrics,
                dict,
            ):
                continue

            result.setdefault(
                name,
                {}
            )

            for key, value in (
                metrics.items()
            ):

                if isinstance(
                    value,
                    (int, float),
                ):

                    result[
                        name
                    ][
                        key
                    ] = float(
                        value
                    )

    return result


# ============================================================
# 分母
# ============================================================

def get_demographic_value(
    city_name: str,
    denominator: str,
    census_data: Dict[
        str,
        Dict[str, float]
    ],
) -> float:
    """
    theme_schema.py の denominator に対応。

    population_10k:
        census population_total / 10000

    area_sqkm:
        fallbackから取得
        将来census/masterへ統合可能

    children_0_5:
        現状fallback。
        国勢調査の年齢階級が取れるようになれば
        census側へ置換可能。

    none:
        1
    """

    if denominator == "none":

        return 1.0

    fallback = (
        WARD_DEMOGRAPHICS_FALLBACK
        .get(
            city_name,
            {},
        )
    )

    census = (
        census_data
        .get(
            city_name,
            {},
        )
    )

    # --------------------------------------------------------
    # 人口1万人
    # --------------------------------------------------------

    if denominator == "population_10k":

        population = census.get(
            "population_total"
        )

        if population is not None:

            return max(
                population / 10000.0,
                0.0001,
            )

        return max(
            float(
                fallback.get(
                    "population_10k",
                    1.0,
                )
            ),
            0.0001,
        )

    # --------------------------------------------------------
    # 面積
    # --------------------------------------------------------

    if denominator == "area_sqkm":

        return max(
            float(
                fallback.get(
                    "area_sqkm",
                    1.0,
                )
            ),
            0.0001,
        )

    # --------------------------------------------------------
    # 0～5歳
    # --------------------------------------------------------

    if denominator == "children_0_5":

        #
        # census側に将来
        #
        # population_0_5
        #
        # が作られたら自動的に利用する。
        #

        children = census.get(
            "population_0_5"
        )

        if children is not None:

            return max(
                children,
                1.0,
            )

        return max(
            float(
                fallback.get(
                    "children_0_5",
                    1.0,
                )
            ),
            1.0,
        )

    raise ValueError(
        f"未対応denominator: {denominator}"
    )


# ============================================================
# 数値抽出
# ============================================================

def safe_number(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        (int, float),
    ):

        if math.isnan(
            float(value)
        ):
            return None

        return float(
            value
        )

    text = str(
        value
    ).strip()

    if not text:
        return None

    text = text.replace(
        ",",
        "",
    )

    try:

        return float(
            text
        )

    except ValueError:

        return None


# ============================================================
# raw_json から metric値を探す
# ============================================================

def extract_metric_from_raw_json(
    raw_json: Any,
    metric_fields: Optional[List[str]],
) -> Optional[float]:

    if not metric_fields:
        return None

    if not raw_json:
        return None

    if isinstance(
        raw_json,
        str,
    ):

        try:

            raw_json = json.loads(
                raw_json
            )

        except Exception:

            return None

    if not isinstance(
        raw_json,
        dict,
    ):
        return None

    #
    # 完全一致を先に試す
    #

    for field in metric_fields:

        if field in raw_json:

            value = safe_number(
                raw_json[
                    field
                ]
            )

            if value is not None:

                return value

    #
    # 列名の空白等を多少吸収
    #

    normalized_map = {
        str(k)
        .strip()
        .replace(" ", "")
        .replace("　", ""):
            v

        for k, v
        in raw_json.items()
    }

    for field in metric_fields:

        normalized_field = (
            field
            .strip()
            .replace(" ", "")
            .replace("　", "")
        )

        if normalized_field in (
            normalized_map
        ):

            value = safe_number(
                normalized_map[
                    normalized_field
                ]
            )

            if value is not None:

                return value

    return None


# ============================================================
# 区別集計
# ============================================================

def collect_ward_metrics(
    conn: sqlite3.Connection,
    *,
    theme: str,
    cfg: Dict[str, Any],
    census_data: Dict[
        str,
        Dict[str, float]
    ],
) -> List[WardMetric]:

    if not table_exists(
        conn,
        "normalized_facilities",
    ):

        logger.warning(
            "normalized_facilities "
            "テーブルがありません。"
        )

        return []

    denominator = cfg.get(
        "denominator",
        "population_10k",
    )

    metric_fields = cfg.get(
        "metric_fields"
    )

    rows = conn.execute(
        """
        SELECT
            municipality,
            latitude,
            longitude,
            raw_json,
            source_dataset_id
        FROM normalized_facilities
        WHERE theme = ?
          AND municipality IS NOT NULL
          AND municipality != ''
        """,
        (theme,),
    ).fetchall()

    grouped: Dict[
        str,
        Dict[str, Any]
    ] = {}

    for row in rows:

        city = row[
            "municipality"
        ]

        group = grouped.setdefault(
            city,
            {
                "count": 0,
                "metric_sum": 0.0,
                "coord_count": 0,
                "datasets": set(),
            },
        )

        group[
            "count"
        ] += 1

        if (
            row["latitude"] is not None
            and row["longitude"] is not None
        ):

            group[
                "coord_count"
            ] += 1

        dataset_id = row[
            "source_dataset_id"
        ]

        if dataset_id:

            group[
                "datasets"
            ].add(
                dataset_id
            )

        #
        # metric_fields が指定されている場合
        # raw_json の実数値を使う。
        #
        # 例:
        #
        # metric_fields:
        #   - 公園面積
        #   - 面積
        #
        # 指定がない場合は施設1件=1として扱う。
        #

        metric_value = (
            extract_metric_from_raw_json(
                row["raw_json"],
                metric_fields,
            )
        )

        if metric_value is None:

            metric_value = 1.0

        group[
            "metric_sum"
        ] += metric_value

    results: List[
        WardMetric
    ] = []

    for city, values in (
        grouped.items()
    ):

        raw_count = int(
            values[
                "count"
            ]
        )

        metric_sum = float(
            values[
                "metric_sum"
            ]
        )

        coordinate_count = int(
            values[
                "coord_count"
            ]
        )

        dataset_count = len(
            values[
                "datasets"
            ]
        )

        denominator_value = (
            get_demographic_value(
                city,
                denominator,
                census_data,
            )
        )

        density = (
            metric_sum
            / denominator_value

            if denominator_value > 0

            else 0.0
        )

        coord_coverage = (

            coordinate_count
            / raw_count

            if raw_count > 0

            else 0.0
        )

        results.append(
            WardMetric(
                city_name=city,

                raw_count=raw_count,

                metric_sum=metric_sum,

                dataset_count=(
                    dataset_count
                ),

                coordinate_count=(
                    coordinate_count
                ),

                coord_coverage=(
                    coord_coverage
                ),

                denominator_value=(
                    denominator_value
                ),

                density=density,
            )
        )

    return results


# ============================================================
# Percentile
# ============================================================

def percentile_score(
    value: float,
    values: List[float],
) -> float:
    """
    23区の相対順位を0～100へ変換。

    最大値そのものではなく、
    「他区と比較してどの位置か」を評価する。

    例:
        最下位 → 0
        中央付近 → 約50
        最上位 → 100

    同値の場合は平均順位を使う。
    """

    if not values:

        return 0.0

    if len(
        values
    ) == 1:

        return 100.0

    sorted_values = sorted(
        values
    )

    below = sum(
        1
        for v in sorted_values
        if v < value
    )

    equal = sum(
        1
        for v in sorted_values
        if math.isclose(
            v,
            value,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    )

    rank = (
        below
        + max(
            0,
            equal - 1,
        ) / 2
    )

    score = (
        rank
        / (
            len(
                sorted_values
            )
            - 1
        )
        * 100
    )

    return round(
        min(
            100.0,
            max(
                0.0,
                score,
            ),
        ),
        1,
    )


# ============================================================
# Quality
# ============================================================

def calculate_quality_score(
    metric: WardMetric,
) -> float:
    """
    データ自体の品質。

    70%:
        座標カバー率

    30%:
        データセット多様性

    dataset 5個以上で満点。
    """

    coord_score = (
        metric.coord_coverage
        * 100.0
    )

    dataset_score = min(
        100.0,

        (
            metric.dataset_count
            / 5.0
        )
        * 100.0,
    )

    score = (
        coord_score
        * 0.70

        +

        dataset_score
        * 0.30
    )

    return round(
        score,
        1,
    )


# ============================================================
# Score
# ============================================================

def calculate_scores(
    *,
    theme: str,
    cfg: Dict[str, Any],
    metrics: List[WardMetric],
) -> List[WardScore]:

    if not metrics:

        return []

    densities = [
        metric.density
        for metric in metrics
    ]

    #
    # YAMLのweight。
    #
    # theme_schemaでは0〜2。
    #
    # これはテーマそのものの重要度として扱う。
    # ただし100点を超えない。
    #

    theme_weight = float(
        cfg.get(
            "weight",
            1.0,
        )
    )

    if resolve_effective_metric_key:

        metric_key = (
            resolve_effective_metric_key(
                theme,
                cfg,
            )
        )

    else:

        metric_key = (
            cfg.get(
                "metric_key"
            )
            or theme
        )

    scores: List[
        WardScore
    ] = []

    for metric in metrics:

        # ----------------------------------------------------
        # 量
        # ----------------------------------------------------

        richness_score = (
            percentile_score(
                metric.density,
                densities,
            )
        )

        # ----------------------------------------------------
        # 品質
        # ----------------------------------------------------

        quality_score = (
            calculate_quality_score(
                metric
            )
        )

        # ----------------------------------------------------
        # total
        #
        # 「施設充実度」を主役にして
        # データ品質は補助評価とする。
        #
        # 80 : 20
        # ----------------------------------------------------

        base_score = (
            richness_score
            * 0.80

            +

            quality_score
            * 0.20
        )

        #
        # YAML weight適用
        #

        total_score = (
            base_score
            * theme_weight
        )

        total_score = round(
            min(
                100.0,
                max(
                    0.0,
                    total_score,
                ),
            ),
            1,
        )

        scores.append(
            WardScore(
                theme=theme,

                metric_key=metric_key,

                city_name=(
                    metric.city_name
                ),

                raw_count=(
                    metric.raw_count
                ),

                density=round(
                    metric.density,
                    4,
                ),

                richness_score=(
                    richness_score
                ),

                quality_score=(
                    quality_score
                ),

                total_score=(
                    total_score
                ),
            )
        )

    return scores


# ============================================================
# 保存
# ============================================================

def save_scores(
    conn: sqlite3.Connection,
    scores: List[WardScore],
) -> None:

    with conn:

        for score in scores:

            conn.execute(
                """
                INSERT INTO ward_scores
                (
                    theme,
                    city_name,
                    raw_count,
                    quality_score,
                    richness_score,
                    total_score,
                    calculated_at
                )

                VALUES
                (
                    ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP
                )

                ON CONFLICT(theme, city_name)
                DO UPDATE SET

                    raw_count =
                        excluded.raw_count,

                    quality_score =
                        excluded.quality_score,

                    richness_score =
                        excluded.richness_score,

                    total_score =
                        excluded.total_score,

                    calculated_at =
                        CURRENT_TIMESTAMP
                """,
                (
                    score.theme,
                    score.city_name,
                    score.raw_count,
                    score.quality_score,
                    score.richness_score,
                    score.total_score,
                ),
            )


# ============================================================
# 1テーマ実行
# ============================================================

def run_category_score(
    *,
    theme: str,
    db_path: Path | str = DEFAULT_DB_PATH,
    themes_dir: Path = DEFAULT_THEMES_DIR,
) -> List[WardScore]:

    logger.info(
        "[CategoryScore] 開始 theme=%s",
        theme,
    )

    # --------------------------------------------------------
    # YAML
    # --------------------------------------------------------

    cfg = load_theme_config(
        theme,
        themes_dir,
    )

    logger.info(
        "[%s] label=%s denominator=%s weight=%s metric_key=%s",
        theme,
        cfg.get(
            "label"
        ),
        cfg.get(
            "denominator"
        ),
        cfg.get(
            "weight",
            1.0,
        ),
        cfg.get(
            "metric_key"
        )
        or theme,
    )

    # --------------------------------------------------------
    # Census
    # --------------------------------------------------------

    census_data = (
        load_census_normalized()
    )

    if census_data:

        logger.info(
            "国勢調査normalized:"
            " %d区読み込み",
            len(
                census_data
            ),
        )

    else:

        logger.warning(
            "国勢調査normalizedが無いため"
            "基礎統計フォールバックを使用します。"
        )

    # --------------------------------------------------------
    # DB
    # --------------------------------------------------------

    conn = connect_db(
        db_path
    )

    try:

        ensure_ward_scores_table(
            conn
        )

        # ----------------------------------------------------
        # 実数集計
        # ----------------------------------------------------

        metrics = (
            collect_ward_metrics(
                conn,

                theme=theme,

                cfg=cfg,

                census_data=(
                    census_data
                ),
            )
        )

        if not metrics:

            logger.warning(
                "[%s] 採点対象となる"
                "normalized_facilitiesがありません。",
                theme,
            )

            return []

        # ----------------------------------------------------
        # 採点
        # ----------------------------------------------------

        scores = calculate_scores(
            theme=theme,

            cfg=cfg,

            metrics=metrics,
        )

        # ----------------------------------------------------
        # DB
        # ----------------------------------------------------

        save_scores(
            conn,
            scores,
        )

        logger.info(
            "[%s] %d区のスコアを"
            "ward_scoresへ保存しました。",
            theme,
            len(
                scores
            ),
        )

        return scores

    finally:

        conn.close()


# ============================================================
# 全テーマ
# ============================================================

def run_all_categories(
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
    themes_dir: Path = DEFAULT_THEMES_DIR,
) -> Dict[str, List[WardScore]]:

    results: Dict[
        str,
        List[WardScore]
    ] = {}

    for yaml_path in sorted(
        themes_dir.glob(
            "*.yaml"
        )
    ):

        theme = (
            yaml_path.stem
        )

        try:

            scores = (
                run_category_score(
                    theme=theme,

                    db_path=db_path,

                    themes_dir=themes_dir,
                )
            )

            results[
                theme
            ] = scores

        except ThemeConfigError as exc:

            logger.error(
                "[%s] YAML設定エラー:\n%s",
                theme,
                exc,
            )

        except Exception as exc:

            logger.exception(
                "[%s] スコア計算失敗: %s",
                theme,
                exc,
            )

    return results


# ============================================================
# 表示
# ============================================================

def get_rank(
    score: float,
) -> str:

    if score >= 85:
        return "S"

    if score >= 70:
        return "A"

    if score >= 55:
        return "B"

    return "C"


def print_ranking(
    scores: List[WardScore],
    label: Optional[str] = None,
) -> None:

    ranking = sorted(
        scores,
        key=lambda x: (
            x.total_score
        ),
        reverse=True,
    )

    print()
    print(
        "=" * 76
    )

    print(
        f" {label or 'テーマ'} "
        "東京23区ランキング"
    )

    print(
        "=" * 76
    )

    print(
        "順位 区名       "
        "総合点  Rank "
        "充実度 品質   件数   密度"
    )

    print(
        "-" * 76
    )

    for index, score in enumerate(
        ranking,
        start=1,
    ):

        print(
            f"{index:2d}位 "
            f"{score.city_name:<6} "
            f"{score.total_score:6.1f} "
            f"{get_rank(score.total_score):>4} "
            f"{score.richness_score:6.1f} "
            f"{score.quality_score:6.1f} "
            f"{score.raw_count:5d} "
            f"{score.density:8.3f}"
        )

    print()


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "Tokyo 23 Wards "
            "カテゴリ採点エンジン"
        )
    )

    parser.add_argument(
        "--theme",
        default=None,
        help=(
            "採点するテーマ。"
            "例: park / disaster / aed"
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "themes/*.yaml を"
            "すべて採点"
        ),
    )

    parser.add_argument(
        "--db-path",
        default=str(
            DEFAULT_DB_PATH
        ),
    )

    parser.add_argument(
        "--themes-dir",
        default=str(
            DEFAULT_THEMES_DIR
        ),
    )

    return parser


# ============================================================
# main
# ============================================================

def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "[%(levelname)s] "
            "%(name)s: "
            "%(message)s"
        ),
    )

    parser = (
        build_parser()
    )

    args = (
        parser.parse_args()
    )

    db_path = Path(
        args.db_path
    )

    themes_dir = Path(
        args.themes_dir
    )

    # --------------------------------------------------------
    # 全テーマ
    # --------------------------------------------------------

    if args.all:

        results = (
            run_all_categories(
                db_path=db_path,
                themes_dir=themes_dir,
            )
        )

        for theme, scores in (
            results.items()
        ):

            if not scores:
                continue

            try:

                cfg = (
                    load_theme_config(
                        theme,
                        themes_dir,
                    )
                )

                label = cfg.get(
                    "label",
                    theme,
                )

            except Exception:

                label = theme

            print_ranking(
                scores,
                label,
            )

        return

    # --------------------------------------------------------
    # 単一テーマ
    # --------------------------------------------------------

    if not args.theme:

        parser.error(
            "--theme または --all "
            "を指定してください。"
        )

    cfg = load_theme_config(
        args.theme,
        themes_dir,
    )

    scores = (
        run_category_score(
            theme=args.theme,
            db_path=db_path,
            themes_dir=themes_dir,
        )
    )

    print_ranking(
        scores,
        cfg.get(
            "label",
            args.theme,
        ),
    )


if __name__ == "__main__":
    main()