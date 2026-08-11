from typing import Dict, Any
# 実際のプロジェクトでは base_orchestrator.py から基底クラスをインポートします
# from .base_orchestrator import BaseOrchestrator

# 各種サービスのモック（実際には services/ 配下の各ファイルからインポートします）
# from services.safety_filter_service import check_input_safety, check_output_safety
# from services.search_service import execute_web_search
# from services.ai_service import call_gemini_api
from services.safety_filter_service import SafetyFilterService

safety_filter_service = SafetyFilterService()

class GeminiOrchestrator: # 本来は BaseOrchestrator を継承: class GeminiOrchestrator(BaseOrchestrator):
    """
    【チャットAI用】Geminiの処理フローを統括するオーケストレーター
    入力の安全確認 → (必要に応じた)検索ツールの呼び出し → AI生成 → 出力の安全確認 を仕切ります。
    """
    def __init__(self):
        self.safety_service = SafetyFilterService()
        self.orchestrator_name = "GeminiChatFlow"

    def execute(self, user_input: str):
        # 入力チェック
        is_safe, reason = self.safety_service.check_input_safety(user_input)
        if not is_safe:
            return {"status": "error", "message": reason}
        print(f"[{self.orchestrator_name}] 処理を開始します。入力: '{user_input}'")

        try:
            # 1. 入力の安全確認 (Input Safety Check)
            # 悪意のあるプロンプトや不適切な言葉が含まれていないかチェック
            print("  -> Step 1: 入力の安全性を検証中...")
            is_input_safe = self._mock_check_input_safety(user_input)
            if not is_input_safe:
                return {
                    "status": "error",
                    "message": "入力に不適切なコンテンツが含まれているため、処理を中断しました。"
                }

            # 2. 検索ツールの呼び出し (Search Tool Grounding)
            # ユーザーの質問に答えるために最新情報や外部知識が必要か判断して検索
            print("  -> Step 2: 必要な情報を検索中...")
            search_context = self._mock_execute_web_search(user_input)

            # 3. Geminiによるテキスト生成 (AI Generation)
            # 入力文と、検索して得た情報をセットにしてGeminiに渡す
            print("  -> Step 3: Gemini APIを呼び出し中...")
            raw_ai_response = self._mock_call_gemini_api(user_input, search_context)

            # 4. 出力の安全確認 (Output Safety Check)
            # AIが生成した回答が、ハルシネーションや不適切な内容を含んでいないか最終確認
            print("  -> Step 4: AI出力の安全性を検証中...")
            is_output_safe = self._mock_check_output_safety(raw_ai_response)
            if not is_output_safe:
                return {
                    "status": "error",
                    "message": "AIの出力が安全基準を満たさなかったため、回答をブロックしました。"
                }

            # 5. 最終結果の返却
            print(f"[{self.orchestrator_name}] 全フローが正常に完了しました。")
            return {
                "status": "success",
                "response": raw_ai_response,
                "used_context": search_context
            }

        except Exception as e:
            # フロー途中で予期せぬエラーが起きた場合もオーケストレーターがキャッチしてシステムダウンを防ぐ
            print(f"[{self.orchestrator_name}] エラー発生: {e}")
            return {
                "status": "error",
                "message": "システム内部でエラーが発生しました。"
            }


    # ==========================================
    # ※以下は本来 `services/` ディレクトリに切り出される「専門の作業係」のダミー実装です
    # ==========================================
    def _mock_check_input_safety(self, text: str) -> bool:
        # services.safety_filter_service.py の役割
        forbidden_words = ["攻撃", "破壊"]
        return not any(word in text for word in forbidden_words)

    def _mock_execute_web_search(self, query: str) -> str:
        # services.search_service.py の役割
        if "卑弥呼" in query or "歴史" in query:
            return "【検索結果】卑弥呼は邪馬台国の女王であり、魏志倭人伝に記述があります。"
        return "【検索結果】特に追加情報なし"

    def _mock_call_gemini_api(self, prompt: str, context: str) -> str:
        # services.ai_service.py の役割
        return f"提供された情報「{context}」に基づき回答します。ご質問の件については..."

    def _mock_check_output_safety(self, text: str) -> bool:
        # services.safety_filter_service.py の役割
        # PII(個人情報)の漏洩や、不適切な表現がないかチェック
        return True