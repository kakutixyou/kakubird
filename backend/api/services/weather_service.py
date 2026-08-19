
# To/backend/api/services/weather_service.py

import traceback
import urllib.parse
from typing import Dict, Any

import httpx


# ===
# Constants
# ===

GEOCODING_API = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

WEATHER_API = (
    "https://api.open-meteo.com/v1/forecast"
)

DEFAULT_TIMEOUT = 10.0


# ===
# Weather Code Mapping
# ===

WEATHER_CODE_MAP = {
    0: "快晴 ☀️",

    1: "晴れ 🌤️",
    2: "晴れ時々曇り 🌤️",
    3: "曇り ☁️",

    45: "霧 🌫️",
    48: "霧 🌫️",

    51: "霧雨 🌧️",
    53: "霧雨 🌧️",
    55: "霧雨 🌧️",
    56: "霧雨 🌧️",
    57: "霧雨 🌧️",

    61: "雨 ☔",
    63: "雨 ☔",
    65: "大雨 ☔",
    66: "着氷性の雨 ❄️",
    67: "着氷性の大雨 ❄️",

    71: "雪 ⛄",
    73: "雪 ⛄",
    75: "大雪 ❄️",
    77: "雪粒 ❄️",

    80: "にわか雨 🌦️",
    81: "にわか雨 🌦️",
    82: "激しいにわか雨 ⛈️",

    85: "にわか雪 🌨️",
    86: "激しいにわか雪 🌨️",

    95: "雷雨 ⛈️",
    96: "雷雨 ⛈️",
    99: "激しい雷雨 ⛈️",
}


# ===
# Helper Functions
# ===

def get_weather_description(code: int) -> str:
    """
    weather code -> 日本語説明
    """

    return WEATHER_CODE_MAP.get(code, "不明")


async def geocode_city(city: str) -> Dict[str, Any]:
    """
    都市名 -> 緯度経度変換

    Returns:
        {
            "success": bool,
            "city_name": str,
            "latitude": float,
            "longitude": float,
        }
    """

    safe_city = urllib.parse.quote(city)

    url = (
        f"{GEOCODING_API}"
        f"?name={safe_city}"
        f"&count=1"
        f"&language=ja"
        f"&format=json"
    )

    try:

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT
        ) as client:

            response = await client.get(url)

            response.raise_for_status()

            data = response.json()

        if "results" not in data:

            return {
                "success": False,
                "message":
                    f"「{city}」の観測地点が見つかりませんでした。"
            }

        result = data["results"][0]

        return {
            "success": True,
            "city_name": result["name"],
            "latitude": result["latitude"],
            "longitude": result["longitude"],
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(e)
        }


# ===
# Current Weather
# ===

async def fetch_current_weather(
    city: str
) -> Dict[str, Any]:
    """
    現在の天気取得
    """

    geo = await geocode_city(city)

    if not geo["success"]:
        return {
            "error": True,
            "message": geo["message"]
        }

    lat = geo["latitude"]
    lon = geo["longitude"]
    city_name = geo["city_name"]

    weather_url = (
        f"{WEATHER_API}"
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&current_weather=true"
        f"&timezone=Asia%2FTokyo"
    )

    try:

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT
        ) as client:

            response = await client.get(weather_url)

            response.raise_for_status()

            data = response.json()

        current_weather = data.get(
            "current_weather",
            {}
        )

        weather_code = current_weather.get(
            "weathercode",
            0
        )

        weather_desc = get_weather_description(
            weather_code
        )

        temperature = current_weather.get(
            "temperature",
            "?"
        )

        windspeed = current_weather.get(
            "windspeed",
            "?"
        )

        message = (
            f"🌤️ **{city_name}** の現在の天気\n\n"
            f"天気: {weather_desc}\n"
            f"気温: {temperature}℃\n"
            f"風速: {windspeed} km/h"
        )

        return {
            "error": False,
            "city": city_name,
            "weather": weather_desc,
            "temperature": temperature,
            "windspeed": windspeed,
            "message": message,
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": True,
            "message": "現在の天気取得に失敗しました。"
        }


# ===
# Weekly Forecast
# ===

async def fetch_weekly_forecast(
    city: str
) -> Dict[str, Any]:
    """
    1週間天気予報
    """

    geo = await geocode_city(city)

    if not geo["success"]:

        return {
            "error": True,
            "message": geo["message"]
        }

    lat = geo["latitude"]
    lon = geo["longitude"]
    city_name = geo["city_name"]

    weather_url = (
        f"{WEATHER_API}"
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&daily="
        f"weathercode,"
        f"temperature_2m_max,"
        f"temperature_2m_min"
        f"&timezone=Asia%2FTokyo"
    )

    try:

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT
        ) as client:

            response = await client.get(weather_url)

            response.raise_for_status()

            data = response.json()

        daily = data.get("daily", {})

        weekly_items = []

        weekly_text = (
            f"📅 **{city_name} の1週間予報**\n\n"
        )

        for i in range(7):

            date = daily["time"][i][5:]

            weather_code = daily["weathercode"][i]

            weather_desc = get_weather_description(
                weather_code
            )

            temp_max = daily["temperature_2m_max"][i]

            temp_min = daily["temperature_2m_min"][i]

            weekly_items.append({
                "date": date,
                "weather": weather_desc,
                "temp_max": temp_max,
                "temp_min": temp_min,
            })

            weekly_text += (
                f"・**{date}**\n"
                f"  {weather_desc}\n"
                f"  最高 {temp_max}℃ / 最低 {temp_min}℃\n\n"
            )

        return {
            "error": False,
            "city": city_name,
            "forecast": weekly_items,
            "message": weekly_text,
        }

    except Exception:

        traceback.print_exc()

        return {
            "error": True,
            "message": "週間天気予報の取得に失敗しました。"
        }


# ===
# Main Public API
# ===

async def execute_weather_fetch(
    city: str,
    forecast_type: str = "weekly"
    
) -> Dict[str, Any]:
    """
    orchestrator / tools から呼ばれる公開API

    forecast_type:
        - current
        - weekly
    """

    try:

        if forecast_type == "weekly":

            return await fetch_weekly_forecast(
                city
            )

        return await fetch_current_weather(
            city
        )

    except Exception:

        traceback.print_exc()

        return {
            "error": True,
            "message": "天気サービス内部エラーが発生しました。"
        }


# ===
# Future Expansion Notes
# ===

"""
将来的な拡張ポイント

1. UV Index
--------------------------------------------------------
daily=uv_index_max

2. Air Quality
--------------------------------------------------------
Open-Meteo Air Quality API

3. Radar Images
--------------------------------------------------------
雨雲レーダー画像

4. Severe Weather Alerts
--------------------------------------------------------
警報・注意報

5. Localization
--------------------------------------------------------
多言語対応

6. Caching
--------------------------------------------------------
Redis / in-memory cache

7. Weather Tool Registry
--------------------------------------------------------
Tool Calling自動化

8. Streaming Forecast
--------------------------------------------------------
リアルタイム更新

9. Geo Auto Detection
--------------------------------------------------------
IP / GPS location support

10. UI Response Blocks
--------------------------------------------------------
WeatherCardBlock
"""

