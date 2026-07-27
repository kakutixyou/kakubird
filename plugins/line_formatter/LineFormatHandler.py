# plugins/line_formatter/LineFormatHandler.py
from typing import Optional, Any
from .LineFormatOrchestrator import LineFormatOrchestrator

class LineFormatHandler:
    def __init__(self):
        self.sub_orchestrator = LineFormatOrchestrator()

    async def calculate_score(self, message: str, signals: dict = None) -> int:
        msg = message.strip()

        # ① 既存：1行整形系のキーワード
        line_keywords = ["改行", "1行", "折り返し"]

        # ② 既存：コード全体の修正・整理系のキーワード
        rewrite_keywords = [
            "正しい形", "正しく書", "全文", "整理したい", "整理して",
            "書き直して", "リライト", "きれいにして", "綺麗にして",
            "修正して", "直して", "フォーマット"
        ]

        # 🆕 ③ 追加：品質チェック・Lint系のキーワード（できることが増えました！）
        lint_keywords = [
            "エラーを探して", "バグ", "PEP8", "ESLint", "Prettier", 
            "最適化して", "リファクタリング", "インデント"
        ]

        has_line_kw = any(k in msg for k in line_keywords)
        has_rewrite_kw = any(k in msg for k in rewrite_keywords)
        has_lint_kw = any(k in msg for k in lint_keywords)

        # コードらしき構造（コードブロック添付や記号密度）も判定材料にする
        looks_like_code_attached = "```" in msg or self._has_code_signature(msg)

        # サブOrchestratorに純粋なフォーマット確信度を聞く
        base = await self.sub_orchestrator.estimate_relevance(message)

        if has_line_kw:
            base = min(100, base + 20)

        if has_lint_kw:
            # 品質チェックの依頼ならかなり高めにスコアをつける
            base = min(100, base + 25)

        # 「整理して」等の言葉＋コードらしき本文がセットで来た場合は強めに優先
        if has_rewrite_kw and looks_like_code_attached:
            base = max(base, 90)  # 確実性が高いので85から90へアップ
        elif has_rewrite_kw:
            # コードの手がかりが薄い場合は少し控えめに
            base = max(base, 60)

        # 🆕 ④ 記憶（Signals/Context）を利用した推論
        # もし直前の会話でファイルを編集中なら、コード整形の文脈である可能性が高い
        if signals and signals.get("active_context"):
            base = min(100, base + 10)

        return base

    def _has_code_signature(self, msg: str) -> bool:
        """
        文字列がプログラムコードっぽいか判定する。
        JS/ReactやPython特有のシグネチャを強化しました。
        """
        symbols = [
            # 汎用・Python
            "{", "}", "def ", "import ", "class ", "return ",
            # 🆕 JS / TS / React 系
            "function", "=>", "const ", "let ", "console.log", 
            "await ", "export ", "<div", "</", "/>"
        ]
        # 記号・予約語が2つ以上含まれていたらコードとみなす
        return sum(1 for s in symbols if s in msg) >= 2

    # 🆕 ⑤ requestからContextManagerを受け取れるように拡張
    async def handle(self, request, ctx: Optional[Any] = None):
        """
        メイン処理。受け取ったメッセージと「脳（ContextManager）」を
        サブOrchestratorに横流しして処理させる。
        """
        message = request.message
        
        # もしrequestの中にContextManagerが埋め込まれていれば取り出す
        context = ctx or getattr(request, "context", None)

        print("⚡ [LineFormatHandler] フォーマット処理を開始します...", flush=True)

        # サブOrchestratorに ContextManager を渡して実行！
        content = await self.sub_orchestrator.route_and_execute(message, ctx=context)
        
        return "ui_code", content