"""
backend/engine/orchestrator/chat_orchestrator/routing_dispatcher.py

Forced Handler（絶対君主制ルーティング）の決定、全Handlerのスコアリング集計、
およびOllamaオフライン時のローカルHandler自動フォールバックを担当するモジュール。
"""
from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple


AUDIT_FORCE_TRIGGERS = (
    "/audit",
    "/sec-audit",
    "/security-check",
    "/vuln",
    "脆弱性",
    "セキュリティ診断",
    "セキュリティ検証",
    "セキュリティ強化",
    "セキュリティ面で強化",
    "apiが脆弱",
    "ルート重複",
    "パストラバーサル",
    "sqlインジェクション",
)

MALWARE_LAB_TRIGGERS = (
    "マルウェア",
    "malware",
    "表層解析",
    "メモリ解析",
    "逆アセンブル",
    "inetsim",
    "pefile",
    "yara",
    "ssdeep",
    "wireshark",
    "remnux",
    "flare",
    "host-only",
    "ホストオンリー",
    "sudo apt",
    "sudo su",
)


def resolve_forced_handler_name(
    message: str,
    inspect_result: Dict[str, Any],
) -> Optional[str]:
    """
    発話とIntentInspector結果から強制実行するHandler名を決定する。
    APIセキュリティ診断は最優先で SecurityAuditHandler にルーティングする。
    """
    msg_lower = (message or "").lower()

    if any(kw in msg_lower for kw in AUDIT_FORCE_TRIGGERS):
        return "SecurityAuditHandler"

    if any(kw in msg_lower for kw in MALWARE_LAB_TRIGGERS):
        return "ChatHandler"

    return inspect_result.get("forced_handler")


def is_offline_error_response(result: Any) -> bool:
    """Handlerの返り値がOllama未接続エラー文字列かどうかを判定する。"""
    if result is None:
        return True
    if not isinstance(result, tuple) or len(result) != 2:
        return True
    _, content = result
    return "Ollamaサーバーに接続できませんでした" in str(content)


async def score_and_sort_handlers(
    handlers: List[Any],
    message: str,
    current_signals: Dict[str, Any],
    feedback_bonus_fn: Callable[[str], int],
) -> List[Dict[str, Any]]:
    """全Handlerのスコアを計算し、降順ソートしたリストを返す。"""
    scored_handlers: List[Dict[str, Any]] = []

    for handler in handlers:
        handler_name = handler.__class__.__name__
        try:
            if hasattr(handler, "calculate_score"):
                sig = inspect.signature(handler.calculate_score)
                if len(sig.parameters) >= 2:
                    base_score = await handler.calculate_score(message, current_signals)
                else:
                    base_score = await handler.calculate_score(message)
            elif hasattr(handler, "can_handle"):
                can_handle = await handler.can_handle(message)
                # OfflineFallbackHandler や OllamaHandler が無条件100点を取らないよう調整
                if handler_name in ("OllamaHandler", "OfflineFallbackHandler", "ParserHandler"):
                    base_score = 40 if can_handle else 0
                else:
                    base_score = 100 if can_handle else 0
            else:
                base_score = 0
        except Exception:
            print(f"❌ {handler_name} のscore計算で例外")
            traceback.print_exc()
            base_score = 0

        bonus = feedback_bonus_fn(handler_name)
        final_score = base_score + bonus

        try:
            estimated_size = getattr(handler, "estimate_size", lambda msg: 1000)(message)
        except Exception:
            estimated_size = 1000

        print(f"🔎 {handler_name} -> ベース:{base_score} 補正:{bonus} 最終:{final_score}")

        scored_handlers.append(
            {
                "handler": handler,
                "score": final_score,
                "size": estimated_size,
            }
        )

    scored_handlers.sort(key=lambda item: item["score"], reverse=True)
    return scored_handlers


def build_routing_debug_block(scored_handlers: List[Dict[str, Any]]) -> Dict[str, Any]:
    top_name = (
        scored_handlers[0]["handler"].__class__.__name__
        if scored_handlers
        else "None"
    )
    return {
        "type": "RoutingDebugBlock",
        "props": {
            "selected": top_name,
            "handlers": [
                {
                    "name": item["handler"].__class__.__name__,
                    "score": item["score"],
                }
                for item in scored_handlers
                if item["score"] > 0
            ],
        },
    }


def attach_debug_block(content: Any) -> Dict[str, Any]:
    if not isinstance(content, dict):
        return {
            "message": str(content),
            "blocks": [],
        }
    if "blocks" not in content:
        content["blocks"] = []
    return content
