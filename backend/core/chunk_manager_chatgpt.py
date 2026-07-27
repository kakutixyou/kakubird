# =========================================================
# chunk_manager.py
# ソースコード・テキストをAI向けChunkへ分割する管理システム
# =========================================================

import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

# =========================================================
# 保存先設定
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")
CHUNK_OUTPUT_DIR = os.path.join(AI_MEMORY_DIR, "chunks")

os.makedirs(CHUNK_OUTPUT_DIR, exist_ok=True)

# =========================================================
# 対応拡張子
# =========================================================

SUPPORTED_EXTENSIONS = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".html",
    ".css",
    ".md",
    ".txt"
)

# =========================================================
# Chunk設定
# =========================================================

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150

# =========================================================
# ユーティリティ
# =========================================================

def is_supported_file(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED_EXTENSIONS)


def normalize_text(text: str) -> str:
    """
    改行や不要文字を整理
    """
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    return text.strip()


# =========================================================
# メタデータ抽出
# =========================================================

def extract_metadata(file_path: str, content: str) -> Dict[str, Any]:
    """
    コードから簡易メタデータを抽出
    """

    imports = []
    exports = []
    functions = []
    classes = []

    # JS/TS import
    js_imports = re.findall(r'import\s+.*?from\s+[\'"](.*?)[\'"]', content)

    # Python import
    py_imports = re.findall(r'from\s+([a-zA-Z0-9_\.]+)\s+import', content)
    py_imports += re.findall(r'import\s+([a-zA-Z0-9_\.]+)', content)

    imports.extend(js_imports)
    imports.extend(py_imports)

    # 関数検出
    functions += re.findall(r'function\s+([a-zA-Z0-9_]+)', content)
    functions += re.findall(r'def\s+([a-zA-Z0-9_]+)', content)

    # class検出
    classes += re.findall(r'class\s+([a-zA-Z0-9_]+)', content)

    # export検出
    exports += re.findall(r'export\s+default\s+([a-zA-Z0-9_]+)', content)

    return {
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "language": detect_language(file_path),
        "imports": list(set(imports)),
        "exports": list(set(exports)),
        "functions": list(set(functions)),
        "classes": list(set(classes)),
        "size": len(content)
    }

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
        ".md": "markdown",
        ".txt": "text"
    }

    return mapping.get(ext, "unknown")

# =========================================================
# Chunk分割
# =========================================================

def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[str]:
    """
    テキストを重複付きでChunk分割
    """

    text = normalize_text(text)

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks

# =========================================================
# コード向けChunk分割
# =========================================================

def split_code_into_chunks(
    code: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> List[str]:
    """
    関数単位を意識したコードChunk
    """

    code = normalize_text(code)

    lines = code.split("\n")

    chunks = []

    current_chunk = []

    current_size = 0

    for line in lines:

        current_chunk.append(line)

        current_size += len(line)

        # 関数/class付近で区切る
        if current_size >= chunk_size and (
            line.strip().startswith("def ")
            or line.strip().startswith("class ")
            or line.strip().startswith("function ")
            or "export default" in line
        ):

            chunks.append("\n".join(current_chunk))

            current_chunk = []

            current_size = 0

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

# =========================================================
# Chunk生成
# =========================================================

def build_chunks_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    1ファイルからChunk配列を生成
    """

    if not is_supported_file(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

    except UnicodeDecodeError:
        print(f"⚠️ UTF-8読み込み失敗: {file_path}")
        return []

    except Exception as e:
        print(f"❌ ファイル読み込み失敗: {file_path}")
        print(e)
        return []

    metadata = extract_metadata(file_path, content)

    language = metadata["language"]

    # コード系はコードChunk
    if language in [
        "python",
        "javascript",
        "react",
        "typescript",
        "react-typescript"
    ]:
        raw_chunks = split_code_into_chunks(content)

    else:
        raw_chunks = split_text_into_chunks(content)

    chunk_objects = []

    for idx, chunk_text in enumerate(raw_chunks):

        chunk_id = str(uuid.uuid4())

        chunk_data = {
            "id": chunk_id,
            "file_path": file_path,
            "file_name": metadata["file_name"],
            "language": language,
            "chunk_index": idx,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata,
            "content": chunk_text
        }

        chunk_objects.append(chunk_data)

    return chunk_objects

# =========================================================
# Chunk保存
# =========================================================

def save_chunks(
    chunks: List[Dict[str, Any]],
    project_name: str = "default_project"
):
    """
    Chunk群をJSON保存
    """

    output_dir = os.path.join(CHUNK_OUTPUT_DIR, project_name)

    os.makedirs(output_dir, exist_ok=True)

    for chunk in chunks:

        chunk_id = chunk["id"]

        output_path = os.path.join(output_dir, f"{chunk_id}.json")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"❌ Chunk保存失敗: {output_path}")
            print(e)

# =========================================================
# ディレクトリ一括Chunk化
# =========================================================

def build_chunks_from_directory(
    target_dir: str,
    project_name: str = "default_project"
) -> List[Dict[str, Any]]:
    """
    ディレクトリ全体をChunk化
    """

    all_chunks = []

    for root, dirs, files in os.walk(target_dir):

        # 不要ディレクトリ除外
        dirs[:] = [
            d for d in dirs
            if d not in [
                "__pycache__",
                "node_modules",
                ".git",
                "dist",
                "build"
            ]
        ]

        for file in files:

            file_path = os.path.join(root, file)

            if not is_supported_file(file_path):
                continue

            print(f"📄 Chunk解析中: {file_path}")

            file_chunks = build_chunks_from_file(file_path)

            all_chunks.extend(file_chunks)

    save_chunks(all_chunks, project_name)

    print(f"🧠 Chunk生成完了: {len(all_chunks)} chunks")

    return all_chunks

# =========================================================
# Chunk検索（簡易）
# =========================================================

def search_chunks_by_keyword(
    keyword: str,
    project_name: str = "default_project"
) -> List[Dict[str, Any]]:
    """
    JSON保存済みChunkを簡易検索
    """

    project_dir = os.path.join(CHUNK_OUTPUT_DIR, project_name)

    if not os.path.exists(project_dir):
        return []

    results = []

    for filename in os.listdir(project_dir):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(project_dir, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                chunk = json.load(f)

            if keyword.lower() in chunk["content"].lower():
                results.append(chunk)

        except Exception:
            pass

    return results

# =========================================================
# Chunk統計
# =========================================================

def get_chunk_statistics(
    project_name: str = "default_project"
) -> Dict[str, Any]:

    project_dir = os.path.join(CHUNK_OUTPUT_DIR, project_name)

    if not os.path.exists(project_dir):
        return {
            "total_chunks": 0
        }

    total_chunks = 0
    languages = {}

    for filename in os.listdir(project_dir):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(project_dir, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                chunk = json.load(f)

            total_chunks += 1

            lang = chunk.get("language", "unknown")

            languages[lang] = languages.get(lang, 0) + 1

        except Exception:
            pass

    return {
        "total_chunks": total_chunks,
        "languages": languages
    }

# =========================================================
# テスト実行
# =========================================================

if __name__ == "__main__":

    print("🧠 Chunk Manager Test")

    target = "./"

    chunks = build_chunks_from_directory(
        target_dir=target,
        project_name="test_project"
    )

    print(f"生成Chunk数: {len(chunks)}")