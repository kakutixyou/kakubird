# embedding_service.py

from __future__ import annotations

import hashlib
import os
from typing import Protocol

import httpx


# =========================================================
# Ollamaの起動確認
# =========================================================

def ollama_available() -> bool:
    try:
        response = httpx.get(
            "http://localhost:11434/api/tags",
            timeout=2.0
        )
        return response.status_code == 200
    except Exception:
        return False


# =========================================================
# プロバイダーインターフェース
# =========================================================

class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


# =========================================================
# Ollamaプロバイダー（本番用）
# =========================================================

class OllamaEmbeddingProvider:
    """
    Ollamaのローカルいくつかを利用して意味ベクトルを生成する。
    チャット用モデル(gemma3)とEmbedding用モデル(nomic-embed-text)を分離。
    """

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
    ) -> None:
        # ✅ チャット用の OLLAMA_MODEL とは別の環境変数で管理
        self.model_name = model_name or os.getenv(
            "OLLAMA_EMBED_MODEL",
            "nomic-embed-text"   # Embedding専用モデル
        )
        raw_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = raw_url.rstrip("/")

    def embed(self, text: str) -> list[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_name,
            "prompt": text,
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()["embedding"]
        except Exception as e:
            raise RuntimeError(
                f"Ollamaでのベクトル変換に失敗しました"
                f"（モデル: {self.model_name}）: {e}"
            )


# =========================================================
# Deterministicプロバイダー（開発・オフライン用）
# =========================================================

class DeterministicEmbeddingProvider:
    """
    外部API不要の簡易埋め込み。
    Ollama未起動時・テスト時のフォールバック。
    「猫」と「ネコ」の意味的類似は検出できないが、
    システムが止まらないための保険として機能する。
    """

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [
            digest[i % len(digest)] / 255.0
            for i in range(self.dimensions)
        ]


# =========================================================
# EmbeddingService（全ファイルからここだけ呼ぶ）
# =========================================================

class EmbeddingService:
    """
    使い方はどこでも同じ：

        embedding_service = EmbeddingService()

    Ollama起動中  → OllamaEmbeddingProvider（nomic-embed-text）
    Ollama未起動  → DeterministicEmbeddingProvider（フォールバック）

    明示的に指定したい場合：
        EmbeddingService(provider=DeterministicEmbeddingProvider())
    """

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        if provider is not None:
            # 明示指定があればそのまま使う
            self.provider = provider
            return

        # ✅ Ollama起動確認して自動切替
        if ollama_available():
            print("✅ Ollama Embedding 使用"
                  f"（モデル: {os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')}）")
            self.provider = OllamaEmbeddingProvider()
        else:
            print("⚠️ Ollama未起動 → DeterministicEmbedding使用（意味検索は無効）")
            self.provider = DeterministicEmbeddingProvider()

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text is empty.")
        return self.provider.embed(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]