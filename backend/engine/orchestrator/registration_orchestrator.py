from typing import Dict, Any

class RegistrationOrchestrator:
    """
    【ユーザー登録用】ユーザー登録の一連のフローを統括するオーケストレーター。
    入力バリデーション → データベースへの保存 → 歓迎メールの送信 を仕切ります。
    """
    def __init__(self):
        self.orchestrator_name = "RegistrationFlow"
        # 本来はここで各専門サービスを初期化します
        # self.validation_service = ValidationService()
        # self.db_service = DatabaseService()
        # self.email_service = EmailService()

    def execute(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ユーザー登録のメインフローを実行します。
        
        Args:
            registration_data: フロントエンドから送られてきた登録データ（username, email, password など）
        """
        print(f"[{self.orchestrator_name}] ユーザー登録リクエストを受理しました。Email: {registration_data.get('email')}")

        try:
            # 1. 入力チェック (Validation Check)
            # メールアドレスの形式や、パスワードの強度、必須項目の有無を検証
            print("  -> Step 1: 入力データのバリデーションを実行中...")
            is_valid, validation_message = self._mock_validate_input(registration_data)
            if not is_valid:
                print(f"  -> [中断] バリデーション失敗: {validation_message}")
                return {
                    "status": "validation_error",
                    "message": f"入力内容に不備があります: {validation_message}"
                }

            # 2. データベースへの保存 (Database Persistence)
            # 重複チェックを行い、パスワードをハッシュ化して安全に保存
            print("  -> Step 2: データベースへユーザー情報を保存中...")
            db_result = self._mock_save_to_database(registration_data)
            
            if db_result["status"] == "exists":
                print("  -> [中断] 既に登録されているメールアドレスです。")
                return {
                    "status": "already_exists",
                    "message": "このメールアドレスは既に登録されています。"
                }
            
            user_id = db_result["user_id"]
            print(f"  -> データベース保存成功。発行されたUserID: {user_id}")

            # 3. 歓迎メールの送信 (Send Welcome Email)
            # 登録完了を知らせるメールを送信（ここは非同期で裏で走らせる設計にすることもあります）
            print("  -> Step 3: 歓迎メールを送信中...")
            email_sent = self._mock_send_welcome_email(registration_data["email"], registration_data["username"])
            
            if not email_sent:
                # メール送信が失敗しても、DB保存は成功しているので登録自体は完了とするケースが多いです。
                # ただし、ログに警告を残すなどの処理をオーケストレーターが仕切ります。
                print("  -> [警告] 歓迎メールの送信に失敗しました（登録は完了しています）。")
                return {
                    "status": "success_with_warning",
                    "user_id": user_id,
                    "message": "ユーザー登録は完了しましたが、メールの送信に失敗しました。"
                }

            # 4. 最終結果の返却
            print(f"[{self.orchestrator_name}] すべての登録フローが正常に完了しました。")
            return {
                "status": "success",
                "user_id": user_id,
                "message": "ユーザー登録が正常に完了しました。"
            }

        except Exception as e:
            # システムダウン（DB接続エラーなど）をキャッチ
            print(f"[{self.orchestrator_name}] 予期せぬエラーが発生しました: {e}")
            return {
                "status": "system_error",
                "message": "サーバー内部エラーが発生しました。時間を置いて再度お試しください。"
            }


    # 
    # ※以下は本来 `services/` に切り出される専門機能のモックです
    # 
    
    def _mock_validate_input(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """services.validation_service.py の役割"""
        required_fields = ["username", "email", "password"]
        for field in required_fields:
            if not data.get(field):
                return False, f"必須項目 '{field}' が不足しています。"
        
        if "@" not in data["email"]:
            return False, "不正なメールアドレスの形式です。"
            
        if len(data["password"]) < 8:
            return False, "パスワードは8文字以上で設定してください。"
            
        return True, "Valid"

    def _mock_save_to_database(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """services.database_service.py またはリポジトリ層の役割"""
        # 特定のテスト用アドレスのみ重複エラーにするシミュレーション
        if data["email"] == "existing@example.com":
            return {"status": "exists"}
            
        # 実際にはここでパスワードのハッシュ化（bcryptなど）を行い、SQL/ORM等でDBにインサートします
        return {
            "status": "created",
            "user_id": "usr_9988776655443322"
        }

    def _mock_send_welcome_email(self, email: str, username: str) -> bool:
        """services.email_service.py の役割"""
        # 本来はここでSMTPサーバーや外部のメール配信API（SendGridなど）を叩きます
        return True