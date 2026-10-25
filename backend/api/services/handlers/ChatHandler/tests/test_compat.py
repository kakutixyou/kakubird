from unittest.mock import MagicMock

from api.services.handlers.ChatHandler.compat import accepts_kwarg


def test_named_param():
    def f(a, signals=None): ...
    assert accepts_kwarg(f, "signals") is True


def test_missing_param():
    def f(a): ...
    assert accepts_kwarg(f, "signals") is False


def test_var_kwargs():
    def f(a, **kw): ...
    assert accepts_kwarg(f, "signals") is True


def test_positional_only_is_not_keyword():
    def f(a, signals, /): ...
    assert accepts_kwarg(f, "signals") is False


def test_class_constructor():
    class New:
        def __init__(self, llm_engine=None): ...

    class Old:
        def __init__(self): ...

    assert accepts_kwarg(New, "llm_engine") is True
    assert accepts_kwarg(Old, "llm_engine") is False


def test_unknown_signature_defaults_true():
    assert accepts_kwarg(MagicMock(), "anything") is True
