#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
backend/engines/census_normalize_engine.py
──────────────────────────────────────────

e-Stat 国勢調査の raw データを、
Tokyo 23 Wards アプリで扱いやすい形式へ正規化する。

入力
----
backend/data/census/raw/

例:

2020_XXXXXXXXXX/
├── metadata.json
├── data.json
└── manifest.json


出力
----
backend/data/census/normalized/

例:

census_2020_XXXXXXXXXX.json


出力イメージ
------------
{
    "survey_year": 2020,
    "stats_data_id": "...",

    "wards": [
        {
            "ward_code": "13121",
            "ward_name": "足立区",

            "metrics": {
                "population_total": 695043,
                "population_male": ...,
                "population_female": ...,
                "population_0_14": ...,
                "population_15_64": ...,
                "population_65_plus": ...,
                "households": ...
            }
        }
    ]
}


重要
----
e-Stat の @cat01 / @cat02 等の意味は
統計表によって異なる。

そのため、

    metadata.json
        +
    data.json

をセットで読み、

    コード → 人間向けラベル

へ変換してから指標を判定する。


このエンジンでは、判定できなかった項目を
勝手に捨てず unknown_metrics として残す。
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)


# ============================================================
# パス
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_RAW_DIR = (
    BACKEND_DIR
    / "data"
    / "census"
    / "raw"
)

DEFAULT_NORMALIZED_DIR = (
    BACKEND_DIR
    / "data"
    / "census"
    / "normalized"
)

DEFAULT_MASTER_DIR = (
    BACKEND_DIR
    / "data"
    / "master"
)

DEFAULT_WARD_CODES_PATH = (
    DEFAULT_MASTER_DIR
    / "tokyo_ward_codes.json"
)


# ============================================================
# 東京23区
# ============================================================

DEFAULT_TOKYO_WARDS = {
    "13101": "千代田区",
    "13102": "中央区",
    "13103": "港区",
    "13104": "新宿区",
    "13105": "文京区",
    "13106": "台東区",
    "13107": "墨田区",
    "13108": "江東区",
    "13109": "品川区",
    "13110": "目黒区",
    "13111": "大田区",
    "13112": "世田谷区",
    "13113": "渋谷区",
    "13114": "中野区",
    "13115": "杉並区",
    "13116": "豊島区",
    "13117": "北区",
    "13118": "荒川区",
    "13119": "板橋区",
    "13120": "練馬区",
    "13121": "足立区",
    "13122": "葛飾区",
    "13123": "江戸川区",
}


# ============================================================
# 指標候補
#
# e-Stat の統計表は表ごとに表現が異なるため、
# 完全一致ではなく「含まれている語」で推測する。
#
# 優先順位が重要なので list で保持する。
# ============================================================

METRIC_RULES = [

    # --------------------------------------------------------
    # 世帯
    # --------------------------------------------------------

    {
        "key": "households",
        "include": [
            "一般世帯数",
            "世帯数",
            "総世帯数",
        ],
        "exclude": [
            "1世帯当たり",
            "世帯人員",
        ],
    },

    # --------------------------------------------------------
    # 年齢3区分
    # --------------------------------------------------------

    {
        "key": "population_0_14",
        "include": [
            "15歳未満",
            "0～14歳",
            "0-14歳",
            "年少人口",
        ],
        "exclude": [
            "割合",
            "比率",
            "%",
        ],
    },

    {
        "key": "population_15_64",
        "include": [
            "15～64歳",
            "15-64歳",
            "生産年齢人口",
        ],
        "exclude": [
            "割合",
            "比率",
            "%",
        ],
    },

    {
        "key": "population_65_plus",
        "include": [
            "65歳以上",
            "老年人口",
        ],
        "exclude": [
            "割合",
            "比率",
            "%",
        ],
    },

    # --------------------------------------------------------
    # 男女
    # --------------------------------------------------------

    {
        "key": "population_male",
        "include": [
            "男",
            "男性",
        ],
        "require_population_context": True,
        "exclude": [
            "女",
            "割合",
            "比率",
            "%",
        ],
    },

    {
        "key": "population_female",
        "include": [
            "女",
            "女性",
        ],
        "require_population_context": True,
        "exclude": [
            "男女計",
            "割合",
            "比率",
            "%",
        ],
    },

    # --------------------------------------------------------
    # 総人口
    #
    # 最後に判定する。
    # --------------------------------------------------------

    {
        "key": "population_total",
        "include": [
            "総人口",
            "人口総数",
            "人口",
        ],
        "exclude": [
            "15歳未満",
            "15～64歳",
            "15-64歳",
            "65歳以上",
            "男",
            "女",
            "割合",
            "率",
            "%",
            "世帯",
        ],
    },
]


# ============================================================
# データクラス
# ============================================================

@dataclass
class NormalizedEvidence:

    metric_key: str

    raw_value: Any

    numeric_value: Optional[float]

    area_code: str

    labels: List[str]

    raw_dimensions: Dict[str, str]


@dataclass
class NormalizedWard:

    ward_code: str

    ward_name: str

    metrics: Dict[str, float]

    evidence: Dict[str, NormalizedEvidence]

    unknown_metrics: List[Dict[str, Any]]


# ============================================================
# 例外
# ============================================================

class CensusNormalizeError(Exception):
    pass


# ============================================================
# JSON
# ============================================================

def load_json(
    path: Path,
) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# Utility
# ============================================================

def ensure_list(
    value: Any,
) -> List[Any]:

    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    return [value]


def extract_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        return str(value)

    if isinstance(
        value,
        dict,
    ):

        for key in (
            "$",
            "name",
            "label",
            "value",
        ):

            if key in value:

                return extract_text(
                    value[key]
                )

    return str(value)


def normalize_text(
    text: str,
) -> str:

    text = str(
        text or ""
    )

    # 全角・半角空白を削除
    text = (
        text
        .replace(" ", "")
        .replace("　", "")
    )

    # 長音・波ダッシュの揺れ
    text = (
        text
        .replace("〜", "～")
        .replace("―", "-")
        .replace("−", "-")
    )

    return text


def safe_float(
    value: Any,
) -> Optional[float]:
    """
    e-Stat VALUE "$" を数値へ変換。

    以下は欠損扱い:
        "-"
        "..."
        "X"
        ""
    """

    if value is None:
        return None

    if isinstance(
        value,
        (int, float),
    ):

        if math.isnan(
            float(value)
        ):
            return None

        return float(value)

    text = str(
        value
    ).strip()

    if not text:
        return None

    if text in {
        "-",
        "－",
        "...",
        "…",
        "X",
        "x",
        "*",
    }:
        return None

    # カンマ除去
    text = text.replace(
        ",",
        "",
    )

    # 注釈等が後ろについているケースへの最低限対応
    text = re.sub(
        r"\s+.*$",
        "",
        text,
    )

    try:

        return float(
            text
        )

    except ValueError:

        return None


# ============================================================
# Ward master
# ============================================================

def load_ward_codes(
    path: Path = DEFAULT_WARD_CODES_PATH,
) -> Dict[str, str]:

    if not path.exists():

        logger.warning(
            "tokyo_ward_codes.json がないため"
            "内蔵23区マスターを使用します。"
        )

        return DEFAULT_TOKYO_WARDS.copy()

    try:

        raw = load_json(
            path
        )

    except Exception as exc:

        logger.warning(
            "ward master読み込み失敗: %s",
            exc,
        )

        return DEFAULT_TOKYO_WARDS.copy()

    result = {}

    if not isinstance(
        raw,
        dict,
    ):
        return DEFAULT_TOKYO_WARDS.copy()

    for code, item in raw.items():

        if isinstance(
            item,
            str,
        ):

            name = item

        elif isinstance(
            item,
            dict,
        ):

            name = (
                item.get("name")
                or item.get("ward_name")
                or item.get("city_name")
            )

        else:

            continue

        if name:

            result[
                str(code)
            ] = str(name)

    return (
        result
        or DEFAULT_TOKYO_WARDS.copy()
    )


# ============================================================
# e-Stat metadata parser
# ============================================================

def build_class_maps(
    metadata: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """
    e-Stat getMetaInfo の CLASS_INF を読み、

        {
            "area": {
                "13101": "千代田区",
                ...
            },

            "cat01": {
                "001": "総数",
                ...
            }
        }

    の形へ変換する。
    """

    maps: Dict[
        str,
        Dict[str, str]
    ] = {}

    metadata_inf = (
        metadata
        .get(
            "GET_META_INFO",
            {},
        )
        .get(
            "METADATA_INF",
            {},
        )
    )

    class_inf = metadata_inf.get(
        "CLASS_INF",
        {},
    )

    class_objs = ensure_list(
        class_inf.get(
            "CLASS_OBJ"
        )
    )

    for obj in class_objs:

        if not isinstance(
            obj,
            dict,
        ):
            continue

        class_id = str(
            obj.get("@id")
            or ""
        ).strip()

        if not class_id:
            continue

        code_map = {}

        classes = ensure_list(
            obj.get(
                "CLASS"
            )
        )

        for item in classes:

            if not isinstance(
                item,
                dict,
            ):
                continue

            code = (
                item.get("@code")
                or item.get("@id")
            )

            if code is None:
                continue

            label = (
                item.get("@name")
                or item.get("$")
                or item.get("NAME")
                or item.get("name")
            )

            if isinstance(
                label,
                dict,
            ):

                label = extract_text(
                    label
                )

            if label is None:
                label = ""

            code_map[
                str(code)
            ] = str(label)

        maps[
            class_id
        ] = code_map

    return maps


# ============================================================
# VALUE dimension
# ============================================================

def extract_dimensions(
    row: Dict[str, Any],
) -> Dict[str, str]:
    """
    VALUE:

    {
        "@tab": "...",
        "@cat01": "...",
        "@cat02": "...",
        "@area": "13121",
        "@time": "...",
        "$": "123"
    }

    から @xxx 部分だけを取り出す。
    """

    dimensions = {}

    for key, value in row.items():

        if not str(
            key
        ).startswith("@"):
            continue

        dimension = str(
            key
        )[1:]

        dimensions[
            dimension
        ] = str(value)

    return dimensions


def resolve_labels(
    dimensions: Dict[str, str],
    class_maps: Dict[str, Dict[str, str]],
) -> List[str]:

    labels = []

    for dimension, code in dimensions.items():

        label = (
            class_maps
            .get(
                dimension,
                {},
            )
            .get(
                code
            )
        )

        if label:

            labels.append(
                str(label)
            )

    return labels


# ============================================================
# Metric判定
# ============================================================

def detect_metric(
    labels: Iterable[str],
) -> Optional[str]:

    normalized_labels = [
        normalize_text(x)
        for x in labels
        if x
    ]

    combined = " ".join(
        normalized_labels
    )

    if not combined:
        return None

    for rule in METRIC_RULES:

        include = [
            normalize_text(x)
            for x in rule.get(
                "include",
                [],
            )
        ]

        exclude = [
            normalize_text(x)
            for x in rule.get(
                "exclude",
                [],
            )
        ]

        # include のうち1つ以上
        if not any(
            word in combined
            for word in include
        ):
            continue

        # exclude が入っていれば対象外
        if any(
            word in combined
            for word in exclude
        ):
            continue

        if rule.get(
            "require_population_context"
        ):

            population_words = [
                "人口",
                "人",
                "総数",
            ]

            if not any(
                x in combined
                for x in population_words
            ):
                continue

        return str(
            rule["key"]
        )

    return None


# ============================================================
# 同一指標が複数出た場合
# ============================================================

def should_replace_metric(
    metric_key: str,
    current: Optional[NormalizedEvidence],
    new: NormalizedEvidence,
) -> bool:
    """
    同じ metric が複数見つかった場合の簡易優先順位。

    原則:
    ・既存がなければ採用
    ・男女計 / 総数 / 総人口の表現を優先
    """

    if current is None:
        return True

    new_text = normalize_text(
        " ".join(
            new.labels
        )
    )

    current_text = normalize_text(
        " ".join(
            current.labels
        )
    )

    preferred_words = [
        "男女計",
        "総数",
        "総人口",
        "人口総数",
    ]

    new_priority = sum(
        word in new_text
        for word in preferred_words
    )

    current_priority = sum(
        word in current_text
        for word in preferred_words
    )

    return (
        new_priority
        > current_priority
    )


# ============================================================
# Normalizer
# ============================================================

class CensusNormalizer:

    def __init__(
        self,
        raw_dir: Path = DEFAULT_RAW_DIR,
        normalized_dir: Path = DEFAULT_NORMALIZED_DIR,
        ward_codes_path: Path = DEFAULT_WARD_CODES_PATH,
    ):

        self.raw_dir = Path(
            raw_dir
        )

        self.normalized_dir = Path(
            normalized_dir
        )

        self.normalized_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ward_codes = load_ward_codes(
            Path(
                ward_codes_path
            )
        )

    # --------------------------------------------------------
    # raw dataset 1件処理
    # --------------------------------------------------------

    def normalize_dataset(
        self,
        dataset_dir: Path,
    ) -> Path:

        dataset_dir = Path(
            dataset_dir
        )

        metadata_path = (
            dataset_dir
            / "metadata.json"
        )

        data_path = (
            dataset_dir
            / "data.json"
        )

        manifest_path = (
            dataset_dir
            / "manifest.json"
        )

        if not metadata_path.exists():

            raise CensusNormalizeError(
                f"metadata.json がありません: "
                f"{dataset_dir}"
            )

        if not data_path.exists():

            raise CensusNormalizeError(
                f"data.json がありません: "
                f"{dataset_dir}"
            )

        metadata = load_json(
            metadata_path
        )

        data = load_json(
            data_path
        )

        manifest = {}

        if manifest_path.exists():

            manifest = load_json(
                manifest_path
            )

        class_maps = build_class_maps(
            metadata
        )

        values = data.get(
            "values",
            []
        )

        if not isinstance(
            values,
            list,
        ):

            raise CensusNormalizeError(
                "data.json の values が"
                "配列ではありません。"
            )

        stats_data_id = (
            data.get(
                "stats_data_id"
            )
            or manifest
            .get(
                "source",
                {},
            )
            .get(
                "stats_data_id"
            )
            or dataset_dir.name
        )

        survey_year = (
            data.get(
                "survey_year"
            )
            or manifest
            .get(
                "dataset",
                {},
            )
            .get(
                "survey_year"
            )
        )

        wards: Dict[
            str,
            NormalizedWard
        ] = {}

        for ward_code, ward_name in (
            self.ward_codes.items()
        ):

            wards[
                ward_code
            ] = NormalizedWard(
                ward_code=ward_code,
                ward_name=ward_name,
                metrics={},
                evidence={},
                unknown_metrics=[],
            )

        matched_count = 0
        unknown_count = 0

        # ----------------------------------------------------
        # VALUE処理
        # ----------------------------------------------------

        for row in values:

            if not isinstance(
                row,
                dict,
            ):
                continue

            dimensions = extract_dimensions(
                row
            )

            area_code = dimensions.get(
                "area"
            )

            if not area_code:
                continue

            # 23区以外なら無視
            if area_code not in wards:
                continue

            raw_value = row.get(
                "$"
            )

            numeric_value = safe_float(
                raw_value
            )

            if numeric_value is None:
                continue

            labels = resolve_labels(
                dimensions,
                class_maps,
            )

            metric_key = detect_metric(
                labels
            )

            ward = wards[
                area_code
            ]

            # ----------------------------------------------
            # 判定不能
            # ----------------------------------------------

            if not metric_key:

                unknown_count += 1

                ward.unknown_metrics.append(
                    {
                        "value": numeric_value,
                        "raw_value": raw_value,
                        "labels": labels,
                        "dimensions": dimensions,
                    }
                )

                continue

            # ----------------------------------------------
            # 指標として採用
            # ----------------------------------------------

            evidence = NormalizedEvidence(
                metric_key=metric_key,
                raw_value=raw_value,
                numeric_value=numeric_value,
                area_code=area_code,
                labels=labels,
                raw_dimensions=dimensions,
            )

            current = ward.evidence.get(
                metric_key
            )

            if should_replace_metric(
                metric_key,
                current,
                evidence,
            ):

                ward.metrics[
                    metric_key
                ] = numeric_value

                ward.evidence[
                    metric_key
                ] = evidence

            matched_count += 1

        # ----------------------------------------------------
        # derived metrics
        # ----------------------------------------------------

        for ward in wards.values():

            self._calculate_derived_metrics(
                ward
            )

        # ----------------------------------------------------
        # JSON化
        # ----------------------------------------------------

        ward_payloads = []

        for ward in wards.values():

            evidence_payload = {
                key: asdict(value)
                for key, value
                in ward.evidence.items()
            }

            ward_payloads.append(
                {
                    "ward_code": ward.ward_code,
                    "ward_name": ward.ward_name,

                    "metrics": ward.metrics,

                    "evidence": evidence_payload,

                    "unknown_metrics": (
                        ward.unknown_metrics
                    ),
                }
            )

        payload = {

            "schema_version": "1.0",

            "source": {
                "provider": "e-Stat",
                "statistics": "国勢調査",
                "stats_data_id": str(
                    stats_data_id
                ),
            },

            "survey_year": (
                int(survey_year)
                if (
                    survey_year
                    and str(
                        survey_year
                    ).isdigit()
                )
                else survey_year
            ),

            "stats_data_id": str(
                stats_data_id
            ),

            "normalization": {
                "ward_count": len(
                    ward_payloads
                ),

                "source_value_count": len(
                    values
                ),

                "matched_value_count": (
                    matched_count
                ),

                "unknown_value_count": (
                    unknown_count
                ),
            },

            "wards": ward_payloads,
        }

        year_text = (
            str(survey_year)
            if survey_year
            else "unknown"
        )

        safe_stats_id = re.sub(
            r"[^0-9A-Za-z_-]",
            "_",
            str(stats_data_id),
        )

        output_path = (
            self.normalized_dir
            / (
                f"census_"
                f"{year_text}_"
                f"{safe_stats_id}.json"
            )
        )

        save_json(
            output_path,
            payload,
        )

        logger.info(
            "国勢調査正規化完了: %s "
            "(matched=%d unknown=%d)",
            output_path,
            matched_count,
            unknown_count,
        )

        return output_path

    # --------------------------------------------------------
    # 派生指標
    # --------------------------------------------------------

    @staticmethod
    def _calculate_derived_metrics(
        ward: NormalizedWard,
    ) -> None:

        metrics = ward.metrics

        total = metrics.get(
            "population_total"
        )

        children = metrics.get(
            "population_0_14"
        )

        working = metrics.get(
            "population_15_64"
        )

        elderly = metrics.get(
            "population_65_plus"
        )

        male = metrics.get(
            "population_male"
        )

        female = metrics.get(
            "population_female"
        )

        households = metrics.get(
            "households"
        )

        # ----------------------------------------------------
        # 年少人口割合
        # ----------------------------------------------------

        if total and children is not None:

            metrics[
                "children_ratio"
            ] = round(
                children
                / total
                * 100,
                3,
            )

        # ----------------------------------------------------
        # 生産年齢人口割合
        # ----------------------------------------------------

        if total and working is not None:

            metrics[
                "working_age_ratio"
            ] = round(
                working
                / total
                * 100,
                3,
            )

        # ----------------------------------------------------
        # 高齢化率
        # ----------------------------------------------------

        if total and elderly is not None:

            metrics[
                "elderly_ratio"
            ] = round(
                elderly
                / total
                * 100,
                3,
            )

        # ----------------------------------------------------
        # 1世帯当たり人口
        # ----------------------------------------------------

        if (
            total
            and households
            and households > 0
        ):

            metrics[
                "population_per_household"
            ] = round(
                total
                / households,
                3,
            )

        # ----------------------------------------------------
        # 男女比
        # ----------------------------------------------------

        if (
            male is not None
            and female
            and female > 0
        ):

            metrics[
                "male_female_ratio"
            ] = round(
                male
                / female
                * 100,
                3,
            )

    # --------------------------------------------------------
    # raw全部処理
    # --------------------------------------------------------

    def normalize_all(
        self,
    ) -> List[Path]:

        if not self.raw_dir.exists():

            raise CensusNormalizeError(
                f"rawディレクトリがありません: "
                f"{self.raw_dir}"
            )

        outputs: List[
            Path
        ] = []

        for dataset_dir in sorted(
            self.raw_dir.iterdir()
        ):

            if not dataset_dir.is_dir():
                continue

            metadata = (
                dataset_dir
                / "metadata.json"
            )

            data = (
                dataset_dir
                / "data.json"
            )

            if not (
                metadata.exists()
                and data.exists()
            ):
                continue

            try:

                output = (
                    self.normalize_dataset(
                        dataset_dir
                    )
                )

                outputs.append(
                    output
                )

            except Exception as exc:

                logger.exception(
                    "正規化失敗 %s: %s",
                    dataset_dir,
                    exc,
                )

        return outputs


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "e-Stat 国勢調査 raw "
            "→ normalized 変換"
        )
    )

    parser.add_argument(
        "--dataset",
        default=None,
        help=(
            "特定rawディレクトリのみ処理。"
            "例: "
            "data/census/raw/"
            "2020_0003445133"
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "raw以下の全統計表を"
            "正規化"
        ),
    )

    parser.add_argument(
        "--raw-dir",
        default=str(
            DEFAULT_RAW_DIR
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=str(
            DEFAULT_NORMALIZED_DIR
        ),
    )

    return parser


def main():

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "[%(levelname)s] "
            "%(name)s: "
            "%(message)s"
        ),
    )

    parser = build_parser()

    args = parser.parse_args()

    normalizer = CensusNormalizer(
        raw_dir=Path(
            args.raw_dir
        ),
        normalized_dir=Path(
            args.output_dir
        ),
    )

    # --------------------------------------------------------
    # 1件
    # --------------------------------------------------------

    if args.dataset:

        output = (
            normalizer.normalize_dataset(
                Path(
                    args.dataset
                )
            )
        )

        print(
            f"normalized: {output}"
        )

        return

    # --------------------------------------------------------
    # 全件
    # --------------------------------------------------------

    if args.all:

        outputs = (
            normalizer.normalize_all()
        )

        print()
        print(
            f"正規化完了: {len(outputs)}件"
        )

        for output in outputs:

            print(
                f"  {output}"
            )

        return

    parser.error(
        "--dataset または --all "
        "を指定してください。"
    )


if __name__ == "__main__":
    main()