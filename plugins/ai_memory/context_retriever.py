# context_retriever.py
from __future__ import annotations

from pathlib import Path

from .embedding_service import EmbeddingService
from .models import ContextPackage, FileInfo
from .vector_store import InMemoryVectorStore


class ContextRetriever:
    """
    ユーザーの質問に対して関連文脈を集める。
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: InMemoryVectorStore,
        max_chunks: int = 8,
        max_files: int = 20,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.max_chunks = max_chunks
        self.max_files = max_files

        self._files: list[FileInfo] = []
        self._recent_messages = []
        self._active_tasks = []
        self._notes: list[str] = []

    # --------------------------------------------------
    # Registration
    # --------------------------------------------------

    def set_files(self, files: list[FileInfo]) -> None:
        self._files = files

    def set_recent_messages(self, messages: list) -> None:
        self._recent_messages = messages

    def set_active_tasks(self, tasks: list) -> None:
        self._active_tasks = tasks

    def set_notes(self, notes: list[str]) -> None:
        self._notes = notes

    # --------------------------------------------------
    # Build Context
    # --------------------------------------------------

    def build_context(self, user_query: str) -> ContextPackage:
        query_vector = self.embedding_service.embed(user_query)

        search_results = self.vector_store.search(
            query_vector=query_vector,
            top_k=self.max_chunks,
        )

        relevant_paths = {
            result.chunk.file_path
            for result in search_results
        }

        relevant_files = [
            file
            for file in self._files
            if file.path in relevant_paths
        ][: self.max_files]

        return ContextPackage(
            user_query=user_query,
            relevant_files=relevant_files,
            relevant_chunks=search_results,
            active_tasks=self._active_tasks,
            recent_messages=self._recent_messages,
            notes=self._notes,
        )