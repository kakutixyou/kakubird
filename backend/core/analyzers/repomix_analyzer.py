# repomix_analyzer.py
import xml.etree.ElementTree as ET
import json
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

# 作成済みの KnowledgeManager をインポート（※パスは実際の環境に合わせてください）
from api.services.manager.KnowledgeManager import KnowledgeManager

logger = logging.getLogger(__name__)

# ===
# 1. 基底クラスの定義 (インターフェース)
# ===
class BaseAnalyzer(ABC):
    """すべてのアナライザーの雛形となる抽象基底クラス"""
    
    @abstractmethod
    def can_handle(self, file_path: str, ext: str) -> bool:
        """このファイルをご自身（アナライザー）が処理可能か判定する"""
        pass

    @abstractmethod
    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        """実際の解析処理を行い、内部状態に蓄積する"""
        pass

    @abstractmethod
    def get_export_data(self) -> Optional[Dict[str, Any]]:
        """KnowledgeManagerに渡すための保存データを返す
        戻り値の形式: {"filename": "出力ファイル名.json", "content": {出力する辞書データ}}
        """
        pass

# ===
# 2. 個別アナライザーの実装 (プラグイン)
# ===
class ComponentAnalyzer(BaseAnalyzer):
    def __init__(self):
        self.data = {"name": "Components List", "description": "UIコンポーネントの一覧", "items": {}}

    def can_handle(self, file_path: str, ext: str) -> bool:
        return ext in [".tsx", ".jsx", ".ts", ".vue"] and "components" in file_path

    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        self.data["items"][file_path] = {"lines": line_count}

    def get_export_data(self) -> Optional[Dict[str, Any]]:
        if not self.data["items"]:
            return None
        return {"filename": "components.json", "content": self.data}


class ApiAnalyzer(BaseAnalyzer):
    def __init__(self):
        self.data = {"name": "API Routes", "description": "バックエンドのAPIエンドポイント一覧", "items": {}}

    def can_handle(self, file_path: str, ext: str) -> bool:
        return ext == ".py" and "api/routes" in file_path

    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        self.data["items"][file_path] = {"lines": line_count}

    def get_export_data(self) -> Optional[Dict[str, Any]]:
        if not self.data["items"]:
            return None
        return {"filename": "api_routes.json", "content": self.data}


class ArchitectureAnalyzer(BaseAnalyzer):
    def __init__(self):
        self.data = {"name": "Project Architecture", "description": "プロジェクト全体のファイル構成", "files": []}

    def can_handle(self, file_path: str, ext: str) -> bool:
        # すべてのファイルを対象とする
        return True

    def analyze(self, file_path: str, ext: str, content: str, line_count: int) -> None:
        self.data["files"].append({"path": file_path, "type": ext})

    def get_export_data(self) -> Optional[Dict[str, Any]]:
        if not self.data["files"]:
            return None
        return {"filename": "architecture.json", "content": self.data}

# ===
# 3. オーケストレーター (メインロジック)
# ===
class RepomixAnalyzer:
    def __init__(self, base_dir: str = "."):
        self.manager = KnowledgeManager(base_dir=base_dir)
        
        # 🧩 ここに使用するアナライザーを登録する
        self.analyzers: List[BaseAnalyzer] = [
            ComponentAnalyzer(),
            ApiAnalyzer(),
            ArchitectureAnalyzer()
            # 新しいアナライザー（TodoAnalyzer等）を作成したらここに追加するだけ
        ]

    def analyze_and_split(self, xml_path: str = "repomix-output.xml", output_dir: str = "backend/engine/knowledge/project_data") -> bool:
        if not os.path.exists(xml_path):
            logger.error(f"❌ XMLファイルが見つかりません: {xml_path}")
            return False

        logger.info(f"🚀 {xml_path} の解析を開始します...")

        try:
            # ET.iterparseで巨大なXMLでも省メモリで処理
            context = ET.iterparse(xml_path, events=("end",))
            for event, elem in context:
                if elem.tag == "file":
                    file_path = elem.get("path")
                    content = elem.text or ""
                    
                    if not file_path:
                        elem.clear() # メモリ解放
                        continue
                        
                    ext = os.path.splitext(file_path)[1].lower()
                    line_count = len(content.splitlines())

                    # 🔄 登録された全アナライザーに処理を打診する
                    for analyzer in self.analyzers:
                        if analyzer.can_handle(file_path, ext):
                            analyzer.analyze(file_path, ext, content, line_count)

                    # 処理が終わった要素をメモリから破棄（巨大XML対応のキモ）
                    elem.clear()

        except Exception as e:
            logger.error(f"❌ XMLの解析中にエラーが発生しました: {e}")
            return False

        # 💾 各アナライザーから結果を回収して KnowledgeManager で一括保存
        files_to_save = []
        for analyzer in self.analyzers:
            export_data = analyzer.get_export_data()
            if export_data:
                files_to_save.append({
                    "path": f"{output_dir}/{export_data['filename']}",
                    "content": json.dumps(export_data['content'], ensure_ascii=False, indent=2)
                })

        if not files_to_save:
            logger.warning(" 保存するデータがありませんでした。")
            return False

        result = self.manager.write_from_json_data(files_to_save)
        
        if result.get("failed"):
            logger.warning(f" 一部のファイル保存に失敗しました: {result['failed']}")
        else:
            logger.info(f"🎉 解析完了！ {output_dir} に分割JSONを保存しました。")
            
        return True

# ===
# 動作テスト用エントリーポイント
# ===
if __name__ == "__main__":
    # ログの基本設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    analyzer = RepomixAnalyzer()
    analyzer.analyze_and_split(xml_path="repomix-output.xml")