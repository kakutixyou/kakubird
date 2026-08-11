import re
import asyncio
from typing import Tuple, Dict, Any
from api.services.handlers.base_handler import BaseHandler
from engine.orchestrator.Scraping_all_orchestra import ScrapingAllOrchestra

class ScrapingHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        # 🌟 バックグラウンドワーカーのインスタンスを保持
        self.orchestra = ScrapingAllOrchestra()

    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        has_url = "http://" in message or "https://" in message
        has_keyword = any(kw in message for kw in ["記憶", "読ん", "スクレイピング", "覚え", "学習"])
        return 90 if (has_url and has_keyword) else 0

    async def handle(self, request) -> Tuple[str, Dict[str, Any]]:
        message = getattr(request, "message", "") if hasattr(request, "message") else str(request)
        
        # 1. URLの抽出
        url_match = re.search(r'(https?://[a-zA-Z0-9\./\-_?=]+)', message)
        if not url_match:
            return "text", {"message": "URLを正しく認識できませんでした。"}
        
        url = url_match.group(1).rstrip('」』】。、')
        purpose = message.replace(url, "").strip()

        # 💡 2. Orchestra（バックグラウンドワーカー）の起動
        # create_task を使うことで、この行は完了を待たずに一瞬で通過します
        asyncio.create_task(self.orchestra.process_url(url, purpose))

        # 3. UIへの即時応答
        display_message = (
            f"<summary>🚀 サイトの解析をバックグラウンドで開始しました</summary>"
            f"<details>対象URL: {url}\n\n"
            f"現在、AIが該当ページを解析し、知識データベースを更新しています。\n"
            f"完了までの間も、通常通りチャットを続けることができます。</details>"
        )

        return "ui_code", {
            "message": display_message,
            "blocks": [] # MemoryStatusBlockを入れる場合はここに記述
        }