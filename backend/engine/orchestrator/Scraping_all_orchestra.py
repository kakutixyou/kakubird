"""
Scraping_all_orchestra.py
====
スクレイピングジョブの総司令塔（バックグラウンドワーカー）

責務:
1. 対象URLからHTMLを取得し、ノイズを除去（BS4）
2. チャンク分割し、ChromaDB（ベクトルDB）へ保存
3. 自作AI向けに解析・蒸留し、KnowledgeRouter用のJSONを生成
4. 処理完了後、scraping_after_handler へ結果を引き継ぐ
"""
import asyncio
import os
import json
import asyncio
import traceback
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup
from typing import Dict, Any, List

# ─── 記憶システム関連 ──────────────────────────────────────
from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.vector_store import ChromaVectorStore
from plugins.ai_memory.embedding_service import EmbeddingService 

# ─── 知識統合アナライザー群 (これまでに設計したもの) ───────────
from core.analyzers.synthesis_analyzer import SynthesisAnalyzer
from core.analyzers.SemanticBuilderAnalyzer import SemanticBuilderAnalyzer
from core.analyzers.ContextDistillationAnalyzer import ContextDistillationAnalyzer

# ─── ファイル管理 ─────────────────────────────────────────
from api.services.manager.KnowledgeManager import KnowledgeManager

# ─── 事後処理ハンドラー ───────────────────────────────────
# from api.services.handlers.scraping_after_handler import ScrapingAfterHandler

"""
orchestrator/Scraping_all_orchestra.py
====
スクレイピングジョブの総司令塔（バックグラウンドワーカー）

責務:
1. 対象URLからHTMLを取得し、ノイズを除去（BS4）
2. チャンク分割し、ChromaDB（ベクトルDB）へ保存
3. 自作AI向けに解析・蒸留し、KnowledgeRouter用のJSONを生成
4. ファイルシステムへの保存
"""

class ScrapingAllOrchestra:
    def __init__(self):
        # 共有インスタンスの初期化
        self.vector_store = ChromaVectorStore()
        self.embedding_service = EmbeddingService()
        self.chunker = CodeChunker(max_lines=10)
        self.knowledge_manager = KnowledgeManager()
        
        # 自作AI向けアナライザーの初期化
        self.synthesis_analyzer = SynthesisAnalyzer()
        self.semantic_builder = SemanticBuilderAnalyzer()
        # 蒸留アナライザー (LLMのコンテキスト上限を考慮して設定)
        self.distillation_analyzer = ContextDistillationAnalyzer(max_code_lines=30, max_todos=10)

    async def process_url(self, url: str, purpose: str = "") -> None:
        """
        スクレイピングの全工程を非同期に実行するメイン関数
        ScrapingHandler から asyncio.create_task() で呼び出される。
        """
        print(f"🕸️ [ScrapingOrchestra] {url} の解析ジョブを開始します...", flush=True)
        
        try:
            # 1. ネットワーク通信とHTML解析 (別スレッドで実行)
            clean_text = await asyncio.to_thread(self._fetch_and_clean_html, url)
            if not clean_text:
                raise ValueError("有効なテキストデータが抽出できませんでした。")

            # 2. チャンク分割 (別スレッドで実行)
            print("✂️ [ScrapingOrchestra] テキストをチャンクに分割中...", flush=True)
            chunks = await asyncio.to_thread(self.chunker.chunk_file, file_path=url, content=clean_text, language="generic")
            
            if not chunks:
                raise ValueError("チャンク分割結果が空です。")

            # 3. Embedding (ベクトル化) と ChromaDB 保存
            await self._embed_and_save_to_chroma(chunks)

            # 4. KnowledgeRouter 向け JSON の構築と保存
            json_save_path = await self._build_and_save_knowledge_json(url, purpose, clean_text)

            print(f"✅ [ScrapingOrchestra] すべてのナレッジ化工程が完了しました！ 保存先: {json_save_path}", flush=True)

            # ※ ここに WebSocket を使ったフロントエンドへの完了通知処理を将来的に追加可能
            # await self._notify_frontend_success(url, len(chunks), json_save_path)

        except Exception as e:
            print(f"❌ [ScrapingOrchestra] 処理中に致命的なエラーが発生しました: {e}", flush=True)
            traceback.print_exc()
            # await self._notify_frontend_error(url, str(e))


    # ──────────────────────────────────────────────
    # 内部処理メソッド群
    # ──────────────────────────────────────────────

    def _fetch_and_clean_html(self, url: str) -> str:
        """
        URLからHTMLを取得し、ノイズを除去して本文のみを返す（同期処理）
        """
        print(f"📥 [ScrapingOrchestra] データのダウンロード中...", flush=True)
        req = Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        
        try:
            with urlopen(req) as response:
                encoding = response.info().get_content_charset(failobj="utf-8")
                html = response.read().decode(encoding, errors='replace')
        except (URLError, HTTPError) as e:
            raise RuntimeError(f"URLの取得に失敗しました: {e}")

        soup = BeautifulSoup(html, 'html.parser')
        main_content = None

        # ドメイン特化のピンポイント抽出
        if "qiita.com" in url or "zenn.dev" in url:
            main_content = soup.find("article")
        elif "stackoverflow.com" in url:
            main_content = soup.find(id="mainbar")
        elif "github.com" in url:
            main_content = soup.find(class_="repository-content")

        # フォールバック
        if not main_content:
            main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup

        # 不要要素の除去
        for tag in main_content(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
            tag.decompose()

        return main_content.get_text(separator='\n', strip=True)

    async def _embed_and_save_to_chroma(self, chunks: List[Any]) -> None:
        """
        チャンクをベクトル化し、ChromaDBへ保存する
        """
        model_name = getattr(self.embedding_service.provider, "model_name", "UnknownModel")
        print(f"🧠 [ScrapingOrchestra] {model_name} を使用して {len(chunks)} 件のベクトル化を開始...", flush=True)

        texts_to_embed = [chunk.content for chunk in chunks]
        
        # ネットワークI/O（API呼び出し）が絡むため別スレッド化
        vectors = await asyncio.to_thread(self.embedding_service.embed_many, texts_to_embed)
        print(f"✨ [ScrapingOrchestra] ベクトル化完了。ChromaDBへ書き込みます...", flush=True)

        # VectorStoreへの追加
        await asyncio.to_thread(self.vector_store.add_many, chunks=chunks, vectors=vectors)
        
        current_count = getattr(self.vector_store, "count", lambda: "不明")()
        print(f"💾 [ScrapingOrchestra] ChromaDB 保存完了。現在の総チャンク数: {current_count}", flush=True)

    async def _build_and_save_knowledge_json(self, url: str, purpose: str, clean_text: str) -> str:
        """
        自作AI用のメタデータを構築し、JSONとして保存する
        """
        print("🏗️ [ScrapingOrchestra] 自作AI向けナレッジJSONのビルドを開始...", flush=True)
        
        # 本来は各種Analyzerが抽出したデータを入れるが、今回は擬似的に本文をコンポーネントとして扱う
        raw_meta = {
            "source_url": url,
            "purpose": purpose,
            "components": [{"name": "ScrapedContent", "code_snippet": clean_text[:5000]}] 
        }
        
        # ドメイン名の抽出 (例: qiita.com -> qiita_com)
        domain_name = url.split("://")[-1].split("/")[0].replace(".", "_")
        
        # 1. コンテキスト蒸留 (ContextDistillationAnalyzer)
        distilled_data = self.distillation_analyzer.analyze(
            raw_meta=raw_meta,
            domain_name=f"scraped_{domain_name}",
            description=f"Auto-scraped knowledge from {url}",
            keywords=["scraped", domain_name, "web", "automation"],
            weight=1.5
        )
        
        # 2. セマンティックグラフ化 (SemanticBuilderAnalyzer)
        semantic_json = self.semantic_builder.analyze(distilled_data.get("content", {}))
        
        # 3. KnowledgeRouter 準拠の最終データ組み立て
        final_knowledge = {
            "name": distilled_data["name"],
            "description": distilled_data["description"],
            "keywords": distilled_data["keywords"],
            "weight": distilled_data["weight"],
            "semantic_graph": semantic_json
        }

        # 保存先の決定 (KnowledgeRouter がスキャンするディレクトリ)
        save_filename = f"scraped_{domain_name}.json"
        
        # プロジェクトルートからのパスを安全に解決
        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.abspath(os.path.join(base_dir, "../knowledge_store"))
        os.makedirs(save_dir, exist_ok=True)
        
        save_path = os.path.join(save_dir, save_filename)
        
        # 4. Manager を使って非同期書き出し
        if hasattr(self.knowledge_manager, "write_file"):
            await asyncio.to_thread(
                self.knowledge_manager.write_file,
                save_path,
                json.dumps(final_knowledge, ensure_ascii=False, indent=2)
            )
        else:
            # フォールバック: 標準のファイル書き込み
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(final_knowledge, f, ensure_ascii=False, indent=2)
        
        print(f"📦 [ScrapingOrchestra] ナレッジJSONの出力完了: {save_filename}", flush=True)
        return save_path
    