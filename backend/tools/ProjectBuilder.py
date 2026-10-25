# tools/ProjectBuilder.py
"""Safe Code Analyzer, Multi-Language Dependency Detector (.py/.java/.ts/.tsx),
Surgical Partial Patcher ("1部分のみ修正" v2), VS Code Bridge, and Non-Destructive Project Builder Tool.

設計方針:
1. 送られたコードや既存ファイルから「目標 (goal)」「つながっている .py / .java / .ts 等 (connected_files)」
   「何ができるか (capabilities)」を即座に解析し、ターミナルとUI双方へ出力する。
2. 自作AIが既存の大切なコードを壊さないよう、4層の非破壊ガード (CodeSafetyGuard) に加え、
   高精度な「1部分のみ修正 (SurgicalPartialPatcher v2)」を提供する:
   - 関数/メソッド置換 (`symbol_replace`) + 存在しない新メソッドのクラス末尾への非破壊追加 (`symbol_insert`)
   - パッチ内の新規 `import` 文の自動分離＆ファイル先頭への自動マージ (`added_imports`)
   - 1ファイル内の複数箇所同時 `SEARCH / REPLACE` (Multi-Hunk 逆順適用 + 自動インデント補正)
   - Javaのメソッドオーバーロード（引数型・引数数）識別 & TypeScript/JSXアロー関数の正確な行範囲特定
   - 呼び出し元ファイル (`reverse_dependencies`) に影響する引数シグネチャ変更のクロスファイル警告 (`cross_file_warnings`)
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class ConnectedFile:
    """1件の連携ファイル（import先または関連モジュール）情報。"""

    path: str
    module: str
    language: str
    relation: str = "imports"  # "imports" | "imported_by" | "same_package" | "pipeline_link"
    symbols: List[str] = field(default_factory=list)
    external: bool = False
    exists_in_project: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolCapability:
    """コード内の公開クラス・関数・APIエンドポイントなどの機能単位。"""

    name: str
    kind: str  # "class" | "function" | "async_function" | "method" | "endpoint" | "component" | "interface"
    signature: str
    summary: str = ""
    line: int = 1
    end_line: Optional[int] = None
    exported: bool = True
    param_count: int = 0
    required_param_count: int = 0
    param_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BreakingChangeIssue:
    """既存コードに対する破壊的変更の検知結果。"""

    file_path: str
    code: str
    message: str
    removed_symbols: List[str] = field(default_factory=list)
    impacted_files: List[str] = field(default_factory=list)
    action_taken: str = "blocked_overwrite"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SafetyGuardReport:
    """既存コード保護ガードの診断・保護レポート。"""

    mode: str = "safe_preserve"  # "safe_preserve" | "partial_patch" | "read_only"
    clean_existing_blocked: bool = False
    protected_files: List[str] = field(default_factory=list)
    backed_up_files: List[str] = field(default_factory=list)
    blocked_overwrites: List[str] = field(default_factory=list)
    proposed_sidecar_files: List[str] = field(default_factory=list)
    breaking_changes: List[BreakingChangeIssue] = field(default_factory=list)
    backup_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "clean_existing_blocked": self.clean_existing_blocked,
            "protected_files": list(self.protected_files),
            "backed_up_files": list(self.backed_up_files),
            "blocked_overwrites": list(self.blocked_overwrites),
            "proposed_sidecar_files": list(self.proposed_sidecar_files),
            "breaking_changes": [item.to_dict() for item in self.breaking_changes],
            "backup_dir": self.backup_dir,
        }


@dataclass
class PartialPatchResult:
    """VS Code連携・1部分のみ修正 (Surgical Partial Patch v2) の実行結果。"""

    success: bool
    file_path: str
    strategy: str  # "symbol_replace" | "symbol_insert" | "search_replace" | "multi_search_replace" | "line_range"
    target_symbol: Optional[str] = None
    modified_start_line: int = 1
    modified_end_line: int = 1
    original_line_count: int = 0
    new_line_count: int = 0
    preserved_symbols_count: int = 0
    hunks_applied: int = 1
    added_imports: List[str] = field(default_factory=list)
    cross_file_warnings: List[str] = field(default_factory=list)
    unified_diff: str = ""
    before_snippet: str = ""
    after_snippet: str = ""
    backup_file_path: Optional[str] = None
    vscode_goto_command: str = ""
    vscode_diff_command: str = ""
    vscode_launched: bool = False
    applied_to_disk: bool = False
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodeAnalysisReport:
    """送られたコードまたはプロジェクトの解析結果。"""

    target_file: str
    language: str
    goal: str
    summary: str
    connected_files: List[ConnectedFile] = field(default_factory=list)
    reverse_dependencies: List[str] = field(default_factory=list)
    external_packages: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    symbols: List[SymbolCapability] = field(default_factory=list)
    line_count: int = 0
    parse_errors: List[str] = field(default_factory=list)
    safety_guard: SafetyGuardReport = field(default_factory=SafetyGuardReport)
    partial_patch: Optional[PartialPatchResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "language": self.language,
            "goal": self.goal,
            "summary": self.summary,
            "connected_files": [item.to_dict() for item in self.connected_files],
            "reverse_dependencies": list(self.reverse_dependencies),
            "external_packages": list(self.external_packages),
            "capabilities": list(self.capabilities),
            "symbols": [item.to_dict() for item in self.symbols],
            "line_count": self.line_count,
            "parse_errors": list(self.parse_errors),
            "safety_guard": self.safety_guard.to_dict(),
            "partial_patch": self.partial_patch.to_dict() if self.partial_patch else None,
        }


# ---------------------------------------------------------------------------
# Multi-Language Code & Dependency Analyzer (.py, .java, .ts, .tsx, .js, .cs)
# ---------------------------------------------------------------------------


class MultiLanguageCodeAnalyzer:
    """Python (.py), Java (.java), TypeScript/React (.ts/.tsx/.js/.jsx), C# (.cs) の
    目標・連携ファイル・できること・シンボル行範囲・引数型を静的解析するクラス。
    """

    LANGUAGE_BY_SUFFIX: Dict[str, str] = {
        ".py": "python",
        ".pyi": "python",
        ".java": "java",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".cs": "csharp",
    }

    PYTHON_STDLIB: Set[str] = {
        "__future__", "abc", "argparse", "ast", "asyncio", "base64", "collections",
        "concurrent", "contextlib", "copy", "csv", "ctypes", "dataclasses",
        "datetime", "decimal", "difflib", "enum", "functools", "glob", "gzip", "hashlib",
        "heapq", "hmac", "html", "http", "importlib", "inspect", "io", "itertools",
        "json", "logging", "math", "multiprocessing", "operator", "os", "pathlib",
        "pickle", "platform", "pprint", "queue", "random", "re", "shutil", "signal",
        "socket", "sqlite3", "ssl", "stat", "statistics", "string", "struct",
        "subprocess", "sys", "tempfile", "textwrap", "threading", "time", "timeit",
        "traceback", "types", "typing", "unicodedata", "unittest", "urllib", "uuid",
        "warnings", "weakref", "xml", "zipfile", "zlib",
    }

    JAVA_STDLIB_PREFIXES: Tuple[str, ...] = (
        "java.",
        "javax.",
        "jakarta.",
        "jdk.",
        "org.w3c.",
        "org.xml.",
    )

    EXCLUDED_DIRS: Set[str] = {
        ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__",
        "node_modules", "dist", "build", "target", ".next", ".venv",
        "venv", "generated_zips", ".ai_backups",
    }

    def analyze_source(
        self,
        code: str,
        *,
        file_path: Optional[str] = None,
        project_root: Optional[Path] = None,
    ) -> CodeAnalysisReport:
        inferred_path = self._infer_file_path(code, file_path)
        language = self.detect_language(code, inferred_path)
        lines = code.splitlines()

        if language == "python":
            goal, symbols, imports, errors = self._analyze_python(code, inferred_path)
        elif language == "java":
            goal, symbols, imports, errors = self._analyze_java(code, inferred_path)
        elif language in {"typescript", "javascript"}:
            goal, symbols, imports, errors = self._analyze_ts_js(code, inferred_path, language)
        elif language == "csharp":
            goal, symbols, imports, errors = self._analyze_csharp(code, inferred_path)
        else:
            goal, symbols, imports, errors = self._analyze_generic(code, inferred_path)

        connected_files, external_packages = self._resolve_connected_files(
            imports=imports,
            source_path=inferred_path,
            language=language,
            project_root=project_root,
        )

        reverse_deps: List[str] = []
        if project_root and project_root.exists() and project_root.is_dir():
            reverse_deps = self._find_reverse_dependencies(
                target_path=inferred_path,
                target_symbols=[s.name for s in symbols if s.exported],
                project_root=project_root,
            )
            for rev_path in reverse_deps:
                rev_lang = self.detect_language("", rev_path)
                if not any(c.path == rev_path and c.relation == "imported_by" for c in connected_files):
                    connected_files.append(
                        ConnectedFile(
                            path=rev_path,
                            module=rev_path,
                            language=rev_lang,
                            relation="imported_by",
                            symbols=[],
                            external=False,
                            exists_in_project=True,
                        )
                    )

        capabilities = self._build_capabilities_summary(
            goal=goal,
            symbols=symbols,
            connected_files=connected_files,
            language=language,
        )

        summary = self._build_overall_summary(
            target_file=inferred_path,
            language=language,
            goal=goal,
            connected_files=connected_files,
            capabilities=capabilities,
        )

        return CodeAnalysisReport(
            target_file=inferred_path,
            language=language,
            goal=goal,
            summary=summary,
            connected_files=connected_files,
            reverse_dependencies=reverse_deps,
            external_packages=external_packages,
            capabilities=capabilities,
            symbols=symbols,
            line_count=len(lines),
            parse_errors=errors,
        )

    @classmethod
    def detect_language(cls, code: str, file_path: Optional[str] = None) -> str:
        if file_path:
            suffix = Path(file_path).suffix.lower()
            if suffix in cls.LANGUAGE_BY_SUFFIX:
                return cls.LANGUAGE_BY_SUFFIX[suffix]

        sample = (code or "")[:4000]
        if re.search(r"(?m)^\s*package\s+[\w.]+\s*;", sample) or re.search(
            r"\bpublic\s+(?:class|interface|enum|record)\s+\w+", sample
        ):
            if "System.out." in sample or re.search(r"(?m)^\s*import\s+[\w.*]+\s*;", sample):
                return "java"
        if re.search(r"(?m)^\s*(?:def|class)\s+\w+.*:\s*$", sample) or "from __future__ import" in sample:
            return "python"
        if re.search(r"\binterface\s+\w+|\bexport\s+(?:type|interface|function|const)\b|React\.ReactElement", sample):
            return "typescript"
        if re.search(r"\bimport\s+.*\s+from\s+['\"]|module\.exports\s*=", sample):
            return "javascript"
        if re.search(r"(?m)^\s*using\s+System", sample):
            return "csharp"
        return "python"

    @staticmethod
    def _infer_file_path(code: str, explicit_path: Optional[str] = None) -> str:
        if explicit_path and str(explicit_path).strip():
            return str(explicit_path).replace("\\", "/").strip()

        for line in (code or "").splitlines()[:10]:
            cleaned = line.strip()
            match = re.match(
                r"^(?:#|//|/\*+)\s*([A-Za-z0-9_./\-]+\.(?:py|java|tsx|ts|jsx|js|cs))\b",
                cleaned,
            )
            if match:
                return match.group(1)

        java_class = re.search(r"\bpublic\s+(?:class|interface|enum|record)\s+([A-Za-z_]\w*)", code or "")
        if java_class:
            return f"{java_class.group(1)}.java"

        py_class = re.search(r"(?m)^\s*class\s+([A-Za-z_]\w*)", code or "")
        if py_class and ("def " in (code or "")):
            return f"{py_class.group(1)}.py"

        tsx_comp = re.search(r"\bexport\s+(?:default\s+)?function\s+([A-Z][A-Za-z0-9_]*)", code or "")
        if tsx_comp:
            return f"{tsx_comp.group(1)}.tsx"

        return "submitted_code.py"

    @staticmethod
    def mask_comments_preserving_lines(code: str) -> str:
        pattern = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/")
        return pattern.sub(
            lambda m: "".join("\n" if ch == "\n" else " " for ch in m.group(0)),
            code,
        )

    # ------------------------------------------------------------------
    # Python Analyzer
    # ------------------------------------------------------------------

    def _analyze_python(
        self, code: str, path: str
    ) -> Tuple[str, List[SymbolCapability], List[Dict[str, Any]], List[str]]:
        symbols: List[SymbolCapability] = []
        imports: List[Dict[str, Any]] = []
        errors: List[str] = []
        module_doc = ""

        try:
            tree = ast.parse(code, filename=path)
            module_doc = (ast.get_docstring(tree) or "").strip()

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    cls_doc = (ast.get_docstring(node) or "").strip()
                    first_doc_line = self._first_meaningful_line(cls_doc)
                    methods: List[str] = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith("_") or item.name == "__init__":
                                methods.append(item.name)
                            m_doc = self._first_meaningful_line(ast.get_docstring(item) or "")
                            start_ln = self._node_start_line(item)
                            end_ln = getattr(item, "end_lineno", start_ln)
                            p_count, req_count, p_types = self._py_param_metadata(item)
                            symbols.append(
                                SymbolCapability(
                                    name=f"{node.name}.{item.name}",
                                    kind="method",
                                    signature=self._py_func_sig(item),
                                    summary=m_doc or f"{node.name} の `{item.name}` メソッド",
                                    line=start_ln,
                                    end_line=end_ln,
                                    exported=not item.name.startswith("_") or item.name == "__init__",
                                    param_count=p_count,
                                    required_param_count=req_count,
                                    param_types=p_types,
                                )
                            )
                    cls_summary = first_doc_line or (
                        f"クラス `{node.name}` ({', '.join(methods[:6])})"
                        if methods
                        else f"クラス `{node.name}`"
                    )
                    cls_start = self._node_start_line(node)
                    cls_end = getattr(node, "end_lineno", cls_start)
                    symbols.insert(
                        0,
                        SymbolCapability(
                            name=node.name,
                            kind="class",
                            signature=f"class {node.name}",
                            summary=cls_summary,
                            line=cls_start,
                            end_line=cls_end,
                            exported=not node.name.startswith("_"),
                        ),
                    )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_doc = self._first_meaningful_line(ast.get_docstring(node) or "")
                    route_decorator = self._extract_py_endpoint_decorator(node)
                    kind = "endpoint" if route_decorator else (
                        "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                    )
                    summary = (
                        f"APIエンドポイント ({route_decorator}): {fn_doc or node.name}"
                        if route_decorator
                        else (fn_doc or f"関数 `{node.name}`")
                    )
                    fn_start = self._node_start_line(node)
                    fn_end = getattr(node, "end_lineno", fn_start)
                    p_count, req_count, p_types = self._py_param_metadata(node)
                    symbols.append(
                        SymbolCapability(
                            name=node.name,
                            kind=kind,
                            signature=self._py_func_sig(node),
                            summary=summary,
                            line=fn_start,
                            end_line=fn_end,
                            exported=not node.name.startswith("_"),
                            param_count=p_count,
                            required_param_count=req_count,
                            param_types=p_types,
                        ),
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(
                            {
                                "module": alias.name,
                                "names": [alias.asname or alias.name],
                                "level": 0,
                            }
                        )
                elif isinstance(node, ast.ImportFrom):
                    imports.append(
                        {
                            "module": node.module or "",
                            "names": [alias.name for alias in node.names],
                            "level": int(node.level or 0),
                        }
                    )
        except SyntaxError as exc:
            errors.append(f"Python構文エラー (line {exc.lineno}): {exc.msg}")
            for match in re.finditer(
                r"(?m)^\s*(?:from\s+([.\w]+)\s+import\s+([^\n#]+)|import\s+([\w.,\s]+))",
                code,
            ):
                if match.group(1):
                    raw_mod = match.group(1)
                    level = len(raw_mod) - len(raw_mod.lstrip("."))
                    names = [p.strip().split(" as ")[0] for p in match.group(2).split(",") if p.strip()]
                    imports.append({"module": raw_mod.lstrip("."), "names": names, "level": level})
                elif match.group(3):
                    for part in match.group(3).split(","):
                        mod_name = part.strip().split(" as ")[0]
                        if mod_name:
                            imports.append({"module": mod_name, "names": [mod_name], "level": 0})

        goal = self._extract_goal_text(module_doc, code, symbols, path)
        return goal, symbols, imports, errors

    @staticmethod
    def _node_start_line(node: ast.AST) -> int:
        decorators = getattr(node, "decorator_list", None) or []
        if decorators:
            return min(getattr(d, "lineno", getattr(node, "lineno", 1)) for d in decorators)
        return int(getattr(node, "lineno", 1))

    @staticmethod
    def _py_param_metadata(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> Tuple[int, int, List[str]]:
        args = [a for a in node.args.args if a.arg not in {"self", "cls"}]
        defaults_count = len(node.args.defaults or [])
        total = len(args)
        required = max(0, total - defaults_count)
        types: List[str] = []
        for a in args:
            if a.annotation:
                try:
                    types.append(ast.unparse(a.annotation))
                except Exception:
                    types.append("Any")
            else:
                types.append("Any")
        return total, required, types

    @staticmethod
    def _py_func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        try:
            args = [a.arg for a in node.args.args if a.arg != "self"]
            arg_str = ", ".join(args[:5]) + (", ..." if len(args) > 5 else "")
            ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            return f"{prefix} {node.name}({arg_str}){ret}"
        except Exception:
            return f"{prefix} {node.name}(...)"

    @staticmethod
    def _extract_py_endpoint_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
        for dec in node.decorator_list:
            try:
                text = ast.unparse(dec)
                if any(
                    verb in text
                    for verb in (".get(", ".post(", ".put(", ".delete(", ".patch(", ".route(")
                ):
                    return text
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # Java Analyzer (.java)
    # ------------------------------------------------------------------

    def _analyze_java(
        self, code: str, path: str
    ) -> Tuple[str, List[SymbolCapability], List[Dict[str, Any]], List[str]]:
        symbols: List[SymbolCapability] = []
        imports: List[Dict[str, Any]] = []
        errors: List[str] = []
        masked = self.mask_comments_preserving_lines(code)

        package_match = re.search(r"(?m)^\s*package\s+([\w.]+)\s*;", masked)
        package_name = package_match.group(1) if package_match else ""

        for match in re.finditer(r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", masked):
            full_import = match.group(1)
            short_name = full_import.rsplit(".", 1)[-1]
            imports.append(
                {
                    "module": full_import,
                    "names": [short_name],
                    "level": 0,
                    "package": package_name,
                }
            )

        javadoc_match = re.search(r"/\*\*([\s\S]*?)\*/", code[:2500])
        top_doc = ""
        if javadoc_match:
            cleaned_lines = [
                re.sub(r"^\s*\*\s?", "", line).strip()
                for line in javadoc_match.group(1).splitlines()
            ]
            top_doc = "\n".join(
                line for line in cleaned_lines if line and not line.startswith("@")
            )

        type_pattern = re.compile(
            r"(?m)^\s*(?:@\w+(?:\([^)]*\))?\s*)*"
            r"(?:public|protected|private)?\s*(?:abstract|final|static|\s)*"
            r"\b(class|interface|enum|record)\s+([A-Za-z_]\w*)"
            r"(?:\s+extends\s+([A-Za-z_][\w.<>,\s]*))?"
            r"(?:\s+implements\s+([A-Za-z_][\w.<>,\s]*))?"
        )
        for match in type_pattern.finditer(masked):
            kind = match.group(1)
            name = match.group(2)
            extends_cls = (match.group(3) or "").strip()
            implements_cls = (match.group(4) or "").strip()
            line_no = masked.count("\n", 0, match.start()) + 1
            end_ln = self._find_brace_end_line(masked, match.start(), line_no)

            for ref_group in (extends_cls, implements_cls):
                for token in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", ref_group):
                    if token not in {"String", "Object", "Serializable", "Comparable", "List", "Map"}:
                        imports.append(
                            {
                                "module": f"{package_name}.{token}" if package_name else token,
                                "names": [token],
                                "level": 0,
                                "same_package_hint": True,
                            }
                        )

            symbols.append(
                SymbolCapability(
                    name=name,
                    kind="class" if kind in {"class", "record", "enum"} else "interface",
                    signature=f"{kind} {name}",
                    summary=top_doc.splitlines()[0] if top_doc else f"Java {kind} `{name}`",
                    line=line_no,
                    end_line=end_ln,
                    exported=True,
                )
            )

        declared_names = {s.name for s in symbols}
        imported_short_names = {n for imp in imports for n in imp.get("names", [])}
        java_builtin = {
            "String", "Integer", "Long", "Double", "Boolean", "Object", "List", "ArrayList",
            "Map", "HashMap", "Set", "HashSet", "Optional", "Stream", "System", "Exception",
            "RuntimeException", "IllegalArgumentException", "Override", "Autowired", "Service",
            "Controller", "RestController", "Component", "Repository", "GetMapping", "PostMapping",
            "PutMapping", "DeleteMapping", "RequestMapping", "PathVariable", "RequestBody",
        }
        for ref_match in re.finditer(
            r"\bnew\s+([A-Z][A-Za-z0-9_]*)\s*\(|([A-Z][A-Za-z0-9_]*)\.[a-z]\w*\s*\(",
            masked,
        ):
            ref_cls = ref_match.group(1) or ref_match.group(2)
            if (
                ref_cls
                and ref_cls not in declared_names
                and ref_cls not in imported_short_names
                and ref_cls not in java_builtin
            ):
                imported_short_names.add(ref_cls)
                imports.append(
                    {
                        "module": f"{package_name}.{ref_cls}" if package_name else ref_cls,
                        "names": [ref_cls],
                        "level": 0,
                        "same_package_hint": True,
                    }
                )

        method_pattern = re.compile(
            r"(?m)^\s*(?:(@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)(?:\([^)]*\))?)\s*)?"
            r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
            r"([A-Za-z_][\w.<>,\[\]\s?]*?)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\{"
        )
        for match in method_pattern.finditer(masked):
            endpoint_ann = (match.group(1) or "").strip()
            return_type = " ".join(match.group(2).split())
            method_name = match.group(3)
            params = " ".join(match.group(4).split())
            if method_name in declared_names or return_type in {"class", "interface", "enum"}:
                continue
            line_no = masked.count("\n", 0, match.start()) + 1
            end_ln = self._find_brace_end_line(masked, match.start(), line_no)
            param_types = self._extract_java_param_types(params)
            kind = "endpoint" if endpoint_ann else "method"
            summary = (
                f"エンドポイント `{endpoint_ann}` -> `{method_name}({', '.join(param_types)})`"
                if endpoint_ann
                else f"メソッド `{method_name}({params})` -> `{return_type}`"
            )
            symbols.append(
                SymbolCapability(
                    name=method_name,
                    kind=kind,
                    signature=f"{return_type} {method_name}({params})",
                    summary=summary,
                    line=line_no,
                    end_line=end_ln,
                    exported=True,
                    param_count=len(param_types),
                    required_param_count=len(param_types),
                    param_types=param_types,
                )
            )

        goal = self._extract_goal_text(top_doc, code, symbols, path)
        return goal, symbols, imports, errors

    @staticmethod
    def _extract_java_param_types(params: str) -> List[str]:
        cleaned = params.strip()
        if not cleaned:
            return []
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        types: List[str] = []
        for part in parts:
            no_ann = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", part)
            no_mod = re.sub(r"\bfinal\b\s*", "", no_ann).strip()
            tokens = no_mod.split()
            if len(tokens) >= 2:
                types.append(" ".join(tokens[:-1]))
            elif tokens:
                types.append(tokens[0])
        return types

    # ------------------------------------------------------------------
    # TypeScript / JavaScript Analyzer (.ts, .tsx, .js, .jsx)
    # ------------------------------------------------------------------

    def _analyze_ts_js(
        self, code: str, path: str, language: str
    ) -> Tuple[str, List[SymbolCapability], List[Dict[str, Any]], List[str]]:
        symbols: List[SymbolCapability] = []
        imports: List[Dict[str, Any]] = []
        errors: List[str] = []
        masked = self.mask_comments_preserving_lines(code)

        for match in re.finditer(
            r"\bimport\s+(?:type\s+)?([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]",
            masked,
        ):
            clause = match.group(1).strip()
            mod = match.group(2).strip()
            names = [
                n.strip().split(" as ")[0].strip()
                for n in re.findall(r"[A-Za-z_$][\w$]*", clause)
                if n not in {"type", "as", "from"}
            ]
            imports.append({"module": mod, "names": names[:8], "level": 1 if mod.startswith(".") else 0})

        for match in re.finditer(
            r"(?m)^\s*(export\s+)?(default\s+)?(?:async\s+)?(function|class|interface|type|const)\s+([A-Za-z_$][\w$]*)",
            masked,
        ):
            exported = bool(match.group(1) or match.group(2))
            raw_kind = match.group(3)
            name = match.group(4)
            line_no = masked.count("\n", 0, match.start()) + 1
            end_ln = self._find_ts_declaration_end_line(masked, match.start(), line_no)
            is_component = raw_kind in {"function", "const"} and name[:1].isupper()
            kind = "component" if is_component else raw_kind
            summary = (
                f"Reactコンポーネント `{name}`"
                if is_component
                else f"{raw_kind} `{name}`"
            )
            symbols.append(
                SymbolCapability(
                    name=name,
                    kind=kind,
                    signature=f"{'export ' if exported else ''}{raw_kind} {name}",
                    summary=summary,
                    line=line_no,
                    end_line=end_ln,
                    exported=exported,
                )
            )

        top_comment = ""
        doc_match = re.search(r"/\*\*([\s\S]*?)\*/", code[:1500])
        if doc_match:
            top_comment = re.sub(r"(?m)^\s*\*\s?", "", doc_match.group(1)).strip()

        goal = self._extract_goal_text(top_comment, code, symbols, path)
        return goal, symbols, imports, errors

    @classmethod
    def _find_ts_declaration_end_line(cls, masked_code: str, start_offset: int, default_line: int) -> int:
        arrow_pos = masked_code.find("=>", start_offset)
        first_brace = masked_code.find("{", start_offset)
        first_semi = masked_code.find(";", start_offset)

        if arrow_pos > 0 and (first_semi < 0 or arrow_pos < first_semi):
            after_arrow = masked_code[arrow_pos + 2 :].lstrip()
            if after_arrow.startswith("("):
                paren_open = masked_code.find("(", arrow_pos + 2)
                return cls._find_matching_delimiter_line(masked_code, paren_open, "(", ")", default_line)

        if first_brace > 0:
            return cls._find_brace_end_line(masked_code, start_offset, default_line)

        if first_semi > start_offset:
            return masked_code.count("\n", 0, first_semi) + 1
        return default_line

    @staticmethod
    def _find_matching_delimiter_line(
        code: str, open_pos: int, open_ch: str, close_ch: str, default_line: int
    ) -> int:
        if open_pos < 0:
            return default_line
        depth = 0
        in_str: Optional[str] = None
        escaped = False
        for idx in range(open_pos, len(code)):
            ch = code[idx]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if in_str:
                if ch == in_str:
                    in_str = None
                continue
            if ch in {"'", '"', "`"}:
                in_str = ch
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    end_idx = idx
                    rest = code[idx + 1 : idx + 5]
                    if ";" in rest:
                        end_idx = idx + 1 + rest.find(";")
                    return code.count("\n", 0, end_idx) + 1
        return default_line

    @classmethod
    def _find_brace_end_line(cls, code: str, start_offset: int, default_line: int) -> int:
        brace_open = code.find("{", start_offset)
        if brace_open < 0:
            semi = code.find(";", start_offset)
            return code.count("\n", 0, semi) + 1 if semi > start_offset else default_line
        return cls._find_matching_delimiter_line(code, brace_open, "{", "}", default_line)

    def _analyze_csharp(
        self, code: str, path: str
    ) -> Tuple[str, List[SymbolCapability], List[Dict[str, Any]], List[str]]:
        symbols: List[SymbolCapability] = []
        imports: List[Dict[str, Any]] = []
        masked = self.mask_comments_preserving_lines(code)
        for match in re.finditer(r"(?m)^\s*using\s+([\w.]+)\s*;", masked):
            imports.append({"module": match.group(1), "names": [match.group(1)], "level": 0})
        for match in re.finditer(
            r"\b(public|internal)\s+(?:partial\s+|static\s+|abstract\s+)*(class|interface|struct|enum)\s+([A-Za-z_]\w*)",
            masked,
        ):
            line_no = masked.count("\n", 0, match.start()) + 1
            symbols.append(
                SymbolCapability(
                    name=match.group(3),
                    kind=match.group(2),
                    signature=f"{match.group(1)} {match.group(2)} {match.group(3)}",
                    summary=f"C# {match.group(2)} `{match.group(3)}`",
                    line=line_no,
                    end_line=self._find_brace_end_line(masked, match.start(), line_no),
                    exported=True,
                )
            )
        goal = self._extract_goal_text("", code, symbols, path)
        return goal, symbols, imports, []

    def _analyze_generic(
        self, code: str, path: str
    ) -> Tuple[str, List[SymbolCapability], List[Dict[str, Any]], List[str]]:
        goal = self._extract_goal_text("", code, [], path)
        return goal, [], [], []

    def _resolve_connected_files(
        self,
        *,
        imports: List[Dict[str, Any]],
        source_path: str,
        language: str,
        project_root: Optional[Path],
    ) -> Tuple[List[ConnectedFile], List[str]]:
        connected: List[ConnectedFile] = []
        external_packages: List[str] = []
        seen_keys: Set[str] = set()

        for item in imports:
            raw_mod = str(item.get("module") or "").strip()
            names = [str(n) for n in (item.get("names") or []) if n]
            level = int(item.get("level") or 0)
            if not raw_mod and not level:
                continue

            if language == "python":
                top_pkg = raw_mod.split(".", 1)[0] if raw_mod else ""
                if level == 0 and top_pkg in self.PYTHON_STDLIB:
                    continue

                resolved_candidates = self._candidate_python_paths(
                    source_path=source_path,
                    module=raw_mod,
                    level=level,
                    names=names,
                )
                existing_match = self._find_existing_candidate(resolved_candidates, project_root)
                is_internal = (
                    level > 0
                    or existing_match is not None
                    or any(
                        part in raw_mod
                        for part in ("backend", "api", "services", "tools", "handler", "handlers", "models", "llm")
                    )
                    or (raw_mod[:1].isupper() and "." not in raw_mod)
                )

                if is_internal:
                    chosen_path = existing_match or (
                        resolved_candidates[0] if resolved_candidates else f"{raw_mod.replace('.', '/')}.py"
                    )
                    key = f"py:{chosen_path}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        connected.append(
                            ConnectedFile(
                                path=chosen_path,
                                module=raw_mod or ".",
                                language="python",
                                relation="imports",
                                symbols=names,
                                external=False,
                                exists_in_project=bool(existing_match),
                            )
                        )
                else:
                    if top_pkg and top_pkg not in external_packages:
                        external_packages.append(top_pkg)

            elif language == "java":
                if raw_mod.startswith(self.JAVA_STDLIB_PREFIXES):
                    continue
                is_external_framework = raw_mod.startswith(
                    ("org.springframework.", "org.junit.", "org.slf4j.", "com.fasterxml.", "lombok.")
                )
                if is_external_framework:
                    pkg_prefix = ".".join(raw_mod.split(".")[:3])
                    if pkg_prefix not in external_packages:
                        external_packages.append(pkg_prefix)
                    continue

                java_rel_path = raw_mod.replace(".", "/") + ".java"
                short_java = raw_mod.rsplit(".", 1)[-1] + ".java"
                existing_match = self._find_existing_candidate(
                    [java_rel_path, f"src/main/java/{java_rel_path}", short_java],
                    project_root,
                )
                chosen_path = (
                    existing_match or short_java
                    if item.get("same_package_hint")
                    else (existing_match or java_rel_path)
                )
                key = f"java:{chosen_path}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    connected.append(
                        ConnectedFile(
                            path=chosen_path,
                            module=raw_mod,
                            language="java",
                            relation="same_package" if item.get("same_package_hint") else "imports",
                            symbols=names,
                            external=False,
                            exists_in_project=bool(existing_match),
                        )
                    )

            elif language in {"typescript", "javascript"}:
                if raw_mod.startswith((".", "@/", "~/")):
                    clean_mod = raw_mod.lstrip("./")
                    candidates = [
                        f"{clean_mod}.tsx",
                        f"{clean_mod}.ts",
                        f"{clean_mod}.jsx",
                        f"{clean_mod}.js",
                        clean_mod,
                    ]
                    existing_match = self._find_existing_candidate(candidates, project_root)
                    chosen_path = existing_match or (
                        clean_mod if Path(clean_mod).suffix else f"{clean_mod}.tsx"
                    )
                    key = f"ts:{chosen_path}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        connected.append(
                            ConnectedFile(
                                path=chosen_path,
                                module=raw_mod,
                                language=language,
                                relation="imports",
                                symbols=names,
                                external=False,
                                exists_in_project=bool(existing_match),
                            )
                        )
                else:
                    if raw_mod not in external_packages:
                        external_packages.append(raw_mod)

        return connected, external_packages

    @staticmethod
    def _candidate_python_paths(
        *,
        source_path: str,
        module: str,
        level: int,
        names: List[str],
    ) -> List[str]:
        candidates: List[str] = []
        parent = PurePosixPath(source_path).parent
        if level > 0:
            base = parent
            for _ in range(max(0, level - 1)):
                base = base.parent
            if module:
                rel = str(base / module.replace(".", "/")).lstrip("./")
                candidates.append(f"{rel}.py")
                candidates.append(f"{rel}/__init__.py")
            for name in names:
                if name and name != "*":
                    rel_name = str(base / (module.replace(".", "/") if module else "") / name).lstrip("./")
                    candidates.append(f"{rel_name}.py")
        else:
            dotted = module.replace(".", "/")
            if dotted:
                candidates.append(f"{dotted}.py")
                for name in names:
                    if name and name[:1].isupper():
                        candidates.append(f"{dotted}/{name}.py")
                candidates.append(f"{PurePosixPath(dotted).name}.py")
        return [c for c in dict.fromkeys(candidates) if c]

    def _find_existing_candidate(
        self, candidates: Sequence[str], project_root: Optional[Path]
    ) -> Optional[str]:
        if not project_root or not project_root.exists():
            return None
        for candidate in candidates:
            direct = project_root / candidate
            if direct.exists() and direct.is_file():
                try:
                    return direct.resolve().relative_to(project_root.resolve()).as_posix()
                except ValueError:
                    return candidate
        target_basenames = {PurePosixPath(c).name for c in candidates if PurePosixPath(c).name}
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS and not d.startswith(".")]
            for fname in files:
                if fname in target_basenames:
                    full = Path(root) / fname
                    try:
                        return full.resolve().relative_to(project_root.resolve()).as_posix()
                    except ValueError:
                        return fname
        return None

    def _find_reverse_dependencies(
        self,
        *,
        target_path: str,
        target_symbols: Sequence[str],
        project_root: Path,
    ) -> List[str]:
        stem = PurePosixPath(target_path).stem
        if not stem or stem == "submitted_code":
            return []

        search_tokens = {stem, *[s.split(".")[0] for s in target_symbols if len(s) >= 3]}
        importers: List[str] = []

        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS and not d.startswith(".")]
            for fname in sorted(files):
                suffix = Path(fname).suffix.lower()
                if suffix not in self.LANGUAGE_BY_SUFFIX:
                    continue
                full = Path(root) / fname
                try:
                    rel = full.resolve().relative_to(project_root.resolve()).as_posix()
                except ValueError:
                    rel = fname
                if rel == target_path or Path(rel).name == Path(target_path).name:
                    continue
                try:
                    if full.stat().st_size > 1_500_000:
                        continue
                    text = full.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                if any(
                    re.search(rf"\b(?:import|from|new)\b[^\n;]*\b{re.escape(tok)}\b", text)
                    for tok in search_tokens
                ):
                    importers.append(rel)
        return importers[:25]

    def _extract_goal_text(
        self,
        docstring: str,
        code: str,
        symbols: Sequence[SymbolCapability],
        path: str,
    ) -> str:
        if docstring:
            first_line = self._first_meaningful_line(docstring)
            if first_line:
                return first_line

        comment_lines: List[str] = []
        for line in code.splitlines()[:25]:
            stripped = line.strip()
            if stripped.startswith(("#", "//")):
                cleaned = re.sub(r"^(?:#+|//+)\s*", "", stripped).strip()
                if (
                    cleaned
                    and not cleaned.endswith((".py", ".java", ".tsx", ".ts", ".js"))
                    and not re.match(r"^[-=]{3,}$", cleaned)
                ):
                    comment_lines.append(cleaned)
        if comment_lines:
            return comment_lines[0][:160]

        top_classes = [s for s in symbols if s.kind in {"class", "interface", "component"}]
        if top_classes:
            first = top_classes[0]
            if first.summary and not first.summary.startswith(("クラス ", "Java ", "React")):
                return first.summary
            return f"`{first.name}` を中心に {len(symbols)} 個のクラス/メソッドを提供するモジュール ({path})"

        if symbols:
            names = ", ".join(s.name for s in symbols[:4])
            return f"`{names}` などの処理・機能を提供するモジュール ({path})"

        return f"`{path}` の処理・ロジックを実行するモジュール"

    @staticmethod
    def _first_meaningful_line(text: str) -> str:
        for line in (text or "").splitlines():
            cleaned = line.strip().strip("=-*# ")
            if cleaned and len(cleaned) >= 4 and not re.match(r"^Phase\s+\d+", cleaned, re.I):
                return cleaned[:160]
        return ""

    @staticmethod
    def _build_capabilities_summary(
        *,
        goal: str,
        symbols: Sequence[SymbolCapability],
        connected_files: Sequence[ConnectedFile],
        language: str,
    ) -> List[str]:
        capabilities: List[str] = []
        classes = [s for s in symbols if s.kind in {"class", "interface", "component"}]
        endpoints = [s for s in symbols if s.kind == "endpoint"]
        functions = [s for s in symbols if s.kind in {"function", "async_function"}]
        methods = [s for s in symbols if s.kind == "method"]

        for cls in classes[:5]:
            capabilities.append(f"[{cls.kind}] {cls.name} (L{cls.line}-L{cls.end_line or cls.line}): {cls.summary}")
        for ep in endpoints[:6]:
            capabilities.append(f"[API] {ep.name} (L{ep.line}): {ep.summary}")
        for fn in functions[:6]:
            capabilities.append(f"[関数] {fn.signature} (L{fn.line}-L{fn.end_line or fn.line}): {fn.summary}")
        if methods:
            for m in methods[:8]:
                capabilities.append(f"[メソッド] {m.name} (L{m.line}-L{m.end_line or m.line}): {m.summary}")
            if len(methods) > 8:
                remaining = ", ".join(m.name.split(".")[-1] for m in methods[8:16])
                capabilities.append(f"[その他メソッド ({len(methods) - 8}件)] {remaining}")
        if not capabilities and goal:
            capabilities.append(f"[{language}] {goal}")
        return capabilities

    @staticmethod
    def _build_overall_summary(
        *,
        target_file: str,
        language: str,
        goal: str,
        connected_files: Sequence[ConnectedFile],
        capabilities: Sequence[str],
    ) -> str:
        conn_count = len([c for c in connected_files if c.relation != "imported_by"])
        rev_count = len([c for c in connected_files if c.relation == "imported_by"])
        return (
            f"{target_file} ({language}) — 目標: {goal} / "
            f"連携先ファイル: {conn_count}件 / 参照元(影響範囲): {rev_count}件 / "
            f"検出された機能・公開シンボル: {len(capabilities)}件"
        )


# ---------------------------------------------------------------------------
# Surgical Partial Patcher v2 & VS Code Bridge ("VSCodeと連携し1部分のみ修正")
# ---------------------------------------------------------------------------


class SurgicalPartialPatcher:
    """ファイル全体を上書きせず、指定された1部分（関数・メソッド・複数SEARCH/REPLACE・行範囲）のみを
    安全に修正し、不足importの自動マージ・新規メソッド挿入・クロスファイル引数影響チェックを行うクラス。
    """

    SEARCH_REPLACE_PATTERN = re.compile(
        r"<{5,9}\s*SEARCH\s*\n(?P<search>[\s\S]*?)\n={5,9}\s*\n(?P<replace>[\s\S]*?)\n>{5,9}\s*REPLACE",
        re.MULTILINE,
    )

    def __init__(
        self,
        project_root: str | Path = ".",
        *,
        backup_root: Optional[str | Path] = None,
        analyzer: Optional[MultiLanguageCodeAnalyzer] = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.backup_root = (
            Path(backup_root).expanduser().resolve()
            if backup_root
            else (self.project_root / ".ai_backups")
        )
        self.analyzer = analyzer or MultiLanguageCodeAnalyzer()

    def apply_partial_patch(
        self,
        file_path: str,
        *,
        patch_code: Optional[str] = None,
        target_symbol: Optional[str] = None,
        search_block: Optional[str] = None,
        replace_block: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        allow_symbol_insert: bool = True,
        auto_merge_imports: bool = True,
        write_to_disk: bool = True,
        launch_vscode: bool = False,
        vscode_mode: str = "diff",  # "diff" | "goto" | "none"
    ) -> PartialPatchResult:
        rel_path = str(file_path).replace("\\", "/").strip()
        target_abs = (self.project_root / rel_path).resolve()
        if not target_abs.exists() or not target_abs.is_file():
            return PartialPatchResult(
                success=False,
                file_path=rel_path,
                strategy="none",
                message=f"対象ファイルが存在しません: {rel_path}",
                error=f"File not found: {rel_path}",
            )

        original_text = target_abs.read_text(encoding="utf-8", errors="ignore")
        if original_text and not original_text.endswith("\n"):
            original_text += "\n"
        original_lines = original_text.splitlines(keepends=True)
        language = self.analyzer.detect_language(original_text, rel_path)
        old_analysis = self.analyzer.analyze_source(
            original_text, file_path=rel_path, project_root=self.project_root
        )

        # Collect all SEARCH/REPLACE blocks if present (Upgrade 2: Multi-Hunk support)
        hunks: List[Tuple[str, str]] = []
        if search_block is not None and replace_block is not None:
            hunks.append((search_block, replace_block))
        elif patch_code:
            for match in self.SEARCH_REPLACE_PATTERN.finditer(patch_code):
                hunks.append((match.group("search"), match.group("replace")))

        strategy = "symbol_replace"
        mod_start = 1
        mod_end = 1
        hunks_applied = 0
        added_imports: List[str] = []
        before_snippet = ""
        after_snippet = ""
        new_text = original_text

        # Strategy A: Single or Multi-Hunk SEARCH / REPLACE
        if hunks:
            strategy = "multi_search_replace" if len(hunks) > 1 else "search_replace"
            resolved_spans: List[Tuple[int, int, str, str]] = []
            for s_block, r_block in hunks:
                span_start, span_end = self._locate_hunk_line_span(original_text, original_lines, s_block)
                if span_start is None or span_end is None:
                    return PartialPatchResult(
                        success=False,
                        file_path=rel_path,
                        strategy=strategy,
                        target_symbol=target_symbol,
                        message="指定された SEARCH ブロックが既存ファイル内で見つかりませんでした。",
                        error=f"SEARCH block not found: {s_block[:80]}",
                    )
                resolved_spans.append((span_start, span_end, s_block, r_block))

            working_lines = list(original_lines)
            before_parts: List[str] = []
            after_parts: List[str] = []
            for span_start, span_end, s_block, r_block in sorted(
                resolved_spans, key=lambda x: x[0], reverse=True
            ):
                orig_chunk = "".join(working_lines[span_start - 1 : span_end]).rstrip("\n")
                if s_block not in orig_chunk and orig_chunk.strip():
                    orig_indent = self._detect_line_indent(working_lines[span_start - 1])
                    adjusted_r = self._reindent_snippet(r_block, orig_indent)
                else:
                    adjusted_r = r_block.rstrip("\n")
                working_lines[span_start - 1 : span_end] = [adjusted_r + "\n"]
                before_parts.insert(0, orig_chunk)
                after_parts.insert(0, adjusted_r)
                hunks_applied += 1

            mod_start = min(s[0] for s in resolved_spans)
            mod_end = max(s[1] for s in resolved_spans)
            before_snippet = "\n---\n".join(before_parts)
            after_snippet = "\n---\n".join(after_parts)
            new_text = "".join(working_lines)

        # Strategy B: Symbol-targeted surgical replacement or smart insertion
        elif target_symbol or patch_code:
            clean_patch_body, extracted_imports = (
                self._separate_top_level_imports(patch_code or "", language)
                if auto_merge_imports and patch_code and start_line is None
                else (patch_code or "", [])
            )

            matched_sym = self._resolve_target_symbol(
                old_analysis.symbols,
                target_symbol=target_symbol,
                patch_code=clean_patch_body,
                language=language,
            )

            if matched_sym and matched_sym.end_line and clean_patch_body.strip():
                strategy = "symbol_replace"
                target_symbol = matched_sym.name
                mod_start = matched_sym.line
                mod_end = matched_sym.end_line
                before_snippet = "".join(original_lines[mod_start - 1 : mod_end]).rstrip("\n")
                base_indent = self._detect_line_indent(original_lines[mod_start - 1])
                adjusted_patch = self._reindent_snippet(clean_patch_body, base_indent)
                after_snippet = adjusted_patch.rstrip("\n")
                working_lines = (
                    original_lines[: mod_start - 1]
                    + [after_snippet + "\n"]
                    + original_lines[mod_end:]
                )
                new_text = "".join(working_lines)
                hunks_applied = 1

            elif start_line is not None and end_line is not None and patch_code is not None:
                strategy = "line_range"
                mod_start = max(1, int(start_line))
                mod_end = min(len(original_lines), max(mod_start, int(end_line)))
                before_snippet = "".join(original_lines[mod_start - 1 : mod_end]).rstrip("\n")
                after_snippet = patch_code.rstrip("\n")
                working_lines = (
                    original_lines[: mod_start - 1]
                    + [after_snippet + "\n"]
                    + original_lines[mod_end:]
                )
                new_text = "".join(working_lines)
                hunks_applied = 1

            elif allow_symbol_insert and clean_patch_body.strip() and self._looks_like_callable_definition(clean_patch_body):
                strategy = "symbol_insert"
                inferred_sym_name = self._extract_patch_symbol_name(clean_patch_body) or target_symbol or "new_symbol"
                target_symbol = inferred_sym_name
                insert_line, target_indent = self._find_smart_insertion_point(
                    old_analysis.symbols, original_lines, clean_patch_body, language
                )
                mod_start = insert_line
                mod_end = insert_line
                before_snippet = "(新規メソッド/関数の追加 — 既存コードの変更なし)"
                adjusted_patch = self._reindent_snippet(clean_patch_body, target_indent)
                after_snippet = adjusted_patch.rstrip("\n")
                working_lines = (
                    original_lines[: insert_line - 1]
                    + ["\n" + after_snippet + "\n"]
                    + original_lines[insert_line - 1 :]
                )
                new_text = "".join(working_lines)
                hunks_applied = 1
            else:
                return PartialPatchResult(
                    success=False,
                    file_path=rel_path,
                    strategy=strategy,
                    target_symbol=target_symbol,
                    message=(
                        "1部分修正の対象となる既存の関数・メソッドを特定できませんでした。"
                        "関数名を指定するか、SEARCH/REPLACE または行範囲を指定してください。"
                    ),
                    error="Could not match target symbol or line range for partial patch",
                )

            if extracted_imports:
                new_text, added_imports = self._merge_imports_into_header(
                    new_text, extracted_imports, language
                )

        # Validate that the patched code has no syntax errors and did not lose other symbols
        new_analysis = self.analyzer.analyze_source(
            new_text, file_path=rel_path, project_root=self.project_root
        )
        if new_analysis.parse_errors and not old_analysis.parse_errors:
            return PartialPatchResult(
                success=False,
                file_path=rel_path,
                strategy=strategy,
                target_symbol=target_symbol,
                modified_start_line=mod_start,
                modified_end_line=mod_end,
                before_snippet=before_snippet,
                after_snippet=after_snippet,
                message=f"1部分修正後のコードに構文エラーが発生するため適用をブロックしました: {'; '.join(new_analysis.parse_errors)}",
                error="; ".join(new_analysis.parse_errors),
            )

        old_exported = {s.name for s in old_analysis.symbols if s.exported}
        new_exported = {s.name for s in new_analysis.symbols if s.exported}
        allowed_target = {target_symbol, (target_symbol or "").split(".")[-1]} - {None, ""}
        unexpected_removed = sorted((old_exported - new_exported) - allowed_target)
        if unexpected_removed:
            return PartialPatchResult(
                success=False,
                file_path=rel_path,
                strategy=strategy,
                target_symbol=target_symbol,
                modified_start_line=mod_start,
                modified_end_line=mod_end,
                before_snippet=before_snippet,
                after_snippet=after_snippet,
                message=(
                    f"1部分修正によって他の既存シンボル ({', '.join(unexpected_removed)}) "
                    f"が消える恐れがあるため適用をブロックしました。"
                ),
                error=f"Unexpected symbol removal: {unexpected_removed}",
            )

        cross_warnings = self._check_signature_compatibility(
            old_symbols=old_analysis.symbols,
            new_symbols=new_analysis.symbols,
            reverse_dependencies=old_analysis.reverse_dependencies,
        )

        unified_diff = "".join(
            difflib.unified_diff(
                original_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{rel_path} (変更前)",
                tofile=f"b/{rel_path} (1部分修正後)",
                n=3,
            )
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_root / timestamp / rel_path
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_text(original_text, encoding="utf-8")

        applied = False
        if write_to_disk:
            target_abs.write_text(new_text, encoding="utf-8")
            applied = True

        goto_cmd = f'code --goto "{target_abs}:{mod_start}:1"'
        diff_cmd = f'code --diff "{backup_file}" "{target_abs}"'
        launched = False
        if launch_vscode:
            launched = self.launch_vscode_editor(
                target_abs=target_abs,
                backup_abs=backup_file,
                line=mod_start,
                mode=vscode_mode,
            )

        preserved_count = len(new_analysis.symbols)
        import_note = f" / 新規import自動追加: {', '.join(added_imports)}" if added_imports else ""
        hunk_note = f" ({hunks_applied}箇所同時適用)" if hunks_applied > 1 else ""
        action_verb = "追加" if strategy == "symbol_insert" else "修正"

        return PartialPatchResult(
            success=True,
            file_path=rel_path,
            strategy=strategy,
            target_symbol=target_symbol,
            modified_start_line=mod_start,
            modified_end_line=mod_end,
            original_line_count=len(original_lines),
            new_line_count=len(new_text.splitlines()),
            preserved_symbols_count=preserved_count,
            hunks_applied=hunks_applied,
            added_imports=added_imports,
            cross_file_warnings=cross_warnings,
            unified_diff=unified_diff,
            before_snippet=before_snippet,
            after_snippet=after_snippet,
            backup_file_path=str(backup_file),
            vscode_goto_command=goto_cmd,
            vscode_diff_command=diff_cmd,
            vscode_launched=launched,
            applied_to_disk=applied,
            message=(
                f"`{rel_path}` の {target_symbol or f'L{mod_start}-L{mod_end}'}{hunk_note} の1部分のみを安全に{action_verb}しました "
                f"（他シンボル {max(0, preserved_count - 1)} 件は100%無傷で維持{import_note}）。"
            ),
        )

    def rollback_last_patch(self, file_path: str, backup_file_path: Optional[str] = None) -> Dict[str, Any]:
        rel_path = str(file_path).replace("\\", "/").strip()
        target_abs = (self.project_root / rel_path).resolve()

        chosen_backup: Optional[Path] = None
        if backup_file_path:
            candidate = Path(backup_file_path).expanduser().resolve()
            if candidate.exists() and candidate.is_file():
                chosen_backup = candidate
        if chosen_backup is None and self.backup_root.exists():
            matches = sorted(self.backup_root.glob(f"*/{rel_path}"), reverse=True)
            if matches:
                chosen_backup = matches[0]

        if chosen_backup is None:
            return {
                "success": False,
                "file_path": rel_path,
                "message": f"`{rel_path}` のバックアップが見つかりませんでした。",
            }

        restored_content = chosen_backup.read_text(encoding="utf-8")
        target_abs.write_text(restored_content, encoding="utf-8")
        return {
            "success": True,
            "file_path": rel_path,
            "restored_from": str(chosen_backup),
            "message": f"`{rel_path}` を変更前の状態（{chosen_backup.name}）へ完全に復元しました。",
        }

    def generate_vscode_tasks_json(
        self,
        *,
        last_patch: Optional[PartialPatchResult] = None,
        write_to_workspace: bool = False,
    ) -> Dict[str, Any]:
        target_rel = last_patch.file_path if last_patch else "${file}"
        line_no = last_patch.modified_start_line if last_patch else 1
        backup_path = last_patch.backup_file_path if last_patch and last_patch.backup_file_path else ""

        tasks: List[Dict[str, Any]] = [
            {
                "label": "🔍 AI部分修正: VS Codeで該当行を開く (Goto Modified Line)",
                "type": "shell",
                "command": "code",
                "args": ["--goto", f"${{workspaceFolder}}/{target_rel}:{line_no}:1"],
                "problemMatcher": [],
                "group": {"kind": "build", "isDefault": True},
            }
        ]
        if backup_path:
            tasks.append(
                {
                    "label": "✂️ AI部分修正: 変更前後のDiffを比較 (Compare Partial Diff)",
                    "type": "shell",
                    "command": "code",
                    "args": ["--diff", backup_path, f"${{workspaceFolder}}/{target_rel}"],
                    "problemMatcher": [],
                }
            )
            tasks.append(
                {
                    "label": "↩️ AI部分修正: 変更前のバックアップに戻す (Rollback Partial Patch)",
                    "type": "shell",
                    "command": "python3",
                    "args": [
                        "-c",
                        (
                            "import shutil; "
                            f"shutil.copy2({backup_path!r}, {str((self.project_root / target_rel).resolve())!r}); "
                            f"print('✅ Restored {target_rel} from backup!')"
                        ),
                    ],
                    "problemMatcher": [],
                }
            )

        tasks_payload = {"version": "2.0.0", "tasks": tasks}
        if write_to_workspace:
            vscode_dir = self.project_root / ".vscode"
            vscode_dir.mkdir(parents=True, exist_ok=True)
            (vscode_dir / "tasks.json").write_text(
                json.dumps(tasks_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return tasks_payload

    @staticmethod
    def launch_vscode_editor(
        *,
        target_abs: Path,
        backup_abs: Optional[Path] = None,
        line: int = 1,
        mode: str = "diff",
    ) -> bool:
        code_bin = shutil.which("code") or shutil.which("code-insiders")
        if not code_bin:
            return False
        try:
            if mode == "diff" and backup_abs and backup_abs.exists():
                subprocess.Popen(
                    [code_bin, "--diff", str(backup_abs), str(target_abs)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [code_bin, "--goto", f"{target_abs}:{max(1, line)}:1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Internal Helpers for Import Auto-Merge, Overload Matching, & Smart Insert
    # ------------------------------------------------------------------

    @staticmethod
    def _separate_top_level_imports(patch_code: str, language: str) -> Tuple[str, List[str]]:
        """パッチコードの先頭に書かれたファイル名コメント (`# File.py` / `// File.java`) と
        `import ...` 文を関数本体から分離し、ヘッダーマージ用に抽出する。
        """
        lines = patch_code.splitlines()
        extracted_imports: List[str] = []
        body_lines: List[str] = []
        in_header = True

        for line in lines:
            stripped = line.strip()
            if in_header:
                if not stripped:
                    continue
                if re.match(r"^(?:#|//|/\*+)\s*[A-Za-z0-9_./\-]+\.(?:py|java|tsx|ts|jsx|js|cs)\b", stripped):
                    continue
                if language == "python" and re.match(r"^(?:import\s+[\w.,\s]+|from\s+[.\w]+\s+import\s+[^\n#]+)$", stripped):
                    extracted_imports.append(stripped)
                    continue
                if language == "java" and re.match(r"^import\s+(?:static\s+)?[\w.*]+\s*;$", stripped):
                    extracted_imports.append(stripped)
                    continue
                if language in {"typescript", "javascript"} and re.match(r"^import\s+.*\s+from\s+['\"][^'\"]+['\"]\s*;?$", stripped):
                    extracted_imports.append(stripped)
                    continue
                in_header = False
            body_lines.append(line)

        return "\n".join(body_lines), extracted_imports

    @staticmethod
    def _merge_imports_into_header(
        file_text: str, new_imports: Sequence[str], language: str
    ) -> Tuple[str, List[str]]:
        existing_lines = file_text.splitlines()
        existing_stripped = {ln.strip() for ln in existing_lines}
        missing = [imp for imp in dict.fromkeys(new_imports) if imp.strip() not in existing_stripped]
        if not missing:
            return file_text, []

        insert_idx = 0
        for idx, line in enumerate(existing_lines[:60]):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith(("from __future__", "import ", "from ")):
                    insert_idx = idx + 1
            elif language == "java":
                if stripped.startswith(("package ", "import ")):
                    insert_idx = idx + 1
            elif language in {"typescript", "javascript"}:
                if stripped.startswith(("/// <reference", "import ")):
                    insert_idx = idx + 1

        updated_lines = (
            existing_lines[:insert_idx]
            + list(missing)
            + existing_lines[insert_idx:]
        )
        return "\n".join(updated_lines) + ("\n" if file_text.endswith("\n") else ""), missing

    @classmethod
    def _resolve_target_symbol(
        cls,
        symbols: Sequence[SymbolCapability],
        *,
        target_symbol: Optional[str],
        patch_code: str,
        language: str = "python",
    ) -> Optional[SymbolCapability]:
        candidates_to_check: List[str] = []
        if target_symbol:
            candidates_to_check.append(target_symbol.strip())

        extracted_name = cls._extract_patch_symbol_name(patch_code)
        if extracted_name and extracted_name not in candidates_to_check:
            candidates_to_check.append(extracted_name)

        patch_java_params: Optional[List[str]] = None
        if language == "java":
            java_m = re.search(
                r"(?m)^\s*(?:public|protected|private)\s+(?:static\s+)?[\w.<>,\[\]\s?]+\s+[a-zA-Z_]\w*\s*\(([^)]*)\)",
                patch_code,
            )
            if java_m:
                patch_java_params = MultiLanguageCodeAnalyzer._extract_java_param_types(java_m.group(1))

        for name in candidates_to_check:
            matches = [
                sym for sym in symbols
                if sym.name == name
                or (
                    sym.name.split(".")[-1] == name
                    and sym.kind in {"method", "function", "async_function", "endpoint", "component"}
                )
            ]
            if not matches:
                continue
            if len(matches) == 1:
                return matches[0]

            if patch_java_params is not None:
                for sym in matches:
                    if sym.param_types == patch_java_params:
                        return sym
                for sym in matches:
                    if sym.param_count == len(patch_java_params):
                        return sym
            return matches[0]
        return None

    @staticmethod
    def _extract_patch_symbol_name(patch_code: str) -> Optional[str]:
        py_fn = re.search(r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", patch_code)
        if py_fn:
            return py_fn.group(1)
        ts_fn = re.search(
            r"(?m)^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|const)\s+([A-Za-z_$][\w$]*)",
            patch_code,
        )
        if ts_fn:
            return ts_fn.group(1)
        java_fn = re.search(
            r"(?m)^\s*(?:public|protected|private)\s+(?:static\s+)?[\w.<>,\[\]\s?]+\s+([a-zA-Z_]\w*)\s*\(",
            patch_code,
        )
        if java_fn:
            return java_fn.group(1)
        return None

    @staticmethod
    def _looks_like_callable_definition(patch_code: str) -> bool:
        return bool(
            re.search(
                r"(?m)^\s*(?:(?:public|protected|private|export|default|async)\s+)*(?:def|function|const|[A-Za-z_][\w.<>,\[\]]*\s+[a-zA-Z_]\w*\s*\()",
                patch_code,
            )
        )

    @classmethod
    def _find_smart_insertion_point(
        cls,
        symbols: Sequence[SymbolCapability],
        original_lines: Sequence[str],
        patch_code: str,
        language: str,
    ) -> Tuple[int, str]:
        classes = [s for s in symbols if s.kind == "class" and s.end_line]
        is_method = (
            ("self" in patch_code or "cls" in patch_code)
            if language == "python"
            else bool(classes and language == "java")
        )
        if classes and is_method:
            primary_cls = classes[0]
            cls_end = int(primary_cls.end_line or len(original_lines))
            if language == "java":
                return max(1, cls_end), "    "
            return min(len(original_lines) + 1, cls_end + 1), "    "
        return len(original_lines) + 1, ""

    @staticmethod
    def _check_signature_compatibility(
        *,
        old_symbols: Sequence[SymbolCapability],
        new_symbols: Sequence[SymbolCapability],
        reverse_dependencies: Sequence[str],
    ) -> List[str]:
        if not reverse_dependencies:
            return []
        warnings: List[str] = []
        old_map = {(s.name, s.kind): s for s in old_symbols}
        for new_sym in new_symbols:
            old_sym = old_map.get((new_sym.name, new_sym.kind))
            if not old_sym:
                continue
            if new_sym.required_param_count > old_sym.required_param_count:
                warnings.append(
                    f"`{new_sym.name}` の必須引数が {old_sym.required_param_count}個 -> {new_sym.required_param_count}個 に増えました。"
                    f"呼び出し元ファイル ({', '.join(reverse_dependencies[:4])}) の引数確認を推奨します。"
                )
        return warnings

    @classmethod
    def _locate_hunk_line_span(
        cls,
        original_text: str,
        original_lines: Sequence[str],
        search_block: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        idx = original_text.find(search_block)
        if idx >= 0:
            start_ln = original_text.count("\n", 0, idx) + 1
            end_ln = start_ln + search_block.count("\n")
            return start_ln, end_ln
        return cls._find_normalized_line_span(original_lines, search_block)

    @staticmethod
    def _detect_line_indent(line: str) -> str:
        match = re.match(r"^([ \t]*)", line)
        return match.group(1) if match else ""

    @staticmethod
    def _reindent_snippet(snippet: str, target_indent: str) -> str:
        lines = snippet.strip("\n").splitlines()
        if not lines:
            return ""
        non_empty = [ln for ln in lines if ln.strip()]
        if not non_empty:
            return snippet
        min_indent = min(len(ln) - len(ln.lstrip(" \t")) for ln in non_empty)
        reindented: List[str] = []
        for ln in lines:
            if not ln.strip():
                reindented.append("")
            else:
                reindented.append(target_indent + ln[min_indent:])
        return "\n".join(reindented)

    @staticmethod
    def _find_normalized_line_span(
        original_lines: Sequence[str], search_block: str
    ) -> Tuple[Optional[int], Optional[int]]:
        search_lines = [ln.strip() for ln in search_block.strip().splitlines() if ln.strip()]
        if not search_lines:
            return None, None
        stripped_orig = [ln.strip() for ln in original_lines]
        n = len(search_lines)
        for i in range(len(stripped_orig) - n + 1):
            if stripped_orig[i : i + n] == search_lines:
                return i + 1, i + n
        return None, None


# ---------------------------------------------------------------------------
# Non-Destructive Code Protection Guard
# ---------------------------------------------------------------------------


class CodeSafetyGuard:
    """自作AIが既存の大切なコードを破壊することを防ぐ保護クラス。"""

    def __init__(
        self,
        project_root: str | Path = ".",
        *,
        backup_root: Optional[str | Path] = None,
        protected_paths: Optional[Iterable[str]] = None,
        block_symbol_deletion: bool = True,
        analyzer: Optional[MultiLanguageCodeAnalyzer] = None,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.backup_root = (
            Path(backup_root).expanduser().resolve()
            if backup_root
            else (self.project_root / ".ai_backups")
        )
        self.protected_paths: Set[str] = {
            str(p).replace("\\", "/").strip() for p in (protected_paths or ()) if str(p).strip()
        }
        self.block_symbol_deletion = bool(block_symbol_deletion)
        self.analyzer = analyzer or MultiLanguageCodeAnalyzer()

    def snapshot_existing_files(self, paths: Optional[Iterable[str]] = None) -> Dict[str, str]:
        snapshots: Dict[str, str] = {}
        if not self.project_root.exists():
            return snapshots

        if paths is not None:
            for rel in paths:
                normalized = str(rel).replace("\\", "/").strip()
                candidate = (self.project_root / normalized).resolve()
                if candidate.exists() and candidate.is_file():
                    try:
                        snapshots[normalized] = candidate.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        pass
            return snapshots

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [
                d for d in dirs
                if d not in MultiLanguageCodeAnalyzer.EXCLUDED_DIRS and not d.startswith(".")
            ]
            for fname in files:
                full = Path(root) / fname
                try:
                    rel = full.resolve().relative_to(self.project_root).as_posix()
                    if full.stat().st_size <= 2_000_000:
                        snapshots[rel] = full.read_text(encoding="utf-8", errors="ignore")
                except (OSError, ValueError):
                    continue
        return snapshots

    def verify_and_guard_changes(
        self,
        *,
        before_snapshots: Mapping[str, str],
        proposed_files: Mapping[str, str],
        apply_to_disk: bool = True,
    ) -> SafetyGuardReport:
        report = SafetyGuardReport(mode="safe_preserve")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_session_dir: Optional[Path] = None

        for rel_path, new_content in proposed_files.items():
            normalized = str(rel_path).replace("\\", "/").strip()
            if normalized not in before_snapshots:
                continue

            old_content = before_snapshots[normalized]
            if old_content == new_content:
                report.protected_files.append(normalized)
                continue

            if backup_session_dir is None:
                backup_session_dir = self.backup_root / timestamp
                report.backup_dir = str(backup_session_dir)
            backup_file = backup_session_dir / normalized
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            backup_file.write_text(old_content, encoding="utf-8")
            report.backed_up_files.append(normalized)

            if normalized in self.protected_paths or Path(normalized).name in self.protected_paths:
                issue = BreakingChangeIssue(
                    file_path=normalized,
                    code="PROTECTED_FILE_LOCKED",
                    message=f"保護対象ファイル `{normalized}` の上書きをブロックしました。",
                    action_taken="restored_original_and_saved_sidecar",
                )
                report.breaking_changes.append(issue)
                report.blocked_overwrites.append(normalized)
                report.protected_files.append(normalized)
                if apply_to_disk:
                    self._restore_and_write_sidecar(normalized, old_content, new_content, report)
                continue

            old_analysis = self.analyzer.analyze_source(
                old_content, file_path=normalized, project_root=self.project_root
            )
            new_analysis = self.analyzer.analyze_source(
                new_content, file_path=normalized, project_root=self.project_root
            )

            if new_analysis.parse_errors and not old_analysis.parse_errors:
                issue = BreakingChangeIssue(
                    file_path=normalized,
                    code="NEW_CODE_SYNTAX_ERROR",
                    message=(
                        f"`{normalized}` の新コードに構文エラーがあるため既存コードを保護しました: "
                        f"{'; '.join(new_analysis.parse_errors)}"
                    ),
                    impacted_files=old_analysis.reverse_dependencies,
                    action_taken="restored_original_and_saved_sidecar",
                )
                report.breaking_changes.append(issue)
                report.blocked_overwrites.append(normalized)
                report.protected_files.append(normalized)
                if apply_to_disk:
                    self._restore_and_write_sidecar(normalized, old_content, new_content, report)
                continue

            if self.block_symbol_deletion:
                old_symbols = {s.name for s in old_analysis.symbols if s.exported}
                new_symbols = {s.name for s in new_analysis.symbols if s.exported}
                removed = sorted(old_symbols - new_symbols)
                if removed:
                    issue = BreakingChangeIssue(
                        file_path=normalized,
                        code="PUBLIC_SYMBOL_REMOVED",
                        message=(
                            f"既存ファイル `{normalized}` の公開シンボル ({', '.join(removed[:6])}) "
                            f"が失われるため、全体上書きをブロックしました（1部分のみ修正モードを推奨）。"
                        ),
                        removed_symbols=removed,
                        impacted_files=old_analysis.reverse_dependencies,
                        action_taken="restored_original_and_saved_sidecar",
                    )
                    report.breaking_changes.append(issue)
                    report.blocked_overwrites.append(normalized)
                    report.protected_files.append(normalized)
                    if apply_to_disk:
                        self._restore_and_write_sidecar(normalized, old_content, new_content, report)
                    continue

            report.protected_files.append(normalized)

        return report

    def _restore_and_write_sidecar(
        self,
        rel_path: str,
        original_content: str,
        proposed_content: str,
        report: SafetyGuardReport,
    ) -> None:
        target = (self.project_root / rel_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original_content, encoding="utf-8")

        sidecar_name = f"{target.stem}.ai_proposed{target.suffix}"
        sidecar_path = target.parent / sidecar_name
        sidecar_path.write_text(proposed_content, encoding="utf-8")
        try:
            rel_sidecar = sidecar_path.relative_to(self.project_root).as_posix()
        except ValueError:
            rel_sidecar = sidecar_name
        if rel_sidecar not in report.proposed_sidecar_files:
            report.proposed_sidecar_files.append(rel_sidecar)


# ---------------------------------------------------------------------------
# Main Tool Class: ProjectBuilder (for tools/ProjectBuilder.py)
# ---------------------------------------------------------------------------


class ProjectBuilder:
    """`tools/` フォルダーに配置して利用するコード解析・1部分のみ修正・VS Code連携・プロジェクトビルダー。"""

    def __init__(
        self,
        project_root: str | Path = ".",
        *,
        build_service: Optional[Any] = None,
        protected_paths: Optional[Iterable[str]] = None,
        enable_terminal_output: bool = True,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.build_service = build_service
        self.enable_terminal_output = bool(enable_terminal_output)
        self.analyzer = MultiLanguageCodeAnalyzer()
        self.safety_guard = CodeSafetyGuard(
            project_root=self.project_root,
            protected_paths=protected_paths,
            analyzer=self.analyzer,
        )
        self.partial_patcher = SurgicalPartialPatcher(
            project_root=self.project_root,
            analyzer=self.analyzer,
        )

    def patch_file_partially(
        self,
        file_path: str,
        *,
        patch_code: Optional[str] = None,
        target_symbol: Optional[str] = None,
        search_block: Optional[str] = None,
        replace_block: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        allow_symbol_insert: bool = True,
        auto_merge_imports: bool = True,
        write_to_disk: bool = True,
        launch_vscode: bool = False,
        vscode_mode: str = "diff",
        update_vscode_tasks: bool = True,
        print_to_terminal: Optional[bool] = None,
    ) -> PartialPatchResult:
        patch_result = self.partial_patcher.apply_partial_patch(
            file_path=file_path,
            patch_code=patch_code,
            target_symbol=target_symbol,
            search_block=search_block,
            replace_block=replace_block,
            start_line=start_line,
            end_line=end_line,
            allow_symbol_insert=allow_symbol_insert,
            auto_merge_imports=auto_merge_imports,
            write_to_disk=write_to_disk,
            launch_vscode=launch_vscode,
            vscode_mode=vscode_mode,
        )

        if patch_result.success and update_vscode_tasks:
            self.partial_patcher.generate_vscode_tasks_json(
                last_patch=patch_result,
                write_to_workspace=write_to_disk,
            )

        should_print = (
            self.enable_terminal_output if print_to_terminal is None else bool(print_to_terminal)
        )
        if should_print:
            self.print_partial_patch_report(patch_result)

        return patch_result

    def analyze_code(
        self,
        code: str,
        *,
        file_path: Optional[str] = None,
        check_existing_protection: bool = True,
        apply_protection_to_disk: bool = False,
        print_to_terminal: Optional[bool] = None,
    ) -> CodeAnalysisReport:
        report = self.analyzer.analyze_source(
            code,
            file_path=file_path,
            project_root=self.project_root,
        )

        self._augment_docstring_connections(code, report)

        if check_existing_protection:
            existing_snapshots = self.safety_guard.snapshot_existing_files([report.target_file])
            if existing_snapshots:
                guard_report = self.safety_guard.verify_and_guard_changes(
                    before_snapshots=existing_snapshots,
                    proposed_files={report.target_file: code},
                    apply_to_disk=apply_protection_to_disk,
                )
                report.safety_guard = guard_report
            else:
                report.safety_guard = SafetyGuardReport(
                    mode="safe_preserve",
                    protected_files=[
                        c.path for c in report.connected_files if c.exists_in_project
                    ],
                )

        should_print = (
            self.enable_terminal_output if print_to_terminal is None else bool(print_to_terminal)
        )
        if should_print:
            self.print_terminal_report(report)

        return report

    def _augment_docstring_connections(self, code: str, report: CodeAnalysisReport) -> None:
        existing_modules = {c.module for c in report.connected_files} | {
            PurePosixPath(c.path).stem for c in report.connected_files
        }
        declared_names = {s.name.split(".")[0] for s in report.symbols}
        target_stem = PurePosixPath(report.target_file).stem

        candidates = set(
            re.findall(
                r"\b([A-Z][a-zA-Z0-9]+(?:Analyzer|Planner|Builder|Service|Validator|Engine|Writer|Generator|Packager|Inspector|State|Handler|PromptBuilder))\b",
                code,
            )
        )
        for name in sorted(candidates):
            if name in existing_modules or name in declared_names or name == target_stem:
                continue
            ext = ".java" if report.language == "java" else ".py"
            candidate_file = f"{name}{ext}"
            matched = self.analyzer._find_existing_candidate([candidate_file], self.project_root)
            report.connected_files.append(
                ConnectedFile(
                    path=matched or candidate_file,
                    module=name,
                    language=report.language,
                    relation="pipeline_link",
                    symbols=[name],
                    external=False,
                    exists_in_project=bool(matched),
                )
            )

    def safe_build(
        self,
        project_context: Dict[str, Any],
        *,
        use_ai: bool = True,
        allow_clean_existing: bool = False,
        submitted_code: Optional[str] = None,
        submitted_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        started = time.monotonic()
        analysis_report: Optional[CodeAnalysisReport] = None
        if submitted_code:
            analysis_report = self.analyze_code(
                submitted_code,
                file_path=submitted_file_path,
                check_existing_protection=True,
                apply_protection_to_disk=False,
                print_to_terminal=self.enable_terminal_output,
            )

        if self.build_service is not None and project_context.get("ready_to_plan", True) and not submitted_code:
            before_snapshots = self.safety_guard.snapshot_existing_files()
            safe_clean = bool(allow_clean_existing and not before_snapshots)
            build_result = self.build_service.build(
                project_context=project_context,
                use_ai=use_ai,
                clean_existing=safe_clean,
            )
            payload = (
                build_result.to_dict()
                if hasattr(build_result, "to_dict")
                else dict(build_result)
            )

            after_snapshots = self.safety_guard.snapshot_existing_files(before_snapshots.keys())
            guard_report = self.safety_guard.verify_and_guard_changes(
                before_snapshots=before_snapshots,
                proposed_files=after_snapshots,
                apply_to_disk=True,
            )
            guard_report.clean_existing_blocked = bool(before_snapshots and not safe_clean)
            payload["safety_guard"] = guard_report.to_dict()
            if analysis_report:
                payload["code_analysis"] = analysis_report.to_dict()
            if guard_report.breaking_changes:
                for bc in guard_report.breaking_changes:
                    if bc.message not in payload.setdefault("warnings", []):
                        payload["warnings"].append(bc.message)
            return payload

        if analysis_report is None:
            analysis_report = self.analyze_code(
                submitted_code or "# Empty input",
                file_path=submitted_file_path,
                print_to_terminal=self.enable_terminal_output,
            )

        return self.to_ui_block_payload(
            analysis_report,
            project_context=project_context,
            elapsed_seconds=round(time.monotonic() - started, 3),
        )

    def to_vscode_block_payload(
        self,
        patch_result: PartialPatchResult,
        *,
        analysis_report: Optional[CodeAnalysisReport] = None,
    ) -> Dict[str, Any]:
        generated_task = self.partial_patcher.generate_vscode_tasks_json(
            last_patch=patch_result,
            write_to_workspace=False,
        )
        cards: List[Dict[str, Any]] = [
            {
                "id": "partial-patch-summary",
                "category": f"✂️ Surgical Partial Patch ({patch_result.strategy})",
                "shortcut_win": f"L{patch_result.modified_start_line}-L{patch_result.modified_end_line}",
                "title": (
                    f"{patch_result.file_path} — "
                    f"{patch_result.target_symbol or f'{patch_result.modified_start_line}〜{patch_result.modified_end_line}行目'} のみピンポイント修正"
                ),
                "description": patch_result.message,
                "trivia": (
                    f"適用箇所: {patch_result.hunks_applied}箇所 / "
                    f"保護された他シンボル: {max(0, patch_result.preserved_symbols_count - 1)}件"
                    + (
                        f" / 先頭へ自動追加したimport: {', '.join(patch_result.added_imports)}"
                        if patch_result.added_imports
                        else ""
                    )
                ),
            },
            {
                "id": "vscode-diff-guide",
                "category": "💻 VS Code Diff & Goto 連携",
                "shortcut_win": "Ctrl+Shift+B",
                "title": "VS Code の左右比較 (Diff View) で変更箇所を即座に確認",
                "description": (
                    f"ターミナルまたは下のボタンから `{patch_result.vscode_diff_command}` を実行すると、"
                    "変更前の自動バックアップと1部分修正後のファイルを並べて比較できます。"
                ),
                "trivia": f"該当行へ直接ジャンプするコマンド: {patch_result.vscode_goto_command}",
            },
        ]

        written_files = [patch_result.file_path, ".vscode/tasks.json"] if patch_result.applied_to_disk else []
        return {
            "cards": cards,
            "generated_task": generated_task,
            "written_files": {"success": written_files},
            "partial_patch": patch_result.to_dict(),
            "code_analysis": analysis_report.to_dict() if analysis_report else None,
        }

    def to_ui_block_payload(
        self,
        report: CodeAnalysisReport,
        *,
        project_context: Optional[Mapping[str, Any]] = None,
        elapsed_seconds: float = 0.05,
    ) -> Dict[str, Any]:
        ctx = dict(project_context or {})
        has_breaking = bool(report.safety_guard.breaking_changes)
        has_parse_err = bool(report.parse_errors)
        has_cross_warn = bool(report.partial_patch and report.partial_patch.cross_file_warnings)
        status = "warning" if (has_breaking or has_parse_err or has_cross_warn) else "success"

        conn_list = [
            f"{c.path} ({c.language}, {c.relation})" for c in report.connected_files
        ]
        logs = [
            f"🎯 目標 (Goal): {report.goal}",
            f"📄 対象ファイル: {report.target_file} ({report.language}, {report.line_count}行)",
            f"🔗 連携ファイル ({len(report.connected_files)}件): {', '.join(conn_list) if conn_list else 'なし'}",
            f"🛡️ 保護モード: {report.safety_guard.mode} (保護ファイル={len(report.safety_guard.protected_files)}件)",
        ]
        if report.partial_patch:
            logs.append(f"✂️ 1部分修正: {report.partial_patch.message}")
            if report.partial_patch.added_imports:
                logs.append(f"📦 自動マージされたimport: {', '.join(report.partial_patch.added_imports)}")
            for cw in report.partial_patch.cross_file_warnings:
                logs.append(f"⚠️ クロスファイル引数注意: {cw}")
            if report.partial_patch.unified_diff:
                logs.append(report.partial_patch.unified_diff)
        for cap in report.capabilities:
            logs.append(f"⚡ 機能: {cap}")
        for bc in report.safety_guard.breaking_changes:
            logs.append(f"🛑 破壊防止ブロック: {bc.message}")

        warnings = [bc.message for bc in report.safety_guard.breaking_changes]
        if report.partial_patch and report.partial_patch.cross_file_warnings:
            warnings.extend(report.partial_patch.cross_file_warnings)

        feature_checks = [
            {
                "key": "goal_detection",
                "title": f"🎯 コードの目標 ({report.target_file})",
                "status": "success",
                "summary": report.goal,
                "checks": [
                    {
                        "name": "言語・行数",
                        "status": "success",
                        "message": f"{report.language} ({report.line_count}行)",
                    }
                ],
            },
            {
                "key": "connected_files",
                "title": f"🔗 つながっているファイル ({len(report.connected_files)}件)",
                "status": "success" if report.connected_files else "pending",
                "summary": "import・同一パッケージ・パイプライン連携・逆参照の検知結果",
                "checks": [
                    {
                        "name": f"{c.path} [{c.language}]",
                        "status": "success" if c.exists_in_project else "planned",
                        "message": (
                            f"関係: {c.relation}"
                            + (f" / シンボル: {', '.join(c.symbols[:5])}" if c.symbols else "")
                        ),
                    }
                    for c in report.connected_files
                ],
            },
            {
                "key": "capabilities",
                "title": f"⚡ 何ができるか ({len(report.capabilities)}件)",
                "status": "success",
                "summary": "公開クラス・関数・APIエンドポイント・メソッドの一覧（行範囲付き）",
                "checks": [
                    {
                        "name": f"{s.name} (L{s.line}-L{s.end_line or s.line})",
                        "status": "success",
                        "message": f"[{s.kind}] {s.summary}",
                    }
                    for s in report.symbols[:15]
                ],
            },
            {
                "key": "code_safety_guard",
                "title": "🛡️ 既存コード保護 & 1部分修正ガード",
                "status": "warning" if (has_breaking or has_cross_warn) else "success",
                "summary": (
                    report.partial_patch.message
                    if report.partial_patch
                    else (
                        "破壊的変更を検知して既存ファイルの上書きをブロックしました。"
                        if has_breaking
                        else "既存の大切なコードを壊さない保護モードが有効です。"
                    )
                ),
                "checks": [
                    {
                        "name": "全体削除 (clean_existing) 防止",
                        "status": "success",
                        "message": "既存プロジェクトの削除を抑止済み",
                    },
                    {
                        "name": "ピンポイント1部分修正 & シンボル保護",
                        "status": "warning" if has_breaking else "success",
                        "message": (
                            f"L{report.partial_patch.modified_start_line}-L{report.partial_patch.modified_end_line} "
                            f"({report.partial_patch.hunks_applied}箇所) のみ更新"
                            if report.partial_patch and report.partial_patch.success
                            else (
                                f"{len(report.safety_guard.breaking_changes)}件の破壊的変更をブロック"
                                if has_breaking
                                else "既存シンボルへの破壊的変更なし"
                            )
                        ),
                    },
                ],
            },
        ]

        steps = [
            {
                "name": "CodeAnalyzer (目標・構造・行範囲解析)",
                "status": "success",
                "message": report.goal,
                "progress_percent": 35,
            },
            {
                "name": "DependencyDetector (.py / .java / .ts 連携検知)",
                "status": "success",
                "message": f"{len(report.connected_files)}件の関連ファイルと{len(report.reverse_dependencies)}件の逆参照を検知しました。",
                "progress_percent": 70,
            },
            {
                "name": "SurgicalPatcher & SafetyGuard (1部分修正・既存保護)",
                "status": "warning" if (has_breaking or has_cross_warn) else "success",
                "message": (
                    report.partial_patch.message
                    if report.partial_patch
                    else (
                        f"{len(report.safety_guard.blocked_overwrites)}件の危険な上書きをブロックし既存コードを保護しました。"
                        if has_breaking
                        else "既存コードの破壊リスクはありません。"
                    )
                ),
                "progress_percent": 100,
            },
        ]

        generation_summary = [
            {
                "path": report.target_file,
                "status": "warning" if has_breaking else "success",
                "source": (
                    f"partial_patch (L{report.partial_patch.modified_start_line}-L{report.partial_patch.modified_end_line})"
                    if report.partial_patch and report.partial_patch.success
                    else f"analyzed ({report.language})"
                ),
                "characters": sum(len(line) for line in report.capabilities),
            },
            *[
                {
                    "path": c.path,
                    "status": "success" if c.exists_in_project else "pending",
                    "source": f"{c.language} ({c.relation})",
                    "characters": 0,
                }
                for c in report.connected_files
            ],
        ]

        return {
            "project_name": str(ctx.get("project_name") or report.target_file),
            "status": status,
            "message": report.partial_patch.message if report.partial_patch else report.summary,
            "files_generated": len(generation_summary),
            "project_root": str(self.project_root),
            "generation": generation_summary,
            "steps": steps,
            "logs": logs,
            "errors": list(report.parse_errors),
            "warnings": warnings,
            "progress_percent": 100,
            "current_stage": "1部分修正・保護チェック完了" if report.partial_patch else "解析・保護チェック完了",
            "elapsed_seconds": elapsed_seconds,
            "estimated_total_minutes": 1,
            "estimated_remaining_minutes": 0,
            "estimate_confidence": "high",
            "feature_checks": feature_checks,
            "code_analysis": report.to_dict(),
            "safety_guard": report.safety_guard.to_dict(),
            "partial_patch": report.partial_patch.to_dict() if report.partial_patch else None,
        }

    @staticmethod
    def print_terminal_report(report: CodeAnalysisReport) -> None:
        border = "=" * 72
        sub_border = "-" * 72
        print(f"\n{border}", flush=True)
        print(
            f"🔍 [AI Code Inspector & Safety Guard] 対象: {report.target_file} ({report.language})",
            flush=True,
        )
        print(border, flush=True)

        print(f"🎯 【目標 (Goal / Purpose)】", flush=True)
        print(f"   {report.goal}", flush=True)
        print(sub_border, flush=True)

        print(
            f"🔗 【つながっているコード・ファイル ({len(report.connected_files)}件)】",
            flush=True,
        )
        if report.connected_files:
            for conn in report.connected_files:
                relation_label = {
                    "imports": "import参照先",
                    "imported_by": "このコードを参照中(影響範囲)",
                    "same_package": "同一パッケージ連携",
                    "pipeline_link": "設計パイプライン連携",
                }.get(conn.relation, conn.relation)
                syms = f" (利用シンボル: {', '.join(conn.symbols[:5])})" if conn.symbols else ""
                exists_mark = "✅既存" if conn.exists_in_project else "📎検出"
                print(
                    f"   - [{conn.language.upper()}] {conn.path} "
                    f"({exists_mark} / {relation_label}){syms}",
                    flush=True,
                )
        else:
            print("   - 外部ファイル依存なし（単体で完結するモジュール）", flush=True)

        if report.external_packages:
            print(
                f"   📦 外部ライブラリ: {', '.join(report.external_packages)}",
                flush=True,
            )
        print(sub_border, flush=True)

        print(
            f"⚡ 【何ができるか (Capabilities / 提供機能: {len(report.capabilities)}件)】",
            flush=True,
        )
        for cap in report.capabilities[:12]:
            print(f"   • {cap}", flush=True)
        print(sub_border, flush=True)

        guard = report.safety_guard
        print(
            f"🛡️ 【既存コード保護ガード (Mode: {guard.mode})】",
            flush=True,
        )
        if guard.breaking_changes:
            for bc in guard.breaking_changes:
                print(f"   🛑 [破壊防止ブロック] {bc.message}", flush=True)
                if bc.removed_symbols:
                    print(
                        f"      -> 守られた既存シンボル: {', '.join(bc.removed_symbols)}",
                        flush=True,
                    )
            if guard.proposed_sidecar_files:
                print(
                    f"   💾 AI提案コード退避先: {', '.join(guard.proposed_sidecar_files)}",
                    flush=True,
                )
        else:
            print(
                "   ✅ 既存の公開クラス・関数・メソッドを破壊する変更はありません。",
                flush=True,
            )
        if guard.backup_dir:
            print(f"   🗂️ 自動バックアップ先: {guard.backup_dir}", flush=True)

        print(f"{border}\n", flush=True)

    @staticmethod
    def print_partial_patch_report(patch: PartialPatchResult) -> None:
        border = "=" * 72
        sub_border = "-" * 72
        print(f"\n{border}", flush=True)
        status_icon = "✂️✅" if patch.success else "✂️🛑"
        print(
            f"{status_icon} [VS Code Surgical Partial Patch (1部分のみ修正)] 対象: {patch.file_path}",
            flush=True,
        )
        print(border, flush=True)
        print(f"📌 修正方式       : {patch.strategy} (適用箇所: {patch.hunks_applied}箇所)", flush=True)
        if patch.target_symbol:
            print(f"🎯 対象シンボル   : {patch.target_symbol}", flush=True)
        print(
            f"📏 変更行範囲     : L{patch.modified_start_line} 〜 L{patch.modified_end_line} "
            f"(全体 {patch.original_line_count}行 -> {patch.new_line_count}行)",
            flush=True,
        )
        print(
            f"🛡️ 保護された機能 : 同ファイル内の他シンボル {max(0, patch.preserved_symbols_count - 1)} 件を100%維持",
            flush=True,
        )
        if patch.added_imports:
            print(
                f"📦 自動追加import : {', '.join(patch.added_imports)}",
                flush=True,
            )
        if patch.cross_file_warnings:
            for cw in patch.cross_file_warnings:
                print(f"⚠️ 連携ファイル注意: {cw}", flush=True)
        print(f"💬 結果メッセージ : {patch.message}", flush=True)
        if patch.backup_file_path:
            print(f"🗂️ 変更前退避先   : {patch.backup_file_path}", flush=True)
        if patch.vscode_goto_command:
            print(f"💻 VS Code行移動  : {patch.vscode_goto_command}", flush=True)
        if patch.vscode_diff_command:
            print(f"🔍 VS Code Diff   : {patch.vscode_diff_command}", flush=True)
        if patch.unified_diff:
            print(sub_border, flush=True)
            print("📝 【Unified Diff (変更箇所のみ)】", flush=True)
            for diff_line in patch.unified_diff.splitlines()[:35]:
                print(f"   {diff_line}", flush=True)
        print(f"{border}\n", flush=True)

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        return {
            "name": "project_builder",
            "description": (
                "送られたコード(.py/.java/.ts/.tsx等)の目標・連携ファイル・できることを解析してターミナルとUIに表示し、"
                "VS Codeと連携して既存コードの1部分のみを安全に修正(partial_patch)またはビルドするツール。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["analyze_code", "partial_patch", "safe_build", "rollback"],
                        "description": "実行モード ('analyze_code' | 'partial_patch' | 'safe_build' | 'rollback')",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "対象ファイルパス（例: ConversationState.py, OrderController.java）",
                    },
                    "target_symbol": {
                        "type": "string",
                        "description": "1部分のみ修正する場合の対象クラス・メソッド・関数名（例: ConversationState.debug_print）",
                    },
                    "code": {
                        "type": "string",
                        "description": "解析するコード、または1部分修正用の関数コード / SEARCH-REPLACEブロック",
                    },
                },
                "required": ["mode"],
            },
        }


__all__ = [
    "BreakingChangeIssue",
    "CodeAnalysisReport",
    "CodeSafetyGuard",
    "ConnectedFile",
    "MultiLanguageCodeAnalyzer",
    "PartialPatchResult",
    "ProjectBuilder",
    "SafetyGuardReport",
    "SurgicalPartialPatcher",
    "SymbolCapability",
]