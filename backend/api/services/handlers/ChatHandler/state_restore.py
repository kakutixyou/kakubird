# api/services/handlers/ChatHandler/state_restore.py
"""signals から ConversationState を復元する。"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from api.services.conversation.ConversationState import ConversationState

logger = logging.getLogger(__name__)


def restore_state(
    current_signals: Dict[str, Any],
    default_mode: str,
    debug: Optional[Callable[[str], None]] = None,
) -> ConversationState:

    raw = current_signals.get("conversation_state")

    if not raw:
        return ConversationState(mode=default_mode)

    try:
        return ConversationState.from_dict(raw)

    except Exception as exc:
        logger.exception("ConversationState restore failed")

        if debug:
            debug(f"state restore failed: {exc}")

        return ConversationState(mode=default_mode)
