import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class ProjectStateManager:
    def __init__(self, state_file_path: str = "current_signals.json"):
        self.state_file_path = state_file_path

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_file_path):
            return self._get_default_state()
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[StateManager] Warning: {self.state_file_path} was corrupted. Initializing state.")
        return self._get_default_state()

    def _get_default_state(self) -> Dict[str, Any]:
        return {
        "active_app_key": None,
        "project_path": None,
        "generated_files": [],
        "history": []
        }

    def save_state(self, state: Dict[str, Any]):

        with open(self.state_file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def update_active_app(self, app_key: str, project_path: str, files: List[str], user_prompt: str = ""):
  
        state = self.load_state()
        state["active_app_key"] = app_key
        state["project_path"] = project_path

        # すでに記録されているファイルとマージ（重複排除）
        current_files = set(state.get("generated_files", []))
        current_files.update(files)
        state["generated_files"] = list(current_files)

        # 履歴の追加 (いつ、何のために、何のファイルを操作したか)
        history_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_prompt": user_prompt,
        "app_key": app_key,
        "files_written": files
        }
        if "history" not in state:
            state["history"] = []
            state["history"].append(history_entry)

        self.save_state(state)
        print(f"[StateManager] State updated for app '{app_key}'. Active files: {len(state['generated_files'])}")

    def get_active_app_key(self) -> Optional[str]:
    
        return self.load_state().get("active_app_key")

    def get_project_path(self) -> Optional[str]:
        return self.load_state().get("project_path")

    def clear_state(self):
        """プロジェクトを完全にまっさらにリセットしたいときに呼び出す"""
        self.save_state(self._get_default_state())
        print("[StateManager] Project state cleared.")