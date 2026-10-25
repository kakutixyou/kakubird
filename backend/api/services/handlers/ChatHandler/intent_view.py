# api/services/handlers/ChatHandler/intent_view.py
"""IntentInspector.inspect() の出力を読むための読み取り専用ビュー。

Inspector の出力の注意点:
    - intent は「会話Intent（agreement 等）があればそれ、無ければ mode」。
      つまり intent だけを見ると mode（project_build 等）を見落とす。
      → mode / intent / action / actions を常に両方見る。
    - forced_handler は Parser / Decomposition / Math などの強制ルーティング。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


def _text(value: Any) -> str:
    return str(value).strip().lower() if value else ""


def _action_names(raw: Any) -> Tuple[str, ...]:

    names = []

    if isinstance(raw, Mapping):
        names = [_text(key) for key in raw.keys()]

    elif isinstance(raw, (list, tuple)):
        for item in raw:

            if isinstance(item, str):
                names.append(_text(item))

            elif isinstance(item, Mapping):
                names.append(
                    _text(
                        item.get("name")
                        or item.get("action")
                        or item.get("intent")
                    )
                )

    return tuple(name for name in names if name)


@dataclass(frozen=True)
class IntentView:
    mode: str = ""
    intent: str = ""
    action: str = ""
    forced_handler: str = ""
    routing_reason: str = ""
    score: int = 0
    actions: Tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Any) -> "IntentView":

        if not isinstance(raw, Mapping):
            return cls()

        try:
            score = int(raw.get("score") or 0)
        except (TypeError, ValueError):
            score = 0

        return cls(
            mode=_text(raw.get("mode")),
            intent=_text(raw.get("intent")),
            action=_text(raw.get("action")),
            forced_handler=_text(raw.get("forced_handler")),
            routing_reason=_text(raw.get("routing_reason")),
            score=score,
            actions=_action_names(raw.get("actions")),
        )

    def candidates(self) -> Tuple[str, ...]:
        """Intent判定に使う全ての名前（mode/intent/action/actions）。"""
        values = (self.mode, self.intent, self.action, *self.actions)
        return tuple(value for value in values if value)
