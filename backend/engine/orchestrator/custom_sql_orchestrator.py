import logging
from typing import Tuple, Any

# =========================================================
# 親クラス（ルールブック）とデータモデルのインポート
# =========================================================
from engine.orchestrator.base_orchestrator import BaseOrchestrator
from model.chat_models import ChatRequest

# =========================================================
# 各専門サービス（AI呼び出し・評価）のインポート
# ※パスは実際のプロジェクト構成に合わせてください
# =========================================================
from sql_builder_v2.backend_sql_v2.api_sql_v2.ai.custom_ai import run_custom_ai
from sql_builder_v2.backend_sql_v2.api_sql_v2.ai.claude_ai import run_claude_ai
from sql_builder_v2.backend_sql_v2.api_sql_v2.ai.judge import evaluate_response

logger = logging.getLogger(__name__)

class CustomSqlOrchestrator(BaseOrchestrator):
    """
    【SQL Builder用】データベースのスキーマに沿った安全なSQLを生成するオーケストレーター。
    [初回生成] → [安全性・品質評価] → [リトライ生成] → [Claudeフォールバック] の多段フローを仕切ります。
    """
    
    def __init__(self, project_root: str = "."):
        # BaseOrchestrator の初期化処理を呼び出し、共通の変数（名前やコンテキスト）をセットアップ
        super().__init__(project_root)
        self.orchestrator_name = "CustomSqlFlow"

    async def route_and_execute(self, request: ChatRequest, **kwargs) -> Tuple[str, Any]:
        """
        [必須実装] SQL生成のメインフローを実行します。
        """
        self._log_start(f"SQL生成フロー開始 (入力: {request.message[:20]}...)")
        
        # 最終的なハンドラー名を追跡するための初期値
        self.last_used_handler = "Custom AI (Primary)"

        try:
            # ====================================================
            # Step 1: 初回のSQL生成
            # ====================================================
            self._log_start("Step 1: Custom AIによる初回SQL生成")
            custom_result = await run_custom_ai(request)
            
            # APIのレスポンスが辞書型か文字列か吸収する
            reply = custom_result.get("reply", "") if isinstance(custom_result, dict) else custom_result
            
            # ====================================================
            # Step 2: 生成されたSQLの評価（Judge）
            # ====================================================
            quality = evaluate_response(reply)
            logger.info(f"[{self.orchestrator_name}] 初回評価結果: {quality}")

            if quality == "good":
                self._log_end("初回生成で成功")
                return "text", reply

            if quality == "danger":
                # DROP TABLEなどの危険なコマンドが含まれていた場合は即座にブロック
                self.last_used_handler = "Safety Validator"
                logger.warning(f"[{self.orchestrator_name}] 危険なSQLを検知しました。処理をブロックします。")
                return "error", "安全でないSQL（破壊的なコマンド等）が検出されたため、実行をブロックしました。"

            # ====================================================
            # Step 3: 品質が不足している場合（"bad"等）のリトライ処理
            # ====================================================
            self._log_start("Step 3: スキーマ指定を強化してリトライ実行")
            self.last_used_handler = "Custom AI (Retry)"
            
            # プロンプトに強制的な制約を書き加えて再リクエスト
            original_message = request.message
            request.message = f"{original_message}（スキーマに沿った正しいSQLのみを出力してください）"
            
            retry_result = await run_custom_ai(request)
            retry_reply = retry_result.get("reply", "") if isinstance(retry_result, dict) else retry_result

            if evaluate_response(retry_reply) == "good":
                self._log_end("リトライ生成で成功")
                return "text", retry_reply

            # ====================================================
            # Step 4: Claudeへのフォールバック（最終手段）
            # ====================================================
            self._log_start("Step 4: Custom AIが失敗したため、Claude 3にフォールバックします")
            self.last_used_handler = "Claude AI (Fallback)"
            
            # リクエストメッセージを元に戻す（Claude用のプロンプトで再構成される想定）
            request.message = original_message 
            
            claude_reply = await run_claude_ai(request)
            if claude_reply:
                # Claudeのレスポンスも文字列抽出する
                final_reply = claude_reply.get("reply", "") if isinstance(claude_reply, dict) else claude_reply
                self._log_end("Claudeフォールバックで成功")
                return "text", final_reply

            # 全ての手段が失敗した場合
            self.last_used_handler = "System (All Failed)"
            return "error", "AIによるSQLの生成と修正に失敗しました。質問を少し具体的に変えてみてください。"

        except Exception as e:
            # ====================================================
            # Step 5: 予期せぬエラー（APIダウン等）は基底クラスに任せる
            # ====================================================
            # BaseOrchestrator の _handle_standard_error を呼ぶことで、
            # DebugOrchestrator が後から解析しやすい形に整形されて返されます。
            return self._handle_standard_error(e, context_info=f"Request Msg: {request.message}")