# api/services/handlers/ChatHandler/project_flow/conversation.py
"""アプリ要件相談中の定型応答（外部依存なし）。"""

from __future__ import annotations

from typing import Any, Dict

_READABLE_FIELDS = {
    "project_name": "アプリ名",
    "framework": "使用するフレームワーク",
    "purpose": "アプリの目的",
    "target_user": "主な利用者",
}


def compose_project_conversation_response(
    project_context: Dict[str, Any],
) -> str:

    missing = project_context.get("missing_requirements", []) or []
    features = project_context.get("features", []) or []
    pages = project_context.get("pages", []) or []

    if missing:
        next_field = missing[0]
        field_name = _READABLE_FIELDS.get(next_field, next_field)

        return (
            "アプリの要件として記録しました。"
            f"現在は「{field_name}」がまだ未確定です。"
            "決まっていれば教えてください。"
            "まだ決めたくなければ、"
            "機能や画面について先に話しても大丈夫です。"
        )

    if features or pages:
        return (
            "ここまでのアプリ要件を保持しました。"
            "さらに機能・画面・デザイン・"
            "データベースなどを追加できます。"
            "内容が固まったら「じゃあ作って」と"
            "言えば生成段階へ進めます。"
        )

    return (
        "アプリ開発の相談として内容を保持しています。"
        "対象ユーザー、目的、欲しい機能、画面構成などを"
        "順番に追加できます。"
    )
