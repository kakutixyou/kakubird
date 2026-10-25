#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/weather/weather_tool.py
旧 weather_fetch.py と WeatherHandler を統合した天気取得ツール。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import httpx
from tools.base_tool import BaseTool


class WeatherTool(BaseTool):
    name = "weather_fetch"
    aliases = ["weather", "weather_search"]
    category = "weather"
    description = "指定された都市（東京、ロンドン、大阪、札幌など）の現在の天気と気温・風速を取得します。"

    fast_route_enabled = False
    priority = 50
    mode = "weather_lookup"
    forced_handler = "WeatherHandler"
    fast_route_score = 90

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        cache: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if msg_lower.startswith("/weather"):
            return True, "weather_command"
        return False, ""

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "天気を知りたい都市名（例: 'Tokyo', 'London', '大阪', '札幌'）",
                }
            },
            "required": ["city"],
        }

    async def execute(self, city: str = "東京", **kwargs: Any) -> Dict[str, Any]:
        try:
            geo_url = (
                f"https://geocoding-api.open-meteo.com/v1/search"
                f"?name={city}&count=1&language=ja&format=json"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                geo_res = await client.get(geo_url)
                geo_res.raise_for_status()
                geo_data = geo_res.json()

            results = geo_data.get("results") or []
            if not results:
                return {
                    "error": True,
                    "message": f"都市 '{city}' が見つかりませんでした。別の表記で試してみてください。",
                }

            location = results[0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name_ja = location.get("name", city)

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}&current_weather=true&timezone=Asia%2FTokyo"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                weather_res = await client.get(weather_url)
                weather_res.raise_for_status()
                weather_data = weather_res.json()

            current = weather_data.get("current_weather", {})
            temp = current.get("temperature")
            wind_speed = current.get("windspeed")
            weather_code = int(current.get("weathercode", -1))
            weather_desc = self._get_weather_description(weather_code)

            return {
                "error": False,
                "message": f"🌤️ {city_name_ja} の現在の天気は「{weather_desc}」、気温は {temp}℃ です。（風速: {wind_speed} km/h）",
                "raw_data": {
                    "city": city_name_ja,
                    "temperature": temp,
                    "weather": weather_desc,
                    "wind_speed": wind_speed,
                },
            }
        except Exception as exc:
            return {"error": True, "message": f"天気情報の取得に失敗しました: {exc}"}

    @staticmethod
    def _get_weather_description(code: int) -> str:
        if code == 0:
            return "快晴"
        if code in (1, 2, 3):
            return "晴れ時々曇り"
        if code in (45, 48):
            return "霧"
        if code in (51, 53, 55, 56, 57):
            return "霧雨"
        if code in (61, 63, 65, 66, 67):
            return "雨"
        if code in (71, 73, 75, 77):
            return "雪"
        if code in (80, 81, 82):
            return "にわか雨"
        if code in (85, 86):
            return "吹雪"
        if code in (95, 96, 99):
            return "雷雨"
        return "不明な天気"