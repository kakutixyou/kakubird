import asyncio
import threading

from api.services.handlers.ChatHandler.project_flow.build_runner import (
    handle_project_build,
    normalize_build_result,
)
from api.services.handlers.ChatHandler.result_builder import ResultBuilder


class FakeState:
    mode = "ai"
    ai_enabled = True
    current_topic = "t"
    turn_count = 1
    project_context = {"project_name": "demo", "framework": "react"}

    def __init__(self):
        self.errors = []
        self.messages = []

    def get_project_context(self):
        return dict(self.project_context)

    def add_assistant_message(self, **kw): self.messages.append(kw)
    def set_error(self, e): self.errors.append(e)
    def clear_error(self): self.errors.clear()
    def to_dict(self): return {"mode": self.mode}
    def debug_print(self): pass


def run(**kw):
    state = kw.pop("state", None) or FakeState()
    base = dict(
        results=ResultBuilder(debug=lambda m: None, enable_debug=False),
        debug=lambda m: None,
        state=state,
        current_signals={},
        analysis={},
        requirement_result={},
        context_result={},
        topic_result={},
    )
    base.update(kw)
    return state, asyncio.run(handle_project_build(**base))


def test_sync_build_runs_off_the_event_loop_thread():
    seen = {}

    class Service:
        def build(self, project_context):
            seen["thread"] = threading.get_ident()
            return {"status": "success", "project_name": "demo"}

    main = threading.get_ident()
    _, (kind, res) = run(build_service=Service())
    assert kind == "project_build"
    assert seen["thread"] != main
    assert res["project_build"]["status"] == "success"


def test_async_build_is_awaited():
    class Service:
        async def build(self, project_context):
            return {"status": "success", "project_name": "demo"}

    _, (_, res) = run(build_service=Service())
    assert res["project_build"]["status"] == "success"


def test_kwargs_passed_only_when_accepted():
    got = {}

    class New:
        def build(self, project_context, use_ai=False, clean_existing=False):
            got.update(use_ai=use_ai, clean_existing=clean_existing)
            return {"status": "success"}

    class Old:
        def build(self, project_context):
            got["old"] = True
            return {"status": "success"}

    run(build_service=New(), use_ai=True, clean_existing=True)
    assert got == {"use_ai": True, "clean_existing": True}

    run(build_service=Old(), use_ai=True, clean_existing=True)
    assert got["old"] is True


def test_delegate_is_preferred_and_blocks_are_unwrapped():
    calls = {}

    class Delegate:
        async def build_project(self, request, project_context, message):
            calls.update(request=request, message=message,
                         name=project_context["project_name"])
            return {
                "message": "ok", "status": "success", "project_name": "demo",
                "blocks": [{"type": "project_build", "data": {
                    "status": "success", "project_name": "demo",
                    "zip_download_url": "/zip/demo.zip", "files_generated": 5}}],
            }

    class Service:
        def build(self, project_context):
            raise AssertionError("delegate があるので呼ばれない")

    _, (kind, res) = run(
        build_service=Service(), build_delegate=Delegate(),
        request="REQ", message="じゃあ作って",
    )
    assert kind == "project_build"
    assert calls == {"request": "REQ", "message": "じゃあ作って", "name": "demo"}
    assert res["project_build"]["zip_download_url"] == "/zip/demo.zip"
    assert res["update_signals"]["last_project_build"]["zip_download_url"]


def test_delegate_failure_is_reported_not_raised():
    class Delegate:
        async def build_project(self, **kw):
            raise RuntimeError("boom")

    state, (kind, res) = run(build_service=None, build_delegate=Delegate())
    assert res["project_build"]["status"] == "error"
    assert state.errors and "boom" in state.errors[0]


def test_unavailable_when_no_service_and_no_delegate():
    _, (_, res) = run(build_service=None, build_delegate=None)
    assert res["project_build"]["status"] == "unavailable"


def test_normalize_blocks_shape():
    out = normalize_build_result(
        {"blocks": [{"type": "project_build", "data": {"status": "error"}}]},
        {"project_name": "x"},
    )
    assert out["status"] == "error" and out["project_name"] == "x"
