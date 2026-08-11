from pathlib import Path
from typing import Tuple, Any, Optional

# 完成した「知識パイプライン3兄弟」をインポート
from backend.engine.KnowledgeRouter import KnowledgeRouter
from engine.Pinpoint_KnowledgeLoader import KnowledgeLoader
from engine.pinpoint_PromptBuilder import PromptBuilder
from api.services.inspectors.IntentInSpector import IntentInspector
# ※LLMクライアントは、実際のプロジェクトの構成に合わせてインポートしてください
# from utils.llm_client import call_llm
from .base_handler import BaseHandler
from pathlib import Path
class PhpHandler(BaseHandler):
    def __init__(self, project_root: str = "."):
        base_path = Path(project_root)
        
        # 1. backend から親(TO(と))に戻り、plugins/project_builder/knowledge へ繋ぐ
        correct_knowledge_path = base_path.parent / "plugins" / "project_builder" / "knowledge"
        
        # 2. 3兄弟に正しいパスを渡す
        # self.router = KnowledgeRouter(knowledge_dir=correct_knowledge_path)
        self.router = KnowledgeRouter(knowledge_dir=str(correct_knowledge_path))
        self.loader = KnowledgeLoader(base_dir=str(correct_knowledge_path))
        
        # ※ _global_rules.json が knowledge フォルダ直下にある前提の書き方です
        self.builder = PromptBuilder(global_rules_path=str(correct_knowledge_path / "_global_rules.json"))

    async def calculate_score(self, msg: str, signals: Optional[dict] = None) -> int:
        """
        Orchestrator（司令塔）から呼ばれるスコア計算。
        「これは自分が担当すべきか？」を判定します。
        """
        keywords = ["php", "laravel", "pdo", "composer", "xampp", "サーバーサイド"]
        msg_lower = msg.lower()
        
        # キーワードが含まれていれば100点（即時実行ショートカットの対象）
        if any(kw in msg_lower for kw in keywords):
            return 100
        
        # 直前の会話の文脈（active_context）がPHPなら80点
        if signals and signals.get("active_context") == "php":
            return 80
            
        return 0

    async def handle(self, msg: str, signals: Optional[dict] = None) -> Tuple[str, Any]:
        """
        メイン処理。Orchestratorから「君の担当だ」と言われたら実行されます。
        """
        print("🚀 [PhpHandler] PHPの処理を開始します...")

        # 1. Router: 目次を見て、今回の質問に必要なファイルのパスを選ぶ
        # 【修正】Routerのroute()は同期関数のため、async互換用の route_async() を呼び出すように変更
        route_result = await self.router.route_async(msg, signals)
        
        # 2. Loader: 選ばれたファイルを実際に読み込む
        # 【修正】RouteResultのプロパティ名が json_paths ではなく file_paths だったので修正
        load_result = await self.loader.load(route_result.file_paths)
        
        # 3. Builder: 読み込んだ知識とユーザーの質問を合体させて、最終プロンプトを作る
        prompt_result = self.builder.build(user_message=msg, load_result=load_result, signals=signals)
        
        print(f"📚 注入したPHP知識: {prompt_result.included_domains}")

        # 4. LLM実行: 完成したプロンプトをLLM（ClaudeやOllamaなど）に投げる
        # ---------------------------------------------------------
        # response_content = await call_llm(prompt_result.text)
        # ---------------------------------------------------------
        
        # 仮のレスポンス（実際はLLMの返答が入ります）
        response_content = "ここにLLMが生成したPHPのコードや解説が入ります。\n\n（※裏側で渡されたプロンプトの文字数: {} 文字）".format(prompt_result.char_count)

        # 5. 返却: (レスポンスの型, 内容) のタプルで返す仕様（ui_code or text）
        # ※PHPのバックエンド処理なので、基本は "text" で返します。
        return "text", response_content

    def estimate_size(self, msg: str) -> int:
        """
        Orchestratorが競合判定に使う見積もりサイズ
        """
        return 1500