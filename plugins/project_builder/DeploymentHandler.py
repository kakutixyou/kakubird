# To\plugins\project_builder\Deploymenthandler.py
import os
import re
import json
import logging
import traceback
import hashlib
import shutil
from datetime import datetime
from typing import Any, Optional, Tuple, List, Dict

# ※ご自身の環境に合わせてインポートパスは調整してください
from .base_handler import BaseHandler
from api.services.inspectors.IntentInSpector import IntentInspector

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEPLOYMENT_COMMANDS = {"/deploy", "/deployment", "/project"}

class DeploymentHandler(BaseHandler):
    def __init__(self, base_dir=".", backup_existing=True):
        # Inspectorから受け取ったメタデータ
        self.detected_surface: Optional[str] = None
        self.detected_theme: Optional[str] = None
        
        # ファイル書き込み用の設定
        self.base_dir = os.path.abspath(base_dir)
        self.backup_existing = backup_existing

    # ==========================================
    # 1. ユーティリティ & ルーティング処理
    # ==========================================
    def _get_text(self, message: Any) -> str:
        """安全にテキストを抽出するヘルパー"""
        if isinstance(message, str):
            return message
        for attr in ["text", "content", "body", "message"]:
            if hasattr(message, attr):
                val = getattr(message, attr)
                if isinstance(val, str):
                    return val
        return str(message)

    def estimate_size(self, message: Any) -> int:
        msg_str = self._get_text(message)
        if "projectのみ" in msg_str:
            return 3000
        return 15000

    async def can_handle(self, message: Any) -> bool:
        msg_str = self._get_text(message).lower()
        if any(msg_str.startswith(cmd) for cmd in DEPLOYMENT_COMMANDS):
            return True
        keywords = ["deploy", "deployment", "project", "builder", "handler", "analyzer", "フォルダ構成", "root/"]
        return any(k in msg_str for k in keywords)

    async def calculate_score(self, message: Any, signals=None) -> int:
        msg_str = self._get_text(message)
        msg_lower = msg_str.strip().lower()

        if any(msg_lower.startswith(cmd) for cmd in DEPLOYMENT_COMMANDS):
            print("🎯 [DeploymentHandler] デプロイコマンドを検知: 100点を返却します", flush=True)
            return 100

        force_keywords = ["フォルダ構成", "フォルダー構成", "ディレクトリ構造", "ts_layer", "set.py", "空箱で構成", "root/", "├──", "└──"]
        if any(k in msg_lower for k in force_keywords):
            # 🔥 修正ポイント: 95点ではなく、絶対に他が勝てない 200点 を返すようにしました
            print("🎯 [DeploymentHandler] 強制キーワード(ツリー構造)を検知: 絶対優先の 200点 を返却します", flush=True)
            return 200

        inspector = IntentInspector(msg_str)
        analysis = inspector.inspect()

        if analysis["mode"] == "deployment":
            self.detected_surface = analysis.get("deployment_surface")
            self.detected_theme = analysis.get("deployment_theme")
            return analysis["score"]

        return 0

    # ==========================================
    # 2. ファイル書き込みエンジン
    # ==========================================
    def _safe_join_path(self, relative_path: str) -> str:
        """ディレクトリトラバーサルを防ぐ安全なパス結合"""
        normalized_rel_path = relative_path.replace("\\", "/").strip("/")
        target_path = os.path.abspath(os.path.join(self.base_dir, normalized_rel_path))
        if not target_path.startswith(self.base_dir):
            raise ValueError(f"不正なファイルパス: {relative_path}")
        return target_path

    def write_file(self, relative_path: str, content: str) -> bool:
        """単一ファイルの書き出し（差分チェック・バックアップ対応）"""
        try:
            target_path = self._safe_join_path(relative_path)
            parent_dir = os.path.dirname(target_path)
            
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            if os.path.exists(target_path):
                new_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
                with open(target_path, 'rb') as f:
                    old_hash = hashlib.md5(f.read()).hexdigest()
                
                if new_hash == old_hash:
                    return True # 変更なしスキップ
                
                if self.backup_existing:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    shutil.copy2(target_path, f"{target_path}.{timestamp}.bak")

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"保存完了: {target_path}")
            return True
        except Exception as e:
            logger.error(f"保存エラー ({relative_path}): {str(e)}")
            return False

    # ==========================================
    # 3. 最強ツリーパーサー
    # ==========================================
    def _parse_tree_to_dict(self, text: str) -> dict:
        """
        会話文を無視し、絵文字(📁)や階層(├──)から深さを測定して完全な辞書を生成する最強パーサー
        """
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        parsed = []
        
        # パス1: 行ごとの深さと名前を抽出
        for line in lines:
            line = line.split('#')[0].rstrip()
            if '```' in line or not line.strip(): 
                continue
            
            # ツリー記号や空白のプレフィックスと、ファイル名部分を分離
            match = re.match(r'^([\s│├└─]*)(?:📁\s*)?(.*)$', line)
            if not match: 
                continue
            
            prefix, name = match.groups()
            name = name.strip()
            if not name: 
                continue
            
            # ディレクトリかどうかの判定 (📁アイコンがあるか、末尾が / か)
            # ※今回のようにいきなりディレクトリから始まるケースも考慮
            is_dir = "📁" in line or name.endswith("/") or name.startswith("📁")
            name = name.replace("📄", "").replace("📁", "").strip().rstrip("/")
            
            # プレフィックスの文字数をそのまま深さ（インデント量）とする
            depth = len(prefix)
            parsed.append({"depth": depth, "name": name, "is_dir": is_dir})

        if not parsed: 
            return {}

        # パス2: 論理的な階層(0, 1, 2...)に正規化
        unique_depths = sorted(list(set(p['depth'] for p in parsed)))
        depth_map = {d: i for i, d in enumerate(unique_depths)}

        structure = {}
        path_stack = []

        # パス3: ディレクトリ構造の辞書に変換
        for p in parsed:
            logical_depth = depth_map[p['depth']]
            name = p['name']
            
            # 現在の深さに合わせてスタックを切り詰める（親ディレクトリに戻る処理）
            path_stack = path_stack[:logical_depth]
            
            # 次の要素が自分より深い位置にあるかチェックして、ディレクトリ判定を補強
            is_folder = p['is_dir']
            current_index = parsed.index(p)
            if current_index + 1 < len(parsed):
                next_p = parsed[current_index + 1]
                if depth_map[next_p['depth']] > logical_depth:
                    is_folder = True

            if is_folder:
                path_stack.append(name)
                full_path = "/".join(path_stack)
                if full_path not in structure:
                    structure[full_path] = []
            else:
                parent_path = "/".join(path_stack) if path_stack else "."
                if parent_path not in structure:
                    structure[parent_path] = []
                structure[parent_path].append(name)

        return structure

    # ==========================================
    # 4. メイン処理
    # ==========================================
    async def handle(self, message: Any) -> Tuple[str, Any]:
        print("⚡ [DeploymentHandler] 新型アルゴリズムでツリーをパースします！", flush=True)
        msg_str = self._get_text(message)
        
        try:
            # 会話文やノイズを無視して、いきなり綺麗な辞書を作る
            folders_dict = self._parse_tree_to_dict(msg_str)
            
            if not folders_dict:
                return "text", "⚠️ ツリー構造を検出できませんでした。罫線(├──)やインデントを含むフォーマットか確認してください。"
            
            # set.py のコード生成
            set_py_code = f"""# set.py
import os

def init_structure():
    base_path = os.getcwd()
    print(f"📁 Initializing empty boxes under: {{base_path}}")
    
    structure = {repr(folders_dict)}
    
    for folder, files in structure.items():
        if folder == ".":
            target_dir = base_path
        else:
            target_dir = os.path.join(base_path, folder.replace("/", os.sep))
            
        os.makedirs(target_dir, exist_ok=True)
        
        for f in files:
            file_path = os.path.join(target_dir, f)
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write("")
                print(f"  📄 Created Empty: {{os.path.relpath(file_path, base_path)}}")

    print("\\n✅ Setup Completed successfully!")

if __name__ == "__main__":
    init_structure()
"""

            response_message = (
                f"どんな形式からでもフォルダツリーをダイレクトに再構築しました！\n"
                f"以下のコードを `set.py` として保存し実行することで、空箱で一括構成できます。\n\n"
                f"```python\n{set_py_code}\n```"
            )
            
            # フロント側のUIブロックエラーを防ぐため、安全にテキストとして返す
            return "text", response_message

        except Exception as e:
            traceback.print_exc()
            return "text", f"解析中にエラーが発生しました: {str(e)}"