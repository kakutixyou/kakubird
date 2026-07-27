
# api/services/analyzers/todo_analyzer.py
import re
from typing import Dict, Any, Optional

# ※BaseAnalyzerのインポートパスは実際の環境に合わせて調整してください
from core.analyzers.base_analyzer import BaseAnalyzer

class TodoAnalyzer(BaseAnalyzer):
    def __init__(self):
        self.data = {
            "name": "Project TODOs",
            "description": "ソースコード内のTODOコメント一覧",
            "items": {}
        }
        # '#' または '//' の後に続く 'TODO:' を検知する正規表現 (大文字小文字を区別しない)
        self.todo_pattern = re.compile(r'(?:#|//)\s*TODO\s*:\s*(.*)', re.IGNORECASE)

    def can_handle(self, file_path: str, ext: str) -> bool:
        # Python, TypeScript, Reactなどのソースコードファイルのみを対象とする
        return ext in [".py", ".ts", ".tsx", ".js", ".jsx"]

    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        todos_in_file = []
        
        # 行ごとに分割してTODOを探す
        for line_num, line in enumerate(content.splitlines(), start=1):
            match = self.todo_pattern.search(line)
            if match:
                todos_in_file.append({
                    "line": line_num,
                    "task": match.group(1).strip()
                })
        
        # TODOが見つかったファイルのみ記録する
        if todos_in_file:
            self.data["items"][file_path] = todos_in_file

    def get_export_data(self) -> Optional[Dict[str, Any]]:
        # TODOが1件も見つからなかった場合はJSONを出力しない
        if not self.data["items"]:
            return None
        return {"filename": "todo_list.json", "content": self.data}