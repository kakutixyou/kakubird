import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Tuple

# ===============================
# 非同期スクレイパー (FastAPI対応)
# ===============================
class AsyncWebScraper:
    # 求人サイトにBot弾きされないよう、一般的なブラウザを装う
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }

    async def fetch(self, url: str) -> str:
        # requestsの代わりに、非同期で動くhttpxを使用
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.HEADERS, timeout=15.0)
            response.raise_for_status()
            
            # 文字化け対策（Shift-JISなどの古いサイトにも対応）
            response.encoding = response.charset_encoding or "utf-8"
            return response.text

# ===============================
# 求人特化型クリーナー
# ===============================
class JobTextCleaner:
    # 先生の設定に加えて、求人サイトで邪魔になるヘッダーやフッターも除去
    REMOVE_TAGS = [
        "script", "style", "noscript", "iframe",
        "header", "footer", "nav", "aside", "svg"
    ]

    def clean(self, html: str) -> Tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        
        title = soup.title.get_text(strip=True) if soup.title else "タイトル不明"

        # 不要なタグをごっそり削除
        for tag in self.REMOVE_TAGS:
            for node in soup.find_all(tag):
                node.decompose()

        # ✨ 求人票特有のチューニング
        # 募集要項の「テーブル（表）」の文字がくっつかないように空白を挿入
        for th_td in soup.find_all(["th", "td"]):
            th_td.append(" ") 
        for br in soup.find_all("br"):
            br.replace_with("\n") # 改行タグは実際の改行に変換

        # テキストの抽出
        text = soup.get_text(" ")
        
        # 連続する空白を1つにまとめつつ、改行は綺麗に残す
        text = re.sub(r'[ \t]+', ' ', text) 
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return title, text.strip()

# ===============================
# 実行用メイン関数（Handlerから呼び出す用）
# ===============================
async def extract_job_text(url: str) -> Optional[str]:
    """
    URLから求人情報を抽出し、AIエンジン（Evaluator）に渡しやすく整形した文字列を返す
    """
    try:
        scraper = AsyncWebScraper()
        cleaner = JobTextCleaner()
        
        html = await scraper.fetch(url)
        title, content = cleaner.clean(html)
        
        if len(content) < 100:
            print("⚠️ 本文が短すぎます（ログインが必要、またはJS描画のサイトの可能性）")
            return None
            
        # AIが文脈を理解しやすいようにヘッダーをつけて返す
        return f"【求人ページタイトル】\n{title}\n\n【ページ本文】\n{content}"
        
    except Exception as e:
        print(f"🚨 求人スクレイピングエラー: {e}")
        return None