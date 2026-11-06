# backend/api/services/handlers/MathHandler/handler.py
import logging
import time
from typing import Any, Dict, Optional, Tuple
import json

from api.services.handlers.base_handler import BaseHandler

# 分割した各モジュールから関数やクラスをインポート
from .routing_rules import must_yield_to_another_handler, recommended_handler
from .extract import (
    message_text, 
    extract_message, 
    extract_signals, 
    normalized_signal, 
    Extractor
)
from .result_normalizer import (
    result_to_dict,
    error_data,
    error_from_exception,
    contains_error
)

# 実際の処理を行うスタッフたち
from .exchange_service import ExchangeService
from .calculator import Calculator
# 追加実装した専門ソルバーをインポート（ファイルが存在する前提）
from .base_converter import FractionBaseConverter
from .logic_solver import LogicSolver

logger = logging.getLogger(__name__)

class MathHandlerConfigurationError(RuntimeError):
    """MathHandler の設定や構成に問題がある場合に送出されます"""
    pass


class MathHandler(BaseHandler):
    """Stable entry point for calculations selected by ChatOrchestrator."""
    HANDLER_NAME = "MathHandler"
    RESULT_TYPE = "math"
    MAX_SCORE = 100

    def __init__(self, enable_debug: bool = False, base_handler_kwargs: Optional[Dict[str, Any]] = None):
        base_kwargs = dict(base_handler_kwargs or {})
        try:
            super().__init__(**base_kwargs)
        except TypeError:
            if base_kwargs:
                raise
            logger.debug("BaseHandler.__init__ was skipped for legacy compatibility")

        self.enable_debug = enable_debug
        
        # スタッフのインスタンス化
        self.extractor = Extractor()
        self.exchange = ExchangeService()
        self.calculator = Calculator()
        # 追加スタッフのインスタンス化
        self.base_converter = FractionBaseConverter()
        self.logic_solver = LogicSolver()
        
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_score: int = 0

    async def calculate_score(self, message: str, current_signals: Optional[dict] = None) -> int:
        text = message_text(message)
        signals = dict(current_signals or {})
        
        # 1. IntentInspectorからの強制指定(forced_handler)を最優先する
        forced = normalized_signal(signals.get("forced_handler"))
        if forced in {"mathhandler", "math_handler", "math"}:
            self.last_score = self.MAX_SCORE
            return self.MAX_SCORE

        # 2. プログラミングなどの別ハンドラの領分なら0点を返す
        if not text or must_yield_to_another_handler(text, current_signals):
            self.last_score = 0
            return 0

        # 3. 会話的意図（教えて、謎など）があるかチェックし、LLM(ChatHandler)に譲る
        intent = signals.get("intent") or getattr(self, "intent_inspector_result", {}).get("intent")
        conversational_keywords = ["教えて", "謎", "理由", "とは", "について", "語って"]
        
        if intent == "knowledge_question" or any(k in text for k in conversational_keywords):
            self.last_score = 10
            return 10

        # 🌟 4. 数式・為替・基数変換・論理演算のいずれかが含まれているか判定
        extracted = self.extractor.extract(text)
        if (extracted.is_currency_conversion or 
            extracted.formula or 
            extracted.is_base_conversion or 
            extracted.is_logic_expression):
            self.last_score = self.MAX_SCORE
            return self.MAX_SCORE

        # 5. 上記どれにも当てはまらない単なるテキストは0点
        self.last_score = 0
        return 0

    async def can_handle(self, message: str, current_signals: Optional[dict] = None) -> bool:
        return await self.calculate_score(message, current_signals) > 0

    def estimate_size(self, message: str) -> int:
        length = len(message_text(message))
        return min(1024, max(256, length * 4))

    def get_name(self) -> str:
        return self.HANDLER_NAME or "MathHandler"

    async def handle(self, request: Any) -> Tuple[str, Dict[str, Any]]:
        """現場監督として、各スタッフに指示を出して処理を進める"""
        started = time.perf_counter()
        
        expression = extract_message(request)
        current_signals = extract_signals(request)

        if not expression:
            data = error_data(
                code="empty_expression",
                message="計算式が空です。",
                expression=expression,
                handler_name=self.get_name()
            )
            return self._finish(data, started)

        if must_yield_to_another_handler(expression, current_signals):
            data = error_data(
                code="math_handler_not_applicable",
                message="この依頼はMathHandlerの対象ではありません。",
                expression=expression,
                handler_name=self.get_name()
            )
            data.setdefault("metadata", {})["recommended_handler"] = recommended_handler(expression)
            return self._finish(data, started)

        try:
            # 1. 抽出
            extracted_data = self.extractor.extract(expression)

            # 🌟 空ブロック判定に新しい要素（基数変換・論理演算）を追加
            if not (extracted_data.is_currency_conversion or 
                    extracted_data.formula or 
                    extracted_data.is_base_conversion or 
                    extracted_data.is_logic_expression):
                data = error_data(
                    code="invalid_math_expression",
                    message="有効な数式・演算式を検出できませんでした。",
                    expression=expression,
                    handler_name=self.get_name()
                )
                return self._finish(data, started)

            # 🌟 2. 各専用ソルバーへのルーティング
            if extracted_data.is_logic_expression:
                # 論理演算モジュールへ渡す
                raw_result = self.logic_solver.evaluate_expression(
                    extracted_data.logic_formula, 
                    extracted_data.variables
                )
                logger.info(f"🧮 論理演算完了: {extracted_data.logic_formula}")
                
            elif extracted_data.is_base_conversion:
                # 基数変換モジュールへ渡す
                raw_result = self.base_converter.convert_base(
                    value=extracted_data.raw_value,
                    from_base=extracted_data.source_base,
                    to_base=extracted_data.target_base
                )
                logger.info(f"🧮 基数変換完了: {extracted_data.raw_value}({extracted_data.source_base}進数) -> {extracted_data.target_base}進数")

            elif extracted_data.is_currency_conversion:
                # 為替モジュールへ渡す
                rate = await self.exchange.get_rate(
                    base=extracted_data.base_currency, 
                    target=extracted_data.target_currency
                )
                raw_result = self.calculator.convert_currency(extracted_data.amount, rate)
                logger.info(f"🧮 為替計算完了: {extracted_data.amount}{extracted_data.base_currency} -> {raw_result}{extracted_data.target_currency} (レート: {rate})")
                
            else:
                # 従来の数式評価モジュールへ渡す
                raw_result = self.calculator.evaluate_expression(extracted_data.formula)
                logger.info(f"🧮 計算完了: {extracted_data.formula} = {raw_result}")

            # 3. 辞書化（各ソルバーがDataClassやDictを返した場合も対応できるよう result_to_dict 側で吸収する想定）
            data = result_to_dict(raw_result)
            data.setdefault("success", not contains_error(data))
            data.setdefault("expression", expression)
            
        except Exception as exc:
            if self.enable_debug:
                raise
            logger.warning("MathHandler execution failed: %s", exc)
            data = error_from_exception(exc, expression, handler_name=self.get_name())

        return self._finish(data, started)

    def _finish(self, data: Dict[str, Any], started: float) -> Tuple[str, Dict[str, Any]]:
        """結果に処理時間やハンドラ名などの共通メタデータを付与して返す"""
        duration_ms = (time.perf_counter() - started) * 1_000
        
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            
        metadata.setdefault("handler", self.get_name())
        data["metadata"] = metadata
        data.setdefault("duration_ms", round(duration_ms, 3))
        
        # データの消失を防ぐ「密輸」処理
        data["content"] = json.dumps(data, ensure_ascii=False)
        data["message"] = json.dumps(data, ensure_ascii=False)
        
        self.last_result = data
        return self.RESULT_TYPE, data
