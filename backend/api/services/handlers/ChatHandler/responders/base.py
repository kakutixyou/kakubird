# api/services/handlers/ChatHandler/responders/base.py
"""Responder の共通インターフェース。"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, Tuple

from ..turn_context import TurnContext

HandlerResult = Tuple[str, Any]

# handler._generate_with_local_llm と同じ形
GenerateFn = Callable[..., Optional[str]]


class Responder(Protocol):
    """条件に合えば結果を返し、合わなければ None を返す。"""

    name: str

    async def try_respond(
        self, ctx: TurnContext
    ) -> Optional[HandlerResult]: ...


def record_assistant(ctx: TurnContext, content: str, source: str) -> None:
    """アシスタント発話を履歴に追加する（全Responder共通の定型）。"""
    ctx.state.add_assistant_message(
        content=content,
        source=source,
        intent=ctx.intent,
        topic=ctx.state.current_topic,
    )
