# api/services/handlers/ChatHandler/responders/text_rules.py
"""Knowledge / ルールベースの応答文を作る。"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from api.services.conversation.ConversationState import ConversationState

from ..compat import accepts_kwarg
from ..knowledge_access import safe_json_response


def compose_response(
    response_composer,
    user_message: str,
    intent: str,
    knowledge: List[Any],
    state: ConversationState,
    debug: Optional[Callable[[str], None]] = None,
) -> str:

    compose = response_composer.compose

    try:
        if accepts_kwarg(compose, "user_message"):
            response = compose(
                user_message=user_message,
                intent=intent,
                knowledge=knowledge,
                state=state,
                is_ai_enabled=False,
            )
        else:
            # 旧ResponseComposer互換
            response = compose(raw_data=knowledge, is_ai_enabled=False)

        if response:
            return str(response)

    except Exception as exc:
        if debug:
            debug(f"ResponseComposer failed: {exc}")

    return safe_json_response(knowledge)


def compose_chatbot_fallback(
    message: str,
    intent: str,
    state: ConversationState,
) -> str:

    lowered = message.lower()

    if any(w in lowered for w in ("こんにちは", "こんばんは", "おはよう")):
        return (
            "こんにちは。"
            "現在はチャットボットモードです。"
            "登録されているJSON Knowledgeと"
            "会話ルールを使って回答します。"
        )

    if any(w in lowered for w in ("ありがとう", "ありがと", "助かった")):
        return (
            "どういたしまして。"
            "必要なら今の話題を続けられます。"
        )

    if intent == "agreement":

        if state.current_topic:
            return (
                "そうですね。"
                f"今は「{state.current_topic}」の話として"
                "文脈を保持しています。"
            )

        return "そうですね。今の会話内容は保持しています。"

    if intent == "follow_up":

        if state.current_topic:
            return (
                f"「{state.current_topic}」についての続きですね。"
                "今回の入力に直接対応する"
                "JSON Knowledgeが見つからなかったため、"
                "確認できない情報の追加は行いません。"
            )

    return (
        "【チャットボットモード】\n"
        "この内容に対応するJSON Knowledgeを"
        "見つけられませんでした。\n"
        "確認できない情報を事実として生成しないよう、"
        "回答を控えています。"
    )
