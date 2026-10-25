#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/ToolResult.py
すべてのツール（ToolRouter / BaseTool / Handlerラッパー）が返す共通結果オブジェクト。
- ToolRouter._normalize_result() から呼ばれる ToolResult.ensure() を実装
- ToolResult.ok() の message 引数にデフォルト値を設定し TypeError を防止
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Mapping, Optional

ToolStatus = Literal["success", "error", "warning", "unavailable"]


@dataclass
class ToolResult:
    """Serializable result shared by MathHandler and ToolRouter tools."""

    type: str
    status: ToolStatus
    message: str = ""

    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    error_code: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def success(self) -> bool:
        return self.status == "success"

    @classmethod
    def ok(
        cls,
        result_type: str,
        *,
        message: str = "",
        data: Optional[ Any ] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> "ToolResult":
        normalized_data: Dict[str, Any]
        if isinstance(data, Mapping):
            normalized_data = dict(data)
        elif data is None:
            normalized_data = {}
        else:
            normalized_data = {"value": data}

        resolved_message = message or str(normalized_data.get("message", f"{result_type} executed successfully."))
        return cls(
            type=result_type,
            status="success",
            message=resolved_message,
            data=normalized_data,
            metadata=dict(metadata or {}),
            duration_ms=duration_ms,
        )

    @classmethod
    def fail(
        cls,
        result_type: str,
        *,
        error_code: str = "tool_error",
        message: str = "ツール実行中にエラーが発生しました。",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> "ToolResult":
        return cls(
            type=result_type,
            status="error",
            error_code=error_code,
            message=message,
            data=dict(data or {}),
            metadata=dict(metadata or {}),
            duration_ms=duration_ms,
        )

    @classmethod
    def unavailable(
        cls,
        result_type: str,
        *,
        message: str,
        error_code: str = "tool_unavailable",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        return cls(
            type=result_type,
            status="unavailable",
            error_code=error_code,
            message=message,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def ensure(
        cls,
        value: Any,
        *,
        default_tool_name: str = "unknown",
    ) -> "ToolResult":
        """
        辞書や既存の戻り値（weather_fetch.py の {"error": False, "message": ...} 等）を
        安全に ToolResult へ変換する。ToolRouter._normalize_result() から呼ばれる。
        """
        if isinstance(value, cls):
            return value

        if isinstance(value, Mapping):
            raw = dict(value)
            result_type = str(raw.get("type") or raw.get("tool") or default_tool_name)

            # エラー判定 ("error": True または "status": "error")
            is_error = bool(raw.get("error") is True or raw.get("status") == "error")
            if is_error:
                return cls.fail(
                    result_type,
                    error_code=str(raw.get("error_code") or "tool_reported_error"),
                    message=str(raw.get("message") or "ツールの処理に失敗しました。"),
                    data=raw,
                )

            msg = str(raw.get("message") or "")
            data_payload = raw.get("data") if isinstance(raw.get("data"), Mapping) else raw
            return cls.ok(
                result_type,
                message=msg,
                data=dict(data_payload),
                metadata=dict(raw.get("metadata") or {}),
            )

        return cls.ok(default_tool_name, message=str(value), data={"result": value})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "status": self.status,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "metadata": self.metadata,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


__all__ = ["ToolResult", "ToolStatus"]