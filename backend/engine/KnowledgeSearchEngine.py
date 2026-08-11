from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Iterable, Optional

from .KnowledgeLoader import KnowledgeLoader
from .PromptBuilder import PromptBuilder

# 既存の場所に合わせて import パスを調整してください
from api.services.manager.KnowledgeManager import KnowledgeManager

logger = logging.getLogger(__name__)


class KnowledgeSearchEngine:
    """
    統合版:
      - KnowledgeManager(index/lazy) で候補集合を高速に作る
      - KnowledgeLoader で必要ファイルだけ実体ロード
      - analyzer -> hybrid_search -> rerank -> compress
      - PromptBuilder へ渡す
    """

    def __init__(
        self,
        knowledge_dirs: List[str | Path],
        cache_enabled: bool = True,
        manager_base_dir: str | Path = ".",
        manager_target_dirs: Optional[List[str]] = None,
        default_limit: int = 5,
    ):
        self.knowledge_dirs = [Path(p).resolve() for p in knowledge_dirs]
        self.cache_enabled = cache_enabled
        self.default_limit = default_limit

        self.loader = KnowledgeLoader(
            knowledge_dirs=self.knowledge_dirs,
            cache_enabled=cache_enabled,
        )
        self.prompt_builder = PromptBuilder()

        # KnowledgeManager統合
        self.manager = KnowledgeManager(str(manager_base_dir))
        # 例: ["knowledge/analyzed_results", "backend/engine/knowledge"]
        self.manager_target_dirs = manager_target_dirs or []

        # 既存キャッシュ
        self.knowledge_cache: Dict[str, Any] = {}
        self.embedding_cache: Dict[str, Any] = {}
        self.vector_cache: Dict[str, Any] = {}

        logger.info("KnowledgeSearchEngine(統合版) 初期化完了")

    # -------------------------------------------------
    # Cache
    # -------------------------------------------------
    def clear_cache(self):
        self.knowledge_cache.clear()
        self.embedding_cache.clear()
        self.vector_cache.clear()
        self.loader.clear_cache()
        logger.info("Cache Clear")

    # -------------------------------------------------
    # Candidate collection via KnowledgeManager
    # -------------------------------------------------
    def _collect_candidates_from_manager(self, force_rebuild: bool = False) -> list:
        """
        KnowledgeManagerの遅延ロードを使って候補を収集。
        manager_target_dirs が空なら空配列を返す（=従来動作にフォールバック）。
        """
        if not self.manager_target_dirs:
            return []

        all_items = []
        for relative_dir in self.manager_target_dirs:
            try:
                items = self.manager.load_all_json_from_dir(
                    relative_dir_path=relative_dir,
                    index_filename="index.json",
                    force_rebuild=force_rebuild,
                )
                all_items.extend(items)
            except Exception as e:
                logger.warning("manager candidate load failed: %s (%s)", relative_dir, e)

        logger.info("Manager candidates: %d", len(all_items))
        return all_items

    def _normalize_text(self, s: str) -> str:
        return (s or "").strip().lower()

    def _manager_filter_paths(self, query: str, lazy_items: list, top_k: int = 200) -> list[str]:
        """
        LazyKnowledgeのメタデータのみで粗い前段フィルタを行い、file_path候補を返す。
        """
        q = self._normalize_text(query)
        words = [w for w in q.split() if len(w) >= 2]

        scored = []
        for item in lazy_items:
            try:
                title = self._normalize_text(item.get("title", ""))
                category = self._normalize_text(item.get("category", ""))
                language = self._normalize_text(item.get("language", ""))
                framework = self._normalize_text(item.get("framework", ""))
                keywords = " ".join(item.get("keywords", []) or [])
                intent = " ".join(item.get("intent", []) or [])
                tags = " ".join(item.get("tags", []) or [])

                blob = " ".join([title, category, language, framework, keywords, intent, tags]).lower()

                score = 0
                if q and q in blob:
                    score += 100
                for w in words:
                    if w in blob:
                        score += 15

                if score > 0:
                    scored.append((score, item.get("file_path")))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        paths = [p for _, p in scored if p][:top_k]

        # 重複除去（順序保持）
        dedup = []
        seen = set()
        for p in paths:
            if p not in seen:
                seen.add(p)
                dedup.append(p)
        return dedup

    # -------------------------------------------------
    # Load
    # -------------------------------------------------
    def load_knowledge(self, file_paths: List[str]):
        logger.info("Knowledge読み込み開始: %d files", len(file_paths))
        return self.loader.load(file_paths)

    # -------------------------------------------------
    # Analyzer
    # -------------------------------------------------
    def select_analyzer(self, file_path: str):
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

    def analyze_document(self, document):
        analyzer = self.select_analyzer(document.path)

        if analyzer is None:
            return document

        try:
            return analyzer.analyze(document)
        except Exception as e:
            logger.exception("analyze error: %s", e)
            return document

    def analyze_documents(self, documents):
        return [self.analyze_document(doc) for doc in documents]

    # -------------------------------------------------
    # Search
    # -------------------------------------------------
    def keyword_search(self, query: str, documents):
        results = []
        q = query.lower()

        for doc in documents:
            score = 0
            text = str(getattr(doc, "content", "")).lower()

            if q in text:
                score += 100

            for word in q.split():
                if word in text:
                    score += 20

            if score > 0:
                results.append({"document": doc, "score": score})

        return results

    def fuzzy_search(self, query: str, documents):
        results = []

        for doc in documents:
            text = str(getattr(doc, "content", "")).lower()
            score = 0

            for word in query.lower().split():
                if len(word) >= 4 and word[:3] in text:
                    score += 10

            if score > 0:
                results.append({"document": doc, "score": score})

        return results

    def embedding_search(self, query: str, documents):
        # TODO: EmbeddingEngine接続
        return []

    def hybrid_search(self, query: str, documents):
        merged = []
        merged.extend(self.keyword_search(query, documents))
        merged.extend(self.fuzzy_search(query, documents))
        merged.extend(self.embedding_search(query, documents))
        return self.rerank(merged)

    def rerank(self, results):
        merged = {}

        for item in results:
            path = item["document"].path
            if path not in merged:
                merged[path] = item
            else:
                merged[path]["score"] += item["score"]

        arr = list(merged.values())
        arr.sort(key=lambda x: x["score"], reverse=True)
        return arr

    def compress_documents(self, results, limit: int):
        return [item["document"] for item in results[:limit]]

    # -------------------------------------------------
    # Prompt
    # -------------------------------------------------
    def build_prompt(self, user_message, documents):
        # PromptBuilder が load_result を要求する場合の互換アダプタ
        class _LoadResultLike:
            def __init__(self, items):
                self.items = items
                self.errors = []
                self.ok = True

        return self.prompt_builder.build(user_message, _LoadResultLike(documents))

    # -------------------------------------------------
    # Main
    # -------------------------------------------------
    def search(
        self,
        message: str,
        file_paths: list[str],
        use_manager_prefilter: bool = True,
        manager_force_rebuild: bool = False,
        limit: Optional[int] = None,
    ):
        logger.info("=" * 60)
        logger.info("Knowledge Search Start")
        logger.info("=" * 60)

        final_limit = limit or self.default_limit
        candidate_paths = file_paths[:]

        # 1) KnowledgeManager前段絞り込み（任意）
        if use_manager_prefilter:
            lazy_items = self._collect_candidates_from_manager(force_rebuild=manager_force_rebuild)
            if lazy_items:
                manager_paths = self._manager_filter_paths(message, lazy_items, top_k=300)
                if manager_paths:
                    # Router結果との積集合を優先（精度）
                    set_router = set(candidate_paths)
                    inter = [p for p in manager_paths if p in set_router]
                    if inter:
                        candidate_paths = inter
                        logger.info("prefilter by intersection: %d", len(candidate_paths))
                    else:
                        # 交差が無ければRouterを信頼（取りこぼし防止）
                        logger.info("no intersection; keep router paths")

        if not candidate_paths:
            return "関連ナレッジ候補が空です。"

        # 2) Load
        load_result = self.load_knowledge(candidate_paths)
        if not load_result.items:
            return "関連ナレッジの読み込み結果が空でした。"

        # 3) Analyze
        analyzed = self.analyze_documents(load_result.items)

        # 4) Hybrid
        searched = self.hybrid_search(message, analyzed)

        # 5) Fallback
        if not searched:
            compressed = analyzed[:final_limit]
        else:
            compressed = self.compress_documents(searched, limit=final_limit)

        # 6) Prompt
        prompt = self.build_prompt(message, compressed)

        logger.info("Knowledge Search Finish")
        return prompt

    async def search_async(self, message: str, file_paths: list[str], **kwargs):
        return self.search(message, file_paths, **kwargs)