# api/services/handlers/GagHandler/profile_store.py
# -*- coding: utf-8 -*-
"""
profile_store.py

ConversationState と GagRuleProfile / ネタ履歴の間の保存・復元を一元管理する。
id(state) キャッシュを使わず、state.facts["_gag_store"] を用いて安全にシリアライズする。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .GagRuleEngine import GagRuleProfile

STORE_KEY = "_gag_store"
MAX_GAG_HISTORY = 10


def load_profile(state: Any) -> Optional[GagRuleProfile]:
    store = _get_store(state)
    raw_profile = store.get("profile")
    if isinstance(raw_profile, dict):
        valid_keys = GagRuleProfile.__dataclass_fields__.keys()
        return GagRuleProfile(**{k: v for k, v in raw_profile.items() if k in valid_keys})
    return None


def load_gag_history(state: Any) -> List[str]:
    """ChatHandlerの雑談を含まない、純粋な過去ネタ本文のみのリストを返す。"""
    store = _get_store(state)
    history = store.get("gag_history", [])
    if isinstance(history, list):
        return [str(item) for item in history if item]
    return []


def load_user_history_texts(state: Any, limit: int = 6) -> List[str]:
    """40%の文脈お題抽選用に、直近のユーザー発言テキストのみを取得する。"""
    if state is None or not hasattr(state, "get_recent_messages"):
        return []
    try:
        messages = state.get_recent_messages(limit=limit)
    except Exception:
        return []

    return [
        str(m.get("content", ""))
        for m in messages
        if isinstance(m, dict) and m.get("role") == "user" and m.get("content")
    ]


def save_turn_data(
    state: Any,
    profile: GagRuleProfile,
    gag_text: str,
    score: Optional[float] = None,
) -> None:
    if state is None:
        return

    store = _get_store(state)
    store["profile"] = profile.to_dict()

    history = load_gag_history(state)
    if gag_text:
        history = (history + [gag_text])[-MAX_GAG_HISTORY:]
    store["gag_history"] = history

    if score is not None:
        store["last_score"] = score

    if hasattr(state, "update_fact"):
        state.update_fact(STORE_KEY, store)
    elif hasattr(state, "facts") and isinstance(state.facts, dict):
        state.facts[STORE_KEY] = store


def _get_store(state: Any) -> Dict[str, Any]:
    if state is None:
        return {}
    facts = getattr(state, "facts", None)
    if isinstance(facts, dict):
        store = facts.get(STORE_KEY)
        if isinstance(store, dict):
            return dict(store)
    return {}