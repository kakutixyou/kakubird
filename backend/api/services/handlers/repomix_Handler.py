```python
# api/services/handlers/repomix_handler.py

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import os
import re
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


# ============================================================
# Optional YAML
# ============================================================

try:
    import yaml  # type: ignore

    YAML_AVAILABLE = True

except ImportError:
    yaml = None  # type: ignore
    YAML_AVAILABLE = False


# ============================================================
# Existing Project Imports
# ============================================================

from api.services.handlers.base_handler import BaseHandler
from api.services.manager.KnowledgeManager import KnowledgeManager
from core.analyzers.base_analyzer import BaseAnalyzer


# ProjectKnowledgeBuilder は移行途中でも
# RepomixHandler 自体を起動できるよう optional import にする。
try:
    from backend.engine.knowledge.ProjectKnowledgeBuilder import (
        ProjectKnowledgeBuilder,
        ProjectKnowledgeBuildResult,
    )

    PROJECT_KNOWLEDGE_BUILDER_AVAILABLE = True

except Exception:
    ProjectKnowledgeBuilder = None  # type: ignore
    ProjectKnowledgeBuildResult = None  # type: ignore

    PROJECT_KNOWLEDGE_BUILDER_AVAILABLE = False


# ============================================================
# Data Models
# ============================================================


@dataclass(frozen=True)
class RepomixInput:
    """
    検出されたRepomix入力。
    """

    path: Path

    input_format: str

    project_id: str

    series: str | None

    sequence: int | None

    modified_ns: int

    size_bytes: int

    def to_dict(
        self,
        project_root: Path,
    ) -> Dict[str, Any]:

        try:
            display_path = (
                self.path
                .relative_to(project_root)
                .as_posix()
            )

        except ValueError:
            display_path = (
                self.path
                .as_posix()
            )

        return {
            "path":
                display_path,

            "format":
                self.input_format,

            "project_id":
                self.project_id,

            "series":
                self.series,

            "sequence":
                self.sequence,

            "modified_ns":
                self.modified_ns,

            "size_bytes":
                self.size_bytes,
        }


@dataclass
class ParsedRepomixFile:
    """
    Repomix内部の1ファイル。
    """

    path: str

    content: str

    extension: str

    line_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path":
                self.path,

            "extension":
                self.extension,

            "line_count":
                self.line_count,

            "content":
                self.content,
        }


# ============================================================
# Repomix Handler
# ============================================================


class RepomixHandler(BaseHandler):
    """
    Repomix出力を解析し、
    Analyzer → Project Knowledgeへ変換するHandler。

    ------------------------------------------------------------
    Main Responsibility
    ------------------------------------------------------------

    1. Repomix入力探索
    2. 対象作品(project_id)特定
    3. 対象作品の最新版Repomix選択
    4. YAML / XML解析
    5. Analyzer実行
    6. 作品別Analyzer JSON保存
    7. ProjectKnowledgeBuilder実行
    8. system_observation生成

    ------------------------------------------------------------
    Not Responsibility
    ------------------------------------------------------------

    - IntentInspector再実行
    - LLM実行
    - ProjectPlanner実行
    - FileGenerator実行
    - BuildValidator実行
    - RepairEngine実行

    ------------------------------------------------------------
    Example Structure
    ------------------------------------------------------------

    projects/
    ├─ font_app/
    │  ├─ project.json
    │  ├─ repomix-output.yml
    │  └─ repomix-output-2.yml
    │
    ├─ calendar_app/
    │  └─ repomix-output.yml
    │
    └─ security_login/
       └─ repomix-output.yml

    ↓

    backend/engine/knowledge/project_data/
    ├─ font_app/
    │  ├─ architecture.json
    │  ├─ features.json
    │  └─ dependencies.json
    │
    └─ calendar_app/
       └─ ...

    ↓

    backend/engine/knowledge/projects/
    ├─ font_app/
    │  └─ project_knowledge.json
    └─ calendar_app/
       └─ project_knowledge.json
    """

    # ========================================================
    # Input File Pattern
    # ========================================================

    INPUT_NAME_RE = re.compile(
        r"^repomix[-_]output"
        r"(?P<suffix>(?:[-_][\w\-]+)?)"
        r"\.(?P<extension>xml|ya?ml)$",
        re.IGNORECASE,
    )

    INPUT_IN_MESSAGE_RE = re.compile(
        r"(?P<name>"
        r"repomix[-_]output"
        r"(?:[-_][\w\-]+)?"
        r"\.(?:xml|ya?ml)"
        r")",
        re.IGNORECASE,
    )

    # ========================================================
    # Scan Settings
    # ========================================================

    IGNORED_SCAN_DIRS = {
        ".git",
        ".idea",
        ".venv",
        ".vscode",
        "__pycache__",
        "node_modules",
        "venv",
        "dist",
        "build",
        ".next",
        "coverage",
    }

    DEFAULT_MAX_INPUT_BYTES = (
        512 * 1024 * 1024
    )

    # ========================================================
    # Constructor
    # ========================================================

    def __init__(
        self,
        project_root: str | Path = ".",
        analyzer_output_root: str = (
            "backend/engine/knowledge/project_data"
        ),
        project_knowledge_root: str = (
            "backend/engine/knowledge/projects"
        ),
        max_input_bytes: int = (
            DEFAULT_MAX_INPUT_BYTES
        ),
        enable_project_knowledge_builder: bool = True,
    ) -> None:

        super().__init__()

        current_file_dir = (
            Path(__file__)
            .resolve()
            .parent
        )

        inferred_root = (
            current_file_dir
            / "../../../../"
        ).resolve()

        if (
            project_root
            and str(project_root) != "."
        ):
            self.resolved_root = (
                Path(project_root)
                .expanduser()
                .resolve()
            )

        else:
            self.resolved_root = (
                inferred_root
            )

        self.analyzer_output_root = (
            analyzer_output_root
            .strip("/\\")
        )

        self.project_knowledge_root = (
            project_knowledge_root
            .strip("/\\")
        )

        self.max_input_bytes = max(
            1,
            int(max_input_bytes),
        )

        self.enable_project_knowledge_builder = bool(
            enable_project_knowledge_builder
        )

        # ----------------------------------------------------
        # Manager
        # ----------------------------------------------------

        self.manager = KnowledgeManager(
            base_dir=str(
                self.resolved_root
            )
        )

        # ----------------------------------------------------
        # Analyzer
        # ----------------------------------------------------

        self.analyzers = (
            self._load_analyzers_dynamically()
        )

        # ----------------------------------------------------
        # Builder
        # ----------------------------------------------------

        self.project_knowledge_builder = None

        if (
            self.enable_project_knowledge_builder
            and PROJECT_KNOWLEDGE_BUILDER_AVAILABLE
            and ProjectKnowledgeBuilder
            is not None
        ):

            try:

                self.project_knowledge_builder = (
                    ProjectKnowledgeBuilder(
                        project_root=
                            self.resolved_root,

                        source_dir=
                            self.analyzer_output_root,

                        output_dir=
                            self.project_knowledge_root,

                        manager=
                            self.manager,
                    )
                )

            except Exception as exc:

                print(
                    "⚠️ [RepomixHandler] "
                    "ProjectKnowledgeBuilder初期化失敗: "
                    f"{exc}"
                )

        print(
            "🧠 [RepomixHandler] "
            f"初期化完了 root="
            f"[{self.resolved_root}]"
        )

    # ========================================================
    # Analyzer Plugin Discovery
    # ========================================================

    def _analyzer_locations(
        self,
    ) -> list[
        tuple[Path, str]
    ]:

        current_dir = (
            Path(__file__)
            .resolve()
            .parent
        )

        candidates = [
            (
                (
                    current_dir.parent
                    / "analyzers"
                ).resolve(),

                "api.services.handlers.analyzers",
            ),
            (
                (
                    current_dir
                    / "../analyzers"
                ).resolve(),

                "api.services.analyzers",
            ),
            (
                (
                    self.resolved_root
                    / "core/analyzers"
                ).resolve(),

                "core.analyzers",
            ),
        ]

        unique: list[
            tuple[Path, str]
        ] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for (
            directory,
            package_name,
        ) in candidates:

            identity = (
                str(directory),
                package_name,
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            unique.append(
                (
                    directory,
                    package_name,
                )
            )

        return unique

    def _load_analyzers_dynamically(
        self,
    ) -> List[BaseAnalyzer]:

        analyzers: List[
            BaseAnalyzer
        ] = []

        loaded_classes: set[
            str
        ] = set()

        for (
            analyzers_dir,
            package_name,
        ) in self._analyzer_locations():

            if not analyzers_dir.is_dir():
                continue

            print(
                "🔍 [Plugin] "
                f"{analyzers_dir} "
                "からAnalyzer探索"
            )

            for file_path in sorted(
                analyzers_dir.glob(
                    "*.py"
                )
            ):

                if (
                    file_path.name
                    .startswith("__")
                ):
                    continue

                if (
                    file_path.stem
                    == "base_analyzer"
                ):
                    continue

                module_path = (
                    f"{package_name}."
                    f"{file_path.stem}"
                )

                try:

                    module = (
                        importlib
                        .import_module(
                            module_path
                        )
                    )

                    for (
                        name,
                        obj,
                    ) in inspect.getmembers(
                        module,
                        inspect.isclass,
                    ):

                        class_id = (
                            f"{obj.__module__}."
                            f"{obj.__qualname__}"
                        )

                        if (
                            class_id
                            in loaded_classes
                        ):
                            continue

                        if obj is BaseAnalyzer:
                            continue

                        if not issubclass(
                            obj,
                            BaseAnalyzer,
                        ):
                            continue

                        if inspect.isabstract(
                            obj
                        ):
                            continue

                        if (
                            obj.__module__
                            != module_path
                        ):
                            continue

                        analyzers.append(
                            obj()
                        )

                        loaded_classes.add(
                            class_id
                        )

                        print(
                            " 🔌 [Loaded] "
                            f"{name} "
                            f"({file_path.name})"
                        )

                except Exception as exc:

                    print(
                        " ❌ [AnalyzerLoadError] "
                        f"{file_path.name}: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

        print(
            "✅ [Plugin] "
            f"{len(analyzers)} Analyzer loaded"
        )

        return analyzers

    # ========================================================
    # Handler Score
    # ========================================================

    async def calculate_score(
        self,
        message: str,
        current_signals: dict | None = None,
    ) -> int:

        msg = (
            str(message or "")
            .casefold()
        )

        strong_keywords = (
            "repomix",
            "repomix_output",
            "repomix-output",
            "全体コード",
            "プロジェクト解析",
            "プロジェクトを読み込",
            "構造を読み込",
            "知識更新",
        )

        if any(
            keyword in msg
            for keyword in strong_keywords
        ):
            return 100

        format_mentioned = any(
            keyword in msg
            for keyword in (
                "xml",
                "yml",
                "yaml",
            )
        )

        project_operation = any(
            keyword in msg
            for keyword in (
                "解析",
                "読み込",
                "取り込",
                "構造",
                "プロジェクト",
            )
        )

        if (
            format_mentioned
            and project_operation
        ):
            return 80

        # IntentInspectorの結果が渡されている場合
        if isinstance(
            current_signals,
            dict,
        ):

            targets = self._ensure_list(
                current_signals.get(
                    "targets"
                )
            )

            actions = self._ensure_list(
                current_signals.get(
                    "actions"
                )
            )

            normalized_targets = {
                value.casefold()
                for value in targets
            }

            normalized_actions = {
                value.casefold()
                for value in actions
            }

            if (
                "repomix"
                in normalized_targets
            ):
                return 100

            if (
                "project"
                in normalized_targets
                and normalized_actions
                & {
                    "analyze",
                    "reference",
                    "import",
                }
            ):
                return 75

        return 0

    # ========================================================
    # Input Name Parsing
    # ========================================================

    @classmethod
    def _parse_input_name(
        cls,
        path: Path,
        project_root: Path,
    ) -> RepomixInput | None:

        match = (
            cls.INPUT_NAME_RE
            .fullmatch(
                path.name
            )
        )

        if match is None:
            return None

        raw_suffix = (
            match.group(
                "suffix"
            )
            or ""
        ).lstrip("-_")

        sequence_match = (
            re.search(
                r"(?P<sequence>\d+)$",
                raw_suffix,
            )
        )

        if sequence_match:

            sequence = int(
                sequence_match.group(
                    "sequence"
                )
            )

            series = (
                raw_suffix[
                    :
                    sequence_match
                    .start()
                ]
                .rstrip("-_")
                or None
            )

        else:

            sequence = None

            series = (
                raw_suffix
                or None
            )

        extension = (
            match.group(
                "extension"
            )
            .casefold()
        )

        input_format = (
            "xml"
            if extension == "xml"
            else "yaml"
        )

        try:

            stat = path.stat()

        except OSError:
            return None

        project_id = (
            cls._infer_project_id_static(
                path=path,
                project_root=
                    project_root,
                series=series,
            )
        )

        return RepomixInput(
            path=
                path.resolve(),

            input_format=
                input_format,

            project_id=
                project_id,

            series=
                series,

            sequence=
                sequence,

            modified_ns=
                stat.st_mtime_ns,

            size_bytes=
                stat.st_size,
        )

    # ========================================================
    # Project ID
    # ========================================================

    @classmethod
    def _infer_project_id_static(
        cls,
        path: Path,
        project_root: Path,
        series: str | None,
    ) -> str:

        # ----------------------------------------------------
        # 1. project.json
        # ----------------------------------------------------

        project_json = (
            path.parent
            / "project.json"
        )

        if project_json.is_file():

            try:

                data = json.loads(
                    project_json
                    .read_text(
                        encoding="utf-8-sig"
                    )
                )

                if isinstance(
                    data,
                    dict,
                ):

                    explicit = str(
                        data.get(
                            "project_id",
                            "",
                        )
                        or data.get(
                            "id",
                            "",
                        )
                    ).strip()

                    if explicit:

                        return (
                            cls
                            ._normalize_project_id(
                                explicit
                            )
                        )

            except Exception:
                pass

        # ----------------------------------------------------
        # 2. Parent folder
        # ----------------------------------------------------

        try:

            relative_parent = (
                path.parent
                .resolve()
                .relative_to(
                    project_root
                    .resolve()
                )
            )

            if relative_parent.parts:

                parent_name = (
                    relative_parent
                    .parts[-1]
                )

                if parent_name.casefold() not in {
                    "backend",
                    "knowledge",
                    "project_data",
                    "projects",
                }:

                    project_id = (
                        cls
                        ._normalize_project_id(
                            parent_name
                        )
                    )

                    if project_id:
                        return project_id

        except ValueError:
            pass

        # ----------------------------------------------------
        # 3. Series
        # ----------------------------------------------------

        if series:

            normalized = (
                cls
                ._normalize_project_id(
                    series
                )
            )

            if normalized:
                return normalized

        return "default_project"

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

    # ========================================================
    # Input Discovery
    # ========================================================

    def _discover_inputs(
        self,
    ) -> list[RepomixInput]:

        discovered: list[
            RepomixInput
        ] = []

        if not self.resolved_root.is_dir():
            return discovered

        for (
            root,
            dirs,
            files,
        ) in os.walk(
            self.resolved_root
        ):

            dirs[:] = sorted(
                directory
                for directory in dirs
                if (
                    directory
                    not in self.IGNORED_SCAN_DIRS
                )
            )

            for file_name in sorted(
                files
            ):

                candidate_path = (
                    Path(root)
                    / file_name
                )

                candidate = (
                    self._parse_input_name(
                        candidate_path,
                        self.resolved_root,
                    )
                )

                if candidate is not None:

                    discovered.append(
                        candidate
                    )

        return discovered

    # ========================================================
    # Selection Helpers
    # ========================================================

    @staticmethod
    def _selection_key(
        candidate: RepomixInput,
    ) -> tuple[
        int,
        int,
        int,
        str,
    ]:

        return (
            1
            if candidate.sequence
            is not None
            else 0,

            candidate.sequence
            if candidate.sequence
            is not None
            else -1,

            candidate.modified_ns,

            candidate.path
            .as_posix()
            .casefold(),
        )

    def _explicit_input_name(
        self,
        request: Any,
        message: str,
    ) -> str | None:

        for attribute in (
            "repomix_path",
            "repomix_input",
            "input_path",
        ):

            value = getattr(
                request,
                attribute,
                None,
            )

            if value:

                return str(
                    value
                ).strip()

        match = (
            self.INPUT_IN_MESSAGE_RE
            .search(
                message
            )
        )

        if match:
            return match.group(
                "name"
            )

        return None

    def _explicit_project_id(
        self,
        request: Any,
        message: str,
        current_signals: dict | None = None,
    ) -> str | None:

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------

        for attribute in (
            "project_id",
            "active_project",
            "target_project",
        ):

            value = getattr(
                request,
                attribute,
                None,
            )

            if value:

                normalized = (
                    self
                    ._normalize_project_id(
                        str(value)
                    )
                )

                if normalized:
                    return normalized

        # ----------------------------------------------------
        # Signals / IntentInspector
        # ----------------------------------------------------

        if isinstance(
            current_signals,
            dict,
        ):

            for key in (
                "project_id",
                "active_project",
                "target_project",
                "current_project",
            ):

                value = (
                    current_signals
                    .get(key)
                )

                if value:

                    normalized = (
                        self
                        ._normalize_project_id(
                            str(value)
                        )
                    )

                    if normalized:
                        return normalized

            project_context = (
                current_signals.get(
                    "project_context"
                )
            )

            if isinstance(
                project_context,
                dict,
            ):

                for key in (
                    "project_id",
                    "name",
                    "project_name",
                ):

                    value = (
                        project_context
                        .get(key)
                    )

                    if value:

                        normalized = (
                            self
                            ._normalize_project_id(
                                str(value)
                            )
                        )

                        if normalized:
                            return normalized

        # ----------------------------------------------------
        # Message heuristic
        # ----------------------------------------------------

        candidates = (
            self._discover_inputs()
        )

        project_ids = {
            item.project_id
            for item in candidates
        }

        normalized_message = (
            message
            .casefold()
            .replace(" ", "_")
        )

        for project_id in sorted(
            project_ids,
            key=len,
            reverse=True,
        ):

            if (
                project_id.casefold()
                in normalized_message
            ):
                return project_id

        return None

    # ========================================================
    # Input Selection
    # ========================================================

    def _select_input(
        self,
        request: Any,
        message: str,
        current_signals: dict | None = None,
    ) -> tuple[
        RepomixInput | None,
        list[RepomixInput],
        str | None,
    ]:

        candidates = (
            self._discover_inputs()
        )

        explicit_input = (
            self._explicit_input_name(
                request,
                message,
            )
        )

        # ----------------------------------------------------
        # 1. Explicit file
        # ----------------------------------------------------

        if explicit_input:

            explicit_path = (
                Path(explicit_input)
                .expanduser()
            )

            if not explicit_path.is_absolute():

                explicit_path = (
                    self.resolved_root
                    / explicit_path
                )

            explicit_path = (
                explicit_path
                .resolve()
            )

            try:

                explicit_path.relative_to(
                    self.resolved_root
                )

            except ValueError:

                return (
                    None,
                    candidates,
                    (
                        "指定されたRepomix入力が"
                        "プロジェクトルート外です"
                    ),
                )

            direct = (
                self._parse_input_name(
                    explicit_path,
                    self.resolved_root,
                )
            )

            if (
                direct is not None
                and explicit_path.is_file()
            ):

                return (
                    direct,
                    candidates,
                    None,
                )

            # basename fallback
            for candidate in candidates:

                if (
                    candidate.path.name
                    .casefold()
                    ==
                    explicit_path.name
                    .casefold()
                ):

                    return (
                        candidate,
                        candidates,
                        None,
                    )

            return (
                None,
                candidates,
                (
                    "指定されたRepomix入力が"
                    "見つかりません: "
                    f"{explicit_input}"
                ),
            )

        # ----------------------------------------------------
        # 2. Explicit project
        # ----------------------------------------------------

        project_id = (
            self._explicit_project_id(
                request,
                message,
                current_signals,
            )
        )

        if project_id:

            project_candidates = [
                item
                for item in candidates
                if (
                    item.project_id
                    == project_id
                )
            ]

            if project_candidates:

                selected = max(
                    project_candidates,
                    key=
                        self._selection_key,
                )

                return (
                    selected,
                    candidates,
                    None,
                )

            return (
                None,
                candidates,
                (
                    "指定されたproject_idに"
                    "対応するRepomixがありません: "
                    f"{project_id}"
                ),
            )

        # ----------------------------------------------------
        # 3. No candidates
        # ----------------------------------------------------

        if not candidates:

            return (
                None,
                [],
                (
                    "Repomix入力が"
                    "見つかりません"
                ),
            )

        # ----------------------------------------------------
        # 4. 作品が1つだけなら最新版
        # ----------------------------------------------------

        project_ids = {
            item.project_id
            for item in candidates
        }

        if len(project_ids) == 1:

            return (
                max(
                    candidates,
                    key=
                        self._selection_key,
                ),
                candidates,
                None,
            )

        # ----------------------------------------------------
        # 5. Multiple projects
        # ----------------------------------------------------

        return (
            None,
            candidates,
            (
                "複数作品のRepomixが存在します。"
                "project_idまたは対象作品を"
                "指定してください。"
            ),
        )

    # ========================================================
    # File Record
    # ========================================================

    @staticmethod
    def _file_record(
        path: Any,
        content: Any,
    ) -> Dict[str, str] | None:

        normalized_path = str(
            path or ""
        ).strip()

        if not normalized_path:
            return None

        if isinstance(
            content,
            (
                dict,
                list,
            ),
        ):

            normalized_content = (
                json.dumps(
                    content,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        else:

            normalized_content = str(
                content or ""
            )

        return {
            "path":
                normalized_path
                .replace(
                    "\\",
                    "/",
                ),

            "content":
                normalized_content,
        }

    @staticmethod
    def _looks_like_file_path(
        value: Any,
    ) -> bool:

        text = str(
            value or ""
        ).strip()

        if (
            not text
            or "\n" in text
        ):
            return False

        return (
            "/" in text
            or "\\" in text
            or bool(
                Path(text).suffix
            )
        )

    # ========================================================
    # XML Parsing
    # ========================================================

    def _parse_xml_text(
        self,
        raw_text: str,
    ) -> tuple[
        list[Dict[str, str]],
        list[Dict[str, str]],
    ]:

        errors: list[
            Dict[str, str]
        ] = []

        text = (
            raw_text
            .lstrip(
                "\ufeff\r\n\t "
            )
        )

        first_tag = (
            text.find("<")
        )

        if first_tag < 0:

            return (
                [],
                [
                    {
                        "reason":
                            "xml_start_not_found",

                        "detail":
                            "XML開始タグがありません",
                    }
                ],
            )

        xml_text = (
            text[first_tag:]
        )

        try:

            root = (
                ET.fromstring(
                    xml_text
                )
            )

        except ET.ParseError:

            without_declaration = (
                re.sub(
                    r"^\s*<\?xml[^>]*\?>",
                    "",
                    xml_text,
                    count=1,
                    flags=
                        re.IGNORECASE,
                )
            )

            try:

                root = (
                    ET.fromstring(
                        "<repomix_root>"
                        f"{without_declaration}"
                        "</repomix_root>"
                    )
                )

            except ET.ParseError as exc:

                return (
                    [],
                    [
                        {
                            "reason":
                                "invalid_xml",

                            "detail":
                                str(exc),
                        }
                    ],
                )

        nodes = list(
            root.findall(
                ".//file"
            )
        )

        root_tag = str(
            root.tag
        ).casefold()

        if root_tag.endswith(
            "file"
        ):
            nodes.insert(
                0,
                root,
            )

        files: list[
            Dict[str, str]
        ] = []

        seen: set[
            str
        ] = set()

        for node in nodes:

            file_path = (
                node.get("path")
                or node.get(
                    "file_path"
                )
                or node.get(
                    "name"
                )
                or ""
            )

            content = "".join(
                node.itertext()
            )

            record = (
                self._file_record(
                    file_path,
                    content,
                )
            )

            if record is None:
                continue

            normalized_key = (
                record["path"]
                .casefold()
            )

            if normalized_key in seen:
                continue

            seen.add(
                normalized_key
            )

            files.append(
                record
            )

        if not files:

            errors.append(
                {
                    "reason":
                        "no_file_entries",

                    "detail":
                        (
                            "XML内に有効な"
                            "file要素がありません"
                        ),
                }
            )

        return files, errors

    # ========================================================
    # YAML Parsing
    # ========================================================

    def _extract_yaml_files(
        self,
        document: Any,
    ) -> list[
        Dict[str, str]
    ]:

        files: list[
            Dict[str, str]
        ] = []

        seen: set[
            str
        ] = set()

        visited: set[
            int
        ] = set()

        def add(
            path: Any,
            content: Any,
        ) -> None:

            record = (
                self._file_record(
                    path,
                    content,
                )
            )

            if record is None:
                return

            key = (
                record["path"]
                .casefold()
            )

            if key in seen:
                return

            seen.add(
                key
            )

            files.append(
                record
            )

        def visit(
            value: Any,
            depth: int = 0,
        ) -> None:

            if depth > 30:
                return

            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):

                identity = id(
                    value
                )

                if identity in visited:
                    return

                visited.add(
                    identity
                )

            # ----------------------------------------
            # Dict
            # ----------------------------------------

            if isinstance(
                value,
                dict,
            ):

                path_value = (
                    value.get("path")
                    or value.get(
                        "file_path"
                    )
                    or value.get(
                        "filePath"
                    )
                    or value.get(
                        "filename"
                    )
                )

                content_value: Any = None

                for key in (
                    "content",
                    "text",
                    "code",
                    "source",
                ):

                    if key in value:

                        content_value = (
                            value[key]
                        )

                        break

                if (
                    path_value
                    is not None
                    and content_value
                    is not None
                ):

                    add(
                        path_value,
                        content_value,
                    )

                # ------------------------------------
                # files:
                #   src/App.tsx: ...
                # ------------------------------------

                mapped_files = (
                    value.get(
                        "files"
                    )
                )

                if isinstance(
                    mapped_files,
                    dict,
                ):

                    for (
                        mapped_path,
                        mapped_value,
                    ) in mapped_files.items():

                        if isinstance(
                            mapped_value,
                            dict,
                        ):

                            mapped_content = (
                                mapped_value.get(
                                    "content"
                                )
                                if "content"
                                in mapped_value
                                else mapped_value.get(
                                    "text",
                                    mapped_value,
                                )
                            )

                        else:

                            mapped_content = (
                                mapped_value
                            )

                        add(
                            mapped_path,
                            mapped_content,
                        )

                # ------------------------------------
                # Arbitrary file path key
                # ------------------------------------

                for (
                    key,
                    child,
                ) in value.items():

                    if (
                        self
                        ._looks_like_file_path(
                            key
                        )
                        and isinstance(
                            child,
                            (
                                str,
                                dict,
                                list,
                            ),
                        )
                    ):

                        if isinstance(
                            child,
                            dict,
                        ):

                            child_content = (
                                child.get(
                                    "content",
                                    child.get(
                                        "text",
                                        child,
                                    ),
                                )
                            )

                        else:

                            child_content = (
                                child
                            )

                        add(
                            key,
                            child_content,
                        )

                    if key not in {
                        "content",
                        "text",
                        "code",
                        "source",
                    }:

                        visit(
                            child,
                            depth + 1,
                        )

            # ----------------------------------------
            # List
            # ----------------------------------------

            elif isinstance(
                value,
                list,
            ):

                for child in value:

                    visit(
                        child,
                        depth + 1,
                    )

            # ----------------------------------------
            # Embedded XML
            # ----------------------------------------

            elif (
                isinstance(
                    value,
                    str,
                )
                and "<file"
                in value
            ):

                (
                    xml_files,
                    _,
                ) = (
                    self
                    ._parse_xml_text(
                        value
                    )
                )

                for record in (
                    xml_files
                ):

                    add(
                        record["path"],
                        record["content"],
                    )

        visit(
            document
        )

        return files

    def _parse_yaml_text(
        self,
        raw_text: str,
    ) -> tuple[
        list[Dict[str, str]],
        list[Dict[str, str]],
    ]:

        if not YAML_AVAILABLE:

            return (
                [],
                [
                    {
                        "reason":
                            "yaml_dependency_missing",

                        "detail":
                            (
                                "PyYAMLが必要です。"
                                "pip install pyyaml"
                            ),
                    }
                ],
            )

        try:

            documents = list(
                yaml.safe_load_all(
                    raw_text
                )
            )

        except Exception as exc:

            return (
                [],
                [
                    {
                        "reason":
                            "invalid_yaml",

                        "detail":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }
                ],
            )

        files: list[
            Dict[str, str]
        ] = []

        seen: set[
            str
        ] = set()

        for document in documents:

            for record in (
                self._extract_yaml_files(
                    document
                )
            ):

                key = (
                    record["path"]
                    .casefold()
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                files.append(
                    record
                )

        errors: list[
            Dict[str, str]
        ] = []

        if not files:

            errors.append(
                {
                    "reason":
                        "no_file_entries",

                    "detail":
                        (
                            "YAML内から"
                            "ファイル情報を抽出できませんでした"
                        ),
                }
            )

        return files, errors

    # ========================================================
    # Input Parsing
    # ========================================================

    def _parse_input(
        self,
        selected: RepomixInput,
    ) -> tuple[
        list[Dict[str, str]],
        list[Dict[str, str]],
    ]:

        if (
            selected.size_bytes
            > self.max_input_bytes
        ):

            return (
                [],
                [
                    {
                        "reason":
                            "input_too_large",

                        "detail":
                            (
                                f"{selected.size_bytes} bytes "
                                "が最大サイズ "
                                f"{self.max_input_bytes} bytes "
                                "を超えています"
                            ),
                    }
                ],
            )

        encodings = (
            "utf-8-sig",
            "utf-8",
            "cp932",
            "shift_jis",
        )

        raw_text: str | None = None

        last_error: Exception | None = None

        for encoding in encodings:

            try:

                raw_text = (
                    selected.path
                    .read_text(
                        encoding=
                            encoding
                    )
                )

                break

            except UnicodeDecodeError as exc:

                last_error = exc

                continue

            except OSError as exc:

                return (
                    [],
                    [
                        {
                            "reason":
                                "read_error",

                            "detail":
                                (
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                        }
                    ],
                )

        if raw_text is None:

            return (
                [],
                [
                    {
                        "reason":
                            "encoding_error",

                        "detail":
                            str(
                                last_error
                                or ""
                            ),
                    }
                ],
            )

        if (
            selected.input_format
            == "xml"
        ):

            return (
                self._parse_xml_text(
                    raw_text
                )
            )

        return (
            self._parse_yaml_text(
                raw_text
            )
        )

    # ========================================================
    # Analyzer Execution
    # ========================================================

    async def _run_analyzers(
        self,
        files: Sequence[
            Dict[str, str]
        ],
    ) -> list[
        Dict[str, str]
    ]:

        errors: list[
            Dict[str, str]
        ] = []

        for file_data in files:

            file_path = (
                file_data[
                    "path"
                ]
            )

            content = (
                file_data[
                    "content"
                ]
            )

            extension = (
                Path(file_path)
                .suffix
                .casefold()
            )

            line_count = len(
                content.splitlines()
            )

            for analyzer in (
                self.analyzers
            ):

                analyzer_name = (
                    analyzer
                    .__class__
                    .__name__
                )

                try:

                    can_handle = (
                        analyzer.can_handle(
                            file_path,
                            extension,
                        )
                    )

                    if inspect.isawaitable(
                        can_handle
                    ):

                        can_handle = await (
                            can_handle
                        )

                    if not can_handle:
                        continue

                    analysis_result = (
                        analyzer.analyze(
                            file_path,
                            extension,
                            content,
                            line_count,
                        )
                    )

                    if inspect.isawaitable(
                        analysis_result
                    ):

                        await (
                            analysis_result
                        )

                except Exception as exc:

                    errors.append(
                        {
                            "path":
                                file_path,

                            "analyzer":
                                analyzer_name,

                            "detail":
                                (
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                        }
                    )

        return errors

    # ========================================================
    # Analyzer Export
    # ========================================================

    @staticmethod
    def _count_export_items(
        content: Any,
    ) -> int:

        if isinstance(
            content,
            list,
        ):

            return len(
                content
            )

        if isinstance(
            content,
            dict,
        ):

            for key in (
                "items",
                "files",
                "features",
                "components",
            ):

                value = (
                    content.get(
                        key
                    )
                )

                if isinstance(
                    value,
                    list,
                ):

                    return len(
                        value
                    )

            return len(
                content
            )

        return (
            1
            if content
            is not None
            else 0
        )

    async def _export_analyzer_results(
        self,
        project_id: str,
    ) -> tuple[
        list[str],
        Dict[str, int],
        list[Dict[str, str]],
    ]:

        saved_paths: list[
            str
        ] = []

        extracted_summary: Dict[
            str,
            int
        ] = {}

        errors: list[
            Dict[str, str]
        ] = []

        safe_project_id = (
            self._normalize_project_id(
                project_id
            )
            or "default_project"
        )

        for analyzer in (
            self.analyzers
        ):

            analyzer_name = (
                analyzer
                .__class__
                .__name__
            )

            try:

                export_data = (
                    analyzer
                    .get_export_data()
                )

                if inspect.isawaitable(
                    export_data
                ):

                    export_data = await (
                        export_data
                    )

                if not isinstance(
                    export_data,
                    dict,
                ):

                    continue

                raw_filename = str(
                    export_data.get(
                        "filename",
                        "",
                    )
                ).strip()

                if not raw_filename:
                    continue

                safe_filename = (
                    Path(
                        raw_filename
                    ).name
                )

                if not (
                    safe_filename
                    .casefold()
                    .endswith(
                        ".json"
                    )
                ):

                    safe_filename += (
                        ".json"
                    )

                content = (
                    export_data.get(
                        "content"
                    )
                )

                save_path = (
                    Path(
                        self.analyzer_output_root
                    )
                    / safe_project_id
                    / safe_filename
                ).as_posix()

                saved = await (
                    asyncio.to_thread(
                        self.manager.write_file,
                        save_path,
                        json.dumps(
                            content,
                            ensure_ascii=False,
                            indent=2,
                            default=str,
                        ),
                    )
                )

                if not saved:

                    errors.append(
                        {
                            "analyzer":
                                analyzer_name,

                            "path":
                                save_path,

                            "detail":
                                (
                                    "KnowledgeManager."
                                    "write_file() "
                                    "returned False"
                                ),
                        }
                    )

                    continue

                saved_paths.append(
                    save_path
                )

                extracted_summary[
                    safe_filename
                ] = (
                    self
                    ._count_export_items(
                        content
                    )
                )

            except Exception as exc:

                errors.append(
                    {
                        "analyzer":
                            analyzer_name,

                        "detail":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }
                )

        return (
            saved_paths,
            extracted_summary,
            errors,
        )

    # ========================================================
    # Project Knowledge Builder
    # ========================================================

    async def _build_project_knowledge(
        self,
        selected: RepomixInput,
        saved_paths: list[str],
    ) -> tuple[
        dict[str, Any] | None,
        list[str],
    ]:

        warnings: list[
            str
        ] = []

        if (
            self.project_knowledge_builder
            is None
        ):

            warnings.append(
                (
                    "ProjectKnowledgeBuilderは"
                    "利用できません。"
                )
            )

            return (
                None,
                warnings,
            )

        source_dir = (
            Path(
                self.analyzer_output_root
            )
            / selected.project_id
        )

        try:

            result = await (
                self
                .project_knowledge_builder
                .build_async(
                    project_id=
                        selected.project_id,

                    source_dir=
                        source_dir,

                    source_repomix=
                        selected.path
                        .as_posix(),

                    extra_metadata={
                        "repomix_format":
                            selected.input_format,

                        "repomix_series":
                            selected.series,

                        "repomix_sequence":
                            selected.sequence,

                        "analyzer_outputs":
                            saved_paths,
                    },
                )
            )

        except Exception as exc:

            warnings.append(
                (
                    "ProjectKnowledgeBuilder失敗: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
            )

            return (
                None,
                warnings,
            )

        if not getattr(
            result,
            "success",
            False,
        ):

            warnings.extend(
                getattr(
                    result,
                    "errors",
                    [],
                )
                or []
            )

        warnings.extend(
            getattr(
                result,
                "warnings",
                [],
            )
            or []
        )

        try:

            return (
                result.to_dict(),
                warnings,
            )

        except Exception:

            return (
                {
                    "success":
                        getattr(
                            result,
                            "success",
                            False,
                        ),

                    "project_id":
                        selected.project_id,

                    "output_path":
                        getattr(
                            result,
                            "output_path",
                            "",
                        ),
                },
                warnings,
            )

    # ========================================================
    # Utilities
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

            text = (
                value.strip()
            )

            return (
                [text]
                if text
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

                text = str(
                    item
                ).strip()

                if text:

                    result.append(
                        text
                    )

            return result

        return [
            str(value)
        ]

    # ========================================================
    # Main
    # ========================================================

    async def handle(
        self,
        request: Any,
    ) -> Tuple[
        str,
        Dict[str, Any],
    ]:

        message = str(
            getattr(
                request,
                "message",
                "",
            )
        )

        # IntentInspectorの結果が
        # request上に載っている場合のみ再利用。
        # ここでIntentInspectorを呼び直さない。
        current_signals = (
            getattr(
                request,
                "intent_analysis",
                None,
            )
            or getattr(
                request,
                "signals",
                None,
            )
            or {}
        )

        # ----------------------------------------------------
        # Select Repomix Input
        # ----------------------------------------------------

        (
            selected,
            candidates,
            selection_error,
        ) = (
            self._select_input(
                request=
                    request,

                message=
                    message,

                current_signals=
                    current_signals,
            )
        )

        candidate_data = [
            candidate.to_dict(
                self.resolved_root
            )
            for candidate
            in sorted(
                candidates,
                key=
                    self._selection_key,
                reverse=True,
            )
        ]

        # ----------------------------------------------------
        # Selection Failure
        # ----------------------------------------------------

        if selected is None:

            projects = sorted(
                {
                    candidate.project_id
                    for candidate
                    in candidates
                }
            )

            reply = (
                "❌ Repomix入力を"
                "選択できませんでした。\n\n"
                f"{selection_error or ''}"
            )

            if projects:

                reply += (
                    "\n\n利用可能な作品:\n"
                    + "\n".join(
                        f"- `{project}`"
                        for project
                        in projects
                    )
                )

            return (
                "text",
                {
                    "message":
                        reply,

                    "system_observation":
                        {
                            "action":
                                "ANALYZE_REPOMIX",

                            "status":
                                "failed",

                            "stage":
                                "input_selection",

                            "error":
                                selection_error,

                            "projects":
                                projects,

                            "candidates":
                                candidate_data,
                        },
                },
            )

        selected_data = (
            selected.to_dict(
                self.resolved_root
            )
        )

        print(
            "\n🚀 [RepomixHandler] "
            f"project={selected.project_id} "
            f"input={selected_data['path']} "
            f"format={selected.input_format} "
            f"sequence={selected.sequence}"
        )

        # ----------------------------------------------------
        # Parse
        # ----------------------------------------------------

        (
            files,
            parse_errors,
        ) = (
            self._parse_input(
                selected
            )
        )

        if not files:

            detail = (
                parse_errors[0].get(
                    "detail",
                    "",
                )
                if parse_errors
                else (
                    "ファイル情報を"
                    "抽出できませんでした"
                )
            )

            return (
                "text",
                {
                    "message":
                        (
                            "❌ Repomix解析失敗: "
                            f"{detail}"
                        ),

                    "system_observation":
                        {
                            "action":
                                "ANALYZE_REPOMIX",

                            "status":
                                "failed",

                            "stage":
                                "parse",

                            "project_id":
                                selected.project_id,

                            "selected_input":
                                selected_data,

                            "parse_errors":
                                parse_errors,

                            "candidates":
                                candidate_data,
                        },
                },
            )

        # ----------------------------------------------------
        # Analyzer Reset
        # ----------------------------------------------------

        self.analyzers = (
            self._load_analyzers_dynamically()
        )

        analyzer_errors: list[
            Dict[str, str]
        ] = []

        if not self.analyzers:

            analyzer_errors.append(
                {
                    "analyzer":
                        "RepomixHandler",

                    "detail":
                        (
                            "利用可能なAnalyzerが"
                            "0件です。"
                        ),
                }
            )

        else:

            analyzer_errors = await (
                self._run_analyzers(
                    files
                )
            )

        # ----------------------------------------------------
        # Export Analyzer Results
        # ----------------------------------------------------

        (
            saved_paths,
            extracted_summary,
            export_errors,
        ) = await (
            self
            ._export_analyzer_results(
                project_id=
                    selected.project_id
            )
        )

        # ----------------------------------------------------
        # ProjectKnowledgeBuilder
        # ----------------------------------------------------

        (
            project_knowledge_result,
            project_knowledge_warnings,
        ) = await (
            self
            ._build_project_knowledge(
                selected=
                    selected,

                saved_paths=
                    saved_paths,
            )
        )

        # ----------------------------------------------------
        # Error Merge
        # ----------------------------------------------------

        all_errors = [
            *parse_errors,
            *analyzer_errors,
            *export_errors,
        ]

        project_knowledge_success = (
            bool(
                project_knowledge_result
                and project_knowledge_result.get(
                    "success"
                )
            )
        )

        if all_errors:

            status = (
                "partial"
            )

        elif (
            self.project_knowledge_builder
            is not None
            and not project_knowledge_success
        ):

            status = (
                "partial"
            )

        else:

            status = (
                "success"
            )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary_lines = [
            (
                f"- 📄 **{name}**: "
                f"`{count}` 件"
            )
            for (
                name,
                count,
            )
            in (
                extracted_summary
                .items()
            )
        ]

        summary_text = (
            "\n".join(
                summary_lines
            )
            or (
                "- Analyzer出力なし"
            )
        )

        project_knowledge_path = ""

        if (
            project_knowledge_result
        ):

            project_knowledge_path = str(
                project_knowledge_result.get(
                    "output_path",
                    "",
                )
            )

        reply_msg = (
            "🧠 **Repomix解析が完了しました**\n\n"
            f"- 🆔 **Project ID**: "
            f"`{selected.project_id}`\n"
            f"- 📥 **入力**: "
            f"`{selected_data['path']}`\n"
            f"- 🏷️ **系列**: "
            f"`{selected.series or 'default'}`\n"
            f"- 🔢 **Version**: "
            f"`{selected.sequence}`\n"
            f"- 🧾 **形式**: "
            f"`{selected.input_format}`\n"
            f"- 📂 **解析ファイル数**: "
            f"`{len(files)}`\n"
            f"- ⚠️ **解析エラー数**: "
            f"`{len(all_errors)}`\n\n"
            f"{summary_text}\n"
        )

        if project_knowledge_path:

            reply_msg += (
                "\n📚 **Project Knowledge**: "
                f"`{project_knowledge_path}`\n"
            )

        if project_knowledge_warnings:

            reply_msg += (
                "\n⚠️ ProjectKnowledge警告:\n"
                + "\n".join(
                    f"- {warning}"
                    for warning
                    in (
                        project_knowledge_warnings[
                            :10
                        ]
                    )
                )
                + "\n"
            )

        # ----------------------------------------------------
        # System Observation
        # ----------------------------------------------------

        system_observation = {
            "action":
                "ANALYZE_REPOMIX",

            "status":
                status,

            "project_id":
                selected.project_id,

            "selected_input":
                selected_data,

            "candidates":
                candidate_data,

            "total_scanned_files":
                len(files),

            "extracted_data":
                extracted_summary,

            "saved_paths":
                saved_paths,

            "project_knowledge":
                project_knowledge_result,

            "project_knowledge_warnings":
                project_knowledge_warnings,

            "errors":
                all_errors[:100],
        }

        # ----------------------------------------------------
        # Return
        # ----------------------------------------------------

        return (
            "ui_code",
            {
                "message":
                    (
                        "Repomix解析と"
                        "Project Knowledge更新に"
                        "成功しました。"
                        if status
                        == "success"
                        else (
                            "Repomix解析は完了しましたが、"
                            "一部に問題があります。"
                        )
                    ),

                "blocks":
                    [
                        {
                            "type":
                                "MarkdownChatBlock",

                            "props":
                                {
                                    "content":
                                        reply_msg
                                },
                        }
                    ],

                "system_observation":
                    system_observation,
            },
        )


# ============================================================
# Standalone Debug
# ============================================================


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "RepomixHandler standalone debug"
        )
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--message",
        default=(
            "repomixを解析して"
        ),
    )

    parser.add_argument(
        "--project-id",
        default=None,
    )

    parser.add_argument(
        "--repomix-path",
        default=None,
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Minimal Request
    # --------------------------------------------------------

    class DummyRequest:
        def __init__(
            self,
        ) -> None:

            self.message = (
                args.message
            )

            self.project_id = (
                args.project_id
            )

            self.repomix_path = (
                args.repomix_path
            )

            self.intent_analysis = {}

    async def main() -> None:

        handler = (
            RepomixHandler(
                project_root=
                    args.project_root
            )
        )

        (
            response_type,
            content,
        ) = await (
            handler.handle(
                DummyRequest()
            )
        )

        print(
            "\n=== Response Type ==="
        )

        print(
            response_type
        )

        print(
            "\n=== Content ==="
        )

        print(
            json.dumps(
                content,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    asyncio.run(
        main()
    )
