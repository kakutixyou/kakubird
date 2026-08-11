# To(と)\backend\api\services\handlers\GitHandler.py
import json
import logging
import re
from pathlib import Path
from typing import Any
from api.services.inspectors.IntentInSpector import IntentInspector
# ロガーの設定（必要に応じてプロジェクトのログ設定に統合してください）
logger = logging.getLogger(__name__)

class GitHandler:
    def __init__(self):
            current_file = Path(__file__).resolve()
            # そこから目的のフォルダへのパスを繋ぐ
            self.knowledge_dir = current_file.parents[4] / "plugins" / "project_builder" / "knowledge" / "Git"
            # 初期化時にJSONファイルをメモリにロードしてキャッシュする（パフォーマンス向上）
            self.knowledge_base = self._load_knowledge()

    def _load_knowledge(self) -> list[dict[str, Any]]:
        """
        git_knowledgeフォルダ内のJSONを一度だけ読み込み、リストとして保持する
        """
        if not self.knowledge_dir.exists():
            logger.warning(f"[GitHandler] ナレッジフォルダが見つかりません: {self.knowledge_dir}")
            return []

        loaded_data = []
        # .json 拡張子のファイルをすべて取得
        for filepath in self.knowledge_dir.glob("*.json"):
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    loaded_data.append(json.load(f))
            except json.JSONDecodeError as e:
                logger.error(f"[GitHandler] JSONの形式エラー ({filepath.name}): {e}")
            except Exception as e:
                logger.error(f"[GitHandler] {filepath.name} の読み込みエラー: {e}")

        return loaded_data

    def handle(self, message: str) -> str:
        """
        メッセージを受け取り、IntentInspectorで解析後、適切なGitナレッジを返す
        """
        # 1. IntentInspectorを使ってメッセージを解析
        inspector = IntentInspector(message)
        intent = inspector.inspect()

        # 2. 抽出されたターゲットや、元のメッセージを取得（比較用に小文字化）
        search_keywords = intent.get("targets", [])
        raw_query = message.lower()

        # 3. ナレッジの検索
        results = self._search_knowledge(raw_query, search_keywords)

        # 4. 結果のフォーマット
        if not results:
            return "申し訳ありません。git_knowledge フォルダから関連する情報を見つけられませんでした。別のキーワードで試してみてください。"

        return self._format_response(results)

    def _search_knowledge(self, raw_query: str, extracted_targets: list[str]) -> list[dict[str, Any]]:
        """
        キャッシュされたナレッジから、キーワードに一致するものを探す（正規表現による厳密検索）
        """
        matched_data = []
        # 抽出されたターゲットを小文字化してSet（集合）にしておく（検索高速化のため）
        extracted_set = {target.lower() for target in extracted_targets}

        for data in self.knowledge_base:
            # JSON側のキーワードも全て小文字化
            json_keywords = {kw.lower() for kw in data.get("keywords", [])}
            
            # 条件1: JSONのキーワードがユーザーの質問(raw_query)に含まれているか
            is_in_query = False
            for kw in json_keywords:
                # 検索キーワードをエスケープ（記号を正規表現として解釈させないため）
                escaped_kw = re.escape(kw)
                
                # ASCII英数字・アンダースコア以外の文字で囲まれているかを判定する正規表現
                # これにより「logout」の誤爆を防ぎつつ、「git logを見たい」など日本語混じりにはマッチさせる
                pattern = rf"(?<![a-zA-Z0-9_]){escaped_kw}(?![a-zA-Z0-9_])"
                
                if re.search(pattern, raw_query):
                    is_in_query = True
                    break
            
            # 条件2: IntentInspectorが抽出したターゲットと、JSONキーワードに共通項があるか（積集合）
            is_target_match = bool(extracted_set & json_keywords)

            # どちらかの条件を満たせばマッチしたと判定
            if is_in_query or is_target_match:
                matched_data.append(data)

        return matched_data

    def _format_response(self, results: list[dict[str, Any]]) -> str:
        """
        見つかったJSONデータを、ユーザーに読みやすいマークダウン形式に整形する
        """
        response_lines = ["Gitのナレッジから以下の情報が見つかりました：\n"]
        
        for data in results:
            response_lines.append(f"### {data.get('name', '無題のナレッジ')}")
            response_lines.append(f"**概要**: {data.get('description', '')}\n")
            
            # 目的 (problem) の出力
            problem = data.get("problem", {})
            if isinstance(problem, dict) and "title" in problem:
                response_lines.append(f"> **目的**: {problem['title']}")
            
            # 解決手順 (solutions) の出力
            solutions = data.get("solutions", {})
            if isinstance(solutions, dict):
                for step_key, step_info in solutions.items():
                    if not isinstance(step_info, dict):
                        continue
                    
                    # Stepのタイトルと説明
                    response_lines.append(f"\n#### {step_key.capitalize()}: {step_info.get('title', '')}")
                    response_lines.append(step_info.get('description', ''))
                    
                    # コマンドの出力 (あれば)
                    commands = step_info.get('commands', [])
                    if commands:
                        response_lines.append("```bash")
                        for cmd in commands:
                            response_lines.append(cmd)
                        response_lines.append("```")
            
            # 複数のナレッジが見つかった場合の区切り線
            response_lines.append("\n---\n")

        return "\n".join(response_lines)
    