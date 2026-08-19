from typing import Dict, Any, List
import traceback

# 本来は以下のカスタム例外やサービスを services/ ディレクトリからインポートします
# from services.payment_service import PaymentService, PaymentGatewayError
# from services.inventory_service import InventoryService, OutOfStockError
# from services.shipping_service import ShippingService
# from services.email_service import EmailService

# --- モック用のカスタム例外 ---
class PaymentGatewayError(Exception): pass
class OutOfStockError(Exception): pass

class OrderOrchestrator:
    """
    【ECサイト用】注文確定のフローを統括するオーケストレーター。
    在庫の確保 → 決済 → 配送手配 → 完了メール送信 を仕切り、
    途中で失敗した場合は、必要に応じて在庫の解放や返金（ロールバック）を行います。
    """
    def __init__(self):
        self.orchestrator_name = "OrderCheckoutFlow"
        # 各専門サービスを初期化（ここでは概念としてコメントアウト）
        # self.inventory_service = InventoryService()
        # self.payment_service = PaymentService()
        # self.shipping_service = ShippingService()
        # self.email_service = EmailService()

    def execute_checkout(self, user_id: str, cart_items: List[Dict[str, Any]], shipping_address: str) -> Dict[str, Any]:
        """
        注文確定のメインフローを実行します。
        """
        print(f"[{self.orchestrator_name}] ユーザー '{user_id}' のチェックアウト処理を開始します。")
        
        # 処理中に確保したリソースを追跡するための変数（ロールバック用）
        reserved_items = []
        transaction_id = None

        try:
            # 
            # 1. 在庫の確認と確保 (Inventory Reservation)
            # 
            print("  -> Step 1: 在庫を確認・確保しています...")
            total_amount = 0
            for item in cart_items:
                # 在庫引当処理
                self._mock_reserve_inventory(item["item_id"], item["quantity"])
                reserved_items.append(item)
                total_amount += item["price"] * item["quantity"]
            
            print(f"  -> 在庫確保完了。合計金額: {total_amount}円")

            # 
            # 2. 決済処理 (Payment Processing)
            # 
            print("  -> Step 2: 決済システムと通信しています...")
            try:
                payment_result = self._mock_process_payment(user_id, total_amount)
                transaction_id = payment_result["transaction_id"]
                print(f"  -> 決済完了。トランザクションID: {transaction_id}")
            except PaymentGatewayError as e:
                print(f"  -> [エラー] 決済に失敗しました: {e}")
                # 決済失敗: 確保した在庫を解放（ロールバック）して終了
                self._rollback_inventory(reserved_items)
                return {
                    "status": "payment_failed",
                    "message": "クレジットカードの決済に失敗しました。カード情報をご確認ください。"
                }

            # 
            # 3. 配送手配 (Shipping Arrangement)
            # 
            print("  -> Step 3: 倉庫へ配送指示を出しています...")
            try:
                tracking_number = self._mock_arrange_shipping(user_id, cart_items, shipping_address)
                print(f"  -> 配送手配完了。追跡番号: {tracking_number}")
            except Exception as e:
                print(f"  -> [エラー] 配送システムで障害発生: {e}")
                # 配送手配失敗: 決済の取り消し（返金）と、在庫の解放（ロールバック）を行って終了
                self._rollback_payment(transaction_id)
                self._rollback_inventory(reserved_items)
                return {
                    "status": "shipping_failed",
                    "message": "配送システムの連携に失敗しました。注文は取り消され、課金はされません。"
                }

            # 
            # 4. 注文完了メールの送信 (Send Confirmation Email)
            # 
            print("  -> Step 4: 注文完了メールを送信しています...")
            # メール送信が失敗しても、注文自体は成立しているのでロールバックはしない
            email_sent = self._mock_send_email(user_id, transaction_id, tracking_number)
            if not email_sent:
                print("  -> [警告] メールの送信に失敗しましたが、注文処理は完了とします。")

            # 
            # 5. 最終結果の返却
            # 
            print(f"[{self.orchestrator_name}] 全ての注文処理が正常に完了しました。")
            return {
                "status": "success",
                "transaction_id": transaction_id,
                "tracking_number": tracking_number,
                "message": "ご注文ありがとうございます。商品の到着をお待ちください。"
            }

        except OutOfStockError as e:
            # 確保途中で在庫切れが発覚した場合
            print(f"[{self.orchestrator_name}] 在庫切れエラー: {e}")
            self._rollback_inventory(reserved_items)
            return {
                "status": "out_of_stock",
                "message": "申し訳ありません。カート内の一部商品が売り切れとなりました。"
            }
        except Exception as e:
            # 予期せぬシステムダウン時の最終安全網
            print(f"[{self.orchestrator_name}] 致命的なシステムエラー発生: {e}")
            traceback.print_exc()
            # 可能な限りのロールバックを試みる
            if transaction_id:
                self._rollback_payment(transaction_id)
            if reserved_items:
                self._rollback_inventory(reserved_items)
            return {
                "status": "system_error",
                "message": "システムエラーが発生しました。注文が完了していない可能性があります。"
            }

    # 
    # 🚨 ロールバック（補償）メソッド
    # 
    def _rollback_inventory(self, items: List[Dict[str, Any]]):
        """確保した在庫を元に戻す処理"""
        if not items:
            return
        print(f"  [Rollback] {len(items)}件の商品の在庫確保を取り消します...")
        for item in items:
            # self.inventory_service.release_inventory(item["item_id"], item["quantity"])
            print(f"    - 商品ID: {item['item_id']} の在庫を戻しました。")

    def _rollback_payment(self, transaction_id: str):
        """完了した決済をキャンセル（返金）する処理"""
        if not transaction_id:
            return
        print(f"  [Rollback] トランザクション [{transaction_id}] の返金処理を実行します...")
        # self.payment_service.refund_payment(transaction_id)
        print("    - 返金処理が完了しました。")


    # 
    # ※以下は本来 `services/` に切り出される専門機能のモックです
    # 
    def _mock_reserve_inventory(self, item_id: str, quantity: int):
        if item_id == "item_out_of_stock":
            raise OutOfStockError(f"商品 {item_id} は在庫が足りません。")
        return True

    def _mock_process_payment(self, user_id: str, amount: int) -> Dict[str, Any]:
        # テストとして、1万円を超える決済はカードが弾かれたことにする
        if amount > 10000:
            raise PaymentGatewayError("クレジットカードの利用限度額を超えています。")
        return {"transaction_id": "txn_abcdef123456"}

    def _mock_arrange_shipping(self, user_id: str, items: list, address: str) -> str:
        # 倉庫システム（WMS）のAPIを叩く想定
        return "TRK-987654321JP"

    def _mock_send_email(self, user_id: str, txn_id: str, tracking_num: str) -> bool:
        return True