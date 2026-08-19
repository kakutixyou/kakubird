# backend/services/orchestrator/response_merger.py

from typing import Any, Dict, List

class ResponseMerger:
    """
    AIのレスポンスやデバッグブロックの生成、および複数ハンドラーのレスポンス合成を行うクラス。
    状態（State）を持たない純粋なメソッド群で構成されるため、単体テストが非常に容易です。
    """

    @staticmethod
    def merge_responses(c1: Any, c2: Any) -> Dict[str, Any]:
        """
        2つのレスポンス（競合時など）を1つのレスポンスにマージする。
        """
        if not isinstance(c1, dict):
            c1 = {"message": str(c1), "blocks": []}

        if not isinstance(c2, dict):
            c2 = {"message": str(c2), "blocks": []}

        return {
            "message": c1.get("message", "") + "\n\n---\n\n" + c2.get("message", ""),
            "blocks": c1.get("blocks", []) + c2.get("blocks", [])
        }

    @staticmethod
    def attach_debug_block(content: Any) -> Dict[str, Any]:
        """
        フロントエンドのデータ構造保証（クラッシュ回避）処理。
        文字列などの辞書型以外が来た場合はラップし、blocksキーが無い場合は補完する。
        """
        if not isinstance(content, dict):
            return {
                "message": str(content),
                "blocks": []
            }
        
        if "blocks" not in content:
            content["blocks"] = []

        return content

    @staticmethod
    def build_routing_debug_block(scored_handlers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        ハンドラーのスコアリング結果から、フロントエンド表示用のルーティングデバッグブロックを生成する。
        """
        if not scored_handlers:
            return {}

        top_handler = scored_handlers[0].get("handler")
        selected_name = top_handler.__class__.__name__ if top_handler else "Unknown"
        
        return {
            "type": "RoutingDebugBlock",
            "props": {
                "selected": selected_name,
                "handlers": [
                    {
                        "name": h["handler"].__class__.__name__,
                        "score": h["score"]
                    }
                    for h in scored_handlers
                    if h["score"] > 0
                ]
            }
        }