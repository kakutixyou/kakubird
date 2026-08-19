#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/collectors/census_collector.py
──────────────────────────────────────
e-Stat APIから国勢調査データを取得し、
Tokyo_hackson_23/backend/data/census/raw/
へ「加工前の証拠データ」として保存するコレクター。

責務:
- e-Stat上の国勢調査統計表を検索
- 統計表メタ情報を取得
- 東京23区に絞って統計データを取得
- APIレスポンスをraw JSONとして保存
- 取得条件・統計表ID・取得日時等をmanifestへ保存

このファイルでは行わない:
- 人口、年齢、高齢化率などへの意味付け
- 指標名の統一
- スコア計算
- React用データへの変換

後段:
    census_normalize_engine.py
        ↓
    census_score_engine.py

前提:
    collectors/estat_client.py が存在すること。

環境変数:
    ESTAT_APP_ID
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    from Tokyo_hackson_23.backend.collectors.estat_client import (
        EStatClient,
        EStatError,
    )
except ImportError:
    # census_collector.py を直接実行する場合のフォールバック
    try:
        from estat_client import EStatClient, EStatError
    except ImportError as exc:
        raise ImportError(
            "estat_client.py を読み込めません。"
            "Tokyo_hackson_23/backend/collectors/"
            "estat_client.py が存在するか確認してください。"
        ) from exc


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# パス
# ──────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CENSUS_DIR = BACKEND_DIR / "data" / "census"
DEFAULT_RAW_DIR = DEFAULT_CENSUS_DIR / "raw"
DEFAULT_MASTER_DIR = BACKEND_DIR / "data" / "master"

DEFAULT_WARD_CODES_PATH = (
    DEFAULT_MASTER_DIR / "tokyo_ward_codes.json"
)


# ──────────────────────────────────────────────
# 東京23区
# ──────────────────────────────────────────────

#
# 自治体コード。
#
# master/tokyo_ward_codes.json が存在する場合は
# そちらを優先する。
#
# ここはmaster未作成でも動作確認できるよう、
# フォールバックとして保持する。
#
DEFAULT_TOKYO_WARDS: Dict[str, str] = {
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


# 国勢調査の政府統計コード
#
# e-Stat上で国勢調査を識別するコード。
#
CENSUS_STATS_CODE = "00200521"


# ──────────────────────────────────────────────
# データクラス
# ──────────────────────────────────────────────

@dataclass
class CensusCollectionResult:
    """
    1回の国勢調査取得結果。
    """

    stats_data_id: str
    survey_year: Optional[str]

    ward_count: int
    value_count: int

    raw_data_path: str
    meta_path: str
    manifest_path: str

    collected_at: str


# ──────────────────────────────────────────────
# 例外
# ──────────────────────────────────────────────

class CensusCollectorError(Exception):
    """国勢調査コレクター用の例外。"""


# ──────────────────────────────────────────────
# Collector
# ──────────────────────────────────────────────

class CensusCollector:

    def __init__(
        self,
        client: Optional[EStatClient] = None,
        raw_dir: Optional[str | Path] = None,
        ward_codes_path: Optional[str | Path] = None,
    ):
        """
        Parameters
        ----------
        client:
            EStatClient。
            省略した場合は自動生成する。

        raw_dir:
            raw JSON保存先。

        ward_codes_path:
            tokyo_ward_codes.json のパス。
        """

        self.client = client or EStatClient()

        self.raw_dir = (
            Path(raw_dir)
            if raw_dir
            else DEFAULT_RAW_DIR
        )

        self.raw_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ward_codes_path = (
            Path(ward_codes_path)
            if ward_codes_path
            else DEFAULT_WARD_CODES_PATH
        )

        self.wards = self._load_ward_codes()

    # ──────────────────────────────────────────
    # 東京23区マスター
    # ──────────────────────────────────────────

    def _load_ward_codes(self) -> Dict[str, str]:
        """
        tokyo_ward_codes.json を読み込む。

        対応形式:

        形式1:
        {
            "13101": "千代田区",
            "13102": "中央区"
        }

        形式2:
        {
            "13101": {
                "name": "千代田区"
            }
        }

        ファイルがなければDEFAULT_TOKYO_WARDSを使用。
        """

        if not self.ward_codes_path.exists():

            logger.warning(
                "tokyo_ward_codes.json がありません。"
                "内蔵23区コードを使用します: %s",
                self.ward_codes_path,
            )

            return DEFAULT_TOKYO_WARDS.copy()

        try:
            with self.ward_codes_path.open(
                "r",
                encoding="utf-8",
            ) as f:
                raw = json.load(f)

        except Exception as exc:
            raise CensusCollectorError(
                "tokyo_ward_codes.json の読み込みに"
                f"失敗しました: {exc}"
            ) from exc

        wards: Dict[str, str] = {}

        for code, value in raw.items():

            code = str(code).strip()

            if isinstance(value, str):
                name = value

            elif isinstance(value, dict):
                name = (
                    value.get("name")
                    or value.get("ward_name")
                    or value.get("city_name")
                )

            else:
                continue

            if not name:
                continue

            wards[code] = str(name)

        if not wards:
            raise CensusCollectorError(
                "tokyo_ward_codes.json から"
                "自治体コードを取得できませんでした。"
            )

        logger.info(
            "自治体コードマスター読み込み: %d件",
            len(wards),
        )

        return wards

    # ──────────────────────────────────────────
    # 統計表検索
    # ──────────────────────────────────────────

    def search_tables(
        self,
        *,
        year: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """
        国勢調査の統計表を検索する。

        例:

            collector.search_tables(
                year="2020",
                keyword="人口 年齢"
            )
        """

        search_word = "国勢調査"

        if keyword:
            search_word += f" AND {keyword}"

        logger.info(
            "国勢調査統計表検索:"
            " year=%s keyword=%s",
            year,
            keyword,
        )

        result = self.client.get_stats_list(
            search_word=search_word,
            stats_code=CENSUS_STATS_CODE,
            survey_years=year,
            limit=limit,
            # 市区町村集計を優先
            collectArea=3,
        )

        data_list = (
            result
            .get("GET_STATS_LIST", {})
            .get("DATALIST_INF", {})
        )

        tables = data_list.get(
            "TABLE_INF",
            [],
        )

        if isinstance(tables, dict):
            tables = [tables]

        if not isinstance(tables, list):
            return []

        logger.info(
            "国勢調査統計表候補: %d件",
            len(tables),
        )

        return tables

    # ──────────────────────────────────────────
    # 検索結果の簡易表示
    # ──────────────────────────────────────────

    def print_table_candidates(
        self,
        tables: Iterable[Dict[str, Any]],
    ) -> None:
        """
        getStatsListの結果から
        statsDataIdと表題をログ表示する。
        """

        count = 0

        for table in tables:

            count += 1

            stats_data_id = (
                table.get("@id")
                or "UNKNOWN"
            )

            title = self._extract_text(
                table.get("TITLE")
            )

            stats_name = self._extract_text(
                table.get("STATISTICS_NAME")
            )

            survey_date = self._extract_text(
                table.get("SURVEY_DATE")
            )

            logger.info(
                "[%03d] statsDataId=%s | %s | %s | %s",
                count,
                stats_data_id,
                stats_name,
                survey_date,
                title,
            )

    # ──────────────────────────────────────────
    # メタ情報取得
    # ──────────────────────────────────────────

    def fetch_meta(
        self,
        stats_data_id: str,
    ) -> Dict[str, Any]:
        """
        指定統計表のメタ情報を取得。
        """

        logger.info(
            "e-Statメタ情報取得: %s",
            stats_data_id,
        )

        return self.client.get_meta_info(
            stats_data_id=stats_data_id,
        )

    # ──────────────────────────────────────────
    # 東京23区の統計データ取得
    # ──────────────────────────────────────────

    def fetch_tokyo_23wards(
        self,
        stats_data_id: str,
        *,
        survey_year: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page_size: int = 100000,
    ) -> Dict[str, Any]:
        """
        指定統計表から東京23区分を取得する。

        cdArea に23区コードをカンマ区切りで指定する。

        filters:
            cdCat01等を追加指定できる。

        例:

            collector.fetch_tokyo_23wards(
                "0000000000",
                filters={
                    "cd_cat01": "001"
                }
            )
        """

        filters = dict(filters or {})

        ward_codes = ",".join(
            self.wards.keys()
        )

        logger.info(
            "東京23区データ取得開始:"
            " statsDataId=%s wards=%d",
            stats_data_id,
            len(self.wards),
        )

        #
        # get_all_stats_data() は estat_client.py 側で
        # VALUEだけをページング取得する。
        #
        values = self.client.get_all_stats_data(
            stats_data_id=stats_data_id,
            page_size=page_size,
            cd_area=ward_codes,
            **filters,
        )

        logger.info(
            "東京23区データ取得完了:"
            " VALUE=%d件",
            len(values),
        )

        return {
            "stats_data_id": stats_data_id,
            "survey_year": survey_year,

            "target": {
                "prefecture": "東京都",
                "area_type": "special_wards",
                "ward_count": len(self.wards),
            },

            "wards": [
                {
                    "code": code,
                    "name": name,
                }
                for code, name
                in self.wards.items()
            ],

            "filters": {
                "cdArea": ward_codes,
                **filters,
            },

            "values": values,
        }

    # ──────────────────────────────────────────
    # 一括取得 + raw保存
    # ──────────────────────────────────────────

    def collect(
        self,
        stats_data_id: str,
        *,
        survey_year: Optional[str] = None,
        dataset_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page_size: int = 100000,
    ) -> CensusCollectionResult:
        """
        国勢調査統計表を取得して、

        raw/
            <year>_<statsDataId>/
                metadata.json
                data.json
                manifest.json

        の形で保存する。

        取得したAPIレスポンスを証跡として保持する。
        """

        stats_data_id = str(
            stats_data_id
        ).strip()

        if not stats_data_id:
            raise ValueError(
                "stats_data_id が必要です。"
            )

        collected_at = (
            datetime.now(timezone.utc)
            .isoformat()
        )

        logger.info(
            "国勢調査収集開始:"
            " statsDataId=%s year=%s",
            stats_data_id,
            survey_year,
        )

        # --------------------------------------
        # 1. メタ情報
        # --------------------------------------

        meta = self.fetch_meta(
            stats_data_id
        )

        # --------------------------------------
        # 2. 23区データ
        # --------------------------------------

        data = self.fetch_tokyo_23wards(
            stats_data_id,
            survey_year=survey_year,
            filters=filters,
            page_size=page_size,
        )

        # --------------------------------------
        # 3. 保存ディレクトリ
        # --------------------------------------

        directory_name = self._build_directory_name(
            stats_data_id=stats_data_id,
            survey_year=survey_year,
        )

        output_dir = (
            self.raw_dir
            / directory_name
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        meta_path = (
            output_dir
            / "metadata.json"
        )

        data_path = (
            output_dir
            / "data.json"
        )

        manifest_path = (
            output_dir
            / "manifest.json"
        )

        # --------------------------------------
        # 4. raw JSON保存
        # --------------------------------------

        self._write_json(
            meta_path,
            meta,
        )

        self._write_json(
            data_path,
            data,
        )

        # --------------------------------------
        # 5. manifest
        # --------------------------------------

        manifest = {
            "source": {
                "provider": "e-Stat",
                "statistics": "国勢調査",
                "stats_code": CENSUS_STATS_CODE,
                "stats_data_id": stats_data_id,
            },

            "dataset": {
                "name": dataset_name,
                "survey_year": survey_year,
            },

            "target": {
                "prefecture": "東京都",
                "municipality_type": "special_ward",
                "ward_count": len(self.wards),
                "ward_codes": list(
                    self.wards.keys()
                ),
            },

            "request": {
                "filters": filters or {},
                "page_size": page_size,
            },

            "result": {
                "value_count": len(
                    data.get("values", [])
                ),
            },

            "files": {
                "metadata": meta_path.name,
                "data": data_path.name,
            },

            "collected_at": collected_at,

            "processing": {
                "stage": "raw",
                "normalized": False,
                "scored": False,
            },
        }

        self._write_json(
            manifest_path,
            manifest,
        )

        logger.info(
            "国勢調査raw保存完了: %s",
            output_dir,
        )

        return CensusCollectionResult(
            stats_data_id=stats_data_id,
            survey_year=survey_year,
            ward_count=len(self.wards),
            value_count=len(
                data.get("values", [])
            ),
            raw_data_path=str(data_path),
            meta_path=str(meta_path),
            manifest_path=str(manifest_path),
            collected_at=collected_at,
        )

    # ──────────────────────────────────────────
    # 検索→候補JSON保存
    # ──────────────────────────────────────────

    def search_and_save(
        self,
        *,
        year: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> Path:
        """
        統計表候補を検索し、
        raw/table_search_XXXX.json に保存する。

        「どのstatsDataIdを使うか決める」段階で使用。
        """

        tables = self.search_tables(
            year=year,
            keyword=keyword,
            limit=limit,
        )

        self.print_table_candidates(
            tables
        )

        timestamp = (
            datetime.now()
            .strftime("%Y%m%d_%H%M%S")
        )

        year_part = (
            year
            if year
            else "all"
        )

        output_path = (
            self.raw_dir
            / (
                f"table_search_"
                f"{year_part}_"
                f"{timestamp}.json"
            )
        )

        payload = {
            "query": {
                "statistics": "国勢調査",
                "stats_code": CENSUS_STATS_CODE,
                "survey_year": year,
                "keyword": keyword,
            },

            "count": len(tables),

            "tables": tables,
        }

        self._write_json(
            output_path,
            payload,
        )

        logger.info(
            "検索結果保存: %s",
            output_path,
        )

        return output_path

    # ──────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────

    @staticmethod
    def _write_json(
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

    @staticmethod
    def _build_directory_name(
        *,
        stats_data_id: str,
        survey_year: Optional[str],
    ) -> str:

        year_part = (
            str(survey_year)
            if survey_year
            else "unknown"
        )

        safe_id = "".join(
            c
            for c in stats_data_id
            if c.isalnum()
            or c in ("-", "_")
        )

        return (
            f"{year_part}_"
            f"{safe_id}"
        )

    @staticmethod
    def _extract_text(
        value: Any,
    ) -> str:
        """
        e-Statでは文字列が

            "人口"

        の場合と、

            {
                "@code": "...",
                "$": "人口"
            }

        の場合があるため吸収する。
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            text = value.get("$")

            if text is not None:
                return str(text)

        return str(value)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "CensusCollector":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "e-Stat 国勢調査データ収集"
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ------------------------------------------
    # search
    # ------------------------------------------

    search_parser = subparsers.add_parser(
        "search",
        help="国勢調査の統計表を検索",
    )

    search_parser.add_argument(
        "--year",
        default=None,
        help="調査年 例: 2020",
    )

    search_parser.add_argument(
        "--keyword",
        default=None,
        help="追加検索キーワード 例: 人口",
    )

    search_parser.add_argument(
        "--limit",
        type=int,
        default=100,
    )

    # ------------------------------------------
    # meta
    # ------------------------------------------

    meta_parser = subparsers.add_parser(
        "meta",
        help="統計表のメタ情報取得",
    )

    meta_parser.add_argument(
        "--stats-data-id",
        required=True,
    )

    # ------------------------------------------
    # collect
    # ------------------------------------------

    collect_parser = subparsers.add_parser(
        "collect",
        help="東京23区データ取得",
    )

    collect_parser.add_argument(
        "--stats-data-id",
        required=True,
        help="e-Stat統計表ID",
    )

    collect_parser.add_argument(
        "--year",
        default=None,
        help="調査年 例: 2020",
    )

    collect_parser.add_argument(
        "--name",
        default=None,
        help="任意のデータセット名",
    )

    collect_parser.add_argument(
        "--page-size",
        type=int,
        default=100000,
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

    try:

        with CensusCollector() as collector:

            # ----------------------------------
            # search
            # ----------------------------------

            if args.command == "search":

                path = collector.search_and_save(
                    year=args.year,
                    keyword=args.keyword,
                    limit=args.limit,
                )

                logger.info(
                    "完了: %s",
                    path,
                )

            # ----------------------------------
            # meta
            # ----------------------------------

            elif args.command == "meta":

                meta = collector.fetch_meta(
                    args.stats_data_id
                )

                print(
                    json.dumps(
                        meta,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            # ----------------------------------
            # collect
            # ----------------------------------

            elif args.command == "collect":

                result = collector.collect(
                    stats_data_id=(
                        args.stats_data_id
                    ),
                    survey_year=args.year,
                    dataset_name=args.name,
                    page_size=args.page_size,
                )

                logger.info(
                    "取得成功:"
                    " statsDataId=%s"
                    " wards=%d"
                    " values=%d",
                    result.stats_data_id,
                    result.ward_count,
                    result.value_count,
                )

                logger.info(
                    "data     : %s",
                    result.raw_data_path,
                )

                logger.info(
                    "metadata : %s",
                    result.meta_path,
                )

                logger.info(
                    "manifest : %s",
                    result.manifest_path,
                )

    except EStatError as exc:

        logger.error(
            "e-Stat APIエラー: %s",
            exc,
        )

        raise SystemExit(1)

    except CensusCollectorError as exc:

        logger.error(
            "国勢調査収集エラー: %s",
            exc,
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()