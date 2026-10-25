"""Explicit tool registry, invocation, and result normalization.

ToolRouter does not infer user intent. ActionPlanner (or another caller) must
select a tool name and provide its arguments. This keeps tool execution
separate from the existing KnowledgeRouter and ChatOrchestrator routing logic.
"""

from __future__ import annotations

import asyncio
import inspect
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

try:
    from api.services.tools.ToolResult import ToolResult
except ModuleNotFoundError:
    from backend.api.services.tools.ToolResult import ToolResult


_MISSING = object()
_VALID_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class ToolRegistrationError(ValueError):
    """Raised when application configuration contains an invalid tool."""


@dataclass
class ToolSpec:
    """Registration information for one executable tool."""

    name: str
    target: Any
    method: Optional[str] = "execute"
    aliases: Tuple[str, ...] = ()
    enabled: bool = True
    run_in_thread: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = _normalize_name(self.name)
        self.aliases = tuple(_normalize_name(alias) for alias in self.aliases)
        self.metadata = dict(self.metadata or {})
        if self.method is not None:
            self.method = str(self.method).strip()
            if not self.method:
                raise ToolRegistrationError("method must not be empty")


class ToolRouter:
    """Register named tools and execute sync or async implementations."""

    def __init__(self, tools: Optional[Iterable[ToolSpec]] = None) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._aliases: Dict[str, str] = {}
        for spec in tools or ():
            self.register_spec(spec)

    @classmethod
    def with_defaults(cls) -> "ToolRouter":
        """Create a router containing tools that are implemented today."""

        try:
            from handlers.Math_Handler.Mathhandler import MathHandler
        except ModuleNotFoundError:
            from handlers.Math_Handler.Mathhandler import MathHandler

        router = cls()
        router.register(
            "math",
            MathHandler(),
            method="execute",
            aliases=("calculate", "calculation"),
            metadata={"result_type": "math"},
        )
        return router

    def register(
        self,
        name: str,
        target: Any,
        *,
        method: Optional[str] = "execute",
        aliases: Iterable[str] = (),
        enabled: bool = True,
        run_in_thread: bool = False,
        metadata: Optional[Mapping[str, Any]] = None,
        replace: bool = False,
    ) -> ToolSpec:
        spec = ToolSpec(
            name=name,
            target=target,
            method=method,
            aliases=tuple(aliases),
            enabled=enabled,
            run_in_thread=run_in_thread,
            metadata=dict(metadata or {}),
        )
        self.register_spec(spec, replace=replace)
        return spec

    def register_callable(
        self,
        name: str,
        function: Callable[..., Any],
        **kwargs: Any,
    ) -> ToolSpec:
        """Register a function instead of an object method."""

        return self.register(name, function, method=None, **kwargs)

    def register_spec(self, spec: ToolSpec, *, replace: bool = False) -> None:
        if not isinstance(spec, ToolSpec):
            raise TypeError("spec must be ToolSpec")
        if spec.target is None:
            raise ToolRegistrationError("tool target must not be None")

        names = (spec.name, *spec.aliases)
        if len(set(names)) != len(names):
            raise ToolRegistrationError("tool name and aliases must be unique")

        collisions = [
            name
            for name in names
            if name in self._tools or name in self._aliases
        ]
        if collisions and not replace:
            raise ToolRegistrationError(
                "tool name or alias is already registered: " + ", ".join(collisions)
            )

        if replace and spec.name in self._tools:
            self.unregister(spec.name)
        elif collisions:
            # Replacing a tool must never silently steal another tool's alias.
            foreign = [name for name in collisions if self._aliases.get(name) != spec.name]
            if foreign:
                raise ToolRegistrationError(
                    "cannot replace aliases owned by another tool: " + ", ".join(foreign)
                )

        self._tools[spec.name] = spec
        for alias in spec.aliases:
            self._aliases[alias] = spec.name

    def unregister(self, name: str) -> bool:
        canonical_name = self._resolve_name(name)
        if canonical_name is None:
            return False
        spec = self._tools.pop(canonical_name)
        for alias in spec.aliases:
            self._aliases.pop(alias, None)
        return True

    def set_enabled(self, name: str, enabled: bool) -> bool:
        spec = self.get_spec(name)
        if spec is None:
            return False
        spec.enabled = bool(enabled)
        return True

    def has_tool(self, name: str, *, include_disabled: bool = False) -> bool:
        spec = self.get_spec(name)
        return bool(spec and (include_disabled or spec.enabled))

    def get_spec(self, name: str) -> Optional[ToolSpec]:
        canonical_name = self._resolve_name(name)
        return self._tools.get(canonical_name) if canonical_name else None

    def list_tools(self, *, include_disabled: bool = True) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for name in sorted(self._tools):
            spec = self._tools[name]
            if not include_disabled and not spec.enabled:
                continue
            items.append(
                {
                    "name": spec.name,
                    "aliases": list(spec.aliases),
                    "enabled": spec.enabled,
                    "method": spec.method,
                    "run_in_thread": spec.run_in_thread,
                    "metadata": dict(spec.metadata),
                }
            )
        return items

    async def route(
        self,
        tool_name: str,
        *,
        arguments: Optional[Mapping[str, Any]] = None,
        payload: Any = _MISSING,
        timeout_seconds: Optional[float] = None,
    ) -> ToolResult:
        """Execute one explicitly named tool and normalize its result.

        Use ``arguments`` for keyword invocation or ``payload`` for one
        positional input. They are mutually exclusive.
        """

        requested_name = str(tool_name or "").strip().lower()
        if arguments is not None and payload is not _MISSING:
            return ToolResult.fail(
                requested_name or "unknown",
                error_code="ambiguous_tool_input",
                message="argumentsとpayloadは同時に指定できません。",
            )
        if arguments is not None and not isinstance(arguments, Mapping):
            return ToolResult.fail(
                requested_name or "unknown",
                error_code="invalid_tool_arguments",
                message="argumentsは辞書形式で指定してください。",
            )
        if timeout_seconds is not None and timeout_seconds <= 0:
            return ToolResult.fail(
                requested_name or "unknown",
                error_code="invalid_timeout",
                message="timeout_secondsは0より大きい値にしてください。",
            )

        spec = self.get_spec(requested_name)
        if spec is None:
            return ToolResult.unavailable(
                requested_name or "unknown",
                error_code="tool_not_registered",
                message=f"ツール「{requested_name or 'unknown'}」は登録されていません。",
            )
        if not spec.enabled:
            return ToolResult.unavailable(
                spec.name,
                error_code="tool_disabled",
                message=f"ツール「{spec.name}」は現在無効です。",
            )

        callable_target = self._get_callable(spec)
        if callable_target is None:
            return ToolResult.unavailable(
                spec.name,
                error_code="tool_method_missing",
                message=f"ツール「{spec.name}」の実行メソッドが見つかりません。",
            )

        call_args: Tuple[Any, ...] = () if payload is _MISSING else (payload,)
        call_kwargs = dict(arguments or {})
        signature_error = self._validate_signature(callable_target, call_args, call_kwargs)
        if signature_error:
            return ToolResult.fail(
                spec.name,
                error_code="invalid_tool_arguments",
                message="ツールに渡した引数が正しくありません。",
                data={"detail": signature_error},
            )

        started = time.perf_counter()
        try:
            operation = self._invoke(spec, callable_target, call_args, call_kwargs)
            if timeout_seconds is not None:
                raw_result = await asyncio.wait_for(operation, timeout=timeout_seconds)
            else:
                raw_result = await operation
        except asyncio.TimeoutError:
            return ToolResult.fail(
                spec.name,
                error_code="tool_timeout",
                message=f"ツール「{spec.name}」の処理が時間内に完了しませんでした。",
            )
        except Exception:
            # Internal details belong in server logs, not in API responses.
            return ToolResult.fail(
                spec.name,
                error_code="tool_execution_failed",
                message=f"ツール「{spec.name}」の実行中にエラーが発生しました。",
            )

        result = self._normalize_result(spec.name, raw_result)
        result.metadata.setdefault("router_tool", spec.name)
        result.metadata.setdefault("requested_tool", requested_name)
        result.metadata.setdefault(
            "router_duration_ms",
            (time.perf_counter() - started) * 1000,
        )
        return result

    async def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Alias used by ActionPlanner-facing code."""

        return await self.route(tool_name, **kwargs)

    async def _invoke(
        self,
        spec: ToolSpec,
        callable_target: Callable[..., Any],
        call_args: Tuple[Any, ...],
        call_kwargs: Dict[str, Any],
    ) -> Any:
        if spec.run_in_thread and not inspect.iscoroutinefunction(callable_target):
            return await asyncio.to_thread(callable_target, *call_args, **call_kwargs)

        result = callable_target(*call_args, **call_kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _get_callable(spec: ToolSpec) -> Optional[Callable[..., Any]]:
        candidate = spec.target if spec.method is None else getattr(spec.target, spec.method, None)
        return candidate if callable(candidate) else None

    @staticmethod
    def _validate_signature(
        callable_target: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Optional[str]:
        try:
            inspect.signature(callable_target).bind(*args, **kwargs)
        except (TypeError, ValueError) as exc:
            # Some extension callables do not expose signatures. ValueError
            # means validation is unavailable, not that the call is invalid.
            if isinstance(exc, ValueError):
                return None
            return str(exc)
        return None

    @staticmethod
    def _normalize_result(tool_name: str, value: Any) -> ToolResult:
        if isinstance(value, ToolResult):
            return value

        if isinstance(value, tuple) and len(value) == 2:
            result_type, content = value
            if isinstance(content, ToolResult):
                result = content
            elif isinstance(content, Mapping):
                result = ToolResult.ensure(content, default_tool_name=tool_name)
            else:
                result = ToolResult.ok(tool_name, data=content)
            result.metadata.setdefault("legacy_result_type", str(result_type))
            return result

        if isinstance(value, Mapping):
            return ToolResult.ensure(value, default_tool_name=tool_name)
        if value is None:
            return ToolResult.fail(
                tool_name,
                error_code="empty_tool_result",
                message=f"ツール「{tool_name}」から結果が返されませんでした。",
            )
        return ToolResult.ok(tool_name, data=value)

    def _resolve_name(self, name: str) -> Optional[str]:
        try:
            normalized = _normalize_name(name)
        except ToolRegistrationError:
            return None
        if normalized in self._tools:
            return normalized
        return self._aliases.get(normalized)


def _normalize_name(name: str) -> str:
    normalized = str(name or "").strip().lower()
    if not _VALID_TOOL_NAME.fullmatch(normalized):
        raise ToolRegistrationError(
            "tool names must match [a-z][a-z0-9_.-]{0,63}"
        )
    return normalized


__all__ = ["ToolRegistrationError", "ToolRouter", "ToolSpec"]
