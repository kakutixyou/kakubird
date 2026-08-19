"""
ProjectTypes.py
===
Project Builder 共通データモデル

役割
---------------------------------------------------------
ProjectBuilder 全体で使用する共通型を定義する。

DeploymentHandler
ProjectPlanner
FolderAnalyzer
ProjectAnalyzer
DependencyResolver
TemplateEngine
FileWriter
BuildValidator

などは、この型だけを受け渡しする。

===
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


# ===
# Enum
# ===

class ProjectLanguage(str, Enum):
    PYTHON = "Python"
    TYPESCRIPT = "TypeScript"
    JAVASCRIPT = "JavaScript"
    HTML = "HTML"
    CSS = "CSS"


class ProjectFramework(str, Enum):
    REACT = "React"
    NEXT = "Next.js"
    FASTAPI = "FastAPI"
    FLASK = "Flask"
    DJANGO = "Django"
    VUE = "Vue"
    NONE = "None"


class PackageManager(str, Enum):
    NPM = "npm"
    PNPM = "pnpm"
    YARN = "yarn"
    PIP = "pip"
    UV = "uv"
    NONE = "none"


# ===
# Folder
# ===

@dataclass
class FolderNode:
    """
    フォルダー構造
    """

    name: str
    children: List["FolderNode"] = field(default_factory=list)
    files: List[str] = field(default_factory=list)


# ===
# Dependency
# ===

@dataclass
class Dependency:

    name: str
    version: str = ""
    required: bool = True


# ===
# Template
# ===

@dataclass
class TemplateInfo:

    name: str
    category: str
    description: str = ""


# ===
# ProjectPlan
# ===

@dataclass
class ProjectPlan:
    """
    ProjectPlanner が作成する設計図
    """

    title: str

    framework: ProjectFramework

    language: ProjectLanguage

    package_manager: PackageManager

    template: Optional[TemplateInfo] = None

    description: str = ""

    options: Dict[str, Any] = field(default_factory=dict)


# ===
# Analysis
# ===

@dataclass
class ProjectAnalysis:

    framework_detected: Optional[str] = None

    language_detected: Optional[str] = None

    problems: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    existing_files: List[str] = field(default_factory=list)


# ===
# BuildPlan
# ===

@dataclass
class BuildPlan:
    """
    実際に生成する内容
    """

    folders: List[FolderNode] = field(default_factory=list)

    files: Dict[str, str] = field(default_factory=dict)

    dependencies: List[Dependency] = field(default_factory=list)


# ===
# Validation
# ===

@dataclass
class ValidationResult:

    success: bool = True

    warnings: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)


# ===
# Knowledge
# ===

@dataclass
class ProjectKnowledgeResult:
    """
    ProjectBuilder の最終成果物
    """

    plan: Optional[ProjectPlan] = None

    analysis: Optional[ProjectAnalysis] = None

    build_plan: Optional[BuildPlan] = None

    validation: Optional[ValidationResult] = None

    metadata: Dict[str, Any] = field(default_factory=dict)