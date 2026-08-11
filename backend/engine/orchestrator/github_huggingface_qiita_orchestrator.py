# backend/engine/orchestrator/github_huggingface_qiita_orchestrator.py
print("🐙 ScrapingOrchestrator が初期化されました", flush=True)

import time
import logging
from typing import Any, Tuple, Optional

# ベースクラスと型定義
from engine.orchestrator.base_orchestrator import BaseOrchestrator
from api.services.inspectors.IntentInSpector import IntentInspector

# スクレイピング特化のエンジン・コレクター群
from collectors.github_collector import GitHubCollector
from collectors.huggingface_collector import HuggingFaceCollector
from collectors.qiita_collector import QiitaCollector
from analyzers.terminal_engine import TerminalEngine

logger = logging.getLogger(__name__)

class GithubHuggingfaceQiitaOrchestrator(BaseOrchestrator):
    """
    GitHub, HuggingFace, Qiita 等のスクレイピング・データ収集に特化したオーケストレーター
    （IntentInspectorとKnowledgeRouterによってルーティングされた場合にのみ起動する）
    """
    def __init__(self, project_root=None, config=None, services=None):
        super().__init__(project_root=project_root, config=config, services=services)
        
        # コレクターの初期化
        self.github_collector = GitHubCollector()
        self.hf_collector = HuggingFaceCollector()
        self.qiita_collector = QiitaCollector()
        
        # 抽出・整形用のエンジン（RAGモードなどで使用）
        self.terminal_engine = TerminalEngine()
        
        # このオーケストレーターの得意分野を定義（IntentInspectorから引き継ぎやすいように）
        self.supported_sources = ["github", "huggingface", "qiita"]
        self.last_used_source = None

    async def handle(self, request: Any) -> Optional[Tuple[str, Any]]:
        """
        メイン処理：リクエストからターゲットを特定し、適切なコレクターを動かす
        """
        self.request = request
        self.message = request.message
        
        logger.info(f"🔍 [ScrapingOrchestrator] 処理開始: {self.message}")
        
        # 1. ターゲットソースの特定
        target_source, query, purpose = self._parse_request(self.message)
        
        if not target_source:
            return "text", "対象となるソース(GitHub, HuggingFace, Qiita)が指定されていません。"
            
        self.last_used_source = target_source
        collected_data = {}
        start_time = time.time()
        
        # 2. データ収集 (Step 1)
        try:
            logger.info(f"📥 [{target_source.upper()}] データの収集を開始します: query={query}")
            if target_source == "github":
                collected_data = self.github_collector.collect(query)
            elif target_source == "huggingface":
                collected_data = self.hf_collector.collect(query)
            elif target_source == "qiita":
                collected_data = self.qiita_collector.collect(query)
                
            collection_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ データ収集完了 ({collection_time}ms): {len(collected_data)}件の主要要素を取得")
            
        except Exception as e:
            error_msg = f"データ収集中にエラーが発生しました: {str(e)}"
            logger.error(f"❌ [ScrapingOrchestrator] {error_msg}")
            return "text", self._create_error_response(error_msg)

        # 3. データの整形・抽出 (RAG用データ抽出モード)
        # ※ ここでは複雑なAnalyzer（LicenseEngine等）は削ぎ落とし、
        #    取得したデータをLLM（TerminalEngine）で学習用・回答用に整形することに集中します
        try:
            formatted_result = self._process_collected_data(target_source, query, purpose, collected_data)
            return "text", formatted_result
            
        except Exception as e:
            error_msg = f"データの整形・解析中にエラーが発生しました: {str(e)}"
            logger.error(f"❌ [ScrapingOrchestrator] {error_msg}")
            return "text", self._create_error_response(error_msg)

    def _parse_request(self, message: str) -> Tuple[Optional[str], str, str]:
        """
        メッセージから「どのソースか」「何を検索/取得するか」「目的は何か」を抽出する簡易パーサー
        ※本来は IntentInspector が行う部分ですが、このオーケストレーター内で完結させるためのヘルパー
        """
        msg_lower = message.lower()
        target_source = None
        
        if "github" in msg_lower or "リポジトリ" in msg_lower:
            target_source = "github"
        elif "huggingface" in msg_lower or "モデル" in msg_lower and "hf" in msg_lower:
            target_source = "huggingface"
        elif "qiita" in msg_lower or "記事" in msg_lower:
            target_source = "qiita"
            
        # 簡易的なクエリ抽出 (実際の運用では正規表現等でもっと賢く抜く)
        # URLが含まれていればそれを最優先とする
        import re
        url_match = re.search(r'https?://[^\s]+', message)
        if url_match:
            query = url_match.group(0)
        else:
            query = message # URLがない場合はメッセージ全体を検索キーワードとする
            
        # 目的はメッセージ全体
        purpose = message
            
        return target_source, query, purpose

    def _process_collected_data(self, target_source: str, query: str, purpose: str, collected: dict) -> dict:
        """
        収集した生データをTerminalEngineに渡し、見やすい形（JSONやMarkdown）に抽出・整形する
        """
        content_text = ""
        
        if target_source == "github":
            essential_files = (
                collected.get("license_files", {})
                | collected.get("dependency_files", {})
            )
            # 全ソースコードを渡すとトークン爆発するため、主要なものだけ
            source_files = collected.get("source_files", {})
            tree_str = "\n".join(collected.get("file_tree", []))
            
            # 簡易的なファイル結合
            files_content = "\n".join([f"--- {k} ---\n{v[:1000]}" for k, v in list(source_files.items())[:5]])
            
            content_text = f"【リポジトリマップ】\n{tree_str}\n\n【主要ファイル】\n{files_content}"
            
        elif target_source == "qiita":
            articles = collected.get("high_value_articles", [])
            content_text = "\n\n---\n\n".join(
                [a.get("full_body", a.get("body_preview", "")) for a in articles]
            )
        else:
            # HuggingFace 等
            content_text = str(collected)[:2000]

        # TerminalEngine で抽出処理
        terminal_result = self.terminal_engine.analyze(
            item_dict={
                "name": query,
                "description": purpose,
                "content": content_text,
            }
        )
        
        # 抽出したマークダウンテキストを取得
        extracted_markdown = getattr(terminal_result, "raw_markdown_text", "")
        if not extracted_markdown:
             # TerminalEngineの出力構造に合わせてフォールバック
             extracted_markdown = f"データの取得に成功しました。\n\n```json\n{str(terminal_result)}\n```"

        return {
            "message": f"{target_source.upper()} からのデータ抽出が完了しました。",
            "blocks": [
                {
                    "type": "MarkdownBlock",
                    "props": {
                        "content": extracted_markdown
                    }
                }
            ]
        }
        
    def _create_error_response(self, msg: str) -> dict:
        return {
            "message": "スクレイピング処理中にエラーが発生しました。",
            "blocks": [
                 {
                    "type": "MarkdownBlock",
                    "props": {
                        "content": f"**Error:**\n{msg}"
                    }
                }
            ]
        }