"""
ProjectTypes.py
===
Project Builder 共通型定義

第1回
---------------------------------------------
・Enum
・基本クラス(BaseProjectObject)

このファイルは ProjectBuilder 全体で使用する
共通型を定義する。

DeploymentHandler
ProjectPlanner
ProjectAnalyzer
FolderAnalyzer
DependencyResolver
TemplateEngine
FileWriter
BuildValidator

などは、この型を利用する。

===
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


# ===
# Build Stage
# ===

class BuildStage(str, Enum):
    """
    現在どの処理段階か
    """

    IDLE = "Idle"

    PLANNING = "Planning"

    ANALYZING = "Analyzing"

    RESOLVING = "Resolving"

    BUILDING = "Building"

    VALIDATING = "Validating"

    FINISHED = "Finished"

    FAILED = "Failed"


# ===
# Programming Language
# ===

class ProjectLanguage(str, Enum):
    """
    使用言語
    """

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


# ===
# Framework
# ===

class ProjectFramework(str, Enum):
    """
    使用フレームワーク
    """

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


# ===
# Package Manager
# ===

class PackageManager(str, Enum):
    """
    パッケージマネージャ
    """

    NPM = "npm"

    PNPM = "pnpm"

    YARN = "yarn"

    BUN = "bun"

    PIP = "pip"

    UV = "uv"

    POETRY = "poetry"

    NONE = "none"

    UNKNOWN = "unknown"


# ===
# Build Mode
# ===

class BuildMode(str, Enum):
    """
    ビルド方式
    """

    CREATE = "Create"

    UPDATE = "Update"

    REBUILD = "Rebuild"

    ANALYZE = "Analyze"

    VALIDATE = "Validate"


# ===
# Build Status
# ===

class BuildStatus(str, Enum):
    """
    処理状態
    """

    SUCCESS = "Success"

    WARNING = "Warning"

    ERROR = "Error"

    RUNNING = "Running"

    CANCELLED = "Cancelled"


# ===
# Base Object
# ===

@dataclass
class BaseProjectObject:
    """
    ProjectBuilder 全体の基底クラス

    すべてのデータクラスは
    このクラスを継承することを想定している。
    """

    name: str = ""

    description: str = ""

    enabled: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式へ変換
        """
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    def update_metadata(self, key: str, value: Any) -> None:
        """
        metadataへ値を追加
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        metadata取得
        """
        return self.metadata.get(key, default)

    def has_metadata(self, key: str) -> bool:
        """
        metadataを保持しているか
        """
        return key in self.metadata

    def clear_metadata(self) -> None:
        """
        metadataを初期化
        """
        self.metadata.clear()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(name='{self.name}', enabled={self.enabled})"
        )
    # ===
# Project Components
# 第2回
# Folder・File・Dependency・Template
# ===



from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# BaseProjectObject は第1回で定義済み
# from .ProjectTypes import BaseProjectObject


# ===
# Folder
# ===

@dataclass
class FolderNode(BaseProjectObject):
    """
    フォルダーを表すノード
    """

    children: List["FolderNode"] = field(default_factory=list)

    files: List["FileNode"] = field(default_factory=list)

    path: str = ""

    def add_folder(self, folder: "FolderNode") -> None:
        self.children.append(folder)

    def add_file(self, file: "FileNode") -> None:
        self.files.append(file)

    @property
    def folder_count(self) -> int:
        return len(self.children)

    @property
    def file_count(self) -> int:
        return len(self.files)


# ===
# File
# ===

@dataclass
class FileNode(BaseProjectObject):
    """
    ファイル情報
    """

    path: str = ""

    extension: str = ""

    content: str = ""

    size: int = 0

    generated: bool = False

    overwrite: bool = False

    encoding: str = "utf-8"

    language: Optional[ProjectLanguage] = None


# ===
# Dependency
# ===

@dataclass
class Dependency(BaseProjectObject):
    """
    ライブラリ情報
    """

    version: str = "latest"

    required: bool = True

    dev_dependency: bool = False

    install_command: str = ""

    homepage: str = ""

    license: str = ""

    description: str = ""


# ===
# Template
# ===

@dataclass
class TemplateInfo(BaseProjectObject):
    """
    テンプレート情報
    """

    category: str = ""

    framework: Optional[ProjectFramework] = None

    language: Optional[ProjectLanguage] = None

    version: str = "1.0"

    author: str = ""

    tags: List[str] = field(default_factory=list)

    folders: List[FolderNode] = field(default_factory=list)

    files: List[FileNode] = field(default_factory=list)

    dependencies: List[Dependency] = field(default_factory=list)

    preview_image: str = ""

    def add_folder(self, folder: FolderNode) -> None:
        self.folders.append(folder)

    def add_file(self, file: FileNode) -> None:
        self.files.append(file)

    def add_dependency(self, dependency: Dependency) -> None:
        self.dependencies.append(dependency)


# ===
# Workspace
# ===

@dataclass
class WorkspaceInfo(BaseProjectObject):
    """
    現在開いているWorkspace情報
    """

    root_path: str = ""

    folders: List[FolderNode] = field(default_factory=list)

    files: List[FileNode] = field(default_factory=list)

    frameworks: List[ProjectFramework] = field(default_factory=list)

    languages: List[ProjectLanguage] = field(default_factory=list)

    dependencies: List[Dependency] = field(default_factory=list)

    def add_folder(self, folder: FolderNode):
        self.folders.append(folder)

    def add_file(self, file: FileNode):
        self.files.append(file)

    def add_dependency(self, dependency: Dependency):
        self.dependencies.append(dependency)
    # ===
# Planning & Analysis
# 第3回
# ProjectPlan・ProjectAnalysis
# ===




# ===
# Project Plan
# ===

@dataclass
class ProjectPlan(BaseProjectObject):
    """
    AIが最初に作る設計図

    ProjectPlanner が生成する。
    """

    framework: Optional[ProjectFramework] = None

    language: Optional[ProjectLanguage] = None

    package_manager: Optional[PackageManager] = None

    build_mode: BuildMode = BuildMode.CREATE

    stage: BuildStage = BuildStage.PLANNING

    workspace_name: str = ""

    template: Optional[TemplateInfo] = None

    target_directory: str = ""

    output_directory: str = ""

    goals: List[str] = field(default_factory=list)

    requirements: List[str] = field(default_factory=list)

    options: Dict[str, Any] = field(default_factory=dict)

    estimated_files: int = 0

    estimated_folders: int = 0

    estimated_dependencies: int = 0

    def add_goal(self, goal: str):

        self.goals.append(goal)

    def add_requirement(self, requirement: str):

        self.requirements.append(requirement)

    def set_option(self, key: str, value: Any):

        self.options[key] = value

    def get_option(self, key: str, default=None):

        return self.options.get(key, default)


# ===
# Project Analysis
# ===

@dataclass
class ProjectAnalysis(BaseProjectObject):
    """
    FolderAnalyzer
    ProjectAnalyzer

    の解析結果
    """

    stage: BuildStage = BuildStage.ANALYZING

    workspace: Optional[WorkspaceInfo] = None

    detected_framework: Optional[ProjectFramework] = None

    detected_language: Optional[ProjectLanguage] = None

    detected_package_manager: Optional[PackageManager] = None

    template: Optional[TemplateInfo] = None

    folders: List[FolderNode] = field(default_factory=list)

    files: List[FileNode] = field(default_factory=list)

    dependencies: List[Dependency] = field(default_factory=list)

    missing_files: List[str] = field(default_factory=list)

    missing_folders: List[str] = field(default_factory=list)

    duplicate_files: List[str] = field(default_factory=list)

    duplicate_dependencies: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    recommendations: List[str] = field(default_factory=list)

    score: float = 0.0

    complexity: float = 0.0

    analyzed: bool = False

    def add_warning(self, message: str):

        self.warnings.append(message)

    def add_error(self, message: str):

        self.errors.append(message)

    def add_recommendation(self, message: str):

        self.recommendations.append(message)

    def add_dependency(self, dependency: Dependency):

        self.dependencies.append(dependency)

    def add_file(self, file: FileNode):

        self.files.append(file)

    def add_folder(self, folder: FolderNode):

        self.folders.append(folder)

    @property
    def has_errors(self) -> bool:

        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:

        return len(self.warnings) > 0

    @property
    def is_valid(self) -> bool:

        return not self.has_errors

    @property
    def total_files(self) -> int:

        return len(self.files)

    @property
    def total_folders(self) -> int:

        return len(self.folders)

    @property
    def total_dependencies(self) -> int:

        return len(self.dependencies)

    def summary(self) -> Dict[str, Any]:
        """
        解析結果を簡潔に返す
        """

        return {

            "framework": (
                self.detected_framework.value
                if self.detected_framework
                else None
            ),

            "language": (
                self.detected_language.value
                if self.detected_language
                else None
            ),

            "files": self.total_files,

            "folders": self.total_folders,

            "dependencies": self.total_dependencies,

            "warnings": len(self.warnings),

            "errors": len(self.errors),

            "score": self.score,

            "complexity": self.complexity,
        }
    # ===
# Build & Validation
# 第4回
# BuildPlan・ValidationResult
# ===

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ===
# Build Plan
# ===

@dataclass
class BuildPlan(BaseProjectObject):
    """
    TemplateEngine が生成する
    実際に構築する内容
    """

    stage: BuildStage = BuildStage.BUILDING

    project_plan: Optional[ProjectPlan] = None

    analysis: Optional[ProjectAnalysis] = None

    folders: List[FolderNode] = field(default_factory=list)

    files: List[FileNode] = field(default_factory=list)

    dependencies: List[Dependency] = field(default_factory=list)

    templates: List[TemplateInfo] = field(default_factory=list)

    environment_variables: Dict[str, str] = field(default_factory=dict)

    install_commands: List[str] = field(default_factory=list)

    build_commands: List[str] = field(default_factory=list)

    run_commands: List[str] = field(default_factory=list)

    post_build_commands: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    estimated_time: float = 0.0

    overwrite_existing: bool = False

    create_gitignore: bool = True

    create_readme: bool = True

    initialized: bool = False

    def add_folder(self, folder: FolderNode):

        self.folders.append(folder)

    def add_file(self, file: FileNode):

        self.files.append(file)

    def add_dependency(self, dependency: Dependency):

        self.dependencies.append(dependency)

    def add_template(self, template: TemplateInfo):

        self.templates.append(template)

    def add_install_command(self, command: str):

        self.install_commands.append(command)

    def add_build_command(self, command: str):

        self.build_commands.append(command)

    def add_run_command(self, command: str):

        self.run_commands.append(command)

    def add_post_build_command(self, command: str):

        self.post_build_commands.append(command)

    def set_environment(self, key: str, value: str):

        self.environment_variables[key] = value

    @property
    def total_files(self):

        return len(self.files)

    @property
    def total_folders(self):

        return len(self.folders)

    @property
    def total_dependencies(self):

        return len(self.dependencies)


# ===
# Validation Result
# ===

@dataclass
class ValidationResult(BaseProjectObject):
    """
    BuildValidator の検査結果
    """

    stage: BuildStage = BuildStage.VALIDATING

    status: BuildStatus = BuildStatus.SUCCESS

    success: bool = True

    checked_files: List[str] = field(default_factory=list)

    missing_files: List[str] = field(default_factory=list)

    checked_folders: List[str] = field(default_factory=list)

    missing_folders: List[str] = field(default_factory=list)

    installed_dependencies: List[str] = field(default_factory=list)

    missing_dependencies: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    fixes: List[str] = field(default_factory=list)

    score: float = 100.0

    validated: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_warning(self, message: str):

        self.warnings.append(message)

        if self.status == BuildStatus.SUCCESS:
            self.status = BuildStatus.WARNING

    def add_error(self, message: str):

        self.errors.append(message)

        self.success = False

        self.status = BuildStatus.ERROR

    def add_fix(self, message: str):

        self.fixes.append(message)

    def add_checked_file(self, path: str):

        self.checked_files.append(path)

    def add_checked_folder(self, path: str):

        self.checked_folders.append(path)

    def add_missing_file(self, path: str):

        self.missing_files.append(path)

    def add_missing_folder(self, path: str):

        self.missing_folders.append(path)

    def add_missing_dependency(self, dependency: str):

        self.missing_dependencies.append(dependency)

    @property
    def has_errors(self):

        return len(self.errors) > 0

    @property
    def has_warnings(self):

        return len(self.warnings) > 0

    @property
    def is_valid(self):

        return self.success and not self.has_errors

    def summary(self) -> Dict[str, Any]:

        return {

            "status": self.status.value,

            "success": self.success,

            "checked_files": len(self.checked_files),

            "checked_folders": len(self.checked_folders),

            "missing_files": len(self.missing_files),

            "missing_folders": len(self.missing_folders),

            "missing_dependencies": len(self.missing_dependencies),

            "warnings": len(self.warnings),

            "errors": len(self.errors),

            "score": self.score
        }
        
    # ===
# Project Knowledge Result
# 第5回
# ===

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ===
# Project Knowledge Result
# ===

@dataclass
class ProjectKnowledgeResult(BaseProjectObject):
    """
    ProjectBuilder の最終成果物

    DeploymentHandler が最後に返すデータ。
    """

    stage: BuildStage = BuildStage.FINISHED

    status: BuildStatus = BuildStatus.SUCCESS

    success: bool = True

    plan: Optional[ProjectPlan] = None

    analysis: Optional[ProjectAnalysis] = None

    build: Optional[BuildPlan] = None

    validation: Optional[ValidationResult] = None

    blocks: List[Dict[str, Any]] = field(default_factory=list)

    logs: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    elapsed_time: float = 0.0

    score: float = 100.0

    completed: bool = False


    # -------------------------------------------------
    # Block
    # -------------------------------------------------

    def add_block(self, block: Dict[str, Any]):

        self.blocks.append(block)


    # -------------------------------------------------
    # Log
    # -------------------------------------------------

    def add_log(self, message: str):

        self.logs.append(message)


    # -------------------------------------------------
    # Warning
    # -------------------------------------------------

    def add_warning(self, message: str):

        self.warnings.append(message)

        if self.status == BuildStatus.SUCCESS:

            self.status = BuildStatus.WARNING


    # -------------------------------------------------
    # Error
    # -------------------------------------------------

    def add_error(self, message: str):

        self.errors.append(message)

        self.success = False

        self.status = BuildStatus.ERROR


    # -------------------------------------------------
    # Metadata
    # -------------------------------------------------

    def set_metadata(self, key: str, value: Any):

        self.metadata[key] = value


    # -------------------------------------------------
    # Utility
    # -------------------------------------------------

    @property
    def has_errors(self):

        return len(self.errors) > 0


    @property
    def has_warnings(self):

        return len(self.warnings) > 0


    @property
    def is_finished(self):

        return self.stage == BuildStage.FINISHED


    @property
    def total_blocks(self):

        return len(self.blocks)


    @property
    def total_logs(self):

        return len(self.logs)


    def finish(self):

        self.completed = True

        self.stage = BuildStage.FINISHED


    def summary(self):

        return {

            "status": self.status.value,

            "stage": self.stage.value,

            "completed": self.completed,

            "score": self.score,

            "warnings": len(self.warnings),

            "errors": len(self.errors),

            "blocks": len(self.blocks),

            "logs": len(self.logs)

        }


    def to_dict(self):

        return {

            "success": self.success,

            "status": self.status.value,

            "stage": self.stage.value,

            "score": self.score,

            "completed": self.completed,

            "warnings": self.warnings,

            "errors": self.errors,

            "logs": self.logs,

            "metadata": self.metadata,

            "summary": self.summary()

        }