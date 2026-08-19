#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/collectors/estat_client.py
──────────────────────────────────
e-Stat（政府統計の総合窓口）API v3.0 と通信するための低レベルクライアント。

このファイルの責務:
- e-Stat APIへのHTTPリクエスト
- 統計表検索
- 統計表メタ情報取得
- 統計データ取得
- APIエラーの共通処理
- リトライ
- JSONレスポンスの返却

このファイルでは以下を行わない:
- 国勢調査データの意味解釈
- 東京23区だけへの絞り込みロジック
- スコア計算
- census/raw への保存ルール
- 指標名の正規化

それらは census_collector.py /
census_normalize_engine.py /
census_score_engine.py 側で担当する。

e-Stat API:
https://api.e-stat.go.jp/rest/3.0/app/json/

環境変数:
    ESTAT_APP_ID

例:
    Windows PowerShell:
        $env:ESTAT_APP_ID="xxxxxxxxxxxxxxxx"

    bash:
        export ESTAT_APP_ID="xxxxxxxxxxxxxxxx"
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 例外
# ──────────────────────────────────────────────

class EStatError(Exception):
    """e-Stat関連エラーの基底クラス。"""


class EStatConfigError(EStatError):
    """APP IDなど設定に問題がある場合。"""


class EStatRequestError(EStatError):
    """HTTP通信そのものに失敗した場合。"""


class EStatAPIError(EStatError):
    """HTTPは成功したがe-Stat API側がエラーを返した場合。"""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        error_msg: Optional[str] = None,
    ):
        super().__init__(message)
        self.status = status
        self.error_msg = error_msg


# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────

@dataclass
class EStatClientConfig:
    """
    e-Stat APIクライアント設定。
    """

    base_url: str = "https://api.e-stat.go.jp/rest/3.0/app/json"

    timeout: int = 30

    # 一時的な通信失敗時の再試行回数
    max_retries: int = 3

    # retry間隔。
    # retryごとに backoff_sec * retry回数 だけ待つ。
    backoff_sec: float = 1.0

    # User-Agent
    user_agent: str = "Tokyo-Hackson-23-Census-Collector/1.0"


# ──────────────────────────────────────────────
# e-Stat API Client
# ──────────────────────────────────────────────

class EStatClient:
    """
    e-Stat API v3.0 クライアント。

    APP IDは、

        EStatClient(app_id="...")

    と直接指定するか、

        ESTAT_APP_ID

    環境変数から取得する。
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        config: Optional[EStatClientConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        self.config = config or EStatClientConfig()

        self.app_id = (
            app_id
            or os.getenv("ESTAT_APP_ID")
            or ""
        ).strip()

        if not self.app_id:
            raise EStatConfigError(
                "e-Stat APP ID が設定されていません。"
                "環境変数 ESTAT_APP_ID または "
                "EStatClient(app_id='...') で指定してください。"
            )

        self.session = session or requests.Session()

        self.session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        })

    # ──────────────────────────────────────────
    # 共通HTTP処理
    # ──────────────────────────────────────────

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        e-Stat APIにGETリクエストする共通処理。

        APP IDはここで自動付与する。
        """

        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        request_params = {
            "appId": self.app_id,
            **params,
        }

        # NoneをAPIへ送らない
        request_params = {
            key: value
            for key, value in request_params.items()
            if value is not None
        }

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):

            try:
                logger.debug(
                    "e-Stat API request endpoint=%s attempt=%d/%d",
                    endpoint,
                    attempt,
                    self.config.max_retries,
                )

                response = self.session.get(
                    url,
                    params=request_params,
                    timeout=self.config.timeout,
                )

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError as exc:
                    raise EStatRequestError(
                        "e-Stat APIのレスポンスをJSONとして解析できませんでした。"
                    ) from exc

                if not isinstance(data, dict):
                    raise EStatRequestError(
                        "e-Stat APIから想定外のレスポンス形式が返されました。"
                    )

                self._check_api_result(data)

                return data

            except EStatAPIError:
                # APIが明示的にエラーを返した場合は
                # 同じリクエストを何度送っても改善しないことが多いので即raise。
                raise

            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.HTTPError,
                EStatRequestError,
            ) as exc:

                last_exception = exc

                if attempt >= self.config.max_retries:
                    break

                wait_sec = self.config.backoff_sec * attempt

                logger.warning(
                    "e-Stat API通信失敗。%.1f秒後に再試行します "
                    "(%d/%d): %s",
                    wait_sec,
                    attempt,
                    self.config.max_retries,
                    exc,
                )

                time.sleep(wait_sec)

        raise EStatRequestError(
            f"e-Stat APIへの接続に失敗しました: {last_exception}"
        )

    # ──────────────────────────────────────────
    # API結果チェック
    # ──────────────────────────────────────────

    @staticmethod
    def _check_api_result(data: Dict[str, Any]) -> None:
        """
        e-Statの

            GET_STATS_LIST
            GET_META_INFO
            GET_STATS_DATA

        等に含まれる RESULT を調べる。
        """

        root = None

        for key in (
            "GET_STATS_LIST",
            "GET_META_INFO",
            "GET_STATS_DATA",
            "GET_DATA_CATALOG",
        ):
            value = data.get(key)

            if isinstance(value, dict):
                root = value
                break

        # 将来APIレスポンスが増えた場合でも、
        # RESULTが見つからないだけで壊さない。
        if root is None:
            return

        result = root.get("RESULT")

        if not isinstance(result, dict):
            return

        raw_status = result.get("STATUS", 0)

        try:
            status = int(raw_status)
        except (TypeError, ValueError):
            status = -1

        error_msg = (
            result.get("ERROR_MSG")
            or result.get("ERROR")
            or ""
        )

        # e-Statでは正常時 STATUS = 0
        if status != 0:
            raise EStatAPIError(
                f"e-Stat APIエラー "
                f"(STATUS={status}): {error_msg}",
                status=status,
                error_msg=str(error_msg),
            )

    # ──────────────────────────────────────────
    # 1. 統計表検索
    # ──────────────────────────────────────────

    def get_stats_list(
        self,
        *,
        search_word: Optional[str] = None,
        stats_code: Optional[str] = None,
        survey_years: Optional[str] = None,
        open_years: Optional[str] = None,
        limit: int = 100,
        start_position: int = 1,
        lang: str = "J",
        **extra_params: Any,
    ) -> Dict[str, Any]:
        """
        e-Stat上の統計表を検索する。

        主な使用例:

            client.get_stats_list(
                search_word="国勢調査",
                survey_years="2020"
            )

        stats_code:
            政府統計コードを指定したい場合に使用。

        extra_params:
            e-Stat側の追加検索パラメータをそのまま指定できる。
        """

        if limit < 1:
            raise ValueError("limit は1以上を指定してください。")

        if start_position < 1:
            raise ValueError(
                "start_position は1以上を指定してください。"
            )

        params: Dict[str, Any] = {
            "lang": lang,
            "searchWord": search_word,
            "statsCode": stats_code,
            "surveyYears": survey_years,
            "openYears": open_years,
            "limit": limit,
            "startPosition": start_position,
        }

        params.update(extra_params)

        return self._request(
            "getStatsList",
            params,
        )

    # ──────────────────────────────────────────
    # 2. メタ情報取得
    # ──────────────────────────────────────────

    def get_meta_info(
        self,
        stats_data_id: str,
        *,
        lang: str = "J",
        **extra_params: Any,
    ) -> Dict[str, Any]:
        """
        指定統計表の分類情報を取得する。

        国勢調査では特に重要。

        例:
        - 地域分類
        - 男女分類
        - 年齢分類
        - 世帯分類
        - 表章事項

        を確認するために使用する。

        stats_data_id:
            e-Statの統計表ID。
        """

        stats_data_id = str(stats_data_id).strip()

        if not stats_data_id:
            raise ValueError(
                "stats_data_id を指定してください。"
            )

        params: Dict[str, Any] = {
            "lang": lang,
            "statsDataId": stats_data_id,
        }

        params.update(extra_params)

        return self._request(
            "getMetaInfo",
            params,
        )

    # ──────────────────────────────────────────
    # 3. 統計データ取得
    # ──────────────────────────────────────────

    def get_stats_data(
        self,
        stats_data_id: str,
        *,
        cd_area: Optional[str] = None,
        cd_cat01: Optional[str] = None,
        cd_cat02: Optional[str] = None,
        cd_cat03: Optional[str] = None,
        cd_cat04: Optional[str] = None,
        cd_cat05: Optional[str] = None,
        cd_time: Optional[str] = None,
        limit: int = 100000,
        start_position: int = 1,
        meta_get_flg: str = "Y",
        cnt_get_flg: str = "N",
        lang: str = "J",
        **extra_params: Any,
    ) -> Dict[str, Any]:
        """
        統計データ本体を取得する。

        重要:
        cdArea や cat01 のコード体系は統計表によって異なるため、
        先に get_meta_info() で分類情報を確認すること。

        例:

            result = client.get_stats_data(
                stats_data_id="xxxxxxxxxx",
                cd_area="13121"
            )

        extra_params を利用すると、
        cdCat06以降などにも対応できる。
        """

        stats_data_id = str(stats_data_id).strip()

        if not stats_data_id:
            raise ValueError(
                "stats_data_id を指定してください。"
            )

        if limit < 1:
            raise ValueError(
                "limit は1以上を指定してください。"
            )

        if start_position < 1:
            raise ValueError(
                "start_position は1以上を指定してください。"
            )

        params: Dict[str, Any] = {
            "lang": lang,
            "statsDataId": stats_data_id,

            "cdArea": cd_area,

            "cdCat01": cd_cat01,
            "cdCat02": cd_cat02,
            "cdCat03": cd_cat03,
            "cdCat04": cd_cat04,
            "cdCat05": cd_cat05,

            "cdTime": cd_time,

            "limit": limit,
            "startPosition": start_position,

            "metaGetFlg": meta_get_flg,
            "cntGetFlg": cnt_get_flg,
        }

        params.update(extra_params)

        return self._request(
            "getStatsData",
            params,
        )

    # ──────────────────────────────────────────
    # 4. 統計データ全件取得
    # ──────────────────────────────────────────

    def get_all_stats_data(
        self,
        stats_data_id: str,
        *,
        page_size: int = 100000,
        **filters: Any,
    ) -> list[Dict[str, Any]]:
        """
        getStatsDataをページングし、
        VALUEデータをまとめて返す便利関数。

        戻り値:

            [
                {
                    "@area": "...",
                    "@cat01": "...",
                    "$": "12345"
                },
                ...
            ]

        census_collector.py はこちらを使ってもよい。
        """

        if page_size < 1:
            raise ValueError(
                "page_size は1以上を指定してください。"
            )

        all_values: list[Dict[str, Any]] = []

        start_position = 1

        while True:

            data = self.get_stats_data(
                stats_data_id,
                limit=page_size,
                start_position=start_position,
                **filters,
            )

            stats_data = data.get(
                "GET_STATS_DATA",
                {}
            ).get(
                "STATISTICAL_DATA",
                {}
            )

            data_inf = stats_data.get(
                "DATA_INF",
                {}
            )

            values = data_inf.get(
                "VALUE",
                []
            )

            if isinstance(values, dict):
                values = [values]

            if not values:
                break

            all_values.extend(values)

            result_inf = stats_data.get(
                "RESULT_INF",
                {}
            )

            total_number = self._safe_int(
                result_inf.get("TOTAL_NUMBER")
            )

            next_key = result_inf.get(
                "NEXT_KEY"
            )

            logger.info(
                "e-Stat取得中: %d / %s 件",
                len(all_values),
                total_number or "?",
            )

            # 全件取得済み
            if total_number is not None:
                if len(all_values) >= total_number:
                    break

            # e-Statが次ページを返していない
            if not next_key:
                break

            next_position = self._safe_int(next_key)

            if next_position is None:
                break

            # 無限ループ防止
            if next_position <= start_position:
                logger.warning(
                    "NEXT_KEYが現在位置以下のため"
                    "ページングを終了します: %s",
                    next_key,
                )
                break

            start_position = next_position

        return all_values

    # ──────────────────────────────────────────
    # 5. JSON保存
    # ──────────────────────────────────────────

    @staticmethod
    def save_json(
        data: Any,
        path: str | Path,
    ) -> Path:
        """
        APIレスポンスを加工せずJSONとして保存する。

        census_collector.py の raw保存にも利用可能。
        """

        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return output_path

    # ──────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> Optional[int]:

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def close(self) -> None:
        """HTTP Sessionを閉じる。"""
        self.session.close()

    def __enter__(self) -> "EStatClient":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()


# ──────────────────────────────────────────────
# 単体動作確認
# ──────────────────────────────────────────────

def main():
    """
    接続テスト。

    python -m Tokyo_hackson_23.backend.collectors.estat_client

    ESTAT_APP_ID が設定されていれば
    「国勢調査」で統計表検索を実施する。
    """

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "[%(levelname)s] "
            "%(name)s: %(message)s"
        ),
    )

    try:
        with EStatClient() as client:

            logger.info(
                "e-Stat API接続テスト開始"
            )

            result = client.get_stats_list(
                search_word="国勢調査",
                limit=10,
            )

            stats_list = result.get(
                "GET_STATS_LIST",
                {}
            ).get(
                "DATALIST_INF",
                {}
            )

            tables = stats_list.get(
                "TABLE_INF",
                []
            )

            if isinstance(tables, dict):
                tables = [tables]

            logger.info(
                "取得した統計表: %d件",
                len(tables),
            )

            for table in tables:

                stats_data_id = (
                    table.get("@id")
                    or table.get("STATISTICS_NAME_SPEC", {})
                    .get("$")
                    or "ID不明"
                )

                title = table.get(
                    "TITLE",
                    ""
                )

                if isinstance(title, dict):
                    title = title.get("$", "")

                logger.info(
                    "  %s : %s",
                    stats_data_id,
                    title,
                )

    except EStatError as exc:

        logger.error(
            "e-Stat接続テスト失敗: %s",
            exc,
        )


if __name__ == "__main__":
    main()