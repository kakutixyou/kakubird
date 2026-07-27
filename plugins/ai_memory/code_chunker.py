#code_chunker.py
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import CodeChunk


class CodeChunker:
    """
    ファイル内容を意味のある単位に分割する。
    MVP版:
      - Python: def / class
      - JS/TS/JSX/TSX: function / const xxx = / export
      - その他: 固定行数
    """

    def __init__(self, max_lines: int = 120) -> None:
        self.max_lines = max_lines

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def chunk_file(self, file_path: str, content: str, language: str) -> list[CodeChunk]:
        if language == "python":
            return self._chunk_python(file_path, content)

        if language in {"javascript", "typescript"}:
            return self._chunk_javascript(file_path, content)

        return self._chunk_generic(file_path, content)

    # --------------------------------------------------
    # Python
    # --------------------------------------------------

    def _chunk_python(self, file_path: str, content: str) -> list[CodeChunk]:
        pattern = re.compile(r"^(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
        return self._chunk_by_pattern(file_path, content, pattern)

    # --------------------------------------------------
    # JavaScript / TypeScript
    # --------------------------------------------------

    def _chunk_javascript(self, file_path: str, content: str) -> list[CodeChunk]:
        pattern = re.compile(
            r"""^(
                export\s+default\s+function\s+([A-Za-z_][A-Za-z0-9_]*)|
                export\s+function\s+([A-Za-z_][A-Za-z0-9_]*)|
                function\s+([A-Za-z_][A-Za-z0-9_]*)|
                const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(async\s*)?\(
            )""",
            re.MULTILINE | re.VERBOSE,
        )
        return self._chunk_by_pattern(file_path, content, pattern)

    # --------------------------------------------------
    # Generic
    # --------------------------------------------------

    def _chunk_generic(self, file_path: str, content: str) -> list[CodeChunk]:
        lines = content.splitlines()
        chunks: list[CodeChunk] = []

        for i in range(0, len(lines), self.max_lines):
            start = i + 1
            end = min(i + self.max_lines, len(lines))
            text = "\n".join(lines[i:end])

            chunks.append(
                self._create_chunk(
                    file_path=file_path,
                    symbol=f"chunk_{start}_{end}",
                    start_line=start,
                    end_line=end,
                    content=text,
                )
            )

        return chunks

    # --------------------------------------------------
    # Pattern-based chunking
    # --------------------------------------------------

    def _chunk_by_pattern(self, file_path: str, content: str, pattern: re.Pattern) -> list[CodeChunk]:
        matches = list(pattern.finditer(content))
        lines = content.splitlines()

        if not matches:
            return self._chunk_generic(file_path, content)

        chunks: list[CodeChunk] = []

        for index, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[index + 1].start() if index + 1 < len(matches) else len(content)

            chunk_text = content[start_pos:end_pos].strip("\n")

            start_line = content[:start_pos].count("\n") + 1
            end_line = start_line + chunk_text.count("\n")

            symbol = self._extract_symbol(match)

            chunks.append(
                self._create_chunk(
                    file_path=file_path,
                    symbol=symbol,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_text,
                )
            )

        return chunks

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _extract_symbol(self, match: re.Match) -> str | None:
        for group in match.groups():
            if isinstance(group, str):
                name = group.strip()
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                    return name
        return None

    def _create_chunk(
        self,
        file_path: str,
        symbol: str | None,
        start_line: int,
        end_line: int,
        content: str,
    ) -> CodeChunk:
        raw_id = f"{file_path}:{symbol}:{start_line}:{end_line}"
        chunk_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()

        return CodeChunk(
            chunk_id=chunk_id, # type: ignore
            file_path=file_path,
            symbol=symbol,
            start_line=start_line,
            end_line=end_line,
            content=content,
            metadata={},
        )
        
        