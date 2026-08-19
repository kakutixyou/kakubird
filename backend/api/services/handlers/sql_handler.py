# backend_sql_v2/api_sql_v2/services/handlers/sql_handler.py
import json
import re
from typing import Tuple, Any

# nlp_serviceからロジックをインポート
# プロジェクトのルート構成に合わせてインポートパスを適宜微調整してください
from plugins.sql_builder_v2.backend_sql_v2.services.nlp_service import (
    detect_template_type,
    extract_entities,
    build_sql_template
)

class SQLHandler:
    def __init__(self):
        pass

    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        """
        メッセージ内容やIntentInspectorの解析信号から、このハンドラーの適合度を判定する。
        """
        msg_lower = message.lower().strip()

        # 1. 明示的なコマンドパス
        if msg_lower.startswith("/sql"):
            return 100

        # 2. IntentInspectorが既にデータベース操作モードと見抜いている場合
        if current_signals and current_signals.get("mode") == "database_operation":
            return 85
        if current_signals and current_signals.get("active_context") == "database":
            return 80

        # 3. 自然言語のキーワード判定（フォールバック用）
        sql_keywords = [
            "データベース", "テーブル", "クエリ", "保存して", "挿入", 
            "更新", "削除", "集計", "結合", "select", "where"
        ]
        if any(kw in msg_lower for kw in sql_keywords):
            return 75

        return 0

    def estimate_size(self, message: str) -> int:
        """レスポンスの予測データサイズ"""
        return 1500

    async def handle(self, request: Any) -> Tuple[str, Any]:
        """
        受領した日本語の指示文をnlp_serviceに通し、
        フロントエンドのSqlBuilderPanelが直接解釈できる構造化データを生成して返す。
        """
        # オーケストレーターから届くリクエストオブジェクトからメッセージを取得
        raw_text = getattr(request, "message", "")
        if not raw_text and hasattr(request, "text"):
            raw_text = request.text

        try:
            # ===
            # 1. nlp_serviceの日本語解析エンジンを駆動
            # ===
            # テンプレート種別の判定 (subquery, left_join, select, insert 等)
            template_type = detect_template_type(raw_text)
            
            # テキストからのエンティティ抽出 (tables, columns, conditions)
            entities = extract_entities(raw_text)
            
            # 対応するSQLテンプレートとパーツデータの組み立て
            template_data = build_sql_template(template_type, raw_text, entities)

            # ===
            # 2. フロントエンド(useAiChat.js)の統一受信ルートに対応するデータ成形
            # ===
            # フロントの `data.response !== undefined && data.source !== undefined` に適合
            response_payload = {
                "response": f"指示「{raw_text}」から、最適なSQLテンプレート【{template_data['title']}】を生成しました。下のパネルから微調整して実行できます。",
                "source": "sql_handler",
                "response_type": "ui_code",
                "blocks": [
                    {
                        "type": "SqlBuilderPanel",  # 👈 フロントの block.jsx がこの名前を見てコンポーネントをスイッチ
                        "props": {
                            "type": template_type,
                            "title": template_data["title"],
                            "icon": template_data["icon"],
                            "description": template_data["description"],
                            "sql": template_data["sql"],
                            "parts": template_data["parts"],
                            "input": raw_text
                        }
                    }
                ]
            }

            return "ui_code", response_payload

        except Exception as e:
            # ハンドラー内部で予期せぬエラーが起きた場合のセーフティフォールバック
            error_payload = {
                "response": f" SQL生成処理中にエラーが発生しました: {str(e)}",
                "source": "sql_handler",
                "response_type": "text",
                "blocks": []
            }
            return "text", error_payload