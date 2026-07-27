from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# =========================================================
# File Information
# =========================================================

@dataclass
class FileInfo:
    """
    ワークスペース内の1ファイルの情報
    """
    path: str
    absolute_path: str
    language: str
    size: int
    modified_at: datetime
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "absolute_path": self.absolute_path,
            "language": self.language,
            "size": self.size,
            "modified_at": self.modified_at.isoformat(),
            "sha256": self.sha256,
        }


# =========================================================
# Code Chunk
# =========================================================

@dataclass
class CodeChunk:
    """
    コードの意味単位
    """
    chunk_id: str
    file_path: str
    symbol: Optional[str]
    start_line: int
    end_line: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "metadata": self.metadata,
        }


# =========================================================
# Search Result
# =========================================================

@dataclass
class SearchResult:
    """
    ベクトル検索結果
    """
    score: float
    chunk: CodeChunk

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "chunk": self.chunk.to_dict(),
        }


# =========================================================
# Task
# =========================================================

@dataclass
class Task:
    title: str
    description: str = ""
    status: str = "todo"  # todo / doing / done
    priority: int = 3     # 1 = highest
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }


# =========================================================
# Conversation Message
# =========================================================

@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


# =========================================================
# Context Package
# =========================================================

@dataclass
class ContextPackage:
    """
    LLM に渡す文脈のまとめ
    """
    user_query: str
    relevant_files: list[FileInfo] = field(default_factory=list)
    relevant_chunks: list[SearchResult] = field(default_factory=list)
    active_tasks: list[Task] = field(default_factory=list)
    recent_messages: list[ConversationMessage] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_query": self.user_query,
            "relevant_files": [f.to_dict() for f in self.relevant_files],
            "relevant_chunks": [c.to_dict() for c in self.relevant_chunks],
            "active_tasks": [t.to_dict() for t in self.active_tasks],
            "recent_messages": [m.to_dict() for m in self.recent_messages],
            "notes": self.notes,
        }