# api/services/manager/KnowledgeManager.py
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from engine.KnowledgeLoader import KnowledgeLoader
from engine.KnowledgeRouter import KnowledgeRouter

logger = logging.getLogger(__name__)


# ============================================================
# Data Models
# ============================================================


@dataclass
class KnowledgeHealthReport:
    """
    Knowledgeフォルダーの健全性チェック結果。
    """

    root: str
    total_files: int = 0
    valid_files: int = 0
    broken_files: list[str] = field(default_factory=list)
    empty_files: list[str] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)
    excluded_files: list[str] = field(default_factory=list)
    read_errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            not self.broken_files
            and not self.empty_files
            and not self.read_errors
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "ok": self.ok,
            "total_files": self.total_files,
            "valid_files": self.valid_files,
            "broken_files": list(self.broken_files),
            "empty_files": list(self.empty_files),
            "unsupported_files": list(self.unsupported_files),
            "excluded_files": list(self.excluded_files),
            "read_errors": list(self.read_errors),
        }


@dataclass
class KnowledgeResolveResult:
    """
    KnowledgeManager.resolve() の結果。

    ChatOrchestrator / ChatHandler 側は基本的に items を
    request.loaded_knowledge や persona_and_flow.process_user_wishes(external_knowledge=...)
    へそのまま渡せる。
    """

    items: list[dict[str, Any]] = field(default_factory=list)
    matched_paths: list[str] = field(default_factory=list)
    matched_domains: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.items) and not not self.errors is False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.items) and not self.errors,
            "items": list(self.items),
            "matched_paths": list(self.matched_paths),
            "matched_domains": list(self.matched_domains),
            "scores": dict(self.scores),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


# ============================================================
# Lazy Knowledge
# ============================================================


class LazyKnowledge:
    """
    JSON本体（または .cs / .md 等のテンプレート本体）は必要になるまで開かない。
    index.json に含まれる metadata は、本体を開かずに高速取得できる。
    """

    def __init__(
        self,
        base_dir: str | Path,
        full_path: str | Path,
        rel_path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.full_path = Path(full_path).resolve()
        self.rel_path = str(rel_path).replace("\\", "/")
        self._parsed_data: Optional[Any] = None
        self._metadata = metadata or {}

    @property
    def data(self) -> Any:
        if self._parsed_data is None:
            try:
                ext = self.full_path.suffix.lower()
                if ext == ".json":
                    with self.full_path.open("r", encoding="utf-8") as file:
                        self._parsed_data = json.load(file)
                else:
                    # JSON以外（Unityの .cs, 企画書の .md, .yml など）はテキスト＋サイドカーmetaとして読み込む
                    with self.full_path.open("r", encoding="utf-8") as file:
                        text_content = file.read()
                    sidecar_data: dict[str, Any] = {}
                    meta_path = self.full_path.with_name(self.full_path.name + ".meta.json")
                    if meta_path.is_file():
                        try:
                            sidecar_data = json.loads(meta_path.read_text(encoding="utf-8"))
                        except Exception:
                            sidecar_data = {}
                    self._parsed_data = {
                        **sidecar_data,
                        "content": text_content,
                        "file_path": self.rel_path,
                    }
            except Exception as exc:
                logger.error("遅延ロード失敗 (%s): %s", self.rel_path, exc)
                self._parsed_data = {}

        return self._parsed_data

    def __getitem__(self, key: str) -> Any:
        if key in self._metadata:
            return self._metadata[key]

        data = self.data

        if key == "file_path":
            return self.rel_path

        if key == "id":
            if isinstance(data, dict):
                return data.get("id", self.full_path.stem)
            return self.full_path.stem

        if key == "title":
            if isinstance(data, dict):
                return data.get("title") or data.get("name") or self.full_path.name
            return self.full_path.name

        if key == "content":
            return data

        if key == "retrieval":
            if not isinstance(data, dict):
                return {}
            retrieval = data.get("retrieval", {})
            if not isinstance(retrieval, dict):
                retrieval = {}
            return {
                "keywords": retrieval.get("keywords", data.get("keywords", [])),
                "message_examples": retrieval.get("message_examples", data.get("message_examples", [])),
                "intent": retrieval.get("intent", data.get("intent", [])),
                "tags": retrieval.get("tags", data.get("tags", [])),
            }

        if isinstance(data, dict):
            return data.get(key)

        return None

    def get(self, key: str, default: Any = None) -> Any:
        try:
            value = self[key]
            return value if value is not None else default
        except Exception:
            return default


# ============================================================
# Knowledge Manager
# ============================================================


class KnowledgeManager:
    """
    Knowledge層の統括クラス。

    進化ポイント:
    1. `.json` だけでなく `.meta.json` サイドカー付きの `.cs` (Unityスクリプト) や `.md` (企画書) も Index 対象に統合
    2. `build_index` 時に `.meta.json` 単体を誤って独立エントリ登録しないようガード
    3. Unity・アプリ企画書・OCRパイプライン等の「ワンクリック一括生成用テンプレート (`blueprint_files` / `files`)」を
       解決して `materialize_blueprint()` で即座にファイル出力できる仕組みを追加
    """

    EXCLUDED_INDEX_FILES = {
        "index.json",
        "registry.json",
    }

    SUPPORTED_SIDE_EXTS = {".cs", ".md", ".py", ".tsx", ".ts", ".yml", ".yaml", ".txt"}

    DEFAULT_INDEX_FILENAME = "index.json"

    def __init__(
        self,
        base_dir: str | Path = ".",
        knowledge_dirs: Optional[Sequence[str | Path]] = None,
        threshold: float = 1.0,
        top_k: Optional[int] = 5,
        cache_enabled: bool = True,
        enable_debug: bool = False,
        project_root: Optional[str | Path] = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.project_root = self._discover_project_root(project_root)
        self.threshold = float(threshold)
        self.top_k = top_k
        self.cache_enabled = bool(cache_enabled)
        self.enable_debug = bool(enable_debug)

        self._index_cache: dict[str, dict[str, Any]] = {}
        self._router_cache: dict[str, KnowledgeRouter] = {}
        self.knowledge_dirs: list[Path] = []

        if knowledge_dirs:
            for knowledge_dir in knowledge_dirs:
                self.register_knowledge_dir(knowledge_dir)

        loader_dirs: list[str | Path] = [
            path for path in (self.knowledge_dirs or [self.base_dir])
        ]
        self._loader = KnowledgeLoader(
            knowledge_dirs=loader_dirs,
            cache_enabled=self.cache_enabled,
        )

        self._debug(
            f"initialized base_dir={self.base_dir}, "
            f"knowledge_dirs={[str(p) for p in self.knowledge_dirs]}"
        )

    def _debug(self, message: str) -> None:
        if not self.enable_debug:
            return
        logger.debug("[KnowledgeManager] %s", message)

    def _safe_join_path(self, relative_path: str | Path) -> str:
        path = Path(relative_path)
        if path.is_absolute():
            target = path.resolve()
        else:
            target = (self.base_dir / path).resolve()

        try:
            target.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"不正なパス: {relative_path}") from exc

        return str(target)

    def _resolve_dir(self, directory: str | Path) -> Path:
        path = Path(directory)
        if path.is_absolute():
            resolved = path.resolve()
            if not self._is_inside_project(resolved):
                raise ValueError(f"Knowledge directory is outside project root: {resolved}")
            return resolved

        base_candidate = (self.base_dir / path).resolve()
        project_candidate = (self.project_root / path).resolve()

        if base_candidate.exists():
            return base_candidate
        if project_candidate.exists():
            return project_candidate
        return base_candidate

    def _discover_project_root(self, explicit_root: Optional[str | Path]) -> Path:
        if explicit_root is not None and str(explicit_root).strip():
            return Path(explicit_root).expanduser().resolve()

        candidates = [self.base_dir, *self.base_dir.parents]
        for candidate in candidates:
            if (candidate / "backend").is_dir() and (candidate / "plugins").is_dir():
                return candidate

        if self.base_dir.name.casefold() == "backend":
            return self.base_dir.parent

        return self.base_dir

    def _is_inside_project(self, target: Path) -> bool:
        try:
            target.resolve().relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def _resolve_indexed_file(self, indexed_path: str | Path, knowledge_root: Path) -> Path:
        raw_path = Path(indexed_path)
        if raw_path.is_absolute():
            candidates = [raw_path.resolve()]
        else:
            candidates = [
                (knowledge_root / raw_path).resolve(),
                (self.base_dir / raw_path).resolve(),
                (self.project_root / raw_path).resolve(),
            ]

        target = next((c for c in candidates if c.is_file()), candidates[0])
        try:
            target.relative_to(knowledge_root.resolve())
        except ValueError as exc:
            raise ValueError(f"Index path is outside Knowledge root: {indexed_path}") from exc
        return target

    def _relative_to_base(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path.resolve()).replace("\\", "/")

    def register_knowledge_dir(self, knowledge_dir: str | Path) -> Path:
        resolved = self._resolve_dir(knowledge_dir)
        if resolved not in self.knowledge_dirs:
            self.knowledge_dirs.append(resolved)

        if hasattr(self, "_loader"):
            loader_dirs: list[str | Path] = [path for path in self.knowledge_dirs]
            self._loader = KnowledgeLoader(
                knowledge_dirs=loader_dirs,
                cache_enabled=self.cache_enabled,
            )

        self._debug(f"Knowledge root registered: {resolved}")
        return resolved

    def configure_knowledge_dirs(self, knowledge_dirs: Sequence[str | Path]) -> None:
        self.knowledge_dirs = []
        for path in knowledge_dirs:
            self.register_knowledge_dir(path)
        self._router_cache.clear()

    def clear_cache(self) -> None:
        self._index_cache.clear()
        self._router_cache.clear()
        try:
            self._loader.clear_cache()
        except Exception:
            pass
        self._debug("cache cleared")

    @staticmethod
    def _ensure_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                text = str(item).strip()
                if text:
                    result.append(text)
            return result
        text = str(value).strip()
        return [text] if text else []

    @staticmethod
    def _merge_unique(*values: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for collection in values:
            for raw in collection:
                text = str(raw).strip()
                if not text:
                    continue
                normalized = text.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                result.append(text)
        return result

    def _extract_metadata(
        self,
        data: dict[str, Any],
        file_path: Path,
        file_size: int,
        mtime: float,
        meta_mtime: float = 0.0,
    ) -> dict[str, Any]:
        retrieval = data.get("retrieval", {})
        if not isinstance(retrieval, dict):
            retrieval = {}

        keywords = self._merge_unique(
            self._ensure_list(data.get("keywords", [])),
            self._ensure_list(retrieval.get("keywords", [])),
        )
        intents = self._merge_unique(
            self._ensure_list(data.get("intent", [])),
            self._ensure_list(retrieval.get("intent", [])),
        )
        tags = self._merge_unique(
            self._ensure_list(data.get("tags", [])),
            self._ensure_list(retrieval.get("tags", [])),
        )

        ext = file_path.suffix.lower().strip(".")
        if ext and ext not in [t.lower() for t in tags]:
            tags.append(ext)

        examples = self._merge_unique(
            self._ensure_list(data.get("message_examples", [])),
            self._ensure_list(retrieval.get("message_examples", [])),
        )

        return {
            "id": data.get("id", file_path.stem),
            "title": data.get("title") or data.get("name") or file_path.name,
            "name": data.get("name", ""),
            "category": data.get("category", "未分類"),
            "description": data.get("description", ""),
            "catchphrase": data.get("catchphrase", ""),
            "video_url": data.get("video_url", ""),
            "subjects": data.get("subjects", []),
            "skills": data.get("skills", []),
            "language": data.get("language", ""),
            "framework": data.get("framework", ""),
            "content_type": data.get("content_type", ext),
            "keywords": keywords,
            "intent": intents,
            "tags": tags,
            "message_examples": examples,
            "project_types": self._ensure_list(data.get("project_types", [])),
            "purposes": self._ensure_list(data.get("purposes", [])),
            "features": self._ensure_list(data.get("features", [])),
            "technologies": self._ensure_list(data.get("technologies", [])),
            "target_users": self._ensure_list(
                data.get("target_users", data.get("target_user", []))
            ),
            "file_path": self._relative_to_base(file_path),
            "size_bytes": file_size,
            "mtime": mtime,
            "meta_mtime": meta_mtime,
        }

    # ========================================================
    # Index (JSON + .meta.json 付き .cs / .md 対応)
    # ========================================================

    def build_index(
        self,
        target_dir: str | Path,
        index_filename: str = DEFAULT_INDEX_FILENAME,
    ) -> dict[str, Any]:
        """
        target_dir 以下の JSON および `.meta.json` サイドカー付きファイル（Unity `.cs`, 企画書 `.md` 等）を
        再帰走査して Index を作る。
        """
        start_time = time.time()
        root = self._resolve_dir(target_dir)

        if not root.exists():
            logger.warning("ディレクトリが存在しません: %s", root)
            return {}

        index_path = root / index_filename
        existing_index: dict[str, Any] = {}

        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as file:
                    raw = json.load(file)
                if isinstance(raw, dict):
                    existing_index = raw
            except Exception:
                logger.warning("既存Indexが破損しているため再構築します: %s", index_path)

        new_index: dict[str, Any] = {}
        total_bytes = 0
        parsed_count = 0
        reused_count = 0
        broken_count = 0

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            lower_name = file_path.name.lower()
            if (
                lower_name in {index_filename.lower(), "registry.json"}
                or lower_name.startswith(".")
                or lower_name.endswith(".meta.json")
            ):
                continue

            ext = file_path.suffix.lower()
            meta_sidecar = file_path.with_name(file_path.name + ".meta.json")

            # .json ファイル、または .meta.json サイドカーを持つ .cs / .md 等のテンプレートを対象にする
            if ext != ".json" and not (ext in self.SUPPORTED_SIDE_EXTS and meta_sidecar.is_file()):
                continue

            rel_path = str(file_path.resolve().relative_to(root.resolve())).replace("\\", "/")

            try:
                file_size = file_path.stat().st_size
                mtime = file_path.stat().st_mtime
                meta_mtime = meta_sidecar.stat().st_mtime if meta_sidecar.is_file() else 0.0
                total_bytes += file_size

                old_meta = existing_index.get(rel_path)
                if (
                    isinstance(old_meta, dict)
                    and old_meta.get("mtime") == mtime
                    and old_meta.get("meta_mtime", 0.0) == meta_mtime
                    and old_meta.get("size_bytes") == file_size
                ):
                    new_index[rel_path] = old_meta
                    reused_count += 1
                    continue

                if file_size == 0:
                    broken_count += 1
                    continue

                if ext == ".json":
                    with file_path.open("r", encoding="utf-8") as file:
                        data = json.load(file)
                    if not isinstance(data, dict):
                        continue
                else:
                    # .cs や .md 等で .meta.json がある場合はサイドカーからメタデータを取得
                    with meta_sidecar.open("r", encoding="utf-8") as mf:
                        data = json.load(mf)
                    if not isinstance(data, dict):
                        data = {}

                metadata = self._extract_metadata(
                    data=data,
                    file_path=file_path,
                    file_size=file_size,
                    mtime=mtime,
                    meta_mtime=meta_mtime,
                )
                new_index[rel_path] = metadata
                parsed_count += 1

            except Exception as exc:
                broken_count += 1
                logger.warning("Index構築エラー: %s / %s", file_path, exc)

        try:
            with index_path.open("w", encoding="utf-8") as file:
                json.dump(new_index, file, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Index保存失敗: %s", exc)

        self._index_cache[str(index_path)] = new_index
        elapsed = time.time() - start_time
        self._debug(
            f"index built root={root}, registered={len(new_index)}, "
            f"parsed={parsed_count}, reused={reused_count}, broken={broken_count}, "
            f"bytes={total_bytes}, time={elapsed:.3f}s"
        )
        return new_index

    # ========================================================
    # Lazy Load
    # ========================================================

    def load_all_json_from_dir(
        self,
        relative_dir_path: str | Path,
        index_filename: str = DEFAULT_INDEX_FILENAME,
        force_rebuild: bool = False,
    ) -> list[LazyKnowledge]:
        target_dir = self._resolve_dir(relative_dir_path)
        if not target_dir.exists():
            logger.warning("ディレクトリが存在しません: %s", target_dir)
            return []

        index_path = target_dir / index_filename
        index_key = str(index_path)
        index_data: Optional[dict[str, Any]] = None

        if not force_rebuild and index_key in self._index_cache:
            index_data = self._index_cache[index_key]
        else:
            if force_rebuild or not index_path.exists():
                self.build_index(target_dir, index_filename)
            try:
                with index_path.open("r", encoding="utf-8") as file:
                    raw = json.load(file)
                index_data = raw if isinstance(raw, dict) else {}
                self._index_cache[index_key] = index_data
            except Exception as exc:
                logger.error("Index読み込み失敗: %s", exc)
                return []

        loaded: list[LazyKnowledge] = []
        for rel_path, metadata in (index_data or {}).items():
            try:
                full_path = self._resolve_indexed_file(
                    indexed_path=rel_path,
                    knowledge_root=target_dir,
                )
            except ValueError:
                continue

            if not full_path.exists():
                continue

            loaded.append(
                LazyKnowledge(
                    base_dir=self.base_dir,
                    full_path=full_path,
                    rel_path=(
                        str(metadata.get("file_path"))
                        if isinstance(metadata, dict) and metadata.get("file_path")
                        else self._relative_to_base(full_path)
                    ),
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
            )
        return loaded

    # ========================================================
    # Keyword Search
    # ========================================================

    def _metadata_score(
        self,
        item: LazyKnowledge,
        keywords: Sequence[str],
    ) -> float:
        normalized_keywords = [
            str(keyword).strip().lower()
            for keyword in keywords
            if str(keyword).strip()
        ]
        if not normalized_keywords:
            return 0.0

        title = str(item.get("title", "")).lower()
        name = str(item.get("name", "")).lower()
        category = str(item.get("category", "")).lower()
        path = str(item.get("file_path", "")).lower()
        keyword_blob = " ".join(self._ensure_list(item.get("keywords", []))).lower()
        intent_blob = " ".join(self._ensure_list(item.get("intent", []))).lower()
        tag_blob = " ".join(self._ensure_list(item.get("tags", []))).lower()
        example_blob = " ".join(self._ensure_list(item.get("message_examples", []))).lower()

        score = 0.0
        for keyword in normalized_keywords:
            if keyword == title:
                score += 8.0
            elif keyword in title:
                score += 5.0
            if keyword == name:
                score += 7.0
            elif keyword in name:
                score += 4.0
            if keyword in keyword_blob:
                score += 4.0
            if keyword in intent_blob:
                score += 4.0
            if keyword in example_blob:
                score += 4.0
            if keyword in tag_blob:
                score += 3.0
            if keyword in category:
                score += 2.0
            if keyword in path:
                score += 1.0
        return score

    def search_by_keywords(
        self,
        relative_dir_path: str | Path,
        keywords: list[str],
        index_filename: str = DEFAULT_INDEX_FILENAME,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        if not keywords:
            return {}

        items = self.load_all_json_from_dir(relative_dir_path, index_filename)
        scored: list[tuple[float, LazyKnowledge]] = []

        for item in items:
            score = self._metadata_score(item, keywords)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].rel_path))
        if limit is not None:
            scored = scored[: max(0, int(limit))]

        matched: dict[str, Any] = {}
        for _, item in scored:
            try:
                matched[Path(item.full_path).name] = item.data
            except Exception as exc:
                logger.error("Knowledgeロード失敗 (%s): %s", item.rel_path, exc)
        return matched

    # ========================================================
    # Router / Loader Integration
    # ========================================================

    def _get_router(
        self,
        root: Path,
        threshold: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> KnowledgeRouter:
        key = (
            f"{root}|"
            f"{threshold if threshold is not None else self.threshold}|"
            f"{top_k if top_k is not None else self.top_k}"
        )
        router = self._router_cache.get(key)
        if router is not None:
            return router

        router = KnowledgeRouter(
            knowledge_dir=root,
            threshold=self.threshold if threshold is None else threshold,
            top_k=self.top_k if top_k is None else top_k,
        )
        self._router_cache[key] = router
        return router

    def _normalize_loaded_item(
        self,
        item: Any,
        root: Path,
        display_path: str,
    ) -> dict[str, Any]:
        content = getattr(item, "content", None)
        description = str(getattr(item, "description", "") or "")
        content_type = str(getattr(item, "content_type", "") or "")

        result: dict[str, Any] = {}
        if isinstance(content, dict):
            result.update(content)
        else:
            result["content"] = content

        if description and not result.get("description"):
            result["description"] = description

        result["_knowledge_path"] = display_path
        result["_knowledge_root"] = str(root)
        result["_knowledge_type"] = content_type
        return result

    def resolve(
        self,
        message: str,
        intent_analysis: Optional[dict[str, Any]] = None,
        knowledge_dirs: Optional[Sequence[str | Path]] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> KnowledgeResolveResult:
        result = KnowledgeResolveResult()
        roots: list[Path] = []

        if knowledge_dirs:
            for directory in knowledge_dirs:
                try:
                    roots.append(self._resolve_dir(directory))
                except Exception as exc:
                    result.warnings.append(str(exc))
        else:
            roots = list(self.knowledge_dirs)

        if not roots:
            result.warnings.append("Knowledge rootが登録されていません。")
            return result

        route_candidates: list[tuple[float, Path, str, str]] = []
        signals = dict(intent_analysis or {})
        if "active_context" not in signals:
            signals["active_context"] = (
                signals.get("current_topic") or signals.get("intent")
            )

        for root in roots:
            if not root.exists():
                result.warnings.append(f"Knowledge rootが存在しません: {root}")
                continue
            try:
                router = self._get_router(root=root, threshold=threshold, top_k=top_k)
                route = router.route(message, signals=signals)
            except Exception as exc:
                result.errors.append(f"KnowledgeRouter failed ({root}): {exc}")
                continue

            score_map = getattr(route, "scores", {})
            domains = getattr(route, "matched_domains", [])
            file_paths = getattr(route, "file_paths", [])

            for index, rel_path in enumerate(file_paths):
                score = (
                    float(score_map.get(str(rel_path), 0.0) or 0.0)
                    if isinstance(score_map, dict)
                    else 0.0
                )
                domain_name = (
                    str(domains[index]) if index < len(domains) else str(rel_path)
                )
                route_candidates.append((score, root, str(rel_path), domain_name))

        route_candidates.sort(key=lambda item: (-item[0], str(item[1]), item[2]))

        deduped: list[tuple[float, Path, str, str]] = []
        seen_abs_paths: set[str] = set()
        for candidate in route_candidates:
            score, root, rel_path, domain_name = candidate
            abs_path = (root / rel_path).resolve()
            key = str(abs_path).lower()
            if key in seen_abs_paths:
                continue
            seen_abs_paths.add(key)
            deduped.append(candidate)

        final_limit = self.top_k if top_k is None else top_k
        if final_limit is not None:
            deduped = deduped[: max(0, int(final_limit))]

        if not deduped:
            return result

        absolute_paths: list[str] = []
        display_paths: list[str] = []
        root_for_item: list[Path] = []

        for score, root, rel_path, domain_name in deduped:
            abs_path = (root / rel_path).resolve()
            try:
                abs_path.relative_to(root)
            except ValueError:
                result.warnings.append(f"不正Knowledge pathをスキップ: {rel_path}")
                continue
            if not abs_path.exists():
                result.warnings.append(f"Knowledge file not found: {abs_path}")
                continue

            absolute_paths.append(str(abs_path))
            display_path = self._relative_to_base(abs_path)
            display_paths.append(display_path)
            root_for_item.append(root)
            result.matched_paths.append(display_path)
            result.matched_domains.append(domain_name)
            result.scores[display_path] = score

        if not absolute_paths:
            return result

        try:
            load_result = self._loader.load(absolute_paths)
        except Exception as exc:
            result.errors.append(f"KnowledgeLoader failed: {exc}")
            return result

        loaded_items = getattr(load_result, "items", [])
        load_errors = getattr(load_result, "errors", [])

        for index, item in enumerate(loaded_items):
            root = root_for_item[index] if index < len(root_for_item) else self.base_dir
            display_path = (
                display_paths[index]
                if index < len(display_paths)
                else str(getattr(item, "path", ""))
            )
            result.items.append(
                self._normalize_loaded_item(
                    item=item,
                    root=root,
                    display_path=display_path,
                )
            )

        for error in load_errors:
            result.errors.append(
                f"{getattr(error, 'path', '')}: {getattr(error, 'reason', '')} {getattr(error, 'detail', '')}".strip()
            )

        return result

    # ========================================================
    # 🆕 ワンクリック企画書・Unity・OCRテンプレート展開ヘルパー
    # ========================================================

    def materialize_blueprint_from_resolved(
        self,
        resolved: KnowledgeResolveResult,
        output_subdir: str = "generated_projects",
    ) -> dict[str, Any]:
        """
        KnowledgeManager.resolve() でヒットした JSON 内に `blueprint_files` または `files` リスト
        （例: Unity の C# スクリプト群、アプリ開発の企画書 .md、OCR ツール設定など）が含まれている場合、
        ワンクリックで指定ディレクトリへ一括書き出しする。
        """
        files_to_write: list[dict[str, Any]] = []
        for item in resolved.items:
            raw_files = item.get("blueprint_files") or item.get("files") or []
            if isinstance(raw_files, list):
                for f_obj in raw_files:
                    if isinstance(f_obj, dict) and f_obj.get("path") and f_obj.get("content") is not None:
                        rel_target = f"{output_subdir.strip('/')}/{str(f_obj['path']).lstrip('/')}"
                        files_to_write.append({"path": rel_target, "content": f_obj["content"]})

        if not files_to_write:
            return {"status": "no_blueprint_files", "success": [], "failed": []}

        write_res = self.write_from_json_data(files_to_write)
        return {"status": "materialized", **write_res}

    # ========================================================
    # Health Check & File Writing & Career Feed
    # ========================================================

    def validate_knowledge_dir(self, knowledge_dir: str | Path) -> KnowledgeHealthReport:
        root = self._resolve_dir(knowledge_dir)
        report = KnowledgeHealthReport(root=str(root))
        if not root.exists():
            report.read_errors.append(f"directory not found: {root}")
            return report

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            name = file_path.name
            if name.lower() in self.EXCLUDED_INDEX_FILES or name.startswith("."):
                report.excluded_files.append(self._relative_to_base(file_path))
                continue
            if name.lower().endswith(".meta.json"):
                continue

            report.total_files += 1
            rel_path = self._relative_to_base(file_path)
            try:
                if file_path.stat().st_size == 0:
                    report.empty_files.append(rel_path)
                    continue
                if file_path.suffix.lower() == ".json":
                    with file_path.open("r", encoding="utf-8") as file:
                        data = json.load(file)
                    if not isinstance(data, dict):
                        report.unsupported_files.append(rel_path)
                        continue
                meta_path = file_path.with_name(name + ".meta.json")
                if meta_path.exists():
                    if meta_path.stat().st_size == 0:
                        report.empty_files.append(f"{rel_path}.meta.json")
                        continue
                    with meta_path.open("r", encoding="utf-8") as mf:
                        json.load(mf)
                report.valid_files += 1
            except json.JSONDecodeError:
                report.broken_files.append(rel_path)
            except Exception as exc:
                report.read_errors.append(f"{rel_path}: {exc}")
        return report

    def validate_all(self) -> list[KnowledgeHealthReport]:
        return [self.validate_knowledge_dir(root) for root in self.knowledge_dirs]

    def write_file(self, relative_path: str | Path, content: str) -> bool:
        try:
            target_path = Path(self._safe_join_path(relative_path))
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(str(content), encoding="utf-8")
            return True
        except Exception as exc:
            logger.error("ファイル保存エラー (%s): %s", relative_path, exc)
            return False

    def write_from_json_data(self, files_list: list[dict[str, Any]]) -> dict[str, list[str]]:
        success_files: list[str] = []
        failed_files: list[str] = []
        for file_info in files_list:
            path = file_info.get("path")
            content = file_info.get("content")
            if path and content is not None:
                if self.write_file(path, str(content)):
                    success_files.append(str(path))
                else:
                    failed_files.append(str(path))
        return {"success": success_files, "failed": failed_files}

    def write_from_markdown_text(self, markdown_text: str) -> dict[str, list[str]]:
        pattern = (
            r"(?i)(?:file|path)[\s:\*]*([a-zA-Z0-9_\-\.\/]+)\s*\n+"
            r"```[a-zA-Z0-9_+\-#]*\n([\s\S]*?)\n```"
        )
        matches = re.findall(pattern, markdown_text)
        files_to_write = [
            {"path": path.strip(), "content": content}
            for path, content in matches
        ]
        return self.write_from_json_data(files_to_write)
