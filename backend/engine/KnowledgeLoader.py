# backend/engine/KnowledgeLoader.py
from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
import xml.etree.ElementTree as ET

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


logger = logging.getLogger(__name__)


# ============================================================
# Optional YAML
# ============================================================

try:
    import yaml  # type: ignore

    YAML_AVAILABLE = True

except Exception:
    yaml = None  # type: ignore
    YAML_AVAILABLE = False


# ============================================================
# Constants
# ============================================================

# KnowledgeRouter が検索・ルーティングのために利用する値。
#
# 原則として、これらは検索用Metadataなので
# LLMへ本文として二重に渡す必要はない。
#
# ただし project_types / features / technologies などは
# 実際のアプリ生成にも重要なので削除対象には入れない。
_ROUTING_ONLY_KEYS = {
    "id",
    "name",
    "title",
    "description",
    "category",
    "domain",
    "domains",
    "keywords",
    "aliases",
    "topics",
    "intent",
    "intents",
    "tags",
    "message_examples",
    "retrieval",
    "search_metadata",
    "routing",
    "weight",
    "priority",
    "negative_keywords",
    "exclude_keywords",
}


# Markdown frontmatter
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*(?:\n|$)",
    re.DOTALL,
)


_DESCRIPTION_LINE_RE = re.compile(
    r"^description:\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)


# textとして安全に扱うファイル
TEXT_EXTENSIONS = {
    # document
    ".txt",
    ".md",
    ".mdx",
    ".rst",

    # web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",

    # JS / TS
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",

    # Python
    ".py",
    ".pyi",

    # C / C++
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cxx",
    ".hpp",
    ".hxx",

    # C#
    ".cs",

    # Java / Kotlin
    ".java",
    ".kt",
    ".kts",

    # Rust / Go
    ".rs",
    ".go",

    # Ruby / PHP
    ".rb",
    ".php",

    # shell
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".bat",
    ".cmd",

    # config
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".properties",
    ".toml",

    # SQL
    ".sql",

    # Unity / Shader
    ".shader",
    ".compute",
    ".cginc",
    ".hlsl",
    ".glsl",

    # misc code/data
    ".vue",
    ".svelte",
    ".graphql",
    ".gql",
    ".proto",

    # project / build
    ".gradle",
    ".cmake",

    # log
    ".log",
}


YAML_EXTENSIONS = {
    ".yml",
    ".yaml",
}


XML_EXTENSIONS = {
    ".xml",
}


JSON_EXTENSIONS = {
    ".json",
}


MARKDOWN_EXTENSIONS = {
    ".md",
    ".mdx",
}


# 明らかなバイナリ
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".svgz",

    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",

    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",

    ".exe",
    ".dll",
    ".so",
    ".dylib",

    ".pdf",

    ".woff",
    ".woff2",
    ".ttf",
    ".otf",

    ".blend",

    ".db",
    ".sqlite",
    ".sqlite3",
}


# ============================================================
# Data Models
# ============================================================


@dataclass
class LoadedKnowledge:
    """
    KnowledgeLoader が読み込んだKnowledge 1件。

    既存コード互換:
        path
        domain_label
        content_type
        description
        content

    追加:
        source_path
        size_bytes
        metadata
        encoding
        cached
    """

    path: str

    domain_label: str

    content_type: str

    description: str = ""

    content: Any = None

    source_path: str = ""

    size_bytes: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    encoding: str = "utf-8"

    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "domain_label": self.domain_label,
            "content_type": self.content_type,
            "description": self.description,
            "content": self.content,
            "source_path": self.source_path,
            "size_bytes": self.size_bytes,
            "metadata": dict(self.metadata),
            "encoding": self.encoding,
            "cached": self.cached,
        }


@dataclass
class LoadError:
    """
    Knowledge 1件の読み込み失敗情報。
    """

    path: str

    reason: str

    detail: str = ""

    exception_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reason": self.reason,
            "detail": self.detail,
            "exception_type": self.exception_type,
        }


@dataclass
class LoadResult:
    """
    KnowledgeLoader.load() の結果。

    既存コード互換を維持。
    """

    items: list[LoadedKnowledge] = field(
        default_factory=list
    )

    errors: list[LoadError] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    requested_count: int = 0

    loaded_count: int = 0

    cache_hits: int = 0

    skipped_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def partial_success(self) -> bool:
        return (
            bool(self.items)
            and bool(self.errors)
        )

    def as_merged_dict(
        self,
    ) -> dict[str, Any]:

        return {
            item.domain_label:
                item.content
            for item in self.items
        }

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "ok": self.ok,
            "partial_success":
                self.partial_success,

            "requested_count":
                self.requested_count,

            "loaded_count":
                self.loaded_count,

            "cache_hits":
                self.cache_hits,

            "skipped_count":
                self.skipped_count,

            "items": [
                item.to_dict()
                for item in self.items
            ],

            "errors": [
                error.to_dict()
                for error in self.errors
            ],

            "warnings":
                list(self.warnings),
        }


@dataclass
class _ResolvedFile:
    """
    Loader内部専用。

    absolute path と表示用path、
    どのKnowledge rootに属するかを保持。
    """

    absolute_path: Path

    knowledge_root: Path

    display_path: str


@dataclass
class _CacheEntry:
    """
    Loader cache。
    """

    mtime_ns: int

    size_bytes: int

    item: LoadedKnowledge


# ============================================================
# Knowledge Loader
# ============================================================


class KnowledgeLoader:
    """
    Knowledgeの実ファイル読込専用クラス。

    ------------------------------------------------------------
    Responsibility
    ------------------------------------------------------------

    KnowledgeRouter:
        どのKnowledgeを使うか決める

    KnowledgeLoader:
        指定されたKnowledgeを安全に読む

    KnowledgeManager:
        Router + Loaderを統括

    ------------------------------------------------------------
    Loaderがやらないこと
    ------------------------------------------------------------

    - Intent解析
    - IntentInspectorの再実行
    - Knowledge選択
    - Knowledgeスコアリング
    - Handler選択
    - LLM呼び出し
    - Prompt生成

    ------------------------------------------------------------
    Supported
    ------------------------------------------------------------

    JSON
    YAML / YML
    Markdown
    XML
    Python
    JS / TS / React
    C / C++
    C#
    SQL
    Unity Shader
    HTML / CSS
    その他テキストファイル

    ------------------------------------------------------------
    Security
    ------------------------------------------------------------

    登録済み Knowledge Root 外のファイルは
    原則として読み込まない。

    ../../secret.txt のような
    path traversal を拒否する。
    """

    def __init__(
        self,
        knowledge_dirs: Sequence[
            str | Path
        ],
        cache_enabled: bool = True,
        allow_unknown_text: bool = True,
        max_file_size_bytes: int | None = None,
        strip_routing_metadata: bool = True,
        enable_debug: bool = False,
    ) -> None:

        self.cache_enabled = bool(
            cache_enabled
        )

        self.allow_unknown_text = bool(
            allow_unknown_text
        )

        self.max_file_size_bytes = (
            int(max_file_size_bytes)
            if max_file_size_bytes
            is not None
            else None
        )

        self.strip_routing_metadata = bool(
            strip_routing_metadata
        )

        self.enable_debug = bool(
            enable_debug
        )

        self.knowledge_dirs: list[
            Path
        ] = []

        for raw_dir in knowledge_dirs:

            path = Path(
                raw_dir
            ).expanduser().resolve()

            if path not in self.knowledge_dirs:
                self.knowledge_dirs.append(
                    path
                )

        self._cache: dict[
            str,
            _CacheEntry,
        ] = {}

        self._debug(
            "initialized "
            f"roots={self.knowledge_dirs}, "
            f"cache={self.cache_enabled}"
        )

    # ========================================================
    # Public API
    # ========================================================

    def load(
        self,
        file_paths: Sequence[
            str | Path
        ],
    ) -> LoadResult:
        """
        複数Knowledgeを読み込む。

        KnowledgeManager.resolve() からの呼び出しを想定。
        """

        result = LoadResult(
            requested_count=len(
                file_paths
            )
        )

        seen: set[str] = set()

        for raw_path in file_paths:

            path_text = str(
                raw_path
            ).strip()

            if not path_text:
                result.skipped_count += 1
                continue

            resolved = self._resolve_file(
                path_text
            )

            if resolved is None:

                error = LoadError(
                    path=path_text,
                    reason="not_found",
                    detail=(
                        "登録済みKnowledgeルート内に"
                        "ファイルがありません。"
                    ),
                )

                result.errors.append(
                    error
                )

                self._log_error(
                    error
                )

                continue

            absolute_key = str(
                resolved.absolute_path
            ).casefold()

            # 同一ファイル重複ロード防止
            if absolute_key in seen:

                result.skipped_count += 1

                self._debug(
                    "duplicate skip: "
                    f"{resolved.absolute_path}"
                )

                continue

            seen.add(
                absolute_key
            )

            item, error, cache_hit = (
                self._read_resolved(
                    resolved
                )
            )

            if item is not None:

                result.items.append(
                    item
                )

                result.loaded_count += 1

                if cache_hit:
                    result.cache_hits += 1

                logger.info(
                    "📚 [KnowledgeLoader] "
                    "読み込み成功: %s (%s)",
                    item.path,
                    item.content_type,
                )

            if error is not None:

                result.errors.append(
                    error
                )

                self._log_error(
                    error
                )

        return result

    async def load_async(
        self,
        file_paths: Sequence[
            str | Path
        ],
    ) -> LoadResult:
        """
        EventLoopをブロックしないLoader。

        ファイルIOはthreadへ逃がす。
        """

        return await asyncio.to_thread(
            self.load,
            file_paths,
        )

    def load_one(
        self,
        file_path: str | Path,
    ) -> LoadedKnowledge | None:
        """
        単一ファイル用の簡易API。
        """

        result = self.load(
            [file_path]
        )

        if not result.items:
            return None

        return result.items[0]

    async def load_one_async(
        self,
        file_path: str | Path,
    ) -> LoadedKnowledge | None:

        return await asyncio.to_thread(
            self.load_one,
            file_path,
        )

    # ========================================================
    # Knowledge Root
    # ========================================================

    def register_knowledge_dir(
        self,
        knowledge_dir: str | Path,
    ) -> Path:
        """
        Loader単体でもKnowledge Rootを追加可能。
        """

        resolved = Path(
            knowledge_dir
        ).expanduser().resolve()

        if resolved not in self.knowledge_dirs:

            self.knowledge_dirs.append(
                resolved
            )

        self._debug(
            f"root registered: {resolved}"
        )

        return resolved

    def configure_knowledge_dirs(
        self,
        knowledge_dirs: Sequence[
            str | Path
        ],
    ) -> None:
        """
        Knowledge Rootを完全置換。
        """

        roots: list[Path] = []

        for raw in knowledge_dirs:

            path = Path(
                raw
            ).expanduser().resolve()

            if path not in roots:
                roots.append(path)

        self.knowledge_dirs = roots

        # Root変更後はcacheが危険なので破棄
        self.clear_cache()

    # ========================================================
    # Cache
    # ========================================================

    def clear_cache(
        self,
    ) -> None:

        self._cache.clear()

        self._debug(
            "cache cleared"
        )

    def invalidate(
        self,
        file_path: str | Path,
    ) -> None:
        """
        特定ファイルだけキャッシュ削除。
        """

        raw_path = str(
            file_path
        )

        resolved = self._resolve_file(
            raw_path
        )

        if resolved is None:
            return

        key = str(
            resolved.absolute_path
        )

        self._cache.pop(
            key,
            None,
        )

    # ========================================================
    # Path Resolution / Security
    # ========================================================

    def _resolve_file(
        self,
        file_path: str,
    ) -> _ResolvedFile | None:
        """
        以下を受け付ける。

        1. KnowledgeManagerが渡すabsolute path
        2. KnowledgeRouterが返すroot-relative path

        ただし必ずknowledge_dirs内に存在する必要がある。
        """

        if not file_path:
            return None

        candidate = Path(
            file_path
        ).expanduser()

        # ----------------------------------------------------
        # absolute path
        # ----------------------------------------------------

        if candidate.is_absolute():

            try:
                resolved = (
                    candidate.resolve()
                )

            except Exception:
                return None

            if not resolved.is_file():
                return None

            for root in self.knowledge_dirs:

                if not self._is_inside(
                    resolved,
                    root,
                ):
                    continue

                relative = (
                    resolved.relative_to(
                        root
                    )
                )

                return _ResolvedFile(
                    absolute_path=
                        resolved,

                    knowledge_root=
                        root,

                    display_path=
                        relative.as_posix(),
                )

            return None

        # ----------------------------------------------------
        # relative path
        # ----------------------------------------------------

        for root in self.knowledge_dirs:

            try:
                resolved = (
                    root
                    / candidate
                ).resolve()

            except Exception:
                continue

            # ../../foo 等を拒否
            if not self._is_inside(
                resolved,
                root,
            ):
                continue

            if not resolved.is_file():
                continue

            relative = (
                resolved.relative_to(
                    root
                )
            )

            return _ResolvedFile(
                absolute_path=
                    resolved,

                knowledge_root=
                    root,

                display_path=
                    relative.as_posix(),
            )

        return None

    @staticmethod
    def _is_inside(
        target: Path,
        root: Path,
    ) -> bool:

        try:

            target.resolve().relative_to(
                root.resolve()
            )

            return True

        except ValueError:

            return False

    # ========================================================
    # Read Dispatcher
    # ========================================================

    def _read_resolved(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
        bool,
    ]:

        abs_path = (
            resolved.absolute_path
        )

        try:

            stat = abs_path.stat()

        except OSError as exc:

            return (
                None,
                self._error(
                    resolved.display_path,
                    "stat_error",
                    exc,
                ),
                False,
            )

        # ----------------------------------------------------
        # File size
        # ----------------------------------------------------

        if (
            self.max_file_size_bytes
            is not None
            and stat.st_size
            > self.max_file_size_bytes
        ):

            return (
                None,
                LoadError(
                    path=
                        resolved.display_path,

                    reason=
                        "file_too_large",

                    detail=(
                        f"{stat.st_size} bytes > "
                        f"{self.max_file_size_bytes} bytes"
                    ),
                ),
                False,
            )

        # ----------------------------------------------------
        # Cache
        # ----------------------------------------------------

        cache_key = str(
            abs_path
        )

        if self.cache_enabled:

            cached = self._cache.get(
                cache_key
            )

            if (
                cached is not None
                and cached.mtime_ns
                == stat.st_mtime_ns
                and cached.size_bytes
                == stat.st_size
            ):

                # キャッシュオブジェクトを書き換えないためコピー
                item = copy.deepcopy(
                    cached.item
                )

                item.cached = True

                return (
                    item,
                    None,
                    True,
                )

        # ----------------------------------------------------
        # Binary
        # ----------------------------------------------------

        suffix = (
            abs_path.suffix
            .casefold()
        )

        if suffix in BINARY_EXTENSIONS:

            return (
                None,
                LoadError(
                    path=
                        resolved.display_path,

                    reason=
                        "binary_unsupported",

                    detail=(
                        "バイナリファイルは"
                        "KnowledgeLoaderの対象外です。"
                    ),
                ),
                False,
            )

        # ----------------------------------------------------
        # Dispatch
        # ----------------------------------------------------

        if suffix in JSON_EXTENSIONS:

            item, error = (
                self._read_json(
                    resolved
                )
            )

        elif suffix in YAML_EXTENSIONS:

            item, error = (
                self._read_yaml(
                    resolved
                )
            )

        elif suffix in MARKDOWN_EXTENSIONS:

            item, error = (
                self._read_markdown(
                    resolved
                )
            )

        elif suffix in XML_EXTENSIONS:

            item, error = (
                self._read_xml(
                    resolved
                )
            )

        elif (
            suffix in TEXT_EXTENSIONS
            or self.allow_unknown_text
        ):

            item, error = (
                self._read_text(
                    resolved
                )
            )

        else:

            item = None

            error = LoadError(
                path=
                    resolved.display_path,

                reason=
                    "unsupported_type",

                detail=
                    f"未対応拡張子: {suffix}",
            )

        # ----------------------------------------------------
        # Cache write
        # ----------------------------------------------------

        if (
            item is not None
            and error is None
            and self.cache_enabled
        ):

            item.cached = False

            self._cache[
                cache_key
            ] = _CacheEntry(
                mtime_ns=
                    stat.st_mtime_ns,

                size_bytes=
                    stat.st_size,

                item=
                    copy.deepcopy(item),
            )

        return (
            item,
            error,
            False,
        )

    # ========================================================
    # JSON
    # ========================================================

    def _read_json(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
    ]:

        abs_path = (
            resolved.absolute_path
        )

        try:

            with abs_path.open(
                "r",
                encoding="utf-8-sig",
            ) as file:

                data = json.load(
                    file
                )

        except json.JSONDecodeError as exc:

            return (
                None,
                self._error(
                    resolved.display_path,
                    "invalid_json",
                    exc,
                ),
            )

        except (
            OSError,
            UnicodeError,
        ) as exc:

            return (
                None,
                self._error(
                    resolved.display_path,
                    "read_error",
                    exc,
                ),
            )

        description = ""

        metadata: dict[
            str,
            Any,
        ] = {}

        if isinstance(
            data,
            dict,
        ):

            description = str(
                data.get(
                    "description",
                    "",
                )
                or data.get(
                    "summary",
                    "",
                )
                or ""
            )

            metadata = (
                self._extract_metadata(
                    data
                )
            )

            if (
                self.strip_routing_metadata
            ):

                content = {
                    key: value
                    for key, value
                    in data.items()
                    if key
                    not in _ROUTING_ONLY_KEYS
                }

            else:

                content = data

        else:

            content = data

        return (
            self._make_item(
                resolved=
                    resolved,

                content_type=
                    "json",

                content=
                    content,

                description=
                    description,

                metadata=
                    metadata,
            ),
            None,
        )

    # ========================================================
    # YAML
    # ========================================================

    def _read_yaml(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
    ]:
        """
        Repomix YAML対応。

        PyYAMLが存在:
            safe_load()

        PyYAML無し:
            textとして読み込み

        これによりPyYAML未導入でも
        Loader全体が停止しない。
        """

        text, error = (
            self._read_text_raw(
                resolved
            )
        )

        if error is not None:

            return (
                None,
                error,
            )

        assert text is not None

        # --------------------------------------------
        # PyYAMLなし
        # --------------------------------------------

        if not YAML_AVAILABLE:

            return (
                self._make_item(
                    resolved=
                        resolved,

                    content_type=
                        "yaml_text",

                    content=
                        text,

                    description="",

                    metadata={
                        "yaml_parsed":
                            False,

                        "yaml_library":
                            "not_available",
                    },
                ),
                None,
            )

        # --------------------------------------------
        # Parse
        # --------------------------------------------

        try:

            data = yaml.safe_load(
                text
            )

        except Exception as exc:

            return (
                None,
                self._error(
                    resolved.display_path,
                    "invalid_yaml",
                    exc,
                ),
            )

        description = ""

        metadata: dict[
            str,
            Any,
        ] = {
            "yaml_parsed":
                True,
        }

        if isinstance(
            data,
            dict,
        ):

            description = str(
                data.get(
                    "description",
                    "",
                )
                or data.get(
                    "summary",
                    "",
                )
                or ""
            )

            metadata.update(
                self._extract_metadata(
                    data
                )
            )

            if self.strip_routing_metadata:

                content = {
                    key: value
                    for key, value
                    in data.items()
                    if key
                    not in _ROUTING_ONLY_KEYS
                }

            else:

                content = data

        else:

            content = data

        return (
            self._make_item(
                resolved=
                    resolved,

                content_type=
                    "yaml",

                content=
                    content,

                description=
                    description,

                metadata=
                    metadata,
            ),
            None,
        )

    # ========================================================
    # Markdown
    # ========================================================

    def _read_markdown(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
    ]:
        """
        frontmatterあり/なし両方を許可。

        旧版:
            frontmatter無し → error

        新版:
            frontmatter無しでも本文をKnowledgeとして読める
        """

        text, error = (
            self._read_text_raw(
                resolved
            )
        )

        if error is not None:

            return (
                None,
                error,
            )

        assert text is not None

        match = (
            _FRONTMATTER_RE.match(
                text
            )
        )

        description = ""

        metadata: dict[
            str,
            Any,
        ] = {}

        body = text

        if match is not None:

            frontmatter_text = (
                match.group(1)
            )

            metadata = (
                self._parse_frontmatter(
                    frontmatter_text
                )
            )

            description = str(
                metadata.get(
                    "description",
                    "",
                )
                or ""
            )

            if not description:

                description_match = (
                    _DESCRIPTION_LINE_RE.search(
                        frontmatter_text
                    )
                )

                if description_match:

                    description = (
                        description_match
                        .group(1)
                        .strip()
                        .strip("'\"")
                    )

            body = (
                text[
                    match.end():
                ].strip()
            )

        return (
            self._make_item(
                resolved=
                    resolved,

                content_type=
                    "markdown",

                content=
                    body,

                description=
                    description,

                metadata=
                    metadata,
            ),
            None,
        )

    # ========================================================
    # XML
    # ========================================================

    def _read_xml(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
    ]:
        """
        XMLは巨大Repomixでも利用する可能性があるため
        raw textを保持する。

        同時にXMLとして最低限validかだけ確認する。
        """

        text, error = (
            self._read_text_raw(
                resolved
            )
        )

        if error is not None:

            return (
                None,
                error,
            )

        assert text is not None

        xml_valid = True

        root_tag = ""

        try:

            root = ET.fromstring(
                text
            )

            root_tag = str(
                root.tag
            )

        except ET.ParseError:

            # Repomix XMLは構成によって
            # 独立rootが無いケースも考慮し、
            # 読込自体は失敗させない。
            xml_valid = False

        return (
            self._make_item(
                resolved=
                    resolved,

                content_type=
                    "xml",

                content=
                    text,

                metadata={
                    "xml_valid":
                        xml_valid,

                    "root_tag":
                        root_tag,
                },
            ),
            None,
        )

    # ========================================================
    # Plain Text / Code
    # ========================================================

    def _read_text(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        LoadedKnowledge | None,
        LoadError | None,
    ]:

        text, error = (
            self._read_text_raw(
                resolved
            )
        )

        if error is not None:

            return (
                None,
                error,
            )

        assert text is not None

        suffix = (
            resolved
            .absolute_path
            .suffix
            .lstrip(".")
            .casefold()
        )

        content_type = (
            suffix
            if suffix
            else "text"
        )

        return (
            self._make_item(
                resolved=
                    resolved,

                content_type=
                    content_type,

                content=
                    text,
            ),
            None,
        )

    def _read_text_raw(
        self,
        resolved: _ResolvedFile,
    ) -> tuple[
        str | None,
        LoadError | None,
    ]:
        """
        encodingを段階的に試す。

        utf-8-sig
        utf-8
        cp932
        shift_jis

        Windows開発環境も考慮。
        """

        encodings = (
            "utf-8-sig",
            "utf-8",
            "cp932",
            "shift_jis",
        )

        last_error: Exception | None = None

        for encoding in encodings:

            try:

                text = (
                    resolved
                    .absolute_path
                    .read_text(
                        encoding=
                            encoding,
                    )
                )

                return (
                    text,
                    None,
                )

            except UnicodeDecodeError as exc:

                last_error = exc

                continue

            except OSError as exc:

                return (
                    None,
                    self._error(
                        resolved.display_path,
                        "read_error",
                        exc,
                    ),
                )

        return (
            None,
            LoadError(
                path=
                    resolved.display_path,

                reason=
                    "encoding_error",

                detail=
                    str(last_error or ""),
            ),
        )

    # ========================================================
    # Metadata
    # ========================================================

    def _extract_metadata(
        self,
        data: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        """
        Router / Project Knowledgeとの共通Metadataを保持する。

        contentからはrouting-only fieldを削除しても
        LoadedKnowledge.metadataには残る。
        """

        retrieval = (
            data.get(
                "retrieval",
                {},
            )
        )

        if not isinstance(
            retrieval,
            dict,
        ):

            retrieval = {}

        search_metadata = (
            data.get(
                "search_metadata",
                {},
            )
        )

        if not isinstance(
            search_metadata,
            dict,
        ):

            search_metadata = {}

        metadata = {
            "id":
                data.get("id"),

            "name":
                data.get("name"),

            "title":
                data.get("title"),

            "category":
                data.get("category"),

            "domain":
                data.get("domain"),

            "domains":
                data.get("domains"),

            "keywords":
                self._merge_list_values(
                    data.get("keywords"),
                    retrieval.get(
                        "keywords"
                    ),
                    search_metadata.get(
                        "keywords"
                    ),
                ),

            "intents":
                self._merge_list_values(
                    data.get("intent"),
                    data.get("intents"),
                    retrieval.get(
                        "intent"
                    ),
                    retrieval.get(
                        "intents"
                    ),
                ),

            "tags":
                self._merge_list_values(
                    data.get("tags"),
                    retrieval.get("tags"),
                    search_metadata.get(
                        "tags"
                    ),
                ),

            "actions":
                self._merge_list_values(
                    data.get("actions"),
                    retrieval.get(
                        "actions"
                    ),
                ),

            "targets":
                self._merge_list_values(
                    data.get("targets"),
                    retrieval.get(
                        "targets"
                    ),
                ),

            "project_types":
                self._merge_list_values(
                    data.get(
                        "project_type"
                    ),
                    data.get(
                        "project_types"
                    ),
                    retrieval.get(
                        "project_type"
                    ),
                    retrieval.get(
                        "project_types"
                    ),
                ),

            "features":
                self._merge_list_values(
                    data.get("features"),
                    retrieval.get(
                        "features"
                    ),
                ),

            "technologies":
                self._merge_list_values(
                    data.get(
                        "technologies"
                    ),
                    data.get(
                        "frameworks"
                    ),
                    retrieval.get(
                        "technologies"
                    ),
                    retrieval.get(
                        "frameworks"
                    ),
                ),

            "knowledge_types":
                self._merge_list_values(
                    data.get(
                        "knowledge_type"
                    ),
                    data.get(
                        "knowledge_types"
                    ),
                ),
        }

        # None/空のみ削除
        return {
            key: value
            for key, value
            in metadata.items()
            if value not in (
                None,
                "",
                [],
                {},
            )
        }

    # ========================================================
    # Markdown Frontmatter
    # ========================================================

    def _parse_frontmatter(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        PyYAMLがあればYAMLとして読む。

        無ければ最小parser。
        """

        if YAML_AVAILABLE:

            try:

                parsed = yaml.safe_load(
                    text
                )

                if isinstance(
                    parsed,
                    dict,
                ):

                    return parsed

            except Exception:
                pass

        return self._parse_simple_frontmatter(
            text
        )

    def _parse_simple_frontmatter(
        self,
        text: str,
    ) -> dict[str, Any]:

        metadata: dict[
            str,
            Any,
        ] = {}

        lines = text.splitlines()

        index = 0

        while index < len(lines):

            line = (
                lines[index]
                .rstrip()
            )

            if (
                not line.strip()
                or line
                .strip()
                .startswith("#")
                or ":" not in line
            ):

                index += 1

                continue

            key, raw_value = (
                line.split(
                    ":",
                    1,
                )
            )

            key = key.strip()

            raw_value = (
                raw_value.strip()
            )

            # ----------------------------------------
            # YAML list
            # ----------------------------------------

            if not raw_value:

                items: list[
                    str
                ] = []

                cursor = (
                    index + 1
                )

                while cursor < len(
                    lines
                ):

                    next_line = (
                        lines[
                            cursor
                        ]
                        .strip()
                    )

                    if not next_line.startswith(
                        "- "
                    ):
                        break

                    item = (
                        next_line[2:]
                        .strip()
                        .strip("'\"")
                    )

                    if item:
                        items.append(
                            item
                        )

                    cursor += 1

                metadata[
                    key
                ] = (
                    items
                    if items
                    else ""
                )

                index = cursor

                continue

            # ----------------------------------------
            # inline list
            # ----------------------------------------

            if (
                raw_value.startswith(
                    "["
                )
                and raw_value.endswith(
                    "]"
                )
            ):

                inner = (
                    raw_value[
                        1:-1
                    ].strip()
                )

                if inner:

                    metadata[
                        key
                    ] = [
                        item.strip()
                        .strip("'\"")
                        for item
                        in inner.split(",")
                    ]

                else:

                    metadata[
                        key
                    ] = []

            else:

                value = (
                    raw_value
                    .strip("'\"")
                )

                lowered = (
                    value.casefold()
                )

                if lowered == "true":

                    metadata[
                        key
                    ] = True

                elif lowered == "false":

                    metadata[
                        key
                    ] = False

                elif lowered in {
                    "null",
                    "none",
                    "~",
                }:

                    metadata[
                        key
                    ] = None

                else:

                    try:

                        if "." in value:

                            metadata[
                                key
                            ] = float(
                                value
                            )

                        else:

                            metadata[
                                key
                            ] = int(
                                value
                            )

                    except ValueError:

                        metadata[
                            key
                        ] = value

            index += 1

        return metadata

    # ========================================================
    # Item Builder
    # ========================================================

    def _make_item(
        self,
        resolved: _ResolvedFile,
        content_type: str,
        content: Any,
        description: str = "",
        metadata: dict[
            str,
            Any,
        ] | None = None,
    ) -> LoadedKnowledge:

        try:

            size_bytes = (
                resolved
                .absolute_path
                .stat()
                .st_size
            )

        except OSError:

            size_bytes = 0

        return LoadedKnowledge(
            path=
                resolved.display_path,

            domain_label=
                self._domain_label(
                    resolved.display_path
                ),

            content_type=
                content_type,

            description=
                str(
                    description
                    or ""
                ),

            content=
                content,

            source_path=
                str(
                    resolved.absolute_path
                ),

            size_bytes=
                size_bytes,

            metadata=
                metadata or {},

            encoding=
                "utf-8",

            cached=
                False,
        )

    # ========================================================
    # Domain Label
    # ========================================================

    @staticmethod
    def _domain_label(
        display_path: str,
    ) -> str:
        """
        projects/font_app/features.json

        ↓

        projects/font_app/features
        """

        return (
            Path(
                display_path
            )
            .with_suffix("")
            .as_posix()
        )

    # ========================================================
    # List helpers
    # ========================================================

    @staticmethod
    def _ensure_list(
        value: Any,
    ) -> list[str]:

        if value is None:

            return []

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            return (
                [value]
                if value
                else []
            )

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            result: list[
                str
            ] = []

            for item in value:

                if isinstance(
                    item,
                    dict,
                ):

                    item = (
                        item.get("name")
                        or item.get("id")
                        or item.get("value")
                    )

                text = (
                    str(item).strip()
                    if item
                    is not None
                    else ""
                )

                if text:

                    result.append(
                        text
                    )

            return result

        if isinstance(
            value,
            dict,
        ):

            candidate = (
                value.get("name")
                or value.get("id")
                or value.get("value")
            )

            return (
                KnowledgeLoader
                ._ensure_list(
                    candidate
                )
            )

        text = str(
            value
        ).strip()

        return (
            [text]
            if text
            else []
        )

    def _merge_list_values(
        self,
        *values: Any,
    ) -> list[str]:

        result: list[str] = []

        seen: set[str] = set()

        for raw_value in values:

            for item in self._ensure_list(
                raw_value
            ):

                key = (
                    item
                    .strip()
                    .casefold()
                )

                if (
                    not key
                    or key in seen
                ):
                    continue

                seen.add(
                    key
                )

                result.append(
                    item
                )

        return result

    # ========================================================
    # Error
    # ========================================================

    @staticmethod
    def _error(
        path: str,
        reason: str,
        exc: Exception,
    ) -> LoadError:

        return LoadError(
            path=
                path,

            reason=
                reason,

            detail=
                str(exc),

            exception_type=
                exc.__class__.__name__,
        )

    @staticmethod
    def _log_error(
        error: LoadError,
    ) -> None:

        logger.warning(
            "⚠️ [KnowledgeLoader] "
            "%s: %s - %s",
            error.reason,
            error.path,
            error.detail,
        )

    # ========================================================
    # Debug
    # ========================================================

    def _debug(
        self,
        message: str,
    ) -> None:

        if not self.enable_debug:
            return

        logger.debug(
            "[KnowledgeLoader] %s",
            message,
        )


# ============================================================
# Standalone Test
# ============================================================


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "KnowledgeLoader standalone debug"
        )
    )

    parser.add_argument(
        "knowledge_dir",
        type=Path,
    )

    parser.add_argument(
        "files",
        nargs="+",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=(
            logging.DEBUG
            if args.debug
            else logging.INFO
        ),
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s - "
            "%(message)s"
        ),
    )

    loader = KnowledgeLoader(
        knowledge_dirs=[
            args.knowledge_dir
        ],
        cache_enabled=
            not args.no_cache,
        enable_debug=
            args.debug,
    )

    load_result = loader.load(
        args.files
    )

    print(
        json.dumps(
            load_result.to_dict(),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
