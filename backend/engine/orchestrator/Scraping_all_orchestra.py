"""
backend/engine/orchestrator/Scraping_all_orchestra.py
====
スクレイピングジョブの総司令塔（バックグラウンドワーカー）

責務:
1. 対象URLからHTMLを取得し、ノイズを除去（BS4）
2. チャンク分割し、ChromaDB（ベクトルDB）へ保存
3. 自作AI向けに解析・蒸留し、KnowledgeRouter用のJSONを生成
4. ファイルシステムへの保存
"""
from __future__ import annotations

import asyncio
import json
import os
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# ─── 記憶システム関連 ──────────────────────────────────────
from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.embedding_service import EmbeddingService
from plugins.ai_memory.vector_store import ChromaVectorStore

# ─── 知識統合アナライザー群 ─────────────────────────────────
try:
    from core.analyzers.synthesis_analyzer import SynthesisAnalyzer
except ImportError:
    SynthesisAnalyzer = None

try:
    from core.analyzers.SemanticBuilderAnalyzer import SemanticBuilderAnalyzer
except ImportError:
    SemanticBuilderAnalyzer = None

try:
    from core.analyzers.ContextDistillationAnalyzer import ContextDistillationAnalyzer
except ImportError:
    ContextDistillationAnalyzer = None

# ─── ファイル管理 ─────────────────────────────────────────
from api.services.manager.KnowledgeManager import KnowledgeManager


@dataclass
class _FallbackChunk:
    """CodeChunkerのシグネチャが異なる場合のフォールバック用チャンク構造"""
    content: str
    file_path: str
    start_line: int = 1
    end_line: int = 1
    language: str = "generic"


class ScrapingAllOrchestra:
    def __init__(self) -> None:
        # 1. VectorStore & EmbeddingService の初期化
        self.vector_store = ChromaVectorStore()
        self.embedding_service = EmbeddingService()

        # 2. CodeChunker の安全な初期化（max_lines 引数の有無に両対応）
        try:
            self.chunker = CodeChunker(max_lines=10)
        except TypeError:
            try:
                self.chunker = CodeChunker(chunk_size=10)
            except TypeError:
                self.chunker = CodeChunker()

        # 3. KnowledgeManager の安全な初期化（base_dir 必須版・引数なし版に両対応）
        here = Path(__file__).resolve()
        project_root = here.parents[2] if len(here.parents) >= 3 else Path(os.getcwd())
        default_kb_dir = project_root / "plugins" / "project_builder" / "knowledge"
        try:
            self.knowledge_manager = KnowledgeManager()
        except TypeError:
            self.knowledge_manager = KnowledgeManager(base_dir=str(default_kb_dir))

        # 4. 自作AI向けアナライザーの安全な初期化
        self.synthesis_analyzer = SynthesisAnalyzer() if SynthesisAnalyzer else None
        self.semantic_builder = SemanticBuilderAnalyzer() if SemanticBuilderAnalyzer else None

        self.distillation_analyzer = None
        if ContextDistillationAnalyzer is not None:
            try:
                self.distillation_analyzer = ContextDistillationAnalyzer(
                    max_code_lines=30, max_todos=10
                )
            except TypeError:
                self.distillation_analyzer = ContextDistillationAnalyzer()

    async def process_url(self, url: str, purpose: str = "") -> None:
        """
        スクレイピングの全工程を非同期に実行するメイン関数
        ScrapingHandler から asyncio.create_task() で呼び出される。
        """
        print(f"🕸️ [ScrapingOrchestra] {url} の解析ジョブを開始します...", flush=True)

        try:
            # 1. ネットワーク通信とHTML解析 (別スレッドで実行)
            clean_text = await asyncio.to_thread(self._fetch_and_clean_html, url)
            if not clean_text:
                raise ValueError("有効なテキストデータが抽出できませんでした。")

            # 2. チャンク分割 (別スレッドで実行)
            print("✂️ [ScrapingOrchestra] テキストをチャンクに分割中...", flush=True)
            chunks = await asyncio.to_thread(self._safe_chunk_text, url, clean_text)

            if not chunks:
                raise ValueError("チャンク分割結果が空です。")

            # 3. Embedding (ベクトル化) と ChromaDB 保存
            await self._embed_and_save_to_chroma(chunks)

            # 4. KnowledgeRouter 向け JSON の構築と保存
            json_save_path = await self._build_and_save_knowledge_json(
                url, purpose, clean_text
            )

            print(
                f"✅ [ScrapingOrchestra] すべてのナレッジ化工程が完了しました！ 保存先: {json_save_path}",
                flush=True,
            )

        except Exception as e:
            print(
                f"❌ [ScrapingOrchestra] 処理中に致命的なエラーが発生しました: {e}",
                flush=True,
            )
            traceback.print_exc()

    # ──────────────────────────────────────────────
    # 内部処理メソッド群
    # ──────────────────────────────────────────────

    def _safe_chunk_text(self, url: str, clean_text: str) -> List[Any]:
        """CodeChunkerのメソッド名や引数の違いを吸収してチャンク分割を行う"""
        if hasattr(self.chunker, "chunk_file"):
            try:
                return self.chunker.chunk_file(
                    file_path=url, content=clean_text, language="generic"
                )
            except TypeError:
                try:
                    return self.chunker.chunk_file(url, clean_text)
                except Exception:
                    pass

        if hasattr(self.chunker, "chunk_text"):
            try:
                return self.chunker.chunk_text(clean_text)
            except Exception:
                pass

        # フォールバック：10行ごとに分割
        lines = [line for line in clean_text.splitlines() if line.strip()]
        chunks: List[Any] = []
        step = 10
        for i in range(0, len(lines), step):
            block = "\n".join(lines[i : i + step])
            chunks.append(
                _FallbackChunk(
                    content=block,
                    file_path=url,
                    start_line=i + 1,
                    end_line=min(i + step, len(lines)),
                )
            )
        return chunks

    def _fetch_and_clean_html(self, url: str) -> str:
        """
        URLからHTMLを取得し、ノイズを除去して本文のみを返す（同期処理）
        """
        print("📥 [ScrapingOrchestra] データのダウンロード中...", flush=True)
        req = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

        try:
            with urlopen(req, timeout=20) as response:
                encoding = response.info().get_content_charset(failobj="utf-8")
                html = response.read().decode(encoding, errors="replace")
        except (URLError, HTTPError) as e:
            raise RuntimeError(f"URLの取得に失敗しました: {e}")

        soup = BeautifulSoup(html, "html.parser")
        main_content = None

        # ドメイン特化のピンポイント抽出
        if "qiita.com" in url or "zenn.dev" in url:
            main_content = soup.find("article")
        elif "stackoverflow.com" in url:
            main_content = soup.find(id="mainbar")
        elif "github.com" in url:
            main_content = soup.find(class_="repository-content")

        # フォールバック
        if not main_content:
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("body")
                or soup
            )

        # 不要要素の除去
        for tag in main_content(
            ["script", "style", "nav", "footer", "header", "aside", "form", "button"]
        ):
            tag.decompose()

        return main_content.get_text(separator="\n", strip=True)

    async def _embed_and_save_to_chroma(self, chunks: List[Any]) -> None:
        """
        チャンクをベクトル化し、ChromaDBへ保存する
        """
        provider = getattr(self.embedding_service, "provider", None)
        model_name = getattr(provider, "model_name", "UnknownModel")
        print(
            f"🧠 [ScrapingOrchestra] {model_name} を使用して {len(chunks)} 件のベクトル化を開始...",
            flush=True,
        )

        texts_to_embed = [
            getattr(chunk, "content", str(chunk)) for chunk in chunks
        ]

        # ネットワークI/O（API呼び出し）が絡むため別スレッド化
        vectors = await asyncio.to_thread(
            self.embedding_service.embed_many, texts_to_embed
        )
        print(
            "✨ [ScrapingOrchestra] ベクトル化完了。ChromaDBへ書き込みます...",
            flush=True,
        )

        # VectorStoreへの追加
        await asyncio.to_thread(
            self.vector_store.add_many, chunks=chunks, vectors=vectors
        )

        current_count = getattr(self.vector_store, "count", lambda: "不明")()
        print(
            f"💾 [ScrapingOrchestra] ChromaDB 保存完了。現在の総チャンク数: {current_count}",
            flush=True,
        )

    async def _build_and_save_knowledge_json(
        self, url: str, purpose: str, clean_text: str
    ) -> str:
        """
        自作AI用のメタデータを構築し、JSONとして保存する
        """
        print("🏗️ [ScrapingOrchestra] 自作AI向けナレッジJSONのビルドを開始...", flush=True)

        raw_meta = {
            "source_url": url,
            "purpose": purpose,
            "components": [
                {"name": "ScrapedContent", "code_snippet": clean_text[:5000]}
            ],
        }

        # ドメイン名の抽出 (例: qiita.com -> qiita_com)
        domain_name = url.split("://")[-1].split("/")[0].replace(".", "_")

        # 1. コンテキスト蒸留 (ContextDistillationAnalyzer)
        if self.distillation_analyzer and hasattr(self.distillation_analyzer, "analyze"):
            distilled_data = self.distillation_analyzer.analyze(
                raw_meta=raw_meta,
                domain_name=f"scraped_{domain_name}",
                description=f"Auto-scraped knowledge from {url}",
                keywords=["scraped", domain_name, "web", "automation"],
                weight=1.5,
            )
        else:
            distilled_data = {
                "name": f"scraped_{domain_name}",
                "description": f"Auto-scraped knowledge from {url}",
                "keywords": ["scraped", domain_name, "web", "automation"],
                "weight": 1.5,
                "content": raw_meta,
            }

        # 2. セマンティックグラフ化 (SemanticBuilderAnalyzer)
        if self.semantic_builder and hasattr(self.semantic_builder, "analyze"):
            semantic_json = self.semantic_builder.analyze(
                distilled_data.get("content", {})
            )
        else:
            semantic_json = distilled_data.get("content", {})

        # 3. KnowledgeRouter 準拠の最終データ組み立て
        final_knowledge = {
            "name": distilled_data["name"],
            "description": distilled_data["description"],
            "keywords": distilled_data["keywords"],
            "weight": distilled_data["weight"],
            "semantic_graph": semantic_json,
        }

        # 保存先の決定
        save_filename = f"scraped_{domain_name}.json"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.abspath(os.path.join(base_dir, "../knowledge_store"))
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, save_filename)

        # 4. Manager を使って非同期書き出し
        if hasattr(self.knowledge_manager, "write_file"):
            await asyncio.to_thread(
                self.knowledge_manager.write_file,
                save_path,
                json.dumps(final_knowledge, ensure_ascii=False, indent=2),
            )
        else:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(final_knowledge, f, ensure_ascii=False, indent=2)

        print(f"📦 [ScrapingOrchestra] ナレッジJSONの出力完了: {save_filename}", flush=True)
        return save_path
