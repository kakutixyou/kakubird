# knowledge_orchestra.py
import logging
from api.services.manager.KnowledgeManager import KnowledgeManager
# from chat_handler import ChatHandler  # ユーザーにメッセージを送るクラス（想定）

logger = logging.getLogger(__name__)

class KnowledgeOrchestra:
    def __init__(self, base_dir="./knowledge_store"):
        self.KnowledgeManager = KnowledgeManager(base_dir)
        # self.chat_handler = ChatHandler()

    def process_latest_knowledge(self):
        """
        KnowledgeManagerを使って最新のJSONを読み込み、
        人間に助言（正解の例）を送る必要があるか判断する
        """
        logger.info("オーケストレータ: ナレッジの評価を開始します...")
        
        # 1. Managerを使って全JSONをロード
        knowledges = self.KnowledgeManager.load_all_json_from_dir("analyzed_results")

        for k in knowledges:
            content = k.get("content", {})
            human_advice = content.get("human_advice", {})
            
            # 2. 人間の確認が必要な場合 (REQUIRES_HUMAN_REVIEW)
            if human_advice.get("status") == "REQUIRES_HUMAN_REVIEW":
                self._notify_human(k.get("name"), human_advice)
            else:
                logger.info(f"{k.get('name')} は安全(SAFE)です。自動処理を継続します。")

    def _notify_human(self, project_name, advice_data):
        """
        ChatHandler経由で、人間にアラートと正解の例（修正案）を通知する
        """
        summary = advice_data.get("summary", "警告があります。")
        alerts = advice_data.get("alerts", [])

        # チャット用のメッセージを組み立てる
        chat_message = f"⚠️ **プロジェクト [{project_name}] に関する重要なお知らせ**\n\n{summary}\n\n"
        
        for alert in alerts:
            chat_message += f"**[{alert['level']}] {alert['analyzer']} より:**\n"
            chat_message += f"{alert['message']}\n"
            
            # ★ ここで「正解の例」をチャットに付与する
            if "correct_example" in alert:
                chat_message += f"\n💡 {alert['correct_example']}\n"
            
            chat_message += "-" * 40 + "\n"

        chat_message += "\nどう対応しますか？ (例: '正解の例をそのまま適用して', '無視して続行して')"

        # 3. ChatHandlerに渡してユーザーに送信（未実装の場合はprintで代用）
        # self.chat_handler.send_message(chat_message)
        print("\n" + chat_message)

# 実行テスト用
if __name__ == "__main__":
    orchestra = KnowledgeOrchestra()
    orchestra.process_latest_knowledge()