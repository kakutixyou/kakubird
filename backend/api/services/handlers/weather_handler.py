# api/services/handlers/weather_handler.py
from typing import Any, Tuple
from .base_handler import BaseHandler
from api.services.weather_service import execute_weather_fetch

class WeatherHandler(BaseHandler):
    """
    天気情報の取得リクエストを担当するハンドラー
    """
    def __init__(self):
        # 🌟 修正ポイント: 海外APIが漢字で空振りする現象を防ぐため、
        # 確実にヒットする「英語名」に変換する辞書を用意しました！
        self.CITY_MAP = {
            "札幌": "Sapporo", "青森": "Aomori", "盛岡": "Morioka", "仙台": "Sendai",
            "秋田": "Akita", "山形": "Yamagata", "福島": "Fukushima", "水戸": "Mito",
            "宇歩宮": "Utsunomiya", "前橋": "Maebashi", "さいたま": "Saitama", "埼玉": "Saitama",
            "千葉": "Chiba", "東京": "Tokyo", "横浜": "Yokohama", "新潟": "Niigata",
            "富山": "Toyama", "金沢": "Kanazawa", "福井": "Fukui", "甲府": "Kofu",
            "長野": "Nagano", "岐阜": "Gifu", "静岡": "Shizuoka", "名古屋": "Nagoya",
            "津": "Tsu", "大津": "Otsu", "京都": "Kyoto", "大阪": "Osaka",
            "神戸": "Kobe", "奈良": "Nara", "和歌山": "Wakayama", "鳥取": "Tottori",
            "松江": "Matsue", "岡山": "Okayama", "広島": "Hiroshima", "山口": "Yamaguchi",
            "徳島": "Tokushima", "高松": "Takamatsu", "松山": "Matsuyama", "高知": "Kochi",
            "福岡": "Fukuoka", "佐賀": "Saga", "長崎": "Nagasaki", "熊本": "Kumamoto",
            "大分": "Oita", "宮崎": "Miyazaki", "鹿児島": "Kagoshima", "那覇": "Naha"
        }

    async def can_handle(self, message: str) -> bool:
        return "天気" in message

    async def handle(self, message: str) -> Tuple[str, Any]:
        print("☁️ Weather Handler 発動: 天気予報を取得します")
        
        try:
            # 1. 日本語のメッセージから都市名を抽出
            target_city_ja = "東京" # デフォルト
            for city_ja in self.CITY_MAP.keys():
                if city_ja in message:
                    target_city_ja = city_ja
                    break
                    
            # 2. APIに渡すための英語名に変換（これで空振りバグを回避！）
            target_city_en = self.CITY_MAP[target_city_ja]
            print(f"🔍 抽出都市: {target_city_ja} -> APIリクエスト: {target_city_en}")
            
            # 3. 「来週」キーワードを追加した判定式！
            if any(k in message for k in ["一週間", "1週間", "週間", "予報", "来週"]):
                result = await execute_weather_fetch(target_city_en, forecast_type="weekly")
            else:
                result = await execute_weather_fetch(target_city_en, forecast_type="current")
                
            return "text", result["message"]
            
        except Exception as e:
            print(f"Weather Handler Error: {e}")
            return "text", "天気情報の取得に失敗しました。"