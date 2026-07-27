import uuid
import time
from typing import Dict, Any

class PaymentGatewayError(Exception):
    """決済システムとの通信エラーなどを表すカスタム例外"""
    pass

class PaymentService:
    """
    決済処理を専門に担当するサービス。
    外部API（Stripe, PayPalなど）との通信や、決済特有のビジネスロジックをここに閉じ込めます。
    """
    def __init__(self, api_key: str = "default_dummy_key"):
        self.api_key = api_key
        # 実際の開発では、ここで決済プロバイダのSDKを初期化します
        # 例: stripe.api_key = self.api_key

    def process_payment(self, user_id: str, amount: int, currency: str = "JPY") -> Dict[str, Any]:
        """
        指定された金額で決済を実行します。
        """
        print(f"[PaymentService] ユーザー '{user_id}' に対して {amount}{currency} の決済処理を開始...")

        # 決済金額のバリデーション（ドメインロジック）
        if amount <= 0:
            raise ValueError("決済金額は1以上である必要があります。")

        try:
            # 外部APIとの通信遅延をシミュレート
            time.sleep(1.0) 

            # ========================================================
            # 実際はここで外部APIを叩きます
            # charge = stripe.Charge.create(amount=amount, currency=currency, source=user_id)
            # ========================================================

            # 疑似的なトランザクションIDを生成
            transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
            print(f"[PaymentService] 決済成功: トランザクションID [{transaction_id}]")

            return {
                "status": "success",
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency
            }

        except Exception as e:
            # 外部APIのエラーをキャッチし、システム内で扱いやすい形に変換して投げる
            print(f"[PaymentService] 決済プロバイダとの通信でエラー発生: {e}")
            raise PaymentGatewayError(f"決済処理に失敗しました: {str(e)}")

    def refund_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        決済のキャンセル（返金）を実行します。
        """
        print(f"[PaymentService] トランザクション [{transaction_id}] の返金処理を開始...")
        
        time.sleep(0.5) # 通信遅延のシミュレート

        print(f"[PaymentService] 返金完了")
        return {
            "status": "refunded",
            "transaction_id": transaction_id
        }