from api.services.handlers.ChatHandler.intent_view import IntentView
from api.services.handlers.ChatHandler.project_flow.build_intent import (
    is_build_intent,
)


def test_none_and_garbage():
    assert IntentView.from_dict(None).candidates() == ()
    assert IntentView.from_dict("x").mode == ""
    assert IntentView.from_dict({"score": "abc"}).score == 0


def test_candidates_include_mode_even_if_intent_is_conversation():
    # Inspector は「会話Intentがあれば intent をそれで上書き」する
    raw = {"mode": "project_build", "intent": "agreement"}
    view = IntentView.from_dict(raw)
    assert "project_build" in view.candidates()
    assert is_build_intent("そうだね", raw, {}) is True


def test_actions_list_dict_and_mapping():
    assert IntentView.from_dict(
        {"actions": ["Build_Project", {"name": "x"}, {"action": "y"}]}
    ).actions == ("build_project", "x", "y")

    assert IntentView.from_dict(
        {"actions": {"start_build": 0.9}}
    ).actions == ("start_build",)


def test_is_build_intent_via_actions_mapping():
    assert is_build_intent("OK", {"actions": {"start_build": 1}}, {}) is True
