# backend/services/orchestrator/handler_scorer.py

import os
import json
import inspect
import traceback
from typing import List, Dict, Any

class HandlerScorer:
    """
    各ハンドラー（ChatHandler, HTMLHandlerなど）が、
    現在のユーザーのメッセージやシグナルに対してどの程度適しているかをスコアリングするクラス。
    """
    def __init__(self, feedback_file: str):
        self.feedback_file = feedback_file

    async def score_all(self, handlers: List[Any], message: str, current_signals: dict, intent_analysis: Any = None) -> List[Dict[str, Any]]:
        """
        全てのハンドラーのスコアを計算し、降順（スコアが高い順）にソートして返す。
        """
        scored_handlers = []

        for handler in handlers:
            handler_name = handler.__class__.__name__

            try:
                base_score = await self._calculate(handler, message, current_signals, intent_analysis)
            except Exception:
                print(f"❌ {handler_name} のscore計算で例外が発生しました")
                traceback.print_exc()
                base_score = 0

            bonus = self._get_feedback_bonus(handler_name)
            final_score = base_score + bonus

            # ハンドラーごとの推定サイズ（トークン数など）を取得。未定義なら1000とする。
            estimated_size = getattr(
                handler,
                "estimate_size",
                lambda msg: 1000
            )(message)

            print(
                f"🔎 {handler_name}"
                f" -> ベース:{base_score}"
                f" 補正:{bonus}"
                f" 最終:{final_score}"
            )

            scored_handlers.append({
                "handler": handler,
                "score": final_score,
                "size": estimated_size
            })

        # スコア順に並び替え (降順)
        scored_handlers.sort(key=lambda h: h["score"], reverse=True)
        return scored_handlers

    async def _calculate(self, handler: Any, message: str, current_signals: dict, intent_analysis: Any) -> int:
        """
        ハンドラーの実装に合わせて動的に引数を変えてスコア計算メソッドを呼び出す。
        """
        if hasattr(handler, "calculate_score"):
            sig = inspect.signature(handler.calculate_score)
            param_count = len(sig.parameters)

            # 引数の数に応じて呼び出し方を切り替える（後方互換性の確保）
            if param_count >= 3:
                # 最新仕様: intent_analysis まで受け取れるハンドラー
                return await handler.calculate_score(message, current_signals, intent_analysis)
            elif param_count == 2:
                # 従来仕様: current_signals まで受け取れるハンドラー
                return await handler.calculate_score(message, current_signals)
            else:
                # 最も古い仕様: message のみ
                return await handler.calculate_score(message)

        # calculate_score がなく、can_handle のみ実装されている場合のフォールバック
        if hasattr(handler, "can_handle"):
            can_handle = await handler.can_handle(message)
            return 100 if can_handle else 0
            
        return 0

    def _get_feedback_bonus(self, handler_name: str) -> int:
        """
        過去のユーザーフィードバック（いいね/悪いね）に基づいたボーナススコアを取得する。
        """
        try:
            if not os.path.exists(self.feedback_file):
                return 0

            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            bonus = data.get(handler_name, 0)
            return int(bonus)
        except Exception:
            return 0