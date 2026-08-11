from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class BuildStage(str, Enum):
    IDLE = "Idle"
    PLANNING = "Planning"
    ANALYZING = "Analyzing"
    RESOLVING = "Resolving"
    BUILDING = "Building"
    VALIDATING = "Validating"
    FINISHED = "Finished"
    FAILED = "Failed"


class ProjectLanguage(str, Enum):
    PYTHON = "Python"
    TYPESCRIPT = "TypeScript"
    JAVASCRIPT = "JavaScript"
    HTML = "HTML"
    CSS = "CSS"
    SCSS = "SCSS"
    JSON = "JSON"
    YAML = "YAML"
    MARKDOWN = "Markdown"
    TEXT = "Text"
    UNKNOWN = "Unknown"


class ProjectFramework(str, Enum):
    REACT = "React"
    NEXT = "Next.js"
    VUE = "Vue"
    ANGULAR = "Angular"
    SVELTE = "Svelte"
    FASTAPI = "FastAPI"
    FLASK = "Flask"
    DJANGO = "Django"
    NONE = "None"
    UNKNOWN = "Unknown"


class PackageManager(str, Enum):
    NPM = "npm"
    PNPM = "pnpm"
    YARN = "yarn"
    BUN = "bun"
    PIP = "pip"
    UV = "uv"
    POETRY = "poetry"
    NONE = "none"
    UNKNOWN = "unknown"


class BuildMode(str, Enum):
    CREATE = "Create"
    UPDATE = "Update"
    REBUILD = "Rebuild"
    ANALYZE = "Analyze"
    VALIDATE = "Validate"


class BuildStatus(str, Enum):
    SUCCESS = "Success"
    WARNING = "Warning"
    ERROR = "Error"
    RUNNING = "Running"
    CANCELLED = "Cancelled"


@dataclass
class BaseProjectObject:
    name: str = ""
    description: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name must be str")
        if not isinstance(self.description, str):
            raise TypeError("description must be str")
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be bool")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    def update_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def has_metadata(self, key: str) -> bool:
        return key in self.metadata

    def clear_metadata(self) -> None:
        self.metadata.clear()


@dataclass
class FileNode(BaseProjectObject):
    path: str = ""
    extension: str = ""
    content: str = ""
    size: int = 0
    generated: bool = False
    overwrite: bool = False
    encoding: str = "utf-8"
    language: Optional[ProjectLanguage] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.path, str):
            raise TypeError("path must be str")
        if not isinstance(self.extension, str):
            raise TypeError("extension must be str")
        if not isinstance(self.content, str):
            raise TypeError("content must be str")
        if not isinstance(self.size, int) or self.size < 0:
            raise ValueError("size must be a non-negative int")
        if not isinstance(self.generated, bool):
            raise TypeError("generated must be bool")
        if not isinstance(self.overwrite, bool):
            raise TypeError("overwrite must be bool")
        if not isinstance(self.encoding, str):
            raise TypeError("encoding must be str")
        if self.language is not None and not isinstance(self.language, ProjectLanguage):
            raise TypeError("language must be ProjectLanguage or None")


@dataclass
class FolderNode(BaseProjectObject):
    children: List["FolderNode"] = field(default_factory=list)
    files: List[FileNode] = field(default_factory=list)
    path: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.children, list):
            raise TypeError("children must be list")
        if not isinstance(self.files, list):
            raise TypeError("files must be list")
        if not isinstance(self.path, str):
            raise TypeError("path must be str")
        for child in self.children:
            if not isinstance(child, FolderNode):
                raise TypeError("children must contain FolderNode only")
        for file in self.files:
            if not isinstance(file, FileNode):
                raise TypeError("files must contain FileNode only")

    def add_folder(self, folder: "FolderNode") -> None:
        if not isinstance(folder, FolderNode):
            raise TypeError("folder must be FolderNode")
        self.children.append(folder)

    def add_file(self, file: FileNode) -> None:
        if not isinstance(file, FileNode):
            raise TypeError("file must be FileNode")
        self.files.append(file)

    @property
    def folder_count(self) -> int:
        return len(self.children)

    @property
    def file_count(self) -> int:
        return len(self.files)


@dataclass
class BuildValidata(BaseProjectObject):
    stage: BuildStage = BuildStage.IDLE
    mode: BuildMode = BuildMode.CREATE
    status: BuildStatus = BuildStatus.RUNNING
    language: ProjectLanguage = ProjectLanguage.UNKNOWN
    framework: ProjectFramework = ProjectFramework.UNKNOWN
    package_manager: PackageManager = PackageManager.UNKNOWN
    root: Optional[FolderNode] = None
    files: List[FileNode] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.stage, BuildStage):
            raise TypeError("stage must be BuildStage")
        if not isinstance(self.mode, BuildMode):
            raise TypeError("mode must be BuildMode")
        if not isinstance(self.status, BuildStatus):
            raise TypeError("status must be BuildStatus")
        if not isinstance(self.language, ProjectLanguage):
            raise TypeError("language must be ProjectLanguage")
        if not isinstance(self.framework, ProjectFramework):
            raise TypeError("framework must be ProjectFramework")
        if not isinstance(self.package_manager, PackageManager):
            raise TypeError("package_manager must be PackageManager")
        if self.root is not None and not isinstance(self.root, FolderNode):
            raise TypeError("root must be FolderNode or None")
        if not isinstance(self.files, list):
            raise TypeError("files must be list")
        if not isinstance(self.errors, list):
            raise TypeError("errors must be list")
        if not isinstance(self.warnings, list):
            raise TypeError("warnings must be list")
        for file in self.files:
            if not isinstance(file, FileNode):
                raise TypeError("files must contain FileNode only")
        for message in self.errors:
            if not isinstance(message, str):
                raise TypeError("errors must contain str only")
        for message in self.warnings:
            if not isinstance(message, str):
                raise TypeError("warnings must contain str only")

    def is_valid(self) -> bool:
        return self.status in {BuildStatus.SUCCESS, BuildStatus.WARNING} and not self.errors

    def add_error(self, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError("message must be str")
        self.errors.append(message)
        self.status = BuildStatus.ERROR
        self.stage = BuildStage.FAILED

    def add_warning(self, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError("message must be str")
        self.warnings.append(message)
        if self.status == BuildStatus.RUNNING:
            self.status = BuildStatus.WARNING

    def add_file(self, file: FileNode) -> None:
        if not isinstance(file, FileNode):
            raise TypeError("file must be FileNode")
        self.files.append(file)

    def set_root(self, root: FolderNode) -> None:
        if not isinstance(root, FolderNode):
            raise TypeError("root must be FolderNode")
        self.root = root

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "stage": self.stage.value,
            "mode": self.mode.value,
            "status": self.status.value,
            "language": self.language.value,
            "framework": self.framework.value,
            "package_manager": self.package_manager.value,
            "root": self.root.to_dict() if self.root else None,
            "files": [f.to_dict() for f in self.files],
            "errors": self.errors,
            "warnings": self.warnings,
        }