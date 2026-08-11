# backend/engine/context/ContextManager.py
import os
import json
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

@dataclass
class RoutingState:
    current_mode: str = "unknown"

@dataclass
class Workspace:
    current_code: Optional[str] = None
    active_artifact_name: str = "app.py"
    version: int = 1

@dataclass
class ChatMessage:
    role: str
    content: str

@dataclass
class MemoryLayer:
    history: List[ChatMessage] = field(default_factory=list)

@dataclass
class UserPreferences:
    global_theme: Optional[str] = None
    is_responsive_default: bool = False

class ContextManager:
    def __init__(self, session_id: str = "default_session", persist_dir: str = "./sessions"):
        self.session_id = session_id
        self.persist_dir = persist_dir
        
        self.routing = RoutingState()
        self.workspace = Workspace()
        self.memory = MemoryLayer()
        self.prefs = UserPreferences()
        
        # 新設: 現在発生しているエラー情報を保持する変数
        self.current_error: Optional[Dict[str, Any]] = None

        if not os.path.exists(self.persist_dir):
            os.makedirs(self.persist_dir, exist_ok=True)

    def set_syntax_error(self, error_dict: Dict[str, Any]):
        """エラー情報を記録し、モードを「自己修復（code_healing）」に切り替える"""
        self.current_error = error_dict
        self.routing.current_mode = "code_healing"

    def clear_error(self):
        """修復が完了したらエラー情報をクリアする"""
        self.current_error = None
        self.routing.current_mode = "unknown"

    def add_chat_history(self, role: str, content: str):
        """チャット履歴を追加する"""
        self.memory.history.append(ChatMessage(role=role, content=content))

    def apply_inspector_result(self, inspect_result: Dict[str, Any]):
        """Inspector の解析結果をコンテキストに反映させる"""
        self.routing.current_mode = inspect_result.get("mode", "unknown")
        
        # UIテーマやレスポンシブフラグが解析されれば反映
        if inspect_result.get("theme"):
            self.prefs.global_theme = inspect_result["theme"]
        if "responsive" in inspect_result:
            self.prefs.is_responsive_default = inspect_result["responsive"]

    def save_state(self):
        """現在のコンテキスト情報をJSONファイルに永続化する"""
        filepath = os.path.join(self.persist_dir, f"{self.session_id}.json")
        state = {
            "history": [asdict(msg) for msg in self.memory.history],
            "current_mode": self.routing.current_mode,
            "current_error": self.current_error,
            "current_code": self.workspace.current_code,
            "active_artifact_name": self.workspace.active_artifact_name,
            "version": self.workspace.version
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ 状態の保存に失敗しました: {e}")

    def get_prompt_signals(self) -> Dict[str, Any]:
        """AIプロンプト用の状態信号を辞書で返す"""
        signals = {
            "active_mode": self.routing.current_mode,
            "theme": self.prefs.global_theme,
            "responsive": self.prefs.is_responsive_default,
            "recent_history": [asdict(msg) for msg in self.memory.history[-3:]],
            "error_info": self.current_error  # シグナルにエラー情報を追加
        }
        
        if self.workspace.current_code:
            signals["active_context"] = f"現在 '{self.workspace.active_artifact_name}' (v{self.workspace.version}) を編集しています。"
            signals["base_code"] = self.workspace.current_code

        return signals