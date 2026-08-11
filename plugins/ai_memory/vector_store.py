# vector_store.py（CHROMA_PATH定数を追加するだけ）

from __future__ import annotations
import math
from dataclasses import dataclass, field
import uuid
import chromadb
from .models import CodeChunk, SearchResult

# ✅ アプリ全体で使う統一パス
CHROMA_PERSIST_PATH = "backend/.ai_memory/chroma_db"
CHROMA_COLLECTION_NAME = "workspace_chunks"


@dataclass
class VectorRecord:
    chunk: CodeChunk
    vector: list[float]
    metadata: dict = field(default_factory=dict)



class InMemoryVectorStore:
    """
    シンプルなメモリ内ベクトルストア。
    開発用・MVP用。
    """

    def __init__(self) -> None:
        self.records: list[VectorRecord] = []

    # --------------------------------------------------
    # Add
    # --------------------------------------------------

    def add(
        self,
        chunk: CodeChunk,
        vector: list[float],
        metadata: dict | None = None,
    ) -> None:
        self.records.append(
            VectorRecord(
                chunk=chunk,
                vector=vector,
                metadata=metadata or {},
            )
        )

    def add_many(
        self,
        chunks: list[CodeChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch.")

        for chunk, vector in zip(chunks, vectors):
            self.add(chunk, vector)

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        scored: list[SearchResult] = []

        for record in self.records:
            score = cosine_similarity(query_vector, record.vector)
            scored.append(
                SearchResult(
                    score=score,
                    chunk=record.chunk,
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    def clear(self) -> None:
        self.records.clear()

    def count(self) -> int:
        return len(self.records)



def cosine_similarity(a, b):
    if len(a) != len(b):
        raise ValueError("Vector dimensions do not match.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ChromaVectorStore:
    """
    ChromaDBを使った永続的なベクトルストア。
    ✅ デフォルトパスを統一定数に変更
    """
    def __init__(
        self,
        persist_directory: str = CHROMA_PERSIST_PATH,   # ✅ 変更
        collection_name: str = CHROMA_COLLECTION_NAME,  # ✅ 変更
    ):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_many(self, chunks, vectors):
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch.")

        ids, documents, embeddings, metadatas = [], [], [], []
        for chunk, vector in zip(chunks, vectors):
            ids.append(chunk.chunk_id if hasattr(chunk, "chunk_id") else str(uuid.uuid4()))
            documents.append(chunk.content)
            embeddings.append(vector)
            meta = chunk.metadata if hasattr(chunk, "metadata") else {}
            meta["file_path"] = chunk.file_path if hasattr(chunk, "file_path") else "unknown"
            metadatas.append(meta)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def count(self):
        return self.collection.count()

    def search(self, query_vector, top_k=5):
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
        )
        return results