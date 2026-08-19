# backend/engine/orchestrator/security_orchestrator.py
"""
SecurityOrchestrator
===
「セキュリティ」に関するユーザーの依頼（脆弱性チェック、認証まわりのレビュー、
シークレット漏洩チェック、依存パッケージの監査など）を、内容に応じて
適切な Handler に振り分ける司令塔です。

■ このファイルの役割
    - route_and_execute() が唯一の入口（BaseOrchestrator の契約）
    - 「何をHandlerに振るか」の判断ロジックだけをここに書く
    - 実際の重い処理（スキャン・診断・レポート生成）は各Handlerに丸投げする
      → Orchestratorを「太らせない」のがポイントです

■ Handlerの置き場所（想定）
    backend/plugins/security_auditor/
        ├── vulnerability_scan_handler.py   … コードの脆弱性スキャン
        ├── auth_check_handler.py           … 認証・認可ロジックのレビュー
        ├── secrets_scan_handler.py         … APIキー/パスワード等のハードコード検出
        ├── dependency_audit_handler.py     … requirements.txt / package.json の脆弱性監査
        └── security_report_handler.py      … 上記の結果をまとめたレポート生成

    ※ chat_orchestrator.py が plugins/project_builder/ChatHandler.py を
      呼んでいるのと同じ関係性です。Orchestrator 1つに対して
      Handlerは複数（テーマごとに1ファイル）という構成にしています。

■ 振り分けルール（HANDLER_KEYWORD_MAP）
    ユーザーの発話（request.message）に含まれるキーワードで一次判定します。
    将来的にはLLMによる意図分類（intent classification）に差し替えてもOKですが、
    最初はキーワード方式のほうがデバッグしやすく、判断材料の量産にも向いています。
"""

import logging
from typing import Tuple, Any, Dict, List

from engine.orchestrator.base_orchestrator import BaseOrchestrator
from model.chat_models import ChatRequest, ChatContext

# ===
# ✅ Handlerのインポート（実装ができたらコメントを外してください）
# ===
# from plugins.security_auditor.vulnerability_scan_handler import VulnerabilityScanHandler
# from plugins.security_auditor.auth_check_handler import AuthCheckHandler
# from plugins.security_auditor.secrets_scan_handler import SecretsScanHandler
# from plugins.security_auditor.dependency_audit_handler import DependencyAuditHandler
# from plugins.security_auditor.security_report_handler import SecurityReportHandler

logger = logging.getLogger(__name__)


class SecurityOrchestrator(BaseOrchestrator):
    """
    セキュリティ関連リクエストの司令塔。
    BaseOrchestrator を継承しているので route_and_execute() の実装が必須です。
    """

    # ---------------------------------------------------
    # 🔑 判断材料その1: キーワード → Handler名 のマッピング表
    # ---------------------------------------------------
    # ここに新しいHandlerを追加するときは、
    # 1. 上のimport文を追加
    # 2. このMAPにキーワードとHandler名を追記
    # の2ステップだけでOKになるように設計してあります。
    HANDLER_KEYWORD_MAP: Dict[str, List[str]] = {
        "vulnerability_scan": ["脆弱性", "vulnerability", "CVE", "エクスプロイト", "exploit"],
        "auth_check": ["認証", "認可", "login", "auth", "権限", "JWT", "セッション"],
        "secrets_scan": ["APIキー", "シークレット", "秘密鍵", "パスワード漏洩", "secret", "token 漏洩"],
        "dependency_audit": ["依存関係", "パッケージ", "requirements.txt", "package.json", "npm audit", "pip audit"],
        "security_report": ["セキュリティレポート", "監査結果", "診断結果まとめ"],
    }

    def __init__(self, project_root: str = "."):
        super().__init__(project_root=project_root)
        # このOrchestrator専用の状態があればここに追加
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
            #   ※ 実装済みのHandlerのみ動く状態にしています。
            #     未実装のものは「準備中です」を返すダミー応答になります。
            # ---------------------------------------------
            if handler_key == "vulnerability_scan":
                self.last_used_handler = "VulnerabilityScanHandler"
                # response_type, content = await VulnerabilityScanHandler().handle(request)
                response_type, content = self._not_implemented_yet("VulnerabilityScanHandler")

            elif handler_key == "auth_check":
                self.last_used_handler = "AuthCheckHandler"
                # response_type, content = await AuthCheckHandler().handle(request)
                response_type, content = self._not_implemented_yet("AuthCheckHandler")

            elif handler_key == "secrets_scan":
                self.last_used_handler = "SecretsScanHandler"
                # response_type, content = await SecretsScanHandler().handle(request)
                response_type, content = self._not_implemented_yet("SecretsScanHandler")

            elif handler_key == "dependency_audit":
                self.last_used_handler = "DependencyAuditHandler"
                # response_type, content = await DependencyAuditHandler().handle(request)
                response_type, content = self._not_implemented_yet("DependencyAuditHandler")

            elif handler_key == "security_report":
                self.last_used_handler = "SecurityReportHandler"
                # response_type, content = await SecurityReportHandler().handle(request)
                response_type, content = self._not_implemented_yet("SecurityReportHandler")

            else:
                # どのキーワードにも当てはまらない場合の汎用フォールバック
                self.last_used_handler = "SecurityOrchestrator (General Fallback)"
                response_type, content = "text", (
                    "セキュリティに関するご相談ですね。もう少し具体的に、"
                    "「脆弱性チェック」「認証の見直し」「APIキー漏洩の確認」"
                    "「依存パッケージの監査」のどれに近いか教えていただけますか？"
                )

            # ---------------------------------------------
            # STEP 3: 文脈（active_context）を更新
            # ---------------------------------------------
            self._set_context(ChatContext(
                topic="security",
                last_handler=self.last_used_handler,
            ))

            self._log_end()
            return response_type, content

        except Exception as e:
            return self._handle_standard_error(e, context_info="SecurityOrchestrator.route_and_execute")

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
                    print(f"🛡️ [SecurityOrchestrator] '{kw}' に反応 → {handler_key}", flush=True)
                    return handler_key
        return "unknown"

    def _not_implemented_yet(self, handler_name: str) -> Tuple[str, str]:
        """Handler未実装のときの仮応答（実装が進んだら削除してください）"""
        return "text", f"（開発中）{handler_name} がまだ実装されていません。次はここを実装しましょう。"