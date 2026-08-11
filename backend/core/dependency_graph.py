# =========================================================
# dependency_graph.py
# プロジェクト依存関係グラフ解析システム
# =========================================================

import os
import re
import json
from typing import Dict, List, Set, Any

# =========================================================
# 基本設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(BASE_DIR, ".ai_memory")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dependency_graph.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================
# 対応拡張子
# =========================================================

SUPPORTED_EXTENSIONS = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx"
)

# =========================================================
# 除外ディレクトリ
# =========================================================

IGNORE_DIRS = [
    "__pycache__",
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "coverage"
]

# =========================================================
# Import解析Regex
# =========================================================

PYTHON_IMPORT_RE_1 = r'import\s+([a-zA-Z0-9_\.]+)'
PYTHON_IMPORT_RE_2 = r'from\s+([a-zA-Z0-9_\.]+)\s+import'

JS_IMPORT_RE = r'import\s+.*?from\s+[\'"](.*?)[\'"]'
JS_REQUIRE_RE = r'require\([\'"](.*?)[\'"]\)'

# =========================================================
# ユーティリティ
# =========================================================

def is_supported_file(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED_EXTENSIONS)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


# =========================================================
# ファイル一覧取得
# =========================================================

def collect_source_files(target_dir: str) -> List[str]:

    source_files = []

    for root, dirs, files in os.walk(target_dir):

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:

            if is_supported_file(file):

                full_path = os.path.join(root, file)

                source_files.append(normalize_path(full_path))

    return source_files

# =========================================================
# Python Import解析
# =========================================================

def extract_python_imports(content: str) -> List[str]:

    imports = []

    imports += re.findall(PYTHON_IMPORT_RE_1, content)
    imports += re.findall(PYTHON_IMPORT_RE_2, content)

    return list(set(imports))

# =========================================================
# JS/TS Import解析
# =========================================================

def extract_js_imports(content: str) -> List[str]:

    imports = []

    imports += re.findall(JS_IMPORT_RE, content)
    imports += re.findall(JS_REQUIRE_RE, content)

    return list(set(imports))

# =========================================================
# 言語判定
# =========================================================

def detect_language(file_path: str) -> str:

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        return "python"

    if ext in [".js", ".jsx"]:
        return "javascript"

    if ext in [".ts", ".tsx"]:
        return "typescript"

    return "unknown"

# =========================================================
# 単一ファイル解析
# =========================================================

def analyze_file_dependencies(file_path: str) -> Dict[str, Any]:

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

    except Exception as e:

        print(f"❌ 読み込み失敗: {file_path}")
        print(e)

        return {
            "imports": [],
            "language": "unknown"
        }

    language = detect_language(file_path)

    imports = []

    if language == "python":
        imports = extract_python_imports(content)

    elif language in ["javascript", "typescript"]:
        imports = extract_js_imports(content)

    return {
        "imports": imports,
        "language": language
    }

# =========================================================
# Dependency Graph構築
# =========================================================

def build_dependency_graph(
    target_dir: str
) -> Dict[str, List[str]]:

    graph = {}

    files = collect_source_files(target_dir)

    print(f"📦 解析対象ファイル数: {len(files)}")

    for file_path in files:

        relative_path = normalize_path(
            os.path.relpath(file_path, target_dir)
        )

        result = analyze_file_dependencies(file_path)

        graph[relative_path] = result["imports"]

        print(f"🔗 {relative_path}")
        print(f"   imports: {len(result['imports'])}")

    return graph

# =========================================================
# 逆依存グラフ
# =========================================================

def build_reverse_dependency_graph(
    graph: Dict[str, List[str]]
) -> Dict[str, List[str]]:

    reverse_graph = {}

    for file, imports in graph.items():

        for dep in imports:

            if dep not in reverse_graph:
                reverse_graph[dep] = []

            reverse_graph[dep].append(file)

    return reverse_graph

# =========================================================
# ファイル接続検索
# =========================================================

def find_related_files(
    graph: Dict[str, List[str]],
    target_keyword: str
) -> List[str]:

    results = []

    for file, imports in graph.items():

        if target_keyword.lower() in file.lower():
            results.append(file)
            continue

        for dep in imports:

            if target_keyword.lower() in dep.lower():
                results.append(file)
                break

    return results

# =========================================================
# 孤立ファイル検出
# =========================================================

def detect_isolated_files(
    graph: Dict[str, List[str]]
) -> List[str]:

    reverse_graph = build_reverse_dependency_graph(graph)

    isolated = []

    for file, imports in graph.items():

        no_imports = len(imports) == 0
        no_references = file not in reverse_graph

        if no_imports and no_references:
            isolated.append(file)

    return isolated

# =========================================================
# ノード統計
# =========================================================

def calculate_graph_statistics(
    graph: Dict[str, List[str]]
) -> Dict[str, Any]:

    total_files = len(graph)

    total_edges = sum(len(v) for v in graph.values())

    most_connected = None
    most_count = 0

    for file, imports in graph.items():

        if len(imports) > most_count:
            most_connected = file
            most_count = len(imports)

    return {
        "total_files": total_files,
        "total_dependencies": total_edges,
        "most_connected_file": most_connected,
        "most_connected_count": most_count
    }

# =========================================================
# JSON保存
# =========================================================

def save_dependency_graph(
    graph: Dict[str, List[str]]
):

    try:

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

            json.dump(
                graph,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(f"💾 保存完了: {OUTPUT_FILE}")

    except Exception as e:

        print("❌ 保存失敗")
        print(e)

# =========================================================
# JSON読み込み
# =========================================================

def load_dependency_graph() -> Dict[str, List[str]]:

    if not os.path.exists(OUTPUT_FILE):
        return {}

    try:

        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception as e:

        print("❌ 読み込み失敗")
        print(e)

        return {}

# =========================================================
# グラフPretty表示
# =========================================================

def print_graph_summary(
    graph: Dict[str, List[str]]
):

    stats = calculate_graph_statistics(graph)

    print("\n==============================")
    print("🧠 Dependency Graph Summary")
    print("==============================")

    print(f"Files: {stats['total_files']}")
    print(f"Dependencies: {stats['total_dependencies']}")
    print(f"Most Connected: {stats['most_connected_file']}")
    print(f"Connection Count: {stats['most_connected_count']}")

    isolated = detect_isolated_files(graph)

    print(f"\n孤立ファイル数: {len(isolated)}")

    if isolated:

        print("\n--- Isolated Files ---")

        for file in isolated[:20]:
            print(f" - {file}")

# =========================================================
# Mermaid形式出力
# =========================================================

def export_mermaid_graph(
    graph: Dict[str, List[str]],
    output_path: str = "./dependency_graph.mmd"
):

    lines = []

    lines.append("graph TD")

    for file, imports in graph.items():

        safe_file = file.replace("/", "_").replace(".", "_")

        for dep in imports:

            safe_dep = dep.replace("/", "_").replace(".", "_")

            lines.append(
                f'    {safe_file}["{file}"] --> {safe_dep}["{dep}"]'
            )

    try:

        with open(output_path, "w", encoding="utf-8") as f:

            f.write("\n".join(lines))

        print(f"📈 Mermaid Graph Exported: {output_path}")

    except Exception as e:

        print("❌ Mermaid出力失敗")
        print(e)

# =========================================================
# メイン解析
# =========================================================

def analyze_project_dependencies(
    target_dir: str
) -> Dict[str, List[str]]:

    print("🧠 Dependency Graph解析開始")

    graph = build_dependency_graph(target_dir)

    save_dependency_graph(graph)

    print_graph_summary(graph)

    return graph

# =========================================================
# テスト実行
# =========================================================

if __name__ == "__main__":

    TARGET_DIR = "./"

    dependency_graph = analyze_project_dependencies(
        TARGET_DIR
    )

    export_mermaid_graph(
        dependency_graph
    )

    print("\n✅ 完了")