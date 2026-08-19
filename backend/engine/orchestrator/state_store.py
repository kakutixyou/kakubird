# backend/services/orchestrator/state_store.py

import os
import json
import re
from typing import Any

class ConversationStateStore:
    """
    AIの会話履歴、シグナル（文脈・状態）、および直近のファイル情報を管理するクラス。
    """
    def __init__(self, context_manager: Any, memory_dir: str = "backend/.ai_memory"):
        self.context_manager = context_manager
        self.memory_dir = memory_dir
        self.feedback_file = os.path.join(self.memory_dir, "feedback_scores.json")
        self.signals_file = os.path.join(self.memory_dir, "user_signals.json") 
        
        # 記憶ディレクトリが存在しない場合は作成
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir, exist_ok=True)

    def save_assistant_response_and_state(self, res_content: Any):
        """AIのレスポンス内容を解析し、履歴とシグナルを保存する"""
        try:
            assistant_text = ""
            if isinstance(res_content, dict):
                assistant_text = res_content.get("message", "")
                
                # ハンドラーから状態更新の要求があれば保存する
                if "update_signals" in res_content:
                    self.save_signals(res_content["update_signals"])
            else:
                assistant_text = str(res_content)

            # AIのテキストを会話履歴に追加
            if assistant_text:
                self.context_manager.add_chat_history("assistant", assistant_text)

            # ファイルパスが含まれていればシグナルを更新
            self._update_signals_with_created_files(assistant_text)
            
            # 全体のステートを保存
            self.context_manager.save_state()
            print("💾 AIの記憶とステートを正常に更新しました。")
        except Exception as e:
            print(f" 記憶の保存中にエラーが発生しました: {e}")

    def save_signals(self, signals_data: dict):
        """新しいシグナルデータをファイルに上書き保存する"""
        try:
            with open(self.signals_file, "w", encoding="utf-8") as f_out:
                json.dump(signals_data, f_out, ensure_ascii=False, indent=4)
            print("📡 会話状態(Context)を更新しました。")
        except Exception as e:
            print(f" 信号の保存に失敗しました: {e}")

    def get_current_signals(self) -> dict:
        """user_signals.jsonから現在のシグナル情報を読み込む。存在しない場合は空の辞書を返す。"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f" シグナルの読み込みに失敗しました: {e}")
        return {}

    def _update_signals_with_created_files(self, assistant_text: str):
        """AIが生成したテキストから『FILE: パス』を抽出し、直近で触ったファイルとして記憶に焼き付ける"""
        pattern = r"(?:FILE|File|Path|path):\s*([a-zA-Z0-9_\-\.\/]+)"
        files = re.findall(pattern, assistant_text)

        if files:
            current_signals = self.get_current_signals()
            recent_files = current_signals.setdefault("recent_files", [])

            for f in files:
                clean_file = f.strip()
                if clean_file not in recent_files:
                    recent_files.append(clean_file)

            # 直近5件のファイルのみ保持
            current_signals["recent_files"] = recent_files[-5:]

            try:
                with open(self.signals_file, "w", encoding="utf-8") as f_out:
                    json.dump(current_signals, f_out, ensure_ascii=False, indent=4)
                print(f"📡 信号(Signals)を更新しました: 最近のファイル={current_signals['recent_files']}")
            except Exception as e:
                print(f" 信号の保存に失敗しました: {e}")