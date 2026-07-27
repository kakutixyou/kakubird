# 現在のscraping_handler.py
import re
import json
import os
import traceback
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup

# 記憶システム関連のモジュールをインポート
# ※ プロジェクトの実際のパスに合わせて適宜調整してください
from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.vector_store import ChromaVectorStore
from plugins.ai_memory.embedding_service import EmbeddingService 

# アプリ全体で共有するインスタンス

shared_vector_store = ChromaVectorStore()
embedding_service = EmbeddingService()

class ScrapingHandler:
    def __init__(self):
        # 🌟 おすすめ（優先）サイトのドメインリスト
        self.RECOMMENDED_DOMAINS = [
            "qiita.com",
            "zenn.dev",
            "stackoverflow.com",
            "github.com",
            "docs.python.org"
        ]

    async def can_handle(self, message: str) -> bool:
        """このハンドラーが処理すべきメッセージか判定する"""
        has_url = "http://" in message or "https://" in message
        has_keyword = any(kw in message for kw in ["記憶", "読ん", "スクレイピング", "覚え", "学習"])
        return has_url and has_keyword

    async def calculate_score(self, message: str) -> int:
        """ChatOrchestrator用のスコア計算"""
        if await self.can_handle(message):
            return 90
        return 0

    def estimate_size(self, message: str) -> int:
        """予想される出力文字数（Orchestratorでのマージ判定用）"""
        return 1500

    async def handle(self, message: str):
        """メインのスクレイピング＆記憶処理"""
        print("🌐 ScrapingHandlerが処理を開始します...", flush=True)

        # 1. URLの抽出
        url_match = re.search(r'(https?://[a-zA-Z0-9\./\-_?=]+)', message)
        if not url_match:
            return "text", "URLを正しく認識できませんでした。"
        
        url = url_match.group(1).rstrip('」』】。、')

        # 2. 優先ドメインのチェック
        is_recommended = any(domain in url for domain in self.RECOMMENDED_DOMAINS)

        if not is_recommended:
            return "text", (
                f"URL({url})を確認しました。\n"
                f"現在の設定では、AIの知識の質を保つため、\n"
                f"Qiita, Zenn, Stack Overflow, GitHub などの技術サイトからの学習を優先しています。\n"
                f"別のURLを指定してください。"
            )

        try:
            # 3. Webページからのデータ取得
            print(f"📥 {url} からデータを取得中...", flush=True)
            req = Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            f = urlopen(req)
            encoding = f.info().get_content_charset(failobj="utf-8")
    
            # ... (urlopen等で html を取得する処理はそのまま) ...
            html = f.read().decode(encoding, errors='replace')

            # 🌟 4. ノイズ除去と【本文のピンポイント抽出】 🌟
            soup = BeautifulSoup(html, 'html.parser')

            # ドメインごとに、本文が格納されている特定のHTMLタグを狙い撃ちする
            main_content = None
            if "qiita.com" in url:
                main_content = soup.find("article")  # Qiitaは <article> タグに本文がある
            elif "zenn.dev" in url:
                main_content = soup.find("article")  # Zennも <article> タグ
            elif "stackoverflow.com" in url:
                main_content = soup.find(id="mainbar")  # Stack Overflow は mainbar
            elif "github.com" in url:
                main_content = soup.find(class_="repository-content")  # GitHub用

            # もし専用タグが見つからなかった場合のフォールバック（安全対策）
            if not main_content:
                main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup

            # ターゲットエリア内から、さらに不要な要素（サイドバー、メニュー、広告など）を削ぎ落とす
            for tag in main_content(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
                tag.decompose()

            # 改行を入れながら、純粋なテキストだけを抽出
            clean_text = main_content.get_text(separator='\n', strip=True)

            # 5. テキストをチャンクに分割
            print("✂️ テキストをチャンクに分割中...", flush=True)
            # ... (以降の処理はそのまま) ...
            chunker = CodeChunker(max_lines=10) # 必要に応じて後で文字数ベース等に調整
            chunks = chunker.chunk_file(file_path=url, content=clean_text, language="generic")

            if not chunks:
                return "text", "有効なテキストデータが見つかりませんでした。"

# 6. 【確認用】抽出したチャンクをJSONファイルとして連番で保存
            save_dir = "backend/.ai_memory/chunks/scraped_history"
            
            # ディレクトリが存在しない場合は作成する
            os.makedirs(save_dir, exist_ok=True)
            
            # 既存のファイルを確認して、空いている連番（_01, _02...）を探す
            counter = 1
            while True:
                # scraping_01.json, scraping_02.json のようなファイル名を作成
                file_name = f"scraping_{counter:02d}.json"
                json_file_path = os.path.join(save_dir, file_name)
                
                # その名前のファイルがまだ存在しなければ決定してループを抜ける
                if not os.path.exists(json_file_path):
                    break
                counter += 1
            
            save_data = [
                {"chunk_id": i, "content": chunk.content} for i, chunk in enumerate(chunks)
            ]
            
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(save_data, json_file, ensure_ascii=False, indent=2)
            
            print(f"📁 確認用のJSONを {json_file_path} に保存しました！", flush=True)

            # 7. ベクトル化とChromaDBへの保存
            model_name = getattr(embedding_service.provider, "model_name", "代替モデル")
            print(f"🧠 {model_name} を使ってベクトル化を開始...", flush=True)
            print(f"チャンク数: {len(chunks)}")

            texts_to_embed = [chunk.content for chunk in chunks]

            print("Embedding呼び出し前")

            vectors = embedding_service.embed_many(texts_to_embed)

            print(f"Embedding完了: {len(vectors)}")

            shared_vector_store.add_many(
                chunks=chunks,
                vectors=vectors
            )

            print("Chroma保存完了")
            current_count = shared_vector_store.count()
            print(f"✅ 保存完了！現在の記憶データ総数: {current_count} チャンク", flush=True)

            # 8. フロントエンド（UI）へ返すデータの構築
            display_message = (
                f"<summary>✅ 新しい知識を学習しました</summary>"
                f"<details>指定されたURLから純粋なテキストデータを抽出し、{len(chunks)} 個のチャンクに分割してベクトルデータベースに保存しました。\n"
                f"現在、AIは合計 {current_count} 個の知識の欠片を持っています。</details>"
            )

            preview_data = {
                "source_url": url,
                "new_chunks_saved": len(chunks),
                "total_chunks_in_memory": current_count,
                # UIプレビュー用に最初のチャンクの内容を少しだけ渡す
                "sample_chunk_preview": chunks[0].content[:200] + "..." if len(chunks[0].content) > 200 else chunks[0].content
            }

            # MemoryStatusBlock を使ってリッチなUIで表示させる
            return "ui_code", {
                "message": display_message,
                "blocks": [
                    {
                        "type": "MemoryStatusBlock",
                        "props": {
                            "data": preview_data,
                            "title": "記憶データベース更新完了"
                        }
                    }
                ]
            }

        except Exception as e:
            traceback.print_exc()
            return "text", f"<summary>⚠️ データの取得または保存に失敗しました</summary><details>エラー詳細: {e}</details>"