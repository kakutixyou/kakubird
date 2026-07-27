from __future__ import annotations

import fnmatch
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

# -----------------------------------------------------
# データモデル (本来は .models から import する部分)
# -----------------------------------------------------
@dataclass
class FileInfo:
    path: str
    absolute_path: str
    language: str
    size: int
    modified_at: datetime
    sha256: str

# -----------------------------------------------------
# 定数定義
# -----------------------------------------------------
DEFAULT_IGNORE_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules",
    "dist", "build", ".next", ".nuxt", ".venv", "venv", "env",
    ".pytest_cache", ".mypy_cache", "coverage", ".turbo", "vector_db"
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "platform.db", "platform.db-shm", "platform.db-wal"
}

SUPPORTED_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".json": "json",
    ".html": "html", ".css": "css", ".scss": "scss", ".sql": "sql",
    ".md": "markdown", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".sh": "shell",
}

# -----------------------------------------------------
# WorkspaceScanner クラス本体
# -----------------------------------------------------
class WorkspaceScanner:
    """
    プロジェクト全体を走査し、AIのコンテキスト用のツリー構造テキストや、
    ファイルの詳細情報（ハッシュ付き）を生成するクラス。
    """
    def __init__(
        self,
        root_path: str | Path | None = None,
        ignore_dirs: set[str] | None = None,
        ignore_files: set[str] | None = None,
        include_hidden: bool = False,
        max_file_size: int = 2 * 1024 * 1024,  # デフォルト 2MB制限
    ) -> None:
        # root_pathが指定されなければ、このファイルから見て3階層上(backend)をルートとする
        if root_path is None:
            self.root_path = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_path = Path(root_path).resolve()
            
        self.ignore_dirs = set(ignore_dirs or DEFAULT_IGNORE_DIRS)
        self.ignore_files = set(ignore_files or DEFAULT_IGNORE_FILES)
        self.ignore_exts = {'.pyc', '.sqlite', '.db', '.png', '.jpg'}
        self.include_hidden = include_hidden
        self.max_file_size = max_file_size

    # -----------------------------------------------------
    # 1. ツリー構造テキスト生成（プロンプト用）
    # -----------------------------------------------------
    def generate_tree_text(self) -> str:
        """AIのプロンプトに埋め込むためのツリー構造テキストを生成する"""
        if not self.root_path.exists():
            return "Error: Root path does not exist."
            
        tree_text = []
        
        def _walk(current_path: Path, prefix: str = ""):
            try:
                # フォルダ内のアイテムを取得し、ソートする（フォルダを上に）
                items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name))
                items = [i for i in items if i.name not in self.ignore_dirs]
                
                for index, item in enumerate(items):
                    is_last = (index == len(items) - 1)
                    connector = "└── " if is_last else "├── "
                    
                    if item.is_dir():
                        if not self.include_hidden and item.name.startswith("."):
                            continue
                        tree_text.append(f"{prefix}{connector}📁{item.name}")
                        extension = "    " if is_last else "│   "
                        _walk(item, prefix + extension)
                    elif item.is_file():
                        if item.suffix in self.ignore_exts or item.name in self.ignore_files:
                            continue
                        if not self.include_hidden and item.name.startswith(".") and item.name not in {".env", ".env.example"}:
                            continue
                        tree_text.append(f"{prefix}{connector}{item.name}")
            except PermissionError:
                pass
                
        tree_text.append(f"📁{self.root_path.name}")
        _walk(self.root_path)
        
        return "\n".join(tree_text)

    # -----------------------------------------------------
    # 2. ファイル詳細情報のスキャン（RAG / ベクトルDB用）
    # -----------------------------------------------------
    def scan(self) -> list[FileInfo]:
        """プロジェクト全体を走査し、FileInfoの一覧を返す"""
        if not self.root_path.exists() or not self.root_path.is_dir():
            raise FileNotFoundError(f"Workspace not found or not a directory: {self.root_path}")

        results: list[FileInfo] = []

        for path in self.root_path.rglob("*"):
            if not path.is_file():
                continue

            if self.should_ignore(path):
                continue

            try:
                info = self.build_file_info(path)
                if info:
                    results.append(info)
            except Exception:
                # 個別ファイルのエラー（権限など）で全体を止めない
                continue

        return sorted(results, key=lambda f: f.path)

    def should_ignore(self, path: Path) -> bool:
        relative = path.relative_to(self.root_path)

        for part in relative.parts:
            if part in self.ignore_dirs:
                return True
            if not self.include_hidden and part.startswith("."):
                if part not in {".env", ".env.example"}:
                    return True

        if path.name in self.ignore_files or path.suffix in self.ignore_exts:
            return True

        try:
            if path.stat().st_size > self.max_file_size:
                return True
        except OSError:
            return True

        return False

    def build_file_info(self, path: Path) -> FileInfo | None:
        stat = path.stat()
        language = SUPPORTED_EXTENSIONS.get(path.suffix.lower(), "text")

        return FileInfo(
            path=str(path.relative_to(self.root_path)).replace("\\", "/"),
            absolute_path=str(path),
            language=language,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            sha256=self.calculate_sha256(path),
        )

    def calculate_sha256(self, path: Path) -> str:
        sha = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

# -----------------------------------------------------
# 実行テスト用
# -----------------------------------------------------
if __name__ == "__main__":
    scanner = WorkspaceScanner()
    
    print("=== 1. プロジェクト構成スキャン結果 (プロンプト用) ===")
    print(scanner.generate_tree_text())
    
    print("\n=== 2. ファイル詳細取得テスト (最初の3件) ===")
    files = scanner.scan()
    for f in files[:3]:
        print(f"- {f.path} ({f.language}, {f.size} bytes) | SHA: {f.sha256[:8]}...")