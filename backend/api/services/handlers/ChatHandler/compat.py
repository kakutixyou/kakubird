# api/services/handlers/ChatHandler/compat.py
"""旧シグネチャ互換を「TypeErrorの握りつぶし」なしで行う。

従来の `try: f(new) except TypeError: f(old)` は、f の内部で起きた
本物の TypeError まで隠してしまう。呼ぶ前にシグネチャで判断する。
"""

from __future__ import annotations

import inspect
from typing import Any


def accepts_kwarg(func: Any, name: str) -> bool:
    """func が キーワード引数 name を受け取れるか。判定不能なら True。"""

    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return True

    param = params.get(name)

    if param is not None and param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        return True

    return any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
