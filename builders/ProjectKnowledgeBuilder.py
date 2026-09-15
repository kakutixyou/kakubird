# backend/engine/knowledge/ProjectKnowledgeBuilder.py
from __future__ import annotations

import asyncio
import json
import logging
import re

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


from api.services.manager.KnowledgeManager import KnowledgeManager


logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================


DEFAULT_SOURCE_DIR = (
    "backend/engine/knowledge/project_data"
)

DEFAULT_OUTPUT_DIR = (
    "backend/engine/knowledge/projects"
)


IGNORED_JSON_FILES = {
    "index.json",
    "registry.json",
    "project_knowledge.json",
}


# Analyzerの出力ファイル名が完全に統一されていなくても
# ある程度意味を推測できるようにする。
CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "architecture": (
        "architecture",
        "architectures",
        "structure",
        "project_structure",
        "folder_structure",
        "modules",
    ),
    "features": (
        "feature",
        "features",
        "function",
        "functions",
        "capability",
        "capabilities",
    ),
    "dependencies": (
        "dependency",
        "dependencies",
        "package",
        "packages",
        "library",
        "libraries",
    ),
    "technologies": (
        "technology",
        "technologies",
        "framework",
        "frameworks",
        "language",
        "languages",
        "stack",
    ),
    "entry_points": (
        "entry_point",
        "entry_points",
        "entrypoint",
        "main",
        "startup",
        "bootstrap",
    ),
    "apis": (
        "api",
        "apis",
        "route",
        "routes",
        "endpoint",
        "endpoints",
    ),
    "components": (
        "component",
        "components",
        "ui",
        "screen",
        "screens",
        "page",
        "pages",
    ),
    "models": (
        "model",
        "models",
        "entity",
        "entities",
        "schema",
        "schemas",
    ),
    "database": (
        "database",
        "db",
        "table",
        "tables",
        "repository",
        "repositories",
    ),
    "services": (
        "service",
        "services",
        "usecase",
        "usecases",
        "logic",
    ),
    "tests": (
        "test",
        "tests",
        "testing",
    ),
    "security": (
        "security",
        "auth",
        "authentication",
        "authorization",
        "permission",
        "permissions",
    ),
    "files": (
        "file",
        "files",
        "source",
        "sources",
    ),
    "issues": (
        "issue",
        "issues",
        "problem",
        "problems",
        "error",
        "errors",
        "warning",
        "warnings",
        "todo",
        "todos",
        "missing",
    ),
}


TECHNOLOGY_ALIASES: dict[str, tuple[str, ...]] = {
    "react": (
        "react",
        "reactjs",
        "react.js",
    ),
    "typescript": (
        "typescript",
        "tsx",
        ".ts",
    ),
    "javascript": (
        "javascript",
        "node",
        "nodejs",
        ".js",
        "jsx",
    ),
    "fastapi": (
        "fastapi",
    ),
    "flask": (
        "flask",
    ),
    "django": (
        "django",
    ),
    "nextjs": (
        "next.js",
        "nextjs",
        "next",
    ),
    "vite": (
        "vite",
    ),
    "electron": (
        "electron",
    ),
    "python": (
        "python",
        ".py",
    ),
    "csharp": (
        "c#",
        "csharp",
        ".cs",
    ),
    "cpp": (
        "c++",
        "cpp",
        ".cpp",
        ".hpp",
    ),
    "unity": (
        "unity",
        "unityengine",
    ),
    "sqlite": (
        "sqlite",
        ".sqlite",
        ".db",
    ),
    "postgresql": (
        "postgres",
        "postgresql",
    ),
    "mysql": (
        "mysql",
    ),
    "supabase": (
        "supabase",
    ),
    "tailwind": (
        "tailwind",
        "tailwindcss",
    ),
}


# ============================================================
# Data Models
# ============================================================


@dataclass
class ProjectKnowledgeSource:
    """
    Analyzerが生成したKnowledge 1ファイル分。
    """

    path: str
    category: str
    content: Any
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "category": self.category,
            "size_bytes": self.size_bytes,
            "content": self.content,
        }


@dataclass
class CompletionCriterion:
    """
    完成条件。

    status:
        implemented
        partial
        missing
        unknown
    """

    id: str
    requirement: str
    status: str = "unknown"
    evidence: list[str] = field(default_factory=list)
    category: str = "general"
    priority: int = 50

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "requirement": self.requirement,
            "status": self.status,
            "evidence": list(self.evidence),
            "category": self.category,
            "priority": self.priority,
        }


@dataclass
class ProjectKnowledge:
    """
    ProjectKnowledgeBuilderが生成する統合Knowledge。
    """

    project_id: str

    project_name: str

    project_type: str = ""

    description: str = ""

    architecture: list[Any] = field(
        default_factory=list
    )

    features: list[Any] = field(
        default_factory=list
    )

    dependencies: list[Any] = field(
        default_factory=list
    )

    technologies: list[str] = field(
        default_factory=list
    )

    entry_points: list[Any] = field(
        default_factory=list
    )

    apis: list[Any] = field(
        default_factory=list
    )

    components: list[Any] = field(
        default_factory=list
    )

    models: list[Any] = field(
        default_factory=list
    )

    database: list[Any] = field(
        default_factory=list
    )

    services: list[Any] = field(
        default_factory=list
    )

    tests: list[Any] = field(
        default_factory=list
    )

    security: list[Any] = field(
        default_factory=list
    )

    files: list[Any] = field(
        default_factory=list
    )

    issues: list[Any] = field(
        default_factory=list
    )

    reusable_patterns: list[Any] = field(
        default_factory=list
    )

    incomplete_features: list[Any] = field(
        default_factory=list
    )

    completion_criteria: list[
        CompletionCriterion
    ] = field(default_factory=list)

    source_files: list[str] = field(
        default_factory=list
    )

    source_repomix: str = ""

    generated_at: str = ""

    retrieval: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":
                f"project_{self.project_id}",

            "name":
                self.project_name,

            "title":
                f"{self.project_name} Project Knowledge",

            "description":
                self.description,

            "category":
                "project_knowledge",

            "knowledge_type":
                "project",

            "project_id":
                self.project_id,

            "project_type":
                self.project_type,

            "architecture":
                self.architecture,

            "features":
                self.features,

            "dependencies":
                self.dependencies,

            "technologies":
                self.technologies,

            "entry_points":
                self.entry_points,

            "apis":
                self.apis,

            "components":
                self.components,

            "models":
                self.models,

            "database":
                self.database,

            "services":
                self.services,

            "tests":
                self.tests,

            "security":
                self.security,

            "files":
                self.files,

            "issues":
                self.issues,

            "reusable_patterns":
                self.reusable_patterns,

            "incomplete_features":
                self.incomplete_features,

            "completion_criteria": [
                criterion.to_dict()
                for criterion
                in self.completion_criteria
            ],

            "source_files":
                self.source_files,

            "source_repomix":
                self.source_repomix,

            "generated_at":
                self.generated_at,

            "retrieval":
                self.retrieval,

            "metadata":
                self.metadata,
        }


@dataclass
class ProjectKnowledgeBuildResult:
    """
    build()の返却結果。
    """

    success: bool = False

    project_id: str = ""

    output_path: str = ""

    knowledge: ProjectKnowledge | None = None

    source_files: list[str] = field(
        default_factory=list
    )

    saved_paths: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    errors: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success":
                self.success,

            "project_id":
                self.project_id,

            "output_path":
                self.output_path,

            "source_files":
                self.source_files,

            "saved_paths":
                self.saved_paths,

            "warnings":
                self.warnings,

            "errors":
                self.errors,

            "knowledge":
                (
                    self.knowledge.to_dict()
                    if self.knowledge
                    else None
                ),
        }


# ============================================================
# Project Knowledge Builder
# ============================================================


class ProjectKnowledgeBuilder:
    """
    RepomixHandler / Analyzerの出力を統合して
    ProjectKnowledgeを生成する。

    ------------------------------------------------------------
    Responsibility
    ------------------------------------------------------------

    RepomixHandler:
        Repomixを解析する

    Analyzer:
        個々のコードや構造を解析する

    ProjectKnowledgeBuilder:
        Analyzer結果を「1プロジェクトの知識」へ統合する

    KnowledgeManager:
        完成したProjectKnowledgeを管理する

    ProjectBuildService:
        ProjectKnowledgeを利用して新規生成・修復する

    ------------------------------------------------------------
    ProjectKnowledgeBuilderがやらないこと
    ------------------------------------------------------------

    - IntentInspector実行
    - Handler選択
    - ファイル生成
    - ビルド実行
    - LLM実行
    - npm / pytest / Unity build
    - RepairEngine実行
    """

    def __init__(
        self,
        project_root: str | Path = ".",
        source_dir: str | Path = DEFAULT_SOURCE_DIR,
        output_dir: str | Path = DEFAULT_OUTPUT_DIR,
        manager: KnowledgeManager | None = None,
        enable_debug: bool = False,
    ) -> None:

        self.project_root = Path(
            project_root
        ).expanduser().resolve()

        self.source_dir = self._resolve_path(
            source_dir
        )

        self.output_dir = self._resolve_path(
            output_dir
        )

        self.enable_debug = bool(
            enable_debug
        )

        self.manager = (
            manager
            if manager is not None
            else KnowledgeManager(
                base_dir=self.project_root
            )
        )

        self._debug(
            f"initialized "
            f"source={self.source_dir} "
            f"output={self.output_dir}"
        )

    # ========================================================
    # Public API
    # ========================================================

    def build(
        self,
        project_id: str,
        project_name: str | None = None,
        source_dir: str | Path | None = None,
        source_repomix: str = "",
        project_type: str = "",
        extra_metadata: Mapping[
            str,
            Any,
        ] | None = None,
        save_split_files: bool = True,
    ) -> ProjectKnowledgeBuildResult:
        """
        ProjectKnowledgeを生成するメインAPI。
        """

        result = ProjectKnowledgeBuildResult(
            project_id=project_id
        )

        normalized_project_id = (
            self._normalize_project_id(
                project_id
            )
        )

        if not normalized_project_id:

            result.errors.append(
                "project_idが空です。"
            )

            return result

        result.project_id = (
            normalized_project_id
        )

        effective_source_dir = (
            self._resolve_source_dir(
                normalized_project_id,
                source_dir,
            )
        )

        if not effective_source_dir.exists():

            result.errors.append(
                "Analyzer出力ディレクトリが"
                "見つかりません: "
                f"{effective_source_dir}"
            )

            return result

        # --------------------------------------------
        # 1. JSON収集
        # --------------------------------------------

        sources, load_warnings = (
            self._load_sources(
                effective_source_dir
            )
        )

        result.warnings.extend(
            load_warnings
        )

        result.source_files = [
            source.path
            for source in sources
        ]

        if not sources:

            result.errors.append(
                "統合可能なAnalyzer JSONが"
                "ありません。"
            )

            return result

        # --------------------------------------------
        # 2. 分類
        # --------------------------------------------

        categorized = (
            self._categorize_sources(
                sources
            )
        )

        # --------------------------------------------
        # 3. ProjectKnowledge構築
        # --------------------------------------------

        knowledge = ProjectKnowledge(
            project_id=
                normalized_project_id,

            project_name=
                (
                    project_name
                    or self._humanize_name(
                        normalized_project_id
                    )
                ),

            project_type=
                project_type,

            source_files=
                result.source_files,

            source_repomix=
                source_repomix,

            generated_at=
                datetime.now(
                    timezone.utc
                ).isoformat(),

            metadata=
                dict(
                    extra_metadata
                    or {}
                ),
        )

        # --------------------------------------------
        # 4. 各カテゴリ統合
        # --------------------------------------------

        knowledge.architecture = (
            self._collect_category(
                categorized,
                "architecture",
            )
        )

        knowledge.features = (
            self._collect_category(
                categorized,
                "features",
            )
        )

        knowledge.dependencies = (
            self._collect_category(
                categorized,
                "dependencies",
            )
        )

        knowledge.entry_points = (
            self._collect_category(
                categorized,
                "entry_points",
            )
        )

        knowledge.apis = (
            self._collect_category(
                categorized,
                "apis",
            )
        )

        knowledge.components = (
            self._collect_category(
                categorized,
                "components",
            )
        )

        knowledge.models = (
            self._collect_category(
                categorized,
                "models",
            )
        )

        knowledge.database = (
            self._collect_category(
                categorized,
                "database",
            )
        )

        knowledge.services = (
            self._collect_category(
                categorized,
                "services",
            )
        )

        knowledge.tests = (
            self._collect_category(
                categorized,
                "tests",
            )
        )

        knowledge.security = (
            self._collect_category(
                categorized,
                "security",
            )
        )

        knowledge.files = (
            self._collect_category(
                categorized,
                "files",
            )
        )

        knowledge.issues = (
            self._collect_category(
                categorized,
                "issues",
            )
        )

        # --------------------------------------------
        # 5. technology検出
        # --------------------------------------------

        knowledge.technologies = (
            self._detect_technologies(
                sources
            )
        )

        # --------------------------------------------
        # 6. project_type自動推定
        # --------------------------------------------

        if not knowledge.project_type:

            knowledge.project_type = (
                self._infer_project_type(
                    knowledge
                )
            )

        # --------------------------------------------
        # 7. reusable pattern抽出
        # --------------------------------------------

        knowledge.reusable_patterns = (
            self._build_reusable_patterns(
                knowledge
            )
        )

        # --------------------------------------------
        # 8. incomplete feature抽出
        # --------------------------------------------

        knowledge.incomplete_features = (
            self._detect_incomplete_features(
                knowledge,
                sources,
            )
        )

        # --------------------------------------------
        # 9. completion criteria生成
        # --------------------------------------------

        knowledge.completion_criteria = (
            self._build_completion_criteria(
                knowledge
            )
        )

        # --------------------------------------------
        # 10. description
        # --------------------------------------------

        knowledge.description = (
            self._build_description(
                knowledge
            )
        )

        # --------------------------------------------
        # 11. retrieval metadata
        # --------------------------------------------

        knowledge.retrieval = (
            self._build_retrieval_metadata(
                knowledge
            )
        )

        # --------------------------------------------
        # 12. 統合Knowledge保存
        # --------------------------------------------

        output_project_dir = (
            self.output_dir
            / normalized_project_id
        )

        output_project_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        main_output = (
            output_project_dir
            / "project_knowledge.json"
        )

        if not self._write_json(
            main_output,
            knowledge.to_dict(),
        ):

            result.errors.append(
                "project_knowledge.jsonの"
                "保存に失敗しました。"
            )

            return result

        result.saved_paths.append(
            self._display_path(
                main_output
            )
        )

        # --------------------------------------------
        # 13. 分割Knowledge保存
        # --------------------------------------------

        if save_split_files:

            split_paths = (
                self._save_split_knowledge(
                    output_project_dir,
                    knowledge,
                )
            )

            result.saved_paths.extend(
                split_paths
            )

        # --------------------------------------------
        # 14. 完成
        # --------------------------------------------

        result.success = True

        result.output_path = (
            self._display_path(
                main_output
            )
        )

        result.knowledge = knowledge

        logger.info(
            "✅ [ProjectKnowledgeBuilder] "
            "project=%s sources=%d output=%s",
            normalized_project_id,
            len(sources),
            result.output_path,
        )

        return result

    async def build_async(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ProjectKnowledgeBuildResult:

        return await asyncio.to_thread(
            self.build,
            *args,
            **kwargs,
        )

    # ========================================================
    # Source Discovery
    # ========================================================

    def _resolve_source_dir(
        self,
        project_id: str,
        explicit_source_dir: (
            str | Path | None
        ),
    ) -> Path:
        """
        優先順位:

        1. explicit source_dir
        2. source_dir/project_id
        3. source_dir
        """

        if explicit_source_dir:

            return self._resolve_path(
                explicit_source_dir
            )

        project_specific = (
            self.source_dir
            / project_id
        )

        if project_specific.exists():

            return project_specific

        return self.source_dir

    def _load_sources(
        self,
        source_dir: Path,
    ) -> tuple[
        list[ProjectKnowledgeSource],
        list[str],
    ]:

        sources: list[
            ProjectKnowledgeSource
        ] = []

        warnings: list[str] = []

        for file_path in sorted(
            source_dir.rglob("*.json")
        ):

            if (
                not file_path.is_file()
                or file_path.name.casefold()
                in IGNORED_JSON_FILES
            ):
                continue

            try:

                raw_text = (
                    file_path.read_text(
                        encoding="utf-8-sig"
                    )
                )

                data = json.loads(
                    raw_text
                )

            except json.JSONDecodeError as exc:

                warnings.append(
                    "JSON破損をスキップ: "
                    f"{file_path} / {exc}"
                )

                continue

            except (
                OSError,
                UnicodeError,
            ) as exc:

                warnings.append(
                    "JSON読込失敗: "
                    f"{file_path} / {exc}"
                )

                continue

            category = (
                self._detect_category(
                    file_path,
                    data,
                )
            )

            sources.append(
                ProjectKnowledgeSource(
                    path=
                        self._display_path(
                            file_path
                        ),

                    category=
                        category,

                    content=
                        data,

                    size_bytes=
                        len(
                            raw_text.encode(
                                "utf-8",
                                errors="ignore",
                            )
                        ),
                )
            )

        return sources, warnings

    # ========================================================
    # Category Detection
    # ========================================================

    def _detect_category(
        self,
        file_path: Path,
        content: Any,
    ) -> str:

        text_parts = [
            file_path.stem,
            file_path.name,
        ]

        if isinstance(
            content,
            dict,
        ):

            for key in (
                "category",
                "type",
                "knowledge_type",
                "title",
                "name",
            ):

                value = content.get(
                    key
                )

                if value:
                    text_parts.append(
                        str(value)
                    )

        blob = " ".join(
            text_parts
        ).casefold()

        for category, patterns in (
            CATEGORY_PATTERNS.items()
        ):

            if any(
                pattern.casefold()
                in blob
                for pattern in patterns
            ):

                return category

        return "general"

    def _categorize_sources(
        self,
        sources: Sequence[
            ProjectKnowledgeSource
        ],
    ) -> dict[
        str,
        list[ProjectKnowledgeSource],
    ]:

        result: dict[
            str,
            list[ProjectKnowledgeSource],
        ] = {}

        for source in sources:

            result.setdefault(
                source.category,
                [],
            ).append(
                source
            )

        return result

    # ========================================================
    # Category Collection
    # ========================================================

    def _collect_category(
        self,
        categorized: Mapping[
            str,
            Sequence[
                ProjectKnowledgeSource
            ],
        ],
        category: str,
    ) -> list[Any]:

        sources = categorized.get(
            category,
            [],
        )

        result: list[Any] = []

        for source in sources:

            extracted = (
                self._unwrap_content(
                    source.content,
                    category,
                )
            )

            for item in self._ensure_items(
                extracted
            ):

                self._append_unique(
                    result,
                    item,
                )

        return result

    def _unwrap_content(
        self,
        value: Any,
        category: str,
    ) -> Any:

        if not isinstance(
            value,
            dict,
        ):

            return value

        preferred_keys = [
            category,
            "items",
            "data",
            "results",
            "files",
            "content",
        ]

        for key in preferred_keys:

            if key in value:

                candidate = (
                    value[key]
                )

                if candidate not in (
                    None,
                    "",
                    [],
                    {},
                ):

                    return candidate

        return value

    # ========================================================
    # Technology Detection
    # ========================================================

    def _detect_technologies(
        self,
        sources: Sequence[
            ProjectKnowledgeSource
        ],
    ) -> list[str]:

        technologies: list[str] = []

        # --------------------------------------------
        # Structured values
        # --------------------------------------------

        for source in sources:

            self._extract_known_keys(
                source.content,
                {
                    "technology",
                    "technologies",
                    "framework",
                    "frameworks",
                    "language",
                    "languages",
                    "stack",
                },
                technologies,
            )

        # --------------------------------------------
        # Text based detection
        # --------------------------------------------

        combined = "\n".join(
            self._to_searchable_text(
                source.content
            )
            for source in sources
        ).casefold()

        for canonical, aliases in (
            TECHNOLOGY_ALIASES.items()
        ):

            if any(
                alias.casefold()
                in combined
                for alias in aliases
            ):

                self._append_unique(
                    technologies,
                    canonical,
                )

        return [
            str(item)
            for item in technologies
            if str(item).strip()
        ]

    # ========================================================
    # Project Type
    # ========================================================

    def _infer_project_type(
        self,
        knowledge: ProjectKnowledge,
    ) -> str:

        tech = {
            item.casefold()
            for item
            in knowledge.technologies
        }

        if (
            "unity" in tech
            and "csharp" in tech
        ):
            return "unity"

        if (
            "electron" in tech
            and "react" in tech
        ):
            return "electron_react"

        if (
            "react" in tech
            and "fastapi" in tech
        ):
            return "react_fastapi"

        if (
            "react" in tech
            and "typescript" in tech
        ):
            return "react_typescript"

        if (
            "nextjs" in tech
        ):
            return "nextjs"

        if (
            "fastapi" in tech
        ):
            return "fastapi"

        if (
            "python" in tech
        ):
            return "python"

        if (
            "cpp" in tech
        ):
            return "cpp"

        return "generic_project"

    # ========================================================
    # Reusable Patterns
    # ========================================================

    def _build_reusable_patterns(
        self,
        knowledge: ProjectKnowledge,
    ) -> list[Any]:

        patterns: list[Any] = []

        if knowledge.architecture:

            patterns.append(
                {
                    "type":
                        "architecture",

                    "description":
                        "既存プロジェクトの"
                        "アーキテクチャ構成",

                    "source":
                        knowledge.architecture,
                }
            )

        if knowledge.services:

            patterns.append(
                {
                    "type":
                        "service_layer",

                    "description":
                        "Service層の実装パターン",

                    "source":
                        knowledge.services,
                }
            )

        if knowledge.database:

            patterns.append(
                {
                    "type":
                        "database",

                    "description":
                        "Database / Repository構成",

                    "source":
                        knowledge.database,
                }
            )

        if knowledge.apis:

            patterns.append(
                {
                    "type":
                        "api",

                    "description":
                        "API / Route設計",

                    "source":
                        knowledge.apis,
                }
            )

        if knowledge.components:

            patterns.append(
                {
                    "type":
                        "ui_component",

                    "description":
                        "UI Component構成",

                    "source":
                        knowledge.components,
                }
            )

        return patterns

    # ========================================================
    # Incomplete Detection
    # ========================================================

    def _detect_incomplete_features(
        self,
        knowledge: ProjectKnowledge,
        sources: Sequence[
            ProjectKnowledgeSource
        ],
    ) -> list[Any]:

        result: list[Any] = []

        # --------------------------------------------
        # Analyzer issues
        # --------------------------------------------

        for issue in knowledge.issues:

            self._append_unique(
                result,
                issue,
            )

        # --------------------------------------------
        # TODO / FIXME detection
        # --------------------------------------------

        for source in sources:

            text = (
                self._to_searchable_text(
                    source.content
                )
            )

            for line in text.splitlines():

                stripped = line.strip()

                if not stripped:
                    continue

                lowered = stripped.casefold()

                if any(
                    marker in lowered
                    for marker in (
                        "todo",
                        "fixme",
                        "not implemented",
                        "未実装",
                        "未完成",
                        "不足",
                    )
                ):

                    self._append_unique(
                        result,
                        {
                            "type":
                                "incomplete",

                            "source":
                                source.path,

                            "detail":
                                stripped[:500],
                        },
                    )

        return result

    # ========================================================
    # Completion Criteria
    # ========================================================

    def _build_completion_criteria(
        self,
        knowledge: ProjectKnowledge,
    ) -> list[
        CompletionCriterion
    ]:

        criteria: list[
            CompletionCriterion
        ] = []

        counter = 1

        # --------------------------------------------
        # Feature criteria
        # --------------------------------------------

        for feature in knowledge.features:

            text = (
                self._item_label(
                    feature
                )
            )

            if not text:
                continue

            criteria.append(
                CompletionCriterion(
                    id=
                        f"FEATURE-{counter:03d}",

                    requirement=
                        text,

                    status=
                        "implemented",

                    evidence=[
                        "features analyzer"
                    ],

                    category=
                        "feature",

                    priority=
                        80,
                )
            )

            counter += 1

        # --------------------------------------------
        # Missing criteria
        # --------------------------------------------

        missing_counter = 1

        for issue in (
            knowledge.incomplete_features
        ):

            text = (
                self._item_label(
                    issue
                )
            )

            if not text:
                continue

            criteria.append(
                CompletionCriterion(
                    id=
                        f"MISSING-{missing_counter:03d}",

                    requirement=
                        text,

                    status=
                        "missing",

                    evidence=[
                        "issue/todo detection"
                    ],

                    category=
                        "incomplete",

                    priority=
                        100,
                )
            )

            missing_counter += 1

        # --------------------------------------------
        # Structural criteria
        # --------------------------------------------

        structural_checks = [
            (
                "STRUCTURE-001",
                "プロジェクト構造が定義されている",
                bool(
                    knowledge.architecture
                    or knowledge.files
                ),
            ),
            (
                "ENTRY-001",
                "エントリーポイントが確認できる",
                bool(
                    knowledge.entry_points
                ),
            ),
            (
                "DEPENDENCY-001",
                "依存関係が確認できる",
                bool(
                    knowledge.dependencies
                ),
            ),
        ]

        for (
            criterion_id,
            requirement,
            implemented,
        ) in structural_checks:

            criteria.append(
                CompletionCriterion(
                    id=
                        criterion_id,

                    requirement=
                        requirement,

                    status=
                        (
                            "implemented"
                            if implemented
                            else "unknown"
                        ),

                    evidence=[],

                    category=
                        "structure",

                    priority=
                        60,
                )
            )

        return criteria

    # ========================================================
    # Description
    # ========================================================

    def _build_description(
        self,
        knowledge: ProjectKnowledge,
    ) -> str:

        parts = [
            (
                f"{knowledge.project_name} "
                f"({knowledge.project_type})"
            )
        ]

        if knowledge.technologies:

            parts.append(
                "技術: "
                + ", ".join(
                    knowledge.technologies[
                        :12
                    ]
                )
            )

        if knowledge.features:

            parts.append(
                "主要機能: "
                + ", ".join(
                    self._item_label(
                        item
                    )
                    for item
                    in knowledge.features[
                        :8
                    ]
                    if self._item_label(
                        item
                    )
                )
            )

        return " / ".join(
            part
            for part in parts
            if part
        )

    # ========================================================
    # Retrieval Metadata
    # ========================================================

    def _build_retrieval_metadata(
        self,
        knowledge: ProjectKnowledge,
    ) -> dict[str, Any]:

        keywords: list[str] = []

        self._append_unique(
            keywords,
            knowledge.project_id,
        )

        self._append_unique(
            keywords,
            knowledge.project_name,
        )

        self._append_unique(
            keywords,
            knowledge.project_type,
        )

        for tech in (
            knowledge.technologies
        ):

            self._append_unique(
                keywords,
                tech,
            )

        for feature in (
            knowledge.features
        ):

            label = (
                self._item_label(
                    feature
                )
            )

            if label:

                self._append_unique(
                    keywords,
                    label,
                )

        tags = [
            "project",
            "repomix",
            "project_knowledge",
            knowledge.project_id,
        ]

        if knowledge.project_type:

            tags.append(
                knowledge.project_type
            )

        return {
            "keywords":
                keywords[:100],

            "intent": [
                "project_reference",
                "project_generation",
                "project_analysis",
                "complete_project",
            ],

            "actions": [
                "reference",
                "analyze",
                "generate",
                "complete",
                "repair",
            ],

            "targets": [
                "project",
                knowledge.project_id,
            ],

            "project_types": [
                knowledge.project_type
            ]
            if knowledge.project_type
            else [],

            "features": [
                self._item_label(
                    feature
                )
                for feature
                in knowledge.features[
                    :50
                ]
                if self._item_label(
                    feature
                )
            ],

            "technologies":
                knowledge.technologies,

            "knowledge_type":
                "project",

            "tags":
                tags,
        }

    # ========================================================
    # Split Output
    # ========================================================

    def _save_split_knowledge(
        self,
        output_dir: Path,
        knowledge: ProjectKnowledge,
    ) -> list[str]:

        saved: list[str] = []

        split_data: dict[
            str,
            Any,
        ] = {
            "architecture.json":
                knowledge.architecture,

            "features.json":
                knowledge.features,

            "dependencies.json":
                knowledge.dependencies,

            "technologies.json":
                knowledge.technologies,

            "entry_points.json":
                knowledge.entry_points,

            "apis.json":
                knowledge.apis,

            "components.json":
                knowledge.components,

            "models.json":
                knowledge.models,

            "database.json":
                knowledge.database,

            "services.json":
                knowledge.services,

            "tests.json":
                knowledge.tests,

            "security.json":
                knowledge.security,

            "issues.json":
                knowledge.issues,

            "reusable_patterns.json":
                knowledge.reusable_patterns,

            "incomplete_features.json":
                knowledge.incomplete_features,

            "completion_criteria.json": [
                item.to_dict()
                for item
                in knowledge.completion_criteria
            ],
        }

        for filename, content in (
            split_data.items()
        ):

            # 空データは保存しない。
            if content in (
                None,
                "",
                [],
                {},
            ):
                continue

            payload = {
                "id":
                    (
                        f"{knowledge.project_id}_"
                        f"{Path(filename).stem}"
                    ),

                "name":
                    (
                        f"{knowledge.project_name} "
                        f"{Path(filename).stem}"
                    ),

                "category":
                    "project_knowledge",

                "project_id":
                    knowledge.project_id,

                "project_type":
                    knowledge.project_type,

                "content":
                    content,

                "retrieval":
                    knowledge.retrieval,
            }

            path = (
                output_dir
                / filename
            )

            if self._write_json(
                path,
                payload,
            ):

                saved.append(
                    self._display_path(
                        path
                    )
                )

        return saved

    # ========================================================
    # Structured Extraction
    # ========================================================

    def _extract_known_keys(
        self,
        value: Any,
        target_keys: set[str],
        output: list[Any],
        depth: int = 0,
    ) -> None:

        if depth > 20:
            return

        if isinstance(
            value,
            dict,
        ):

            for key, child in (
                value.items()
            ):

                if (
                    key.casefold()
                    in target_keys
                ):

                    for item in (
                        self._ensure_items(
                            child
                        )
                    ):

                        self._append_unique(
                            output,
                            item,
                        )

                self._extract_known_keys(
                    child,
                    target_keys,
                    output,
                    depth + 1,
                )

        elif isinstance(
            value,
            list,
        ):

            for item in value:

                self._extract_known_keys(
                    item,
                    target_keys,
                    output,
                    depth + 1,
                )

    # ========================================================
    # Utilities
    # ========================================================

    def _resolve_path(
        self,
        value: str | Path,
    ) -> Path:

        path = Path(
            value
        ).expanduser()

        if path.is_absolute():

            resolved = (
                path.resolve()
            )

        else:

            resolved = (
                self.project_root
                / path
            ).resolve()

        return resolved

    @staticmethod
    def _normalize_project_id(
        value: str,
    ) -> str:

        text = (
            str(value or "")
            .strip()
            .casefold()
        )

        text = re.sub(
            r"[^a-z0-9_\-]+",
            "_",
            text,
        )

        text = re.sub(
            r"_+",
            "_",
            text,
        )

        return text.strip(
            "_-"
        )

    @staticmethod
    def _humanize_name(
        project_id: str,
    ) -> str:

        return (
            project_id
            .replace("_", " ")
            .replace("-", " ")
            .strip()
            .title()
        )

    @staticmethod
    def _ensure_items(
        value: Any,
    ) -> list[Any]:

        if value is None:

            return []

        if isinstance(
            value,
            list,
        ):

            return value

        if isinstance(
            value,
            tuple,
        ):

            return list(
                value
            )

        return [
            value
        ]

    def _append_unique(
        self,
        output: list[Any],
        item: Any,
    ) -> None:

        if item in (
            None,
            "",
            [],
            {},
        ):
            return

        signature = (
            self._stable_signature(
                item
            )
        )

        existing = {
            self._stable_signature(
                value
            )
            for value in output
        }

        if signature not in existing:

            output.append(
                item
            )

    @staticmethod
    def _stable_signature(
        value: Any,
    ) -> str:

        try:

            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )

        except Exception:

            return str(
                value
            )

    def _to_searchable_text(
        self,
        value: Any,
    ) -> str:

        if value is None:

            return ""

        if isinstance(
            value,
            str,
        ):

            return value

        try:

            return json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

        except Exception:

            return str(
                value
            )

    def _item_label(
        self,
        item: Any,
    ) -> str:

        if item is None:

            return ""

        if isinstance(
            item,
            str,
        ):

            return item.strip()

        if isinstance(
            item,
            dict,
        ):

            for key in (
                "name",
                "title",
                "feature",
                "description",
                "requirement",
                "detail",
                "path",
                "id",
            ):

                value = item.get(
                    key
                )

                if value:

                    return str(
                        value
                    ).strip()

            return json.dumps(
                item,
                ensure_ascii=False,
                default=str,
            )[:300]

        return str(
            item
        ).strip()

    def _write_json(
        self,
        path: Path,
        data: Any,
    ) -> bool:

        try:

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            relative = (
                self._display_path(
                    path
                )
            )

            return bool(
                self.manager.write_file(
                    relative,
                    json.dumps(
                        data,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    ),
                )
            )

        except Exception as exc:

            logger.error(
                "ProjectKnowledge保存失敗 "
                "%s: %s",
                path,
                exc,
            )

            return False

    def _display_path(
        self,
        path: Path,
    ) -> str:

        try:

            return (
                path.resolve()
                .relative_to(
                    self.project_root
                )
                .as_posix()
            )

        except ValueError:

            return (
                path.resolve()
                .as_posix()
            )

    def _debug(
        self,
        message: str,
    ) -> None:

        if not self.enable_debug:
            return

        logger.debug(
            "[ProjectKnowledgeBuilder] %s",
            message,
        )


# ============================================================
# Standalone Test
# ============================================================


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "ProjectKnowledgeBuilder "
            "standalone debug"
        )
    )

    parser.add_argument(
        "project_id",
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
    )

    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--project-name",
        default=None,
    )

    parser.add_argument(
        "--project-type",
        default="",
    )

    parser.add_argument(
        "--source-repomix",
        default="",
    )

    parser.add_argument(
        "--no-split",
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

    builder = ProjectKnowledgeBuilder(
        project_root=
            args.project_root,

        source_dir=
            args.source_dir,

        output_dir=
            args.output_dir,

        enable_debug=
            args.debug,
    )

    build_result = builder.build(
        project_id=
            args.project_id,

        project_name=
            args.project_name,

        project_type=
            args.project_type,

        source_repomix=
            args.source_repomix,

        save_split_files=
            not args.no_split,
    )

    print(
        json.dumps(
            build_result.to_dict(),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
