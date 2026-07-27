# =========================================================
# project_scanner.py
# プロジェクト全体解析システム
# フォルダ構造 / ファイル構造 / AI解析用Index生成
# =========================================================

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List

# =========================================================
# 内部モジュール
# =========================================================

from core.chunk_manager_chatgpt import build_chunks_from_directory
from core.dependency_graph import analyze_project_dependencies
from core.memory_manager import save_project_analysis

# =========================================================
# 基本設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")

SCAN_OUTPUT_DIR = os.path.join(
    AI_MEMORY_DIR,
    "project_scans"
)

os.makedirs(SCAN_OUTPUT_DIR, exist_ok=True)

# =========================================================
# 無視フォルダ
# =========================================================

IGNORE_DIRS = [
    "__pycache__",
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    ".vscode",
    ".idea",
    "coverage"
]

# =========================================================
# 対応拡張子
# =========================================================

SOURCE_EXTENSIONS = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".html",
    ".css",
    ".md"
)

# =========================================================
# ファイルサイズ制限
# =========================================================

MAX_FILE_SIZE = 1024 * 1024 * 2  # 2MB

# =========================================================
# ユーティリティ
# =========================================================

def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def is_source_file(filename: str) -> bool:
    return filename.lower().endswith(SOURCE_EXTENSIONS)

# =========================================================
# 言語判定
# =========================================================

def detect_language(file_path: str) -> str:

    ext = os.path.splitext(file_path)[1].lower()

    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "react",
        ".ts": "typescript",
        ".tsx": "react-typescript",
        ".json": "json",
        ".html": "html",
        ".css": "css",
        ".md": "markdown"
    }

    return mapping.get(ext, "unknown")

# =========================================================
# フレームワーク推定
# =========================================================

def detect_frameworks(file_list: List[str]) -> List[str]:

    frameworks = []

    joined = " ".join(file_list).lower()

    if "package.json" in joined:
        frameworks.append("nodejs")

    if "react" in joined or ".jsx" in joined or ".tsx" in joined:
        frameworks.append("react")

    if "next.config" in joined:
        frameworks.append("nextjs")

    if "fastapi" in joined:
        frameworks.append("fastapi")

    if "django" in joined:
        frameworks.append("django")

    if "flask" in joined:
        frameworks.append("flask")

    if "tailwind" in joined:
        frameworks.append("tailwindcss")

    if "vite" in joined:
        frameworks.append("vite")

    return list(set(frameworks))

# =========================================================
# ファイル情報解析
# =========================================================

def analyze_file(
    file_path: str
) -> Dict[str, Any]:

    try:

        stat = os.stat(file_path)

        size = stat.st_size

        if size > MAX_FILE_SIZE:

            return {
                "path": normalize_path(file_path),
                "skipped": True,
                "reason": "file_too_large"
            }

        with open(file_path, "r", encoding="utf-8") as f:

            content = f.read()

    except UnicodeDecodeError:

        return {
            "path": normalize_path(file_path),
            "skipped": True,
            "reason": "encoding_error"
        }

    except Exception as e:

        return {
            "path": normalize_path(file_path),
            "skipped": True,
            "reason": str(e)
        }

    functions = []
    classes = []
    imports = []

    # Python
    functions += re.findall(
        r'def\s+([a-zA-Z0-9_]+)',
        content
    )

    classes += re.findall(
        r'class\s+([a-zA-Z0-9_]+)',
        content
    )

    imports += re.findall(
        r'import\s+([a-zA-Z0-9_\.]+)',
        content
    )

    # JS/TS
    functions += re.findall(
        r'function\s+([a-zA-Z0-9_]+)',
        content
    )

    imports += re.findall(
        r'import\s+.*?from\s+[\'"](.*?)[\'"]',
        content
    )

    return {
        "path": normalize_path(file_path),
        "language": detect_language(file_path),
        "size": size,
        "line_count": len(content.splitlines()),
        "functions": list(set(functions)),
        "classes": list(set(classes)),
        "imports": list(set(imports)),
        "skipped": False
    }

# =========================================================
# フォルダツリー構築
# =========================================================

def build_folder_tree(
    target_dir: str
) -> Dict[str, Any]:

    tree = {}

    for root, dirs, files in os.walk(target_dir):

        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS
        ]

        relative_root = normalize_path(
            os.path.relpath(root, target_dir)
        )

        if relative_root == ".":
            relative_root = "root"

        tree[relative_root] = {
            "directories": dirs,
            "files": files
        }

    return tree

# =========================================================
# ソースファイル収集
# =========================================================

def collect_source_files(
    target_dir: str
) -> List[str]:

    collected = []

    for root, dirs, files in os.walk(target_dir):

        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS
        ]

        for file in files:

            if not is_source_file(file):
                continue

            full_path = os.path.join(root, file)

            collected.append(
                normalize_path(full_path)
            )

    return collected

# =========================================================
# Main Scanner
# =========================================================

def scan_project(
    target_dir: str,
    project_name: str = "default_project"
) -> Dict[str, Any]:

    print("🧠 Project Scan開始")

    files = collect_source_files(target_dir)

    print(f"📦 Source Files: {len(files)}")

    analyzed_files = []

    languages = {}
    total_lines = 0

    for file_path in files:

        print(f"🔍 解析中: {file_path}")

        analysis = analyze_file(file_path)

        analyzed_files.append(analysis)

        if not analysis.get("skipped"):

            lang = analysis["language"]

            languages[lang] = (
                languages.get(lang, 0) + 1
            )

            total_lines += analysis["line_count"]

    frameworks = detect_frameworks(files)

    folder_tree = build_folder_tree(target_dir)

    dependency_graph = analyze_project_dependencies(
        target_dir
    )

    chunks = build_chunks_from_directory(
        target_dir,
        project_name
    )

    result = {
        "project_name": project_name,
        "scanned_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "target_dir": normalize_path(target_dir),

        "statistics": {
            "total_files": len(files),
            "total_chunks": len(chunks),
            "total_lines": total_lines,
            "languages": languages,
            "frameworks": frameworks
        },

        "folder_tree": folder_tree,

        "files": analyzed_files,

        "dependency_graph": dependency_graph
    }

    output_file = os.path.join(
        SCAN_OUTPUT_DIR,
        f"{project_name}.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    save_project_analysis(
        project_name,
        result
    )

    print("✅ Project Scan完了")

    return result

# =========================================================
# 検索
# =========================================================

def search_project_files(
    keyword: str,
    project_name: str
) -> List[Dict[str, Any]]:

    scan_file = os.path.join(
        SCAN_OUTPUT_DIR,
        f"{project_name}.json"
    )

    if not os.path.exists(scan_file):
        return []

    with open(scan_file, "r", encoding="utf-8") as f:

        data = json.load(f)

    results = []

    for file in data.get("files", []):

        path = file.get("path", "")

        if keyword.lower() in path.lower():

            results.append(file)

            continue

        functions = file.get("functions", [])

        for func in functions:

            if keyword.lower() in func.lower():

                results.append(file)

                break

    return results

# =========================================================
# 最近大きく変更された場所推定
# =========================================================

def detect_hotspots(
    project_name: str
) -> List[Dict[str, Any]]:

    scan_file = os.path.join(
        SCAN_OUTPUT_DIR,
        f"{project_name}.json"
    )

    if not os.path.exists(scan_file):
        return []

    with open(scan_file, "r", encoding="utf-8") as f:

        data = json.load(f)

    files = data.get("files", [])

    scored = []

    for file in files:

        score = 0

        score += len(file.get("functions", [])) * 2
        score += len(file.get("imports", []))
        score += file.get("line_count", 0) // 100

        scored.append({
            "path": file.get("path"),
            "score": score
        })

    scored.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return scored[:20]

# =========================================================
# AI向けProject Summary
# =========================================================

def build_project_summary(
    project_name: str
) -> str:

    scan_file = os.path.join(
        SCAN_OUTPUT_DIR,
        f"{project_name}.json"
    )

    if not os.path.exists(scan_file):

        return "Project Scanなし"

    with open(scan_file, "r", encoding="utf-8") as f:

        data = json.load(f)

    stats = data.get("statistics", {})

    summary = f"""
# Project Summary

Project:
{project_name}

Files:
{stats.get("total_files")}

Chunks:
{stats.get("total_chunks")}

Lines:
{stats.get("total_lines")}

Languages:
{stats.get("languages")}

Frameworks:
{stats.get("frameworks")}
"""

    return summary

# =========================================================
# テスト
# =========================================================

if __name__ == "__main__":

    TARGET_DIR = "./"

    result = scan_project(
        target_dir=TARGET_DIR,
        project_name="jimdo_studio_ai"
    )

    print("\n")
    print(build_project_summary(
        "jimdo_studio_ai"
    ))

    print("\n🔥 Hotspots")

    hotspots = detect_hotspots(
        "jimdo_studio_ai"
    )

    for item in hotspots[:10]:

        print(
            f"{item['score']:>3} | {item['path']}"
        )