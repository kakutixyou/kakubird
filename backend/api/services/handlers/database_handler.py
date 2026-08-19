# database_handler.py
import json
from typing import Tuple, Any
from datetime import datetime
from .base_handler import BaseHandler
from core.job_database import get_all_jobs

from api.services.inspectors.IntentInSpector import IntentInspector

from ..inspectors.IntentInSpector import IntentInspector


from ..inspectors.IntentInSpector import IntentInspector

DB_COMMANDS = {"/db", "/database"}

class DatabaseHandler(BaseHandler):
    """
    データベース関連の質問や、保存済みデータの呼び出しを担当するハンドラー
    """
    
    async def can_handle(self, message: str) -> bool:
        msg = message.lower()
        if any(msg.startswith(cmd) for cmd in DB_COMMANDS):
            return True
            
        keywords = ["一覧", "保存済", "保存した", "データベース", "求人データ"]
        is_request_display = ("見せて" in msg or "表示して" in msg) and ("データ" in msg or "履歴" in msg or "求人" in msg)
        
        return any(k in msg for k in keywords) or is_request_display

    # ----------------------------------------------------
    # 🌟 Inspectorへの全権委譲 ＆ 連続使用ボーナスの安全化
    # ----------------------------------------------------
    async def calculate_score(self, message: str, signals: dict = None) -> int: # type: ignore
        msg_lower = message.strip().lower()
        
        # 1. 絶対コマンドは強制100点
        if any(msg_lower.startswith(cmd) for cmd in DB_COMMANDS):
            return 100
            
        # 2. Inspector（共通の審査員）に委譲
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        if analysis["mode"] == "database_operation":
            score = analysis["score"]
            
            # 3. 長期的な文脈（信号）による微調整も、Inspectorの法律（最大85点）に従わせる
            if signals and signals.get("last_used_handler") == "DatabaseHandler":
                score += 10
                
            return min(score, 85)

        return 0

    # ----------------------------------------------------
    # 🌟 既存の堅牢なデータ取得・パース処理は完全維持！
    # ----------------------------------------------------
    async def handle(self, message: str) -> Tuple[str, Any]:
        print("🗄️ Database Handler 発動: 保存済み求人一覧の取得")
        
        try:
            jobs = get_all_jobs()
        except Exception as e:
            print(f"❌ DB読み込みエラー: {e}")
            return "text", "申し訳ありません。データベースの読み込み中にエラーが発生しました。"

        if not jobs:
            return "text", "データベースに保存された求人データはまだありません。\n求人票のテキストや画像をアップロードしてAIに解析させてみましょう！"

        # 1. チャットの吹き出し用にMarkdownで綺麗な「一覧表」を作る
        md_table = f"### 📂 保存済みの求人データ（計 {len(jobs)} 件）\n\n"
        md_table += "| ID | 企業名 | AI判定 | 保存日時 |\n"
        md_table += "|:---:|---|---|---|\n"

        label_emoji = {
            "white": "✨ 優良",
            "gray_to_white": "👍 安全",
            "gray": " 注意",
            "black": "🚨 警戒"
        }

        json_data_list = []

        for job in jobs:
            c_name = job.get('company_name', '不明な企業')
            label = job.get('overall_label', 'gray')
            display_label = label_emoji.get(label, f"🔍 {label}")
            
            # --- 罠1対策: 日時フォーマットの安全な変換 ---
            created_at_raw = job.get('created_at', '')
            if isinstance(created_at_raw, datetime):
                date_short = created_at_raw.strftime('%Y-%m-%d %H:%M')
            else:
                date_short = str(created_at_raw)[:16] if created_at_raw else "不明"
            
            md_table += f"| {job.get('id', '?')} | **{c_name}** | {display_label} | {date_short} |\n"

            # --- 罠2対策: raw_jsonのパース（文字列だったらオブジェクトに戻す） ---
            raw_json_field = job.get('raw_json', '{}')
            parsed_json = {}
            if isinstance(raw_json_field, str):
                try:
                    parsed_json = json.loads(raw_json_field)
                except json.JSONDecodeError:
                    parsed_json = {"error": "JSONパース失敗", "raw_data": raw_json_field}
            else:
                parsed_json = raw_json_field

            # 2. JsonViewerBlockに渡す用の生データリストを作成
            json_data_list.append({
                "id": job.get('id'),
                "company_name": c_name,
                "data": parsed_json 
            })

        # 3. UIコードとして返却する
        content = {
            "message": md_table + "\n\n💡 リスト下のブロックを展開すると、各求人の詳細なAI解析生データ（JSON）を階層構造で確認できますよ！",
            "blocks": [
                {
                    "type": "JsonViewerBlock",
                    "props": {
                        "title": f"💾 データベース生データ ({len(jobs)}件)",
                        "data": json_data_list
                    }
                }
            ]
        }
        
        return "ui_code", content