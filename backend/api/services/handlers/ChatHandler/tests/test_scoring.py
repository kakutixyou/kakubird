import pytest

from api.services.handlers.ChatHandler.scoring import calculate_chat_score

LONG = "あ" * 30


def score(message, signals=None):
    return calculate_chat_score(message, signals)


def test_empty_is_zero():
    assert score("") == 0
    assert score("   ") == 0


def test_unknown_short_and_long():
    assert score("hi", {}) == 70
    assert score(LONG, {}) == 60


@pytest.mark.parametrize("mode", [
    "project_build", "app_generation", "code_analysis",
    "script_extraction", "math_calculation",
])
def test_delegated_modes_are_zero(mode):
    assert score("hi", {"active_mode": mode}) == 0


@pytest.mark.parametrize("mode", ["chat", "greeting", "thanks"])
def test_chat_modes(mode):
    assert score(LONG, {"active_mode": mode}) == 85


def test_mode_change_intent():
    sig = {
        "active_mode": "git_operation",
        "intent_analysis": {"intent": "mode_change"},
    }
    assert score("x", sig) == 90


def test_other_known_mode_is_zero():
    assert score("hi", {"active_mode": "git_operation"}) == 0


# --- active_mode が無い時は intent_analysis.mode を使う ---
def test_fallback_to_intent_analysis_mode():
    sig = {"intent_analysis": {"mode": "project_build"}}
    assert score("hi", sig) == 0

    sig = {"intent_analysis": {"mode": "unknown"}}
    assert score("hi", sig) == 70


# --- forced_handler（IntentInspector の強制ルーティング）---
@pytest.mark.parametrize("handler", [
    "MathHandler", "ParserHandler", "DecompositionHandler",
])
def test_forced_other_handler_is_zero(handler):
    sig = {"intent_analysis": {"mode": "unknown", "forced_handler": handler}}
    assert score("hi", sig) == 0


def test_forced_chat_handler_is_not_blocked():
    sig = {"intent_analysis": {"mode": "unknown",
                               "forced_handler": "ChatHandler"}}
    assert score("hi", sig) == 70


# --- project_builder（mode_rule.py の ProjectBuilderModeRule が出す名前）---
def test_project_builder_default_is_delegated():
    assert score("アプリの画面", {"active_mode": "project_builder"}) == 0


def test_project_builder_chat_policy():
    s = calculate_chat_score(
        "アプリの画面",
        {"active_mode": "project_builder"},
        project_builder_policy="chat",
    )
    assert s == 80


def test_chat_policy_does_not_override_forced_handler():
    sig = {
        "active_mode": "project_builder",
        "intent_analysis": {"forced_handler": "ParserHandler"},
    }
    assert calculate_chat_score(
        "x", sig, project_builder_policy="chat"
    ) == 0
