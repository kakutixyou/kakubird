# api/services/handlers/ChatHandler/scoring.py
"""ChatHandler のハンドラー選択スコア（外部依存なし）。

司令塔（ChatOrchestrator / IntentInspector）が決めたモードに従う。
ChatHandler 自身で文面解析（Project判定など）はしない。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .constants import (
    CHAT_MODES,
    DEFAULT_SCORE,
    DELEGATED_MODES,
    MODE_CHANGE_INTENTS,
    PROJECT_CONSULT_MODES,
    PROJECT_CONSULT_SCORE,
)
from .intent_view import IntentView


def resolve_active_mode(
    signals: Dict[str, Any],
    view: IntentView,
) -> str:
    """active_mode を優先し、無ければ intent_analysis.mode を使う。"""

    active = str(signals.get("active_mode") or "").strip().lower()

    if active:
        return active

    return view.mode or "unknown"


def calculate_chat_score(
    message: Any,
    signals: Optional[Dict[str, Any]],
    default_score: int = DEFAULT_SCORE,
    debug: Optional[Callable[[str], None]] = None,
    project_builder_policy: str = "delegate",
) -> int:
    """
    project_builder_policy:
        "delegate": project_builder モードは ProjectBuilderHandler に任せる（0点）
        "chat"    : ChatHandler が要件相談として引き受ける
    """

    text = message if isinstance(message, str) else str(message)

    if not text.strip():
        return 0

    signals = signals if isinstance(signals, dict) else {}

    view = IntentView.from_dict(signals.get("intent_analysis"))
    active_mode = resolve_active_mode(signals, view)

    # 0. 別ハンドラーへの強制ルーティング（Parser / Math 等）
    if (
        view.forced_handler
        and "chat" not in view.forced_handler
    ):
        if debug:
            debug(f"skipping: forced_handler={view.forced_handler}")
        return 0

    # 1a. アプリ関連発話を ChatHandler が引き受ける設定
    if (
        project_builder_policy == "chat"
        and active_mode in PROJECT_CONSULT_MODES
    ):
        return PROJECT_CONSULT_SCORE

    # 1b. 他ハンドラーが担当するモード（暴走防止）
    if active_mode in DELEGATED_MODES:
        if debug:
            debug(f"skipping: active_mode={active_mode}")
        return 0

    # 2. 自分が担当するモード
    if active_mode in CHAT_MODES:
        return 85

    # 3. AI/Chatbot モード切替インテント
    if view.intent in MODE_CHANGE_INTENTS:
        return 90

    # 4. Unknown時のフォールバック（短文は拾う）
    if active_mode == "unknown":
        return 70 if len(text.strip()) <= 20 else default_score

    # 他の専用ハンドラーが担当する領域
    return 0
