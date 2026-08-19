from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class ConversationMemory:
    def __init__(self, storage_path: Path, max_messages: int = 100):
        self.storage_path = storage_path
        self.max_messages = max_messages
        self.messages: list[ConversationMessage] = []
        self.load()

    def add(self, role: str, content: str) -> None:
        self.messages.append(
            ConversationMessage(role=role, content=content, timestamp=datetime.utcnow())
        )
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
        self.save()

    def get_recent(self, limit: int = 20) -> list[ConversationMessage]:
        return self.messages[-limit:]

    def get_all(self) -> list[ConversationMessage]:
        return list(self.messages)

    def count(self) -> int:
        return len(self.messages)

    def clear(self) -> None:
        self.messages = []
        self.save()

    # ===
    # Persistence
    # ===

    def save(self) -> None:
        data = [message.to_dict() for message in self.messages]

        with self.storage_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> None:
        if not self.storage_path.exists():
            self.messages = []
            return

        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            self.messages = []
            return

        messages: list[ConversationMessage] = []

        for item in raw:
            try:
                timestamp_str = item.get("timestamp")
                timestamp = (
                    datetime.fromisoformat(timestamp_str)
                    if timestamp_str
                    else datetime.utcnow()
                )

                messages.append(
                    ConversationMessage(
                        role=item.get("role", "assistant"),
                        content=item.get("content", ""),
                        timestamp=timestamp,
                    )
                )
            except Exception:
                continue

        self.messages = messages[-self.max_messages :]

    # ===
    # Export
    # ===

    def to_dict(self) -> list[dict]:
        return [message.to_dict() for message in self.messages]