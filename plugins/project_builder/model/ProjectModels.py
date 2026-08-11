# =========================================================
# ProjectBuilder 共通型定義 (統合版)
# ChatGPTの強力なパイプライン設計と、
# Tool 1〜3のアトミック分割・AST解析の概念を統合した完全版モデル。
# =========================================================
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

# =========================================================
# Enums (状態・設定)
# =========================================================
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
    JSON = "JSON"
    MARKDOWN = "Markdown"
    UNKNOWN = "Unknown"

class ProjectFramework(str, Enum):
    REACT = "React"
    ELECTRON = "Electron"
    NODEJS = "Node.js"
    NONE = "None"
    UNKNOWN = "Unknown"

class BuildMode(str, Enum):
    CREATE = "Create"
    UPDATE = "Update"
    REBUILD = "Rebuild"
    ANALYZE = "Analyze"   # コード解析モード
    SPLIT = "Split"       # Tool 1~3: コード分割モード
    VALIDATE = "Validate"

class BuildStatus(str, Enum):
    SUCCESS = "Success"
    WARNING = "Warning"
    ERROR = "Error"
    RUNNING = "Running"
    CANCELLED = "Cancelled"

# =========================================================
# Base Object (すべての基底)
# =========================================================
@dataclass
class BaseProjectObject:
    name: str = ""
    description: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

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

# =========================================================
# コード解析特有の拡張モデル (Tool 1〜3の概念)
# =========================================================
class CodeNodeType(str, Enum):
    """アトミック分割されたコードブロックの種類 (Tool 2 & 3)"""
    IMPORT = "Import"         # 00_imports.js
    VARIABLE = "Variable"     # 10_variables.js
    FUNCTION = "Function"     # 20_functions.js
    CLASS = "Class"
    EVENT_LISTENER = "EventListener"
    GLOBAL_STATE = "GlobalState" # 90_globals.js

@dataclass
class CodeNode(BaseProjectObject):
    """
    分割されたコードの最小単位（関数1つ、変数1つ等）
    ReactのCanvas上で1つのノードとして表示される。
    """
    node_type: CodeNodeType = CodeNodeType.FUNCTION
    content: str = ""
    start_line: int = 0
    end_line: int = 0
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "node_type": self.node_type.value,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "dependencies": self.dependencies
        })
        return d

# =========================================================
# Project Components (ファイル・フォルダ)
# =========================================================
@dataclass
class FileNode(BaseProjectObject):
    path: str = ""
    extension: str = ""
    content: str = ""
    size: int = 0
    language: Optional[ProjectLanguage] = None
    # --- 拡張: AST解析結果のノード群を保持 ---
    ast_nodes: List[CodeNode] = field(default_factory=list)
    tier: int = 3 # Tool 1のPriority (1:Infra, 2:Module, 3:UI)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "path": self.path,
            "extension": self.extension,
            "language": self.language.value if self.language else None,
            "tier": self.tier,
            "ast_nodes": [node.to_dict() for node in self.ast_nodes]
        })
        return d

@dataclass
class FolderNode(BaseProjectObject):
    path: str = ""
    children: List["FolderNode"] = field(default_factory=list)
    files: List[FileNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "path": self.path,
            "files": [f.to_dict() for f in self.files],
            "children": [c.to_dict() for c in self.children]
        })
        return d

@dataclass
class WorkspaceInfo(BaseProjectObject):
    root_path: str = ""
    folders: List[FolderNode] = field(default_factory=list)
    files: List[FileNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "root_path": self.root_path,
            "files": [f.to_dict() for f in self.files],
            "folders": [folder.to_dict() for folder in self.folders]
        })
        return d

# =========================================================
# Analysis & Planning (解析と計画)
# =========================================================
@dataclass
class ProjectAnalysis(BaseProjectObject):
    """AST解析・依存関係スキャンの結果 (Tool 1 & 2)"""
    stage: BuildStage = BuildStage.ANALYZING
    workspace: Optional[WorkspaceInfo] = None
    score: float = 0.0
    complexity: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage": self.stage.value,
            "workspace": self.workspace.to_dict() if self.workspace else None,
            "score": self.score,
            "warnings": self.warnings,
            "errors": self.errors
        })
        return d

@dataclass
class ProjectPlan(BaseProjectObject):
    """分割・再構築の計画 (Tool 1の動的閾値判定結果など)"""
    stage: BuildStage = BuildStage.PLANNING
    build_mode: BuildMode = BuildMode.SPLIT
    target_directory: str = ""
    output_directory: str = ""
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage": self.stage.value,
            "build_mode": self.build_mode.value,
            "target_directory": self.target_directory,
            "output_directory": self.output_directory,
            "options": self.options
        })
        return d

# =========================================================
# Result (最終結果)
# =========================================================
@dataclass
class ProjectKnowledgeResult(BaseProjectObject):
    """Electron(React) へ最終的に送信される巨大なJSONの元"""
    stage: BuildStage = BuildStage.FINISHED
    status: BuildStatus = BuildStatus.SUCCESS
    success: bool = True
    plan: Optional[ProjectPlan] = None
    analysis: Optional[ProjectAnalysis] = None
    logs: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage": self.stage.value,
            "status": self.status.value,
            "success": self.success,
            "plan": self.plan.to_dict() if self.plan else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "logs": self.logs,
            "elapsed_time": self.elapsed_time
        })
        return d