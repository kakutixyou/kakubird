import os
import json
from datetime import datetime, timedelta
from .base_handler import BaseHandler # 環境に合わせてインポートパスを調整してください

class GantChartHandler(BaseHandler):
    def __init__(self):
        # Viteの公開ディレクトリ（public/plugins/timeline/）を出力先に設定
        self.output_dir = os.path.join(
            os.getcwd(), 
            "public", "plugins", "timeline"
        )
        # フォルダが存在しない場合は作成
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "dummy_gantt.json")

    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        """
        ユーザーのメッセージからガントチャート生成の意図をスコアリング
        """
        keywords = ["ガントチャート", "スケジュール", "リスケ", "ダミー", "gantt", "進捗"]
        if any(kw in message.lower() for kw in keywords):
            return 90 # 高スコアを返して発火させる
        return 0

    def estimate_size(self, message: str) -> int:
        return 300

    async def handle(self, request) -> tuple[str, str]:
        """
        現在の日付を基準に、Frappe Gantt互換のダミーJSONを生成して保存する
        """
        # 基準日（今日）を取得し、動的に日付を計算することでいつでも「現在進行形」に見せる
        today = datetime.now()
        
        # Frappe Ganttの必須プロパティに準拠したタスクリスト
        tasks = [
            {
                "id": "Task_1",
                "name": "要件定義と基本設計 (完了済)",
                "start": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
                "end": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                "progress": 100,
                "dependencies": "",
                "custom_class": "bar-completed"
            },
            {
                "id": "Task_2",
                "name": "DBスキーマ・インフラ構築 (担当: Dev_A)",
                "start": (today - timedelta(days=6)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "progress": 80,
                "dependencies": "Task_1",
                "custom_class": "bar-backend"
            },
            {
                "id": "Task_3",
                "name": "UIコンポーネント実装 (担当: Dev_B)",
                "start": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
                "progress": 65,
                "dependencies": "Task_1",
                "custom_class": "bar-frontend"
            },
            {
                "id": "Task_4",
                "name": "コア機能APIと結合 (担当: Dev_C)",
                "start": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=9)).strftime("%Y-%m-%d"),
                "progress": 10,
                "dependencies": "Task_2, Task_3",
                "custom_class": "bar-backend"
            },
            {
                "id": "Task_5",
                "name": "総合テストとQA (担当: Dev_D)",
                "start": (today + timedelta(days=10)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
                "progress": 0,
                "dependencies": "Task_4",
                "custom_class": "bar-qa"
            }
        ]

        try:
            # publicフォルダにJSONファイルとして書き出し
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            
            response_msg = (
                "🛡️ **防衛用ガントチャートの生成が完了しました。**\n"
                f"出力先: `{self.output_file}`\n\n"
                "複数人のチーム体制で順調にタスクを消化している理想的なタイムラインを構成しています。\n"
                "画面上のシールドボタンを押して、Frappe Ganttビューアを起動し、クライアントに共有してください。"
            )
            return "text", response_msg
        
        except Exception as e:
            return "text", f" ガントチャートの生成に失敗しました: {e}"