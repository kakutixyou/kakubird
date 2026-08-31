import re
import json
import os
import traceback
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup

# 記憶システム関連のモジュールをインポート
from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.vector_store import ChromaVectorStore
from plugins.ai_memory.embedding_service import EmbeddingService 

# アプリ全体で共有するインスタンス
shared_vector_store = ChromaVectorStore()
embedding_service = EmbeddingService()

class ScrapingHandler:
    def __init__(self):
        pass

    async def can_handle(self, message: str) -> bool:
        """このハンドラーが処理すべきメッセージか判定する"""
        has_url = "http://" in message or "https://" in message
        has_keyword = any(kw in message for kw in ["記憶", "読ん", "スクレイピング", "覚え", "学習", "インプット"])
        return has_url and has_keyword

    async def calculate_score(self, message: str) -> int:
        """ChatOrchestrator用のスコア計算"""
        if await self.can_handle(message):
            return 90
        return 0

    def estimate_size(self, message: str) -> int:
        """予想される出力文字数"""
        return 1500

    async def handle(self, message: str):
        """メインのスクレイピング＆記憶処理"""
        print("🌐 ScrapingHandlerが処理を開始します...", flush=True)

        # 1. URLの抽出
        url_match = re.search(r'(https?://[a-zA-Z0-9\./\-_?=]+)', message)
        if not url_match:
            return "text", "❌ URLを正しく認識できませんでした。有効なURLが含まれているか確認してください。"
        
        url = url_match.group(1).rstrip('」』】。、')

        # Unityコンテンツ判定
        is_unity_content = "docs.unity3d.com" in url or "unity" in url.lower()

        # Unity公式の古いバージョンURLは学習をスキップ
        if "docs.unity3d.com" in url:
            if re.search(r'/(5\.|2017\.|2018\.|2019\.|2020\.|2021\.)', url):
                return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: Unity 2021以前の古い公式ドキュメントのため、学習対象から除外しました。"

        # 2. Webページからのデータ取得
        try:
            print(f"📥 {url} からデータを取得中...", flush=True)
            req = Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            
            # タイムアウトを10秒に設定
            with urlopen(req, timeout=10) as response:
                content_type = response.info().get_content_type()
                
                # PDF形式などのバイナリチェック
                if "pdf" in content_type:
                    return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: PDFファイルです。現在のシステムはWebページ（HTML）のみ対応しています。"
                
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: 対応していないデータ形式（{content_type}）のため読み込めませんでした。"

                encoding = response.info().get_content_charset(failobj="utf-8")
                html = response.read().decode(encoding, errors='replace')

        except HTTPError as e:
            return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: Webサーバーからエラーが返されました（HTTP {e.code}: {e.reason}）。アクセス制限またはページが存在しない可能性があります。"
        except URLError as e:
            return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: サイトに接続できませんでした（{e.reason}）。URLが間違っているか、サーバーがダウンしている可能性があります。"
        except Exception as e:
            return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: 通信中にエラーが発生しました（詳細: {e}）。"

        try:
            # 3. BeautifulSoupでの解析とノイズ除去
            soup = BeautifulSoup(html, 'html.parser')

            main_content = None
            
            # ドメイン・用途ごとのピンポイント抽出
            if "qiita.com" in url or "zenn.dev" in url:
                main_content = soup.find("article")
            elif "stackoverflow.com" in url:
                main_content = soup.find(id="mainbar")
            elif "github.com" in url:
                main_content = soup.find(class_="repository-content") or soup.find("article")
            elif "docs.unity3d.com" in url:
                main_content = (
                    soup.find("div", class_="mb20") or 
                    soup.find("div", class_="section") or 
                    soup.find("div", id="content-wrap")
                )
            elif "wikipedia.org" in url:
                main_content = soup.find(id="bodyContent")
            elif any(domain in url for domain in ["pokewiki", "pokemongo", "game8", "gamewith", "atwiki"]):
                main_content = soup.find("main") or soup.find(id="content") or soup.find(class_="article-body")

            # 汎用フォールバック（歴史・政治経済・悩み・一般ブログなど）
            if not main_content:
                main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup

            # 不要なUIタグの削除
            for tag in main_content(["script", "style", "nav", "footer", "header", "aside", "form", "button", "iframe", "noscript"]):
                tag.decompose()

            # 共通UIノイズの除去
            for noise in main_content.find_all(class_=re.compile(r'(sidebar|toc|navigation|header|footer|menu|breadcrumb|search-form|ad-box)', re.I)):
                noise.decompose()

            # 改行を入れて本文テキスト抽出
            clean_text = main_content.get_text(separator='\n', strip=True)

            # 🌟 テキストが不十分な場合の理由通知（Notion/Scrapbox/SPA/ログイン保護対策）
            if not clean_text or len(clean_text) < 50:
                return "text", (
                    f"⚠️ 【読み込めませんでした】\nURL: {url}\n"
                    f"理由: ページから十分な本文テキストを取得できませんでした。\n"
                    f"※ JavaScript描画サイト（Notion, Scrapbox, Cloudflare Pages等）や、ログインが必要なページの可能性があります。"
                )

            # 4. テキストをチャンクに分割
            print("✂️ テキストをチャンクに分割中...", flush=True)
            chunker = CodeChunker(max_lines=10)
            chunks = chunker.chunk_file(file_path=url, content=clean_text, language="generic")

            if not chunks:
                return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: テキストの分割処理後に有効なデータが残りませんでした。"

            # 5. Unityコンテンツの場合のみ古すぎるコードを除外
            # （ポケモン・世界史・化石・諸説あり・お悩み等は一切削らずすべて全保存）
            valid_chunks = []
            for chunk in chunks:
                content = chunk.content
                if is_unity_content:
                    is_old_version = re.search(r'(Unity\s*(5\.|2017|2018|2019|2020))', content, re.I)
                    is_deprecated_api = re.search(r'(FindObjectOfType|FindObjectsOfType|GUIText|WorldAnchor)', content)
                    if not (is_old_version or is_deprecated_api):
                        valid_chunks.append(chunk)
                else:
                    valid_chunks.append(chunk)

            chunks = valid_chunks

            if not chunks:
                return "text", (
                    f"⚠️ 【読み込めませんでした】\nURL: {url}\n"
                    f"理由: ページの内容が古いUnityの仕様や非推奨コードのみで構成されているため、学習をスキップしました。"
                )

            # 6. 【確認用】抽出したチャンクをJSONファイルとして保存
            save_dir = "backend/.ai_memory/chunks/scraped_history"
            os.makedirs(save_dir, exist_ok=True)
            
            counter = 1
            while True:
                file_name = f"scraping_{counter:02d}.json"
                json_file_path = os.path.join(save_dir, file_name)
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
            vectors = embedding_service.embed_many(texts_to_embed)

            shared_vector_store.add_many(
                chunks=chunks,
                vectors=vectors
            )

            current_count = shared_vector_store.count()
            print(f"✅ 保存完了！現在の記憶データ総数: {current_count} チャンク", flush=True)

            # 8. フロントエンド（UI）へ返すデータの構築（成功時）
            display_message = (
                f"<summary>✅ 新しい知識を学習しました</summary>"
                f"<details>指定されたURLからテキストデータを抽出し、{len(chunks)} 個のチャンクに分割してベクトルデータベースに保存しました。\n"
                f"現在、AIは合計 {current_count} 個の知識の欠片を持っています。</details>"
            )

            preview_data = {
                "source_url": url,
                "new_chunks_saved": len(chunks),
                "total_chunks_in_memory": current_count,
                "sample_chunk_preview": chunks[0].content[:200] + "..." if len(chunks[0].content) > 200 else chunks[0].content
            }

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
            return "text", f"⚠️ 【読み込めませんでした】\nURL: {url}\n理由: 処理中に予期せぬエラーが発生しました（詳細: {e}）。"
