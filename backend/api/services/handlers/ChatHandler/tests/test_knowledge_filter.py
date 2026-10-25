from api.services.handlers.ChatHandler.knowledge_filter import (
    has_knowledge_channel,
    is_system_context,
    split_knowledge,
)

HEALTH = {"id": "system/knowledge_health", "content_type": "generated_context"}
PROGRESS = {"id": "system/project_progress", "source_path": "system/project_progress"}
REAL = {"id": "calendar", "source_path": "domains/calendar.json",
        "content_type": "json"}


def test_is_system_context():
    assert is_system_context(HEALTH)
    assert is_system_context(PROGRESS)
    assert is_system_context({"content_type": "generated_context"})
    assert not is_system_context(REAL)
    assert not is_system_context("text")
    assert not is_system_context(None)


def test_split_keeps_order():
    real, system = split_knowledge([HEALTH, REAL, PROGRESS])
    assert real == [REAL]
    assert system == [HEALTH, PROGRESS]


def test_only_system_items_means_no_real_knowledge():
    real, _ = split_knowledge([HEALTH, PROGRESS])
    assert real == []


def test_knowledge_channel():
    class Orchestrated:
        loaded_knowledge = []

    class Standalone:
        pass

    assert has_knowledge_channel(Orchestrated()) is True   # 空でも「管理されている」
    assert has_knowledge_channel(Standalone()) is False
