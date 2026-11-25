from __future__ import annotations

import csv
import io
import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional
from urllib.parse import quote

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
STOOQ_URL = "https://stooq.com/q/d/l/"
TIMEOUT_SECONDS = 15
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.^_-]{1,24}$")


class StockFollowupRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    recommendation_date: date
    reference_price: Optional[float] = Field(default=None, gt=0)
    recommendation_url: Optional[str] = Field(default=None, max_length=2000)


def _add_month(value: date) -> date:
    month_index = value.month  # 1-based destination month before year normalization
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _load_daily_closes(symbol: str, start: date, end: date) -> list[dict]:
    normalized_symbol = symbol.strip().lower()
    if not SYMBOL_PATTERN.fullmatch(normalized_symbol):
        raise HTTPException(status_code=422, detail="銘柄コードの形式を確認してください（例: 7203.jp、aapl.us）。")
    try:
        response = requests.get(
            STOOQ_URL,
            params={"s": normalized_symbol, "i": "d", "d1": start.strftime("%Y%m%d"), "d2": end.strftime("%Y%m%d")},
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": "KakubirdStockFollowup/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"株価データを取得できませんでした: {str(exc)[:180]}") from exc

    rows = []
    try:
        for row in csv.DictReader(io.StringIO(response.text)):
            if not row.get("Date") or not row.get("Close") or row["Close"] in ("N/A", "-", ""):
                continue
            rows.append({"date": date.fromisoformat(row["Date"]), "close": float(row["Close"])})
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="株価データの��式を読み取れませんでした。") from exc
    return sorted(rows, key=lambda row: row["date"])


def _price_on_or_before(rows: list[dict], target: date) -> Optional[dict]:
    eligible = [row for row in rows if row["date"] <= target]
    return eligible[-1] if eligible else None


def _price_on_or_after(rows: list[dict], target: date) -> Optional[dict]:
    return next((row for row in rows if row["date"] >= target), None)


def _classify_return(percent: float) -> str:
    if percent > 0:
        return "上昇"
    if percent < 0:
        return "下落"
    return "変わらず"


@router.post("/api/stock-followup")
def stock_followup(request: StockFollowupRequest):
    today = date.today()
    if request.recommendation_date > today:
        raise HTTPException(status_code=422, detail="紹介日は今日以前の日付を指定してください。")

    horizon_dates = {
        "1日後": request.recommendation_date + timedelta(days=1),
        "7日後": request.recommendation_date + timedelta(days=7),
        "1ヶ月後": _add_month(request.recommendation_date),
    }
    # Fetch through the furthest horizon that has already elapsed; future checkpoints remain pending.
    fetch_end = min(today, max(horizon_dates.values()))
    rows = _load_daily_closes(request.symbol, request.recommendation_date - timedelta(days=10), fetch_end)
    if not rows:
        raise HTTPException(status_code=404, detail="指定期間の株価が見つかりません。銘柄コード（例: 7203.jp / aapl.us）とデータ提供範囲をご確認ください。")

    baseline = {"date": request.recommendation_date.isoformat(), "close": request.reference_price, "basis": "紹介価格（手入力）"}
    if request.reference_price is None:
        quote = _price_on_or_before(rows, request.recommendation_date)
        if quote is None:
            # A recommendation published before the first available quote: use the first close after it and disclose the proxy.
            quote = _price_on_or_after(rows, request.recommendation_date)
        if quote is None:
            raise HTTPException(status_code=404, detail="紹介日の基準株価を取得できませんでした。紹介価格を入力してください。")
        baseline = {"date": quote["date"].isoformat(), "close": quote["close"], "basis": "紹介日近辺の日足終値（紹介価格の代用値）"}

    base_price = float(baseline["close"])
    horizons = {}
    for label, target in horizon_dates.items():
        if target > today:
            horizons[label] = {"target_date": target.isoformat(), "status": "pending", "message": "判定日がまだ来ていません。"}
            continue
        quote = _price_on_or_after(rows, target)
        if quote is None:
            horizons[label] = {"target_date": target.isoformat(), "status": "pending", "message": "判定日以降の取引日データがまだありません。"}
            continue
        change = (quote["close"] - base_price) / base_price * 100
        horizons[label] = {
            "target_date": target.isoformat(),
            "price_date": quote["date"].isoformat(),
            "close": quote["close"],
            "change_percent": round(change, 2),
            "status": "up" if change > 0 else "down" if change < 0 else "flat",
            "judgment": _classify_return(change),
        }

    return {
        "symbol": request.symbol.strip().upper(),
        "recommendation_date": request.recommendation_date.isoformat(),
        "recommendation_url": request.recommendation_url,
        "baseline": baseline,
        "horizons": horizons,
        "data_source": "Stooq daily historical prices",
        "disclaimer": "株価の終値変化のみの機械的な振り返りです。紹介日当日の終値は実際に買えた価格とは限らず、指定がない場合は紹介日近辺の終値を代用します。配当・手数料・税金・売買タイミング・株式分割・投資金額を反映した実損益ではなく、紹介者の実力や将来成績を示すものでもありません。投資判断には利用せず、元情報と株価データを確認してください。",
    }
