import pytest

from api.services.handlers.ChatHandler.mode_switch import (
    extract_requested_mode,
    mode_switch_response,
)


class Req:
    chat_mode = None
    ai_mode = None


@pytest.mark.parametrize("message, expected", [
    ("aiモードにして", "ai"),
    ("チャットボットモードにして", "chatbot"),
    ("生成aiを使わない", "chatbot"),
    ("aiモードって何？", None),
    ("aiモードについて教えて", None),
    ("今日の天気", None),
])
def test_text_switch(message, expected):
    assert extract_requested_mode(Req(), message) == expected
    assert (mode_switch_response(message) is not None) == (expected is not None)


def test_request_field_wins():
    r = Req()
    r.chat_mode = "chatbot"
    assert extract_requested_mode(r, "aiモードにして") == "chatbot"
