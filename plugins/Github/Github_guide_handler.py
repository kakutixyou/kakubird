# plugins/Github/Github_guide_handler.py
import logging
import traceback
from typing import Any, Tuple, Optional

# ※ご自身の環境に合わせてインポートパスは調整してください
from project_builder.base_handler import BaseHandler
from api.services.inspectors.IntentInSpector import IntentInspector

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GitHub関連の反応キーワード群
GITHUB_COMMANDS = {"/github", "/push", "/git"}

class GithubGuideHandler(BaseHandler):
    def __init__(self, base_dir="."):
        # Inspectorから受け取るメタデータ用
        self.detected_mode: Optional[str] = None
        self.base_dir = base_dir

    # 
    # 1. ユーティリティ & ルーティング処理
    # 
    def _get_text(self, message: Any) -> str:
        """安全にテキストを抽出するヘルパー"""
        if isinstance(message, str):
            return message
        for attr in ["text", "content", "body", "message"]:
            if hasattr(message, attr):
                val = getattr(message, attr)
                if isinstance(val, str):
                    return val
        return str(message)

    def estimate_size(self, message: Any) -> int:
        return 10000

    async def can_handle(self, message: Any) -> bool:
        msg_str = self._get_text(message).lower()
        if any(msg_str.startswith(cmd) for cmd in GITHUB_COMMANDS):
            return True
        keywords = ["github", "push", "gitignore", "env_sample", "git init", "ギットハブ", "プッシュ"]
        return any(k in msg_str for k in keywords)

    async def calculate_score(self, message: Any, signals=None) -> int:
        msg_str = self._get_text(message)
        msg_lower = msg_str.strip().lower()

        # コマンド検知時は高スコア
        if any(msg_lower.startswith(cmd) for cmd in GITHUB_COMMANDS):
            print("🎯 [GithubGuideHandler] GitHubコマンドを検知: 100点を返却します", flush=True)
            return 100

        # 具体的な要望が含まれている場合は絶対優先
        force_keywords = [".gitignore", "env_sample", "githubにpush"]
        if sum(1 for k in force_keywords if k in msg_lower) >= 1:
            print("🎯 [GithubGuideHandler] GitHubのファイル生成要求を検知: 優先スコア 150点 を返却します", flush=True)
            return 150

        # IntentInspectorでさらに文脈をチェック（他のハンドラーとの競合対策）
        inspector = IntentInspector(msg_str)
        analysis = inspector.inspect()
        
        self.detected_mode = analysis.get("mode")
        
        # もしInspector側で 'github' や 'version_control' の意図を判定できればスコアを加算
        if self.detected_mode in ["github", "version_control", "git"]:
            return analysis.get("score", 90)

        return 0

    # 
    # 2. ファイルテンプレート生成
    # 
    def _generate_gitignore(self) -> str:
        """プロジェクト用の .gitignore テンプレート"""
        return """# Node.js / React / Frontend
node_modules/
build/
dist/
.npm/

# Environment Variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Python / Backend
__pycache__/
*.py[cod]
*$py.class
venv/
env/
.venv/
Pipfile.lock

# OS / Editor
.DS_Store
.vscode/
.idea/
*.suo
*.ntvs*
*.njsproj
"""

    def _generate_env_sample(self) -> str:
        """プロジェクト用の .env_sample テンプレート"""
        return """# データベース設定
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_db_user_here
DB_PASSWORD=your_db_password_here

# API連携（OpenAIやGitHubなど）
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...

# アプリケーション設定
DEBUG=True
PORT=3000
FRONTEND_URL=http://localhost:3000
"""

 # 
    # 3. メイン処理 (ブロック生成)
    # 
    async def handle(self, message: Any) -> Tuple[str, Any]:
        print("⚡ [GithubGuideHandler] GitHub Pushガイドとテンプレートファイルを生成します", flush=True)
        
        try:
            # テンプレート文字列の取得
            gitignore_code = self._generate_gitignore()
            env_sample_code = self._generate_env_sample()

            # UIブロックの構築（MarkdownChatBlockとCodeBlockを活用）
            blocks = [
                {
                    "type": "CodeBlock",
                    "props": {
                        "language": "ignore",
                        "filename": ".gitignore",
                        "code": gitignore_code
                    }
                },
                {
                    "type": "CodeBlock",
                    "props": {
                        "language": "bash",
                        "filename": ".env_sample",
                        "code": env_sample_code
                    }
                },
                {
                    "type": "MarkdownChatBlock",
                    "props": {
                        "content": "### 🚀 次のステップ（コマンド実行）\n\nファイルの作成と保存が終わったら、ターミナルで以下のコマンドを上から順に実行してください。\n\n```bash\n# 1. Gitの初期化\ngit init\n\n# 2. 変更した全てのファイルをステージング (※ .envなどは無視されます)\ngit add .\n\n# 3. コミット\ngit commit -m \"Initial commit: プロジェクトの初期設定\"\n\n# 4. ブランチ名を main に変更\ngit branch -M main\n\n# 5. リモートリポジトリの登録 (※ <URL>を自分のものに変更してください)\ngit remote add origin <あなたのGitHubリポジトリURL>\n\n# 6. GitHubへプッシュ\ngit push -u origin main\n```"
                    }
                }
            ]

            # 💡 【重要修正】AIChatMessageList.jsx の 'ui_code' 分岐に合致させる構造
            response_data = {
                "message": "GitHubへのPush準備を始めます。\nセキュリティと整理のため、まずはプロジェクトの一番上の階層（ルート）に **`.gitignore`** と **`.env_sample`** を作成してください。",
                "blocks": blocks
            }

            # 第一引数を "ui_code" にすることで、フロント側で <WidgetCard> として綺麗に表示される
            return "ui_code", response_data

        except Exception as e:
            traceback.print_exc()
            return "text", f"GitHub準備の解析中にエラーが発生しました: {str(e)}"