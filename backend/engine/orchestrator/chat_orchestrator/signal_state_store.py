"""
backend/engine/orchestrator/chat_orchestrator/signal_state_store.py

user_signals.json の読み書き、フィードバックボーナス取得、作成ファイル履歴の追跡、
および会話メモリ全消去（リセット）を担当するモジュール。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict


class SignalStateStore:
    """会話状態（Signals）とフィードバックファイルの永続化を管理する。"""

    FILE_REF_PATTERN = re.compile(r"(?:FILE|File|Path|path):\s*([a-zA-Z0-9_\-\.\/]+)")

    def __init__(self, memory_dir: str, signals_file: str, feedback_file: str) -> None:
        self.memory_dir = memory_dir
        self.signals_file = signals_file
        self.feedback_file = feedback_file
        os.makedirs(self.memory_dir, exist_ok=True)

    def save_signals(self, signals_data: Dict[str, Any]) -> None:
        try:
            with open(self.signals_file, "w", encoding="utf-8") as f_out:
                json.dump(signals_data, f_out, ensure_ascii=False, indent=4)
            print("📡 会話状態(Context)を更新しました。")
        except Exception as e:
            print(f"⚠️ 信号の保存に失敗: {e}")

    def get_current_signals(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception as e:
            print(f"⚠️ シグナル読み込み失敗: {e}")
        return {}

    def update_signals_with_created_files(self, assistant_text: str) -> None:
        files = self.FILE_REF_PATTERN.findall(assistant_text or "")
        if not files:
            return

        current_signals = self.get_current_signals()
        recent_files = current_signals.setdefault("recent_files", [])

        for file_path in files:
            clean_file = file_path.strip()
            if clean_file not in recent_files:
                recent_files.append(clean_file)

        current_signals["recent_files"] = recent_files[-5:]

        try:
            with open(self.signals_file, "w", encoding="utf-8") as f_out:
                json.dump(current_signals, f_out, ensure_ascii=False, indent=4)
            print(f"📡 Signals更新: {current_signals['recent_files']}")
        except Exception as e:
            print(f"⚠️ Signals保存失敗: {e}")

    def save_assistant_response_and_state(
        self,
        context_manager: Any,
        res_content: Any,
    ) -> None:
        try:
            assistant_text = ""
            if isinstance(res_content, dict):
                assistant_text = res_content.get("message", "")
                if "update_signals" in res_content:
                    self.save_signals(res_content["update_signals"])
            else:
                assistant_text = str(res_content)

            if assistant_text:
                context_manager.add_chat_history("assistant", assistant_text)

            self.update_signals_with_created_files(assistant_text)
            context_manager.save_state()
            print("💾 AIの記憶とステートを正常に更新しました。")
        except Exception as e:
            print(f"⚠️ 記憶の保存中にエラーが発生しました: {e}")

    def reset_all_memory(self, context_manager: Any) -> Dict[str, Any]:
        """
        1. user_signals.json (.ai_memory内)
        2. ContextManager の履歴・状態ファイル
        3. オンメモリの ConversationState
        のすべてを完全に初期化する。
        """
        try:
            from conversation.ConversationState import ConversationState
            empty_state = ConversationState().to_dict()
        except Exception:
            empty_state = {
                "mode": "chatbot",
                "turn_count": 0,
                "current_topic": None,
                "previous_topic": None,
                "current_intent": None,
                "previous_intent": None,
                "last_entity": None,
                "active_knowledge": [],
                "facts": {},
                "user_opinions": {},
                "project_context": {},
                "history": [],
                "summary": {},
                "error": None,
            }

        clean_signals = {
            "conversation_state": empty_state,
            "recent_files": [],
            "active_mode": "chatbot",
        }

        self.save_signals(clean_signals)

        try:
            clear_method = getattr(context_manager, "clear", None)
            reset_method = getattr(context_manager, "reset", None)
            if callable(clear_method):
                clear_method()
            elif callable(reset_method):
                reset_method()
            else:
                for attr in ("history", "chat_history", "messages"):
                    if hasattr(context_manager, attr):
                        setattr(context_manager, attr, [])
                state = getattr(context_manager, "state", None)
                reset_all = getattr(state, "reset_all", None)
                if callable(reset_all):
                    reset_all()
            if hasattr(context_manager, "save_state"):
                context_manager.save_state()
        except Exception as e:
            print(f"⚠️ [ChatOrchestrator] ContextManagerのリセット中に警告: {e}")

        try:
            if os.path.exists(self.memory_dir):
                for fname in os.listdir(self.memory_dir):
                    if fname.endswith(".json") and fname not in (
                        "knowledge_audit_cache.json",
                        "feedback_scores.json",
                        "user_signals.json",
                    ):
                        fpath = os.path.join(self.memory_dir, fname)
                        os.remove(fpath)
                        print(f"🗑️ [ChatOrchestrator] 記憶ファイルを削除: {fpath}")
        except Exception as e:
            print(f"⚠️ [ChatOrchestrator] メモリフォルダ掃除中に警告: {e}")

        print("🧹 [ChatOrchestrator] すべての会話メモリ・Project Contextを完全消去しました！")
        return clean_signals

    def get_feedback_bonus(self, handler_name: str) -> int:
        try:
            if not os.path.exists(self.feedback_file):
                return 0
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            bonus = data.get(handler_name, 0)
            return int(bonus)
        except Exception:
            return 0
