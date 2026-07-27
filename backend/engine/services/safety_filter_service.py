import re
from typing import Tuple, List

class SafetyFilterService:
    print("[SafetyFilterService] サービスが初期化されました。")
    """
    入出力テキストの安全性を検証する専門サービス。
    NGワードのチェックや、個人情報（PII）のパターン検知などを担当します。
    """
    def __init__(self):
        # 実際の運用ではデータベースや外部の設定ファイルから読み込むことが多いです
        self.banned_words: List[str] = [
            "ハッキング", "爆弾の作り方", "差別的な発言のダミー"
        ]
        
        # 簡易的な個人情報（PII）検知用の正規表現
        # 例: クレジットカード番号っぽい16桁の数字を検知
        self.credit_card_pattern = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
        # 例: 日本のマイナンバー（12桁の数字）の簡易検知
        self.mynumber_pattern = re.compile(r'\b\d{12}\b')

    def check_input_safety(self, text: str) -> Tuple[bool, str]:
        """
        ユーザーからの入力（プロンプト）が安全かどうかを判定します。
        
        Returns:
            Tuple[bool, str]: (安全かどうかの真偽値, ブロックされた場合の理由)
        """
        print("[SafetyFilterService] 入力テキストの安全性を検証中...")

        # 1. NGワードチェック（プロンプトインジェクション対策など）
        for word in self.banned_words:
            if word in text:
                print(f"[SafetyFilterService] 警告: NGワード '{word}' を検知しました。")
                return False, "ポリシーに違反する単語が含まれています。"

        # 2. 外部APIを用いた高度な判定（モック）
        # 実際にはここで Google Perspective API などを呼び出して有害度スコアを測ることもあります
        # if self._call_external_moderation_api(text) > 0.8:
        #     return False, "有害なコンテンツと判定されました。"

        return True, "OK"

    def check_output_safety(self, text: str) -> Tuple[bool, str]:
        """
        AIが生成した出力が安全かどうかを判定します。
        主にハルシネーションによる個人情報の漏洩などを防ぎます。
        
        Returns:
            Tuple[bool, str]: (安全かどうかの真偽値, ブロックされた場合の理由)
        """
        print("[SafetyFilterService] AI出力テキストの安全性を検証中...")

        # 1. 個人情報（PII）の漏洩チェック
        if self.credit_card_pattern.search(text):
            print("[SafetyFilterService] 警告: クレジットカード番号のような文字列を検知しました。")
            return False, "機密情報が含まれている可能性があるため、出力をブロックしました。"

        if self.mynumber_pattern.search(text):
            print("[SafetyFilterService] 警告: マイナンバーのような文字列を検知しました。")
            return False, "機密情報が含まれている可能性があるため、出力をブロックしました。"

        # 2. 出力結果に対するNGワードチェック（AIが不適切な言葉を生成していないか）
        for word in self.banned_words:
            if word in text:
                print(f"[SafetyFilterService] 警告: AIがNGワード '{word}' を生成しました。")
                return False, "不適切なコンテンツが生成されたため、出力をブロックしました。"

        return True, "OK"