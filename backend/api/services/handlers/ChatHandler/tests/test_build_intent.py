"""Build判定のテスト。 pytest api/services/handlers/ChatHandler/tests"""

import pytest

from api.services.handlers.ChatHandler.project_flow.build_intent import (
    is_build_intent,
)

WITH_CTX = {"framework": "react", "project_name": "demo"}
NO_CTX = {}


@pytest.mark.parametrize("message", [
    "じゃあ作って",
    "この内容で作って",
    "アプリを生成して",
    "プロジェクトを作って",
])
@pytest.mark.parametrize("ctx", [WITH_CTX, NO_CTX])
def test_strong_phrases_always_build(message, ctx):
    assert is_build_intent(message, {}, ctx) is True


@pytest.mark.parametrize("message", [
    "ビルドして", "実装を始めて", "コードを生成して", "実際に作って",
])
def test_need_context_phrases(message):
    assert is_build_intent(message, {}, WITH_CTX) is True
    assert is_build_intent(message, {}, NO_CTX) is False


@pytest.mark.parametrize("message", [
    "生成して", "実装して", "生成して！", "実装してください", "作って。",
])
def test_bare_commands_need_context(message):
    assert is_build_intent(message, {}, WITH_CTX) is True
    assert is_build_intent(message, {}, NO_CTX) is False


@pytest.mark.parametrize("message", [
    "要約を生成して",
    "この文章を生成して",
    "レポートを実装して",
    "アプリを作りたい",
    "ビルドしないで",
    "まだ作らないで",
    "アプリを作ってどうやって公開するの",
    "アプリを作って とは？",
    "",
])
def test_not_build(message):
    assert is_build_intent(message, {}, WITH_CTX) is False


def test_explicit_intent_wins():
    assert is_build_intent("OK", {"intent": "build_project"}, NO_CTX) is True
    assert is_build_intent(
        "OK", {"actions": [{"name": "start_build"}]}, NO_CTX
    ) is True
