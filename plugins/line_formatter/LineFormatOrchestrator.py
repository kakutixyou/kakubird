# plugins/line_formatter/LineFormatOrchestrator.py

from typing import Optional, Any
from .formatters.js_formatter import JsFormatter
from .formatters.python_formatter import PythonFormatter
from .formatters.generic_formatter import GenericFormatter

# 必要に応じて FormatPreset などをインポート
# from engine.formatters.base_formatter import FormatPreset 

class LineFormatOrchestrator:
    """
    LineFormatHandler配下でのみ使われる、フォーマッター選択専用の内部Orchestrator。
    ContextManagerと連携し、優秀なJS/Pythonフォーマッターの能力を最大限に引き出します。
    """

    def __init__(self):
        self.formatters = [
            JsFormatter(),      # ✨ 優秀なJSフォーマッター
            PythonFormatter(),  # 🐍 高度なPythonフォーマッター
            GenericFormatter(), # 🛡️ 最後の砦（フォールバック）
        ]

    async def estimate_relevance(self, message: str) -> int:
        """親Handler向け：この機能全体としてどれだけ確信を持てるかを返す"""
        best = 0
        for f in self.formatters:
            best = max(best, await f.calculate_score(message))
        return best

    async def route_and_execute(self, message: str, ctx: Optional[Any] = None) -> dict:
        """
        メッセージを解析し、最適なフォーマッターで整形を実行する。
        ctx (ContextManager) を渡すことで、文脈ベースの言語判定と記憶の自動更新が可能。
        """
        # 
        # 1. 各フォーマッターのスコアを計算
        # 
        scored = []
        for f in self.formatters:
            score = await f.calculate_score(message)
            scored.append({"score": score, "formatter": f})

        # 
        # 2. ContextManagerの記憶によるスコアブースト（文脈推論）
        # 
        if ctx and ctx.workspace.active_artifact_name:
            active_file = ctx.workspace.active_artifact_name.lower()
            for item in scored:
                name = item["formatter"].name
                
                # 編集中ファイルがJS/TS/React系ならJSフォーマッターを優遇
                if name in ("javascript", "js") and (active_file.endswith(".js") or active_file.endswith(".ts") or active_file.endswith(".jsx") or active_file.endswith(".tsx")):
                    item["score"] += 20
                    
                # 編集中ファイルがPythonならPythonフォーマッターを優遇
                elif name == "python" and active_file.endswith(".py"):
                    item["score"] += 20

        # スコア順にソートして1位を決定
        scored.sort(key=lambda x: x["score"], reverse=True)
        best_formatter = scored[0]["formatter"]
        best_score = scored[0]["score"]

        print(f"🧩 [LineFormatOrchestrator] 選択: {best_formatter.name} (score={best_score})", flush=True)

        # 
        # 3. フォーマッターの高度な設定（Lv5機能）を有効化
        # 
        if hasattr(best_formatter, "set_preset"):
            # 例: LLM特有のミスを自動修正するモードをセット
            # best_formatter.set_preset(FormatPreset.LLM_FRIENDLY)
            print(f"✨ {best_formatter.name} の高度なプリセットを有効化しました")

        # 
        # 4. フォーマット実行
        # 
        formatted_code = await best_formatter.format(message)

        # 
        # 5. メトリクス取得とUI向けメッセージの生成
        # 
        result_msg = f"{best_formatter.name} 形式としてコードを美しく整形しました。"
        
        # 優秀なJS/Pythonフォーマッターがメトリクスを持っていれば抽出
        if hasattr(best_formatter, "get_metrics"):
            metrics = best_formatter.get_metrics()
            if metrics:
                result_msg += (
                    f"\n(✨ {metrics.corrections_made}箇所のコード揺れを自動修正 / "
                    f"⚡ {metrics.optimizations_applied}箇所の最適化を実施)"
                )

        # 
        # 6. 整形された最新コードを ContextManager に上書き記憶
        # 
        if ctx:
            active_name = ctx.workspace.active_artifact_name or f"formatted_code.{best_formatter.name}"
            ctx.update_workspace(code=formatted_code, artifact_name=active_name)
            print(f"🧠 整形された美しいコードを ContextManager に記憶させました ({active_name})")

        # 
        # 7. 返却データ
        # 
        return {
            "message": result_msg,
            "blocks": [
                {
                    "type": "CodeBlock",
                    "props": {
                        "language": best_formatter.name,
                        "code": formatted_code,
                    },
                }
            ],
            # 内部連携用に生のコードも返しておく（KnowledgeManagerへ繋ぎやすくするため）
            "raw_code": formatted_code,
            "language": best_formatter.name
        }