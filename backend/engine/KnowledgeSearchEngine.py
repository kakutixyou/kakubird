"""
KnowledgeSearchEngine
==============================================

AIがKnowledgeを検索するための司令塔

役割
----------------------------------------------
・KnowledgeLoaderとの連携
・Analyzer自動選択
・検索前の解析
・Embeddingの準備
・PromptBuilderへ渡すデータ生成

このクラスは処理を行うのではなく、
各EngineやManagerを統括するOrchestraとして動作する。

==============================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# -----------------------------------------
# 他モジュール
# -----------------------------------------

from .KnowledgeLoader import KnowledgeLoader
from .PromptBuilder import PromptBuilder

logger = logging.getLogger(__name__)


class KnowledgeSearchEngine:

    ###############################################
    # 初期化
    ###############################################

    def __init__(
        self,
        knowledge_dirs: List[str | Path],
        cache_enabled: bool = True,
    ):

        self.loader = KnowledgeLoader(
            knowledge_dirs=knowledge_dirs,
            cache_enabled=cache_enabled,
        )

        self.prompt_builder = PromptBuilder()

        self.cache_enabled = cache_enabled

        self.knowledge_cache: Dict[str, Any] = {}

        self.embedding_cache: Dict[str, Any] = {}

        self.vector_cache: Dict[str, Any] = {}

        logger.info("KnowledgeSearchEngine 初期化完了")

    ###############################################
    # キャッシュ
    ###############################################

    def clear_cache(self):

        self.knowledge_cache.clear()
        self.embedding_cache.clear()
        self.vector_cache.clear()

        self.loader.clear_cache()

        logger.info("Cache Clear")

    ###############################################
    # Knowledge
    ###############################################

    def load_knowledge(
        self,
        file_paths: List[str]
    ):

        logger.info("Knowledge読み込み開始")

        return self.loader.load(file_paths)

    def reload_knowledge(
        self,
        file_paths: List[str]
    ):

        self.loader.clear_cache()

        return self.loader.load(file_paths)

    ###############################################
    # Analyzer
    ###############################################

    def select_analyzer(
        self,
        file_path: str
    ):

        suffix = Path(file_path).suffix.lower()

        if suffix in [".html", ".htm"]:
            from .tag_analyzer import TagAnalyzer
            return TagAnalyzer()

        if suffix in [".tsx", ".jsx"]:
            from .component_analyzer import ComponentAnalyzer
            return ComponentAnalyzer()

        if suffix in [".css"]:
            from .css_analyzer import CSSAnalyzer
            return CSSAnalyzer()

        if suffix in [".py"]:
            from .AdvancedPythonAnalyzer import AdvancedPythonAnalyzer
            return AdvancedPythonAnalyzer()

        if suffix in [".xml"]:
            from .repomix_analyzer import RepomixAnalyzer
            return RepomixAnalyzer()

        return None

    ###############################################
    # 1ファイル解析
    ###############################################

    def analyze_document(
        self,
        document
    ):

        analyzer = self.select_analyzer(document.path)

        if analyzer is None:

            logger.info(
                "Analyzerが存在しません : %s",
                document.path
            )

            return document

        try:

            logger.info(
                "Analyzer実行 : %s",
                analyzer.__class__.__name__
            )

            analysis = analyzer.analyze(document)

            return analysis

        except Exception as e:

            logger.exception(e)

            return document

    ###############################################
    # 複数ファイル解析
    ###############################################

    def analyze_documents(
        self,
        documents
    ):

        analyzed = []

        for doc in documents:

            analyzed.append(
                self.analyze_document(doc)
            )

        return analyzed
        ###############################################
    # Keyword Search
    ###############################################

    def keyword_search(
        self,
        query: str,
        documents
    ):

        logger.info("Keyword Search")

        results = []

        query = query.lower()

        for doc in documents:

            score = 0

            text = str(getattr(doc, "content", "")).lower()

            if query in text:
                score += 100

            for word in query.split():

                if word in text:
                    score += 20

            if score > 0:

                results.append({
                    "document": doc,
                    "score": score
                })

        return results

    ###############################################
    # Fuzzy Search
    ###############################################

    def fuzzy_search(
        self,
        query: str,
        documents
    ):

        logger.info("Fuzzy Search")

        results = []

        for doc in documents:

            text = str(getattr(doc, "content", "")).lower()

            score = 0

            for word in query.lower().split():

                if word[:3] in text:
                    score += 10

            if score > 0:

                results.append({
                    "document": doc,
                    "score": score
                })

        return results

    ###############################################
    # Embedding Search
    ###############################################

    def embedding_search(
        self,
        query: str,
        documents
    ):

        logger.info("Embedding Search")

        #
        # 後で EmbeddingEngine.py を接続
        #

        return []

    ###############################################
    # Vector Search
    ###############################################

    def vector_search(
        self,
        query_embedding
    ):

        logger.info("Vector Search")

        #
        # 後で VectorDB.py を接続
        #

        return []

    ###############################################
    # Hybrid Search
    ###############################################

    def hybrid_search(
        self,
        query,
        documents
    ):

        keyword = self.keyword_search(
            query,
            documents
        )

        fuzzy = self.fuzzy_search(
            query,
            documents
        )

        embedding = self.embedding_search(
            query,
            documents
        )

        results = []

        results.extend(keyword)
        results.extend(fuzzy)
        results.extend(embedding)

        return self.rerank(results)

    ###############################################
    # Rerank
    ###############################################

    def rerank(
        self,
        results
    ):

        logger.info("ReRank")

        merged = {}

        for item in results:

            path = item["document"].path

            if path not in merged:

                merged[path] = item

            else:

                merged[path]["score"] += item["score"]

        result = list(merged.values())

        result.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return result

    ###############################################
    # Compression
    ###############################################

    def compress_documents(
        self,
        results,
        limit=5
    ):

        logger.info("Compression")

        docs = []

        for item in results[:limit]:

            docs.append(
                item["document"]
            )

        return docs

    ###############################################
    # Prompt
    ###############################################

    def build_prompt(
        self,
        user_message,
        documents
    ):

        load_result = self.loader.load(
            [
                doc.path
                for doc in documents
            ]
        )

        return self.prompt_builder.build(
            user_message,
            load_result
        )

    ###############################################
    # Main Search
    ###############################################

    def search(
        self,
        message: str,
        file_paths: list[str]
    ):

        logger.info("=" * 50)
        logger.info("Knowledge Search Start")
        logger.info("=" * 50)

        #
        # Knowledge読み込み
        #

        load_result = self.load_knowledge(
            file_paths
        )

        #
        # Analyzer
        #

        analyzed = self.analyze_documents(
            load_result.items
        )

        #
        # Hybrid検索
        #

        search_result = self.hybrid_search(
            message,
            analyzed
        )

        #
        # 圧縮
        #

        compressed = self.compress_documents(
            search_result
        )

        #
        # PromptBuilder
        #

        prompt = self.build_prompt(
            message,
            compressed
        )

        logger.info("Knowledge Search Finish")

        return prompt

    ###############################################
    # Async
    ###############################################

    async def search_async(
        self,
        message,
        file_paths
    ):

        return self.search(
            message,
            file_paths
        )