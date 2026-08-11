# api/services/handlers/github_handler.py
import traceback
from typing import Any, Tuple
from .base_handler import BaseHandler
from api.services.github_service import smart_github_search
from api.services.inspectors.IntentInSpector  import IntentInspector

GITHUB_COMMANDS = {"/github", "/search"}

class GithubHandler(BaseHandler):
    """
    GitHubリポジトリの検索依頼を担当するハンドラー
    """
    
    async def can_handle(self, message: str) -> bool:
        msg_lower = message.lower()
        if any(msg_lower.startswith(cmd) for cmd in GITHUB_COMMANDS):
            return True
            
        search_keywords = ["探して", "調べて", "検索して", "見つけて", "教えて", "探したい", "検索", "似た"]
        return "github" in msg_lower and any(k in msg_lower for k in search_keywords)

    # ----------------------------------------------------
    # 🌟 新設：Inspectorによるスコア判定（最大85点キャップ）
    # ----------------------------------------------------
    async def calculate_score(self, message: str, signals=None) -> int:
        msg_lower = message.strip().lower()

        # 1. 絶対コマンドは強制100点（即決）
        if any(msg_lower.startswith(cmd) for cmd in GITHUB_COMMANDS):
            return 100

        # 2. Inspector（共通の審査員）に委譲
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        if analysis["mode"] == "github_search":
            return analysis["score"]

        return 0

    # ----------------------------------------------------
    # 🌟 既存の素晴らしい検索ロジックはそのまま維持！
    # ----------------------------------------------------
    async def handle(self, message: str) -> Tuple[str, Any]:
        print("⚡ GitHub Handler 発動: GitHub検索へ直行します")
        
        try:
            # 絶対コマンドが使われていた場合は、コマンド部分を削る
            clean_query = message.lower()
            for cmd in GITHUB_COMMANDS:
                if clean_query.startswith(cmd):
                    clean_query = clean_query.replace(cmd, "", 1)
            
            # 1. 検索クエリから不要な「話し言葉」を削ぎ落とす
            noise_words = [
                "関係の", "関連の", "についての", "について",
                "のgithub", "githubの", "github",
                "作品を", "プロジェクトを", "リポジトリを", "ものを",
                "探してほしい", "探して", "調べて", "教えて", "検索して", "見つけて",
                "。", "、", "！", "？", "お願い"
            ]
            
            for word in noise_words:
                clean_query = clean_query.replace(word, " ")
            
            # 余分な空白を削除
            clean_query = " ".join(clean_query.split()).strip()
            
            # もし削りすぎて空になったらフォールバック
            if not clean_query:
                clean_query = "AI agent"
                
            print(f"🔍 抽出された検索クエリ: {clean_query}")

            # 2. 綺麗になったキーワードで検索を実行
            search_result = await smart_github_search(clean_query)
            
            return "github_search", search_result
            
        except Exception as e:
            traceback.print_exc()
            return "text", "GitHub検索中にエラーが発生しました。"