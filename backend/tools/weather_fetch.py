import httpx
from typing import Any, Dict
from tools.base import BaseTool # 先ほど定義した基底クラスをインポート

class WeatherFetchTool(BaseTool):
    @property
    def name(self) -> str:
        return "weather_fetch"

    @property
    def description(self) -> str:
        return "指定された都市（東京、ロンドンなど）の現在の天気と気温を取得します。"

    def get_schema(self) -> Dict[str, Any]:
        """Ollama (OpenAI互換) に渡すためのJSONスキーマ"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "天気を知りたい都市名（例: 'Tokyo', 'London', '大阪', '札幌'）"
                        }
                    },
                    "required": ["city"]
                }
            }
        }

    async def execute(self, city: str, **kwargs) -> Dict[str, Any]:
        """
        実際のAPI通信ロジック
        ステップ1: 都市名から緯度・経度を取得 (ジオコーディング)
        ステップ2: 緯度・経度から天気を取得
        """
        try:
            # ==========================================
            # 1. ジオコーディングAPI (都市名 -> 緯度/経度)
            # ==========================================
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ja&format=json"
            async with httpx.AsyncClient(timeout=10.0) as client:
                geo_res = await client.get(geo_url)
                geo_res.raise_for_status()
                geo_data = geo_res.json()

            if "results" not in geo_data or len(geo_data["results"]) == 0:
                return {
                    "error": True,
                    "message": f"都市 '{city}' が見つかりませんでした。別の表記で試してみてください。"
                }

            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name_ja = location["name"]

            # ==========================================
            # 2. 天気予報API (緯度/経度 -> 天気データ)
            # ==========================================
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
            weather_code = current.get("weathercode")

            # 天気コードを日本語に変換
            weather_desc = self._get_weather_description(weather_code)

            # ==========================================
            # 3. フロントエンド（またはLLM）に返すデータの成形
            # ==========================================
            return {
                "error": False,
                # フロントエンドにそのままテキストとして出す用のメッセージ
                "message": f"🌤️ {city_name_ja} の現在の天気は「{weather_desc}」、気温は {temp}℃ です。（風速: {wind_speed} km/h）",
                # LLMが後から処理しやすいように生データも返す
                "raw_data": {
                    "city": city_name_ja,
                    "temperature": temp,
                    "weather": weather_desc,
                    "wind_speed": wind_speed
                }
            }

        except httpx.RequestError as e:
            return {"error": True, "message": f"天気APIへの接続に失敗しました: {str(e)}"}
        except Exception as e:
            return {"error": True, "message": f"予期せぬエラーが発生しました: {str(e)}"}

    def _get_weather_description(self, code: int) -> str:
        """
        WMO Weather interpretation codes (WW) を日本語にマッピング
        参照: https://open-meteo.com/en/docs
        """
        if code == 0: return "快晴"
        if code in [1, 2, 3]: return "晴れ時々曇り"
        if code in [45, 48]: return "霧"
        if code in [51, 53, 55, 56, 57]: return "霧雨"
        if code in [61, 63, 65, 66, 67]: return "雨"
        if code in [71, 73, 75, 77]: return "雪"
        if code in [80, 81, 82]: return "にわか雨"
        if code in [85, 86]: return "雪降"
        if code in [95, 96, 99]: return "雷雨"
        return "不明な天気"