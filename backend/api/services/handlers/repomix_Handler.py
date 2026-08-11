# repomix_handler.py
import os
import json
import asyncio
import importlib
import inspect
import xml.etree.ElementTree as ET
from typing import Tuple, Dict, Any, List

# 既存のベースクラスとManagerのインポート（※パスは環境に合わせてください）
from api.services.handlers.base_handler import BaseHandler
from api.services.manager.KnowledgeManager import KnowledgeManager
from core.analyzers.base_analyzer import BaseAnalyzer

class RepomixHandler(BaseHandler):
    def __init__(self, project_root: str = "."):
        super().__init__()
        
        # 🚨 プロジェクトルートのパス解決
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        self.resolved_root = os.path.abspath(os.path.join(current_file_dir, "../../../../"))
        if project_root and project_root != ".":
            self.resolved_root = os.path.abspath(project_root)

        print(f"🧠 [RepomixHandler] 初期化: ルートパス [{self.resolved_root}]")

        # ファイル書き出し用のManagerを初期化
        self.manager = KnowledgeManager(base_dir=self.resolved_root)
        
        # 保存先のディレクトリとXMLの場所を定義
        self.output_dir = "backend/engine/knowledge/project_data"
        self.xml_path = os.path.join(self.resolved_root, "repomix-output.xml")

        # 🔌 アナライザー（プラグイン）の動的ロードを実行
        self.analyzers = self._load_analyzers_dynamically()

    def _load_analyzers_dynamically(self) -> List[BaseAnalyzer]:
        """
        analyzerフォルダ内の.pyファイルをスキャンし、BaseAnalyzerを継承した
        クラスを自動で見つけてインスタンス化するメソッド。
        """
        analyzers_list = []
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # handlers フォルダから見て、analyzers フォルダへのパス（環境に合わせて調整）
        analyzers_dir = os.path.abspath(os.path.join(current_dir, "../analyzers"))
        package_name = "api.services.analyzers" 

        print(f"🔍 [Plugin] {analyzers_dir} からアナライザーを探索します...")

        if not os.path.exists(analyzers_dir):
            print(f"⚠️ [Plugin] アナライザーフォルダが見つかりません: {analyzers_dir}")
            return []

        for filename in os.listdir(analyzers_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"{package_name}.{module_name}"

                try:
                    module = importlib.import_module(module_path)
                    
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, BaseAnalyzer) and 
                            obj is not BaseAnalyzer and 
                            not inspect.isabstract(obj) and 
                            obj.__module__ == module_path):
                            
                            analyzers_list.append(obj())
                            print(f" 🔌 [Loaded] {name} ({filename})")
                            
                except Exception as e:
                    print(f" ❌ [Error] {filename} のロード中にエラーが発生しました: {e}")

        print(f"✅ [Plugin] 合計 {len(analyzers_list)} 個のアナライザーを起動しました。")
        return analyzers_list

    # =========================================================
    # 1. 意図の検知（スコア計算）
    # =========================================================
    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        msg_lower = message.lower()
        target_keywords = ["repomix", "xml", "全体コード", "プロジェクト解析", "知識更新", "構造を読み込んで"]
        if any(kw in msg_lower for kw in target_keywords):
            return 100
        return 0

    # =========================================================
    # 2. メイン処理（解析とJSON保存）
    # =========================================================
    async def handle(self, request) -> Tuple[str, Dict[str, Any]]:
        message = request.message
        print("\n🚀 [RepomixHandler] XMLの解析と知識の再構築を開始します...")

        if not os.path.exists(self.xml_path):
            error_msg = f"❌ `repomix-output.xml` が見つかりません。\nプロジェクトルート (`{self.xml_path}`) で `repomix` コマンドを実行してください。"
            return "text", {"message": error_msg}

        # --- A. 巨大なXMLのパース ---
        try:
            with open(self.xml_path, 'r', encoding='utf-8-sig') as f:
                raw_text = f.read()

            start_idx = raw_text.find('<')
            xml_content = raw_text[start_idx:] if start_idx != -1 else raw_text
            safe_xml_string = f"<root>\n{xml_content}\n</root>"
            root = ET.fromstring(safe_xml_string)
            
        except ET.ParseError as e:
            return "text", {"message": f"❌ XMLのパースに失敗しました: {e}"}

        # --- B. データの分類・抽出（完全自動化） ---
        file_count = 0
        for file_node in root.findall(".//file"):
            file_count += 1
            file_path = file_node.get("path", "")
            content = file_node.text or ""
            ext = os.path.splitext(file_path)[1].lower()
            line_count = len(content.splitlines())

            # 🚀 ロード済みの全アナライザーに判定＆処理を委譲
            for analyzer in self.analyzers:
                if analyzer.can_handle(file_path, ext):
                    analyzer.analyze(file_path, ext, content, line_count)

        # --- C. Managerを使って安全にJSON書き出し (非同期対応) ---
        saved_paths = []
        extracted_summary = {}

        for analyzer in self.analyzers:
            export_data = analyzer.get_export_data()
            if export_data:
                save_path = f"{self.output_dir}/{export_data['filename']}"
                
                await asyncio.to_thread(
                    self.manager.write_file,
                    save_path,
                    json.dumps(export_data['content'], ensure_ascii=False, indent=2)
                )
                
                saved_paths.append(save_path)
                
                # アイテム数（リストの長さ）をカウントしてログ・AI用に保持
                content_dict = export_data['content']
                item_count = len(content_dict.get('items', []) or content_dict.get('files', []))
                extracted_summary[export_data['filename']] = item_count

        # --- D. ユーザーへの完了報告とLLMへのコンテキスト引き継ぎ ---
        # 動的に抽出結果のメッセージを組み立てる
        summary_text = "\n".join([f"- 📄 **{k}**: `{v}` 件" for k, v in extracted_summary.items()])

        reply_msg = (
            f"🧠 **プロジェクト知識のアップデートが完了しました！**\n\n"
            f"巨大な `repomix-output.xml` を解析し、AI専用の辞書（JSON）に変換・保存しました。\n\n"
            f"- 📂 **解析した総ファイル数**: `{file_count}` ファイル\n"
            f"{summary_text}\n\n"
            f"データは `{self.output_dir}` 配下に安全に保存されました。次回の指示からこの最新知識を活用します！"
        )

        blocks = [
            {
                "type": "MarkdownChatBlock",
                "props": {"content": reply_msg}
            }
        ]

        # 💡 オーケストレーター(自律AI)が次の一手を考えるための「システム的な観察結果」
        system_observation = {
            "action": "ANALYZE_REPOMIX",
            "status": "success",
            "extracted_data": extracted_summary,
            "total_scanned_files": file_count,
            "saved_paths": saved_paths
        }

        return "ui_code", {
            "message": "知識のアップデートに成功しました。",
            "blocks": blocks,
            "system_observation": system_observation
        }