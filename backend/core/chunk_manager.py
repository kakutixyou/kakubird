# ===
# chunk_manager.py
# ソースコード・テキストをAI向けChunkへ分割する管理システム
# ===

import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

# ===
# 保存先設定
# ===

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AI_MEMORY_DIR = os.path.join(BASE_DIR, ".ai_memory")
CHUNK_OUTPUT_DIR = os.path.join(AI_MEMORY_DIR, "chunks")

os.makedirs(CHUNK_OUTPUT_DIR, exist_ok=True)

# ===
# オンメモリキャッシュ（検索爆速化用）
# ===
_chunk_cache: Dict[str, List[Dict[str, Any]]] = {}

# ===
# 対応拡張子
# ===

SUPPORTED_EXTENSIONS = (
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".json", ".html", ".css", ".md", ".txt"
)

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150

# ===
# ユーティリティ・メタデータ抽出
# ===

def is_supported_file(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED_EXTENSIONS)

def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()

def extract_metadata(file_path: str, content: str) -> Dict[str, Any]:
    imports, exports, functions, classes = [], [], [], []
    
    # 正規表現による簡易抽出
    imports.extend(re.findall(r'import\s+.*?from\s+[\'"](.*?)[\'"]', content))
    imports.extend(re.findall(r'from\s+([a-zA-Z0-9_\.]+)\s+import', content))
    functions.extend(re.findall(r'function\s+([a-zA-Z0-9_]+)', content))
    functions.extend(re.findall(r'def\s+([a-zA-Z0-9_]+)', content))
    classes.extend(re.findall(r'class\s+([a-zA-Z0-9_]+)', content))
    exports.extend(re.findall(r'export\s+default\s+([a-zA-Z0-9_]+)', content))

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

def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".jsx": "react",
        ".ts": "typescript", ".tsx": "react-typescript",
        ".json": "json", ".html": "html", ".css": "css",
        ".md": "markdown", ".txt": "text"
    }
    return mapping.get(ext, "unknown")

# ===
# Chunk分割ロジック
# ===

def split_text_into_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    text = normalize_text(text)
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks

def split_code_into_chunks(code: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    code = normalize_text(code)
    lines = code.split("\n")
    chunks, current_chunk = [], []
    current_size = 0

    for line in lines:
        current_chunk.append(line)
        current_size += len(line)

        # 関数/class付近で区切る。または、巨大すぎる場合は強制的に区切る（安全装置）
        is_boundary = line.strip().startswith(("def ", "class ", "function ", "export default"))
        is_too_large = current_size >= (chunk_size * 1.5)

        if current_size >= chunk_size and (is_boundary or is_too_large):
            chunks.append("\n".join(current_chunk))
            current_chunk, current_size = [], 0

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

# ===
# Chunk生成・保存
# ===

def build_chunks_from_file(file_path: str) -> List[Dict[str, Any]]:
    if not is_supported_file(file_path): return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    metadata = extract_metadata(file_path, content)
    language = metadata["language"]

    if language in ["python", "javascript", "react", "typescript", "react-typescript"]:
        raw_chunks = split_code_into_chunks(content)
    else:
        raw_chunks = split_text_into_chunks(content)

    return [{
        "id": str(uuid.uuid4()),
        "file_path": file_path,
        "file_name": metadata["file_name"],
        "language": language,
        "chunk_index": idx,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": metadata,
        "content": chunk_text
    } for idx, chunk_text in enumerate(raw_chunks)]

def save_chunks(chunks: List[Dict[str, Any]], project_name: str = "default_project"):
    output_dir = os.path.join(CHUNK_OUTPUT_DIR, project_name)
    os.makedirs(output_dir, exist_ok=True)
    
    for chunk in chunks:
        output_path = os.path.join(output_dir, f"{chunk['id']}.json")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    # 新しく保存した場合はキャッシュをクリアして再読み込みを促す
    if project_name in _chunk_cache:
        del _chunk_cache[project_name]

def build_chunks_from_directory(target_dir: str, project_name: str = "default_project") -> List[Dict[str, Any]]:
    all_chunks = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ["__pycache__", "node_modules", ".git", "dist", "build", "venv", ".venv"]]
        for file in files:
            file_path = os.path.join(root, file)
            if is_supported_file(file_path):
                all_chunks.extend(build_chunks_from_file(file_path))

    save_chunks(all_chunks, project_name)
    print(f"🧠 Chunk生成完了: {len(all_chunks)} chunks")
    return all_chunks

# ===
# 爆速Chunk検索（キャッシュ対応）
# ===

def search_chunks_by_keyword(keyword: str, project_name: str = "default_project") -> List[Dict[str, Any]]:
    project_dir = os.path.join(CHUNK_OUTPUT_DIR, project_name)
    if not os.path.exists(project_dir): return []

    # キャッシュに存在しない場合は、全JSONを読み込んでメモリにキャッシュする
    if project_name not in _chunk_cache:
        print(f"📦 [Cache Miss] {project_name} のChunkをメモリにロードします...")
        loaded_chunks = []
        for filename in os.listdir(project_dir):
            if filename.endswith(".json"):
                path = os.path.join(project_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded_chunks.append(json.load(f))
                except Exception:
                    pass
        _chunk_cache[project_name] = loaded_chunks

    # メモリ上から検索（爆速）
    results = []
    keyword_lower = keyword.lower()
    for chunk in _chunk_cache[project_name]:
        if keyword_lower in chunk["content"].lower():
            results.append(chunk)

    return results

# ===
# ChunkManager Class Wrapper
# ===

class ChunkManager:

    def chunk_file(
        self,
        file_path: str,
        content: str,
        language: str = "text"
    ):
        metadata = extract_metadata(file_path, content)

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

        chunks = []

        for idx, chunk_text in enumerate(raw_chunks):
            chunks.append({
                "id": str(uuid.uuid4()),
                "file_path": file_path,
                "file_name": metadata["file_name"],
                "language": language,
                "chunk_index": idx,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "metadata": metadata,
                "content": chunk_text
            })

        return chunks