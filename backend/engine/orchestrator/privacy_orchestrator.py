# backend/engine/orchestrator/privacy_orchestrator.py
"""
PrivacyOrchestrator
===
「プライバシー」に関するユーザーの依頼（個人情報(PII)の検出、GDPR/個人情報保護法への
準拠チェック、データ匿名化、同意管理、データ保持期間の設計など）を、内容に応じて
適切な Handler に振り分ける司令塔です。

■ このファイルの役割
    SecurityOrchestrator と全く同じ設計思想です。
    - route_and_execute() が唯一の入口（BaseOrchestrator の契約）
    - 判断ロジック（どのHandlerに振るか）だけをここに書く
    - 実際の処理（PII検出・匿名化・レポート）はHandlerに丸投げする

■ Handlerの置き場所（想定）
    backend/plugins/privacy_guardian/
        ├── pii_detection_handler.py         … 氏名・住所・メール等の個人情報検出
        ├── gdpr_compliance_handler.py        … GDPR/APPI(個人情報保護法)準拠チェック
        ├── data_anonymization_handler.py     … マスキング・仮名化・匿名化処理の提案/実行
        ├── consent_management_handler.py     … 同意取得フローの設計・レビュー
        └── data_retention_handler.py         … データ保持期間・削除ポリシーの設計

    ※ security_orchestrator.py の plugins/security_auditor/ と対になる構成です。
      「テーマ名のフォルダに、Handlerを機能ごとに1ファイルずつ置く」というルールを
      プロジェクト全体で統一しています。

■ 振り分けルール（HANDLER_KEYWORD_MAP）
    セキュリティと同様、まずはキーワード方式で一次判定します。
    セキュリティと違い、プライバシーは「法令名」もキーワードとして強いシグナルに
    なるので、GDPR / 個人情報保護法 / APPI なども拾えるようにしています。
"""

import logging
from typing import Tuple, Any, Dict, List

from engine.orchestrator.base_orchestrator import BaseOrchestrator
from model.chat_models import ChatRequest, ChatContext

# ===
# ✅ Handlerのインポート（実装ができたらコメントを外してください）
# ===
# from plugins.privacy_guardian.pii_detection_handler import PiiDetectionHandler
# from plugins.privacy_guardian.gdpr_compliance_handler import GdprComplianceHandler
# from plugins.privacy_guardian.data_anonymization_handler import DataAnonymizationHandler
# from plugins.privacy_guardian.consent_management_handler import ConsentManagementHandler
# from plugins.privacy_guardian.data_retention_handler import DataRetentionHandler

logger = logging.getLogger(__name__)


class PrivacyOrchestrator(BaseOrchestrator):
    """
    プライバシー関連リクエストの司令塔。
    BaseOrchestrator を継承しているので route_and_execute() の実装が必須です。
    """

    # ---------------------------------------------------
    # 🔑 判断材料その1: キーワード → Handler名 のマッピング表
    # ---------------------------------------------------
    HANDLER_KEYWORD_MAP: Dict[str, List[str]] = {
        "pii_detection": ["個人情報", "PII", "氏名", "メールアドレス", "電話番号", "マイナンバー"],
        "gdpr_compliance": ["GDPR", "個人情報保護法", "APPI", "コンプライアンス", "準拠", "法令"],
        "data_anonymization": ["匿名化", "仮名化", "マスキング", "anonymize", "pseudonymize"],
        "consent_management": ["同意", "オプトイン", "オプトアウト", "consent", "利用規約"],
        "data_retention": ["保持期間", "削除ポリシー", "retention", "データ削除"],
    }

    def __init__(self, project_root: str = "."):
        super().__init__(project_root=project_root)
        self.last_scan_target: str | None = None

    # =====
    # 🚨 必須実装: route_and_execute
    # =====
    async def route_and_execute(self, request: ChatRequest, **kwargs) -> Tuple[str, Any]:
        self._log_start(task_description=request.message[:30])

        try:
            # ---------------------------------------------
            # STEP 1: どのHandlerに振るかを判定する
            # ---------------------------------------------
            handler_key = self._decide_handler(request.message)

            # ---------------------------------------------
            # STEP 2: 判定結果に応じてHandlerを呼び出す
            # ---------------------------------------------
            if handler_key == "pii_detection":
                self.last_used_handler = "PiiDetectionHandler"
                # response_type, content = await PiiDetectionHandler().handle(request)
                response_type, content = self._not_implemented_yet("PiiDetectionHandler")

            elif handler_key == "gdpr_compliance":
                self.last_used_handler = "GdprComplianceHandler"
                # response_type, content = await GdprComplianceHandler().handle(request)
                response_type, content = self._not_implemented_yet("GdprComplianceHandler")

            elif handler_key == "data_anonymization":
                self.last_used_handler = "DataAnonymizationHandler"
                # response_type, content = await DataAnonymizationHandler().handle(request)
                response_type, content = self._not_implemented_yet("DataAnonymizationHandler")

            elif handler_key == "consent_management":
                self.last_used_handler = "ConsentManagementHandler"
                # response_type, content = await ConsentManagementHandler().handle(request)
                response_type, content = self._not_implemented_yet("ConsentManagementHandler")

            elif handler_key == "data_retention":
                self.last_used_handler = "DataRetentionHandler"
                # response_type, content = await DataRetentionHandler().handle(request)
                response_type, content = self._not_implemented_yet("DataRetentionHandler")

            else:
                # どのキーワードにも当てはまらない場合の汎用フォールバック
                self.last_used_handler = "PrivacyOrchestrator (General Fallback)"
                response_type, content = "text", (
                    "プライバシーに関するご相談ですね。もう少し具体的に、"
                    "「個人情報の検出」「法令への準拠チェック」「データの匿名化」"
                    "「同意管理」「データ保持期間の設計」のどれに近いか教えていただけますか？"
                )

            # ---------------------------------------------
            # STEP 3: 文脈（active_context）を更新
            # ---------------------------------------------
            self._set_context(ChatContext(
                topic="privacy",
                last_handler=self.last_used_handler,
            ))

            self._log_end()
            return response_type, content

        except Exception as e:
            return self._handle_standard_error(e, context_info="PrivacyOrchestrator.route_and_execute")

    # =====
    # 🛠️ 内部ユーティリティ
    # =====
    def _decide_handler(self, message: str) -> str:
        """
        メッセージ本文を見て、HANDLER_KEYWORD_MAP と照合し
        最初にヒットしたHandlerキーを返す。
        """
        for handler_key, keywords in self.HANDLER_KEYWORD_MAP.items():
            for kw in keywords:
                if kw.lower() in message.lower():
                    print(f"🔒 [PrivacyOrchestrator] '{kw}' に反応 → {handler_key}", flush=True)
                    return handler_key
        return "unknown"

    def _not_implemented_yet(self, handler_name: str) -> Tuple[str, str]:
        """Handler未実装のときの仮応答（実装が進んだら削除してください）"""
        return "text", f"（開発中）{handler_name} がまだ実装されていません。次はここを実装しましょう。"