import os
import json
import glob
from typing import Any, Tuple
from .base_handler import BaseHandler

from api.services.inspectors.IntentInSpector import IntentInspector
class ChatHandler(BaseHandler):
    def __init__(self):
        # 知識データのパス設定
        self.knowledge_dir = os.path.join(
            os.getcwd(), 
            "plugins", "project_builder", "knowledge"
        )
        self.knowledge_cache = {}

    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        # 🚨 パターンS：自己防衛（メンタル・リーガル）モード
        # 限界を迎えている時は、他のあらゆるハンドラーを差し置いて最優先で発火させる（確定100点）
        if analysis.get("mode") == "self_defense":
            return 100 

        # ---------------------------------------------------------
        # パターンA：システムの仕組みやルールについて聞かれている場合
        # ---------------------------------------------------------
        if analysis["mode"] == "system_inquiry":
            return analysis["score"]

        # ---------------------------------------------------------
        # パターンB：どの専門分野（デプロイ、UI、JSON等）でもない場合
        # ---------------------------------------------------------
        if analysis["mode"] == "unknown":
            score = 60
            active_context = current_signals.get("active_context") if current_signals else None
            if active_context:
                score = 45
                
            if len(message.strip()) < 10:
                score = 70
            return min(score, 85)

        return 0

    def estimate_size(self, message: str) -> int:
        return 500

    def _extract_keywords(self, message: str) -> list:
        # 技術スタックに加えて、防衛用のトリガーキーワードを追加
        keywords = [
            # 技術系
            "react", "electron", "aws", "docker", "github", "flask", "fastapi", "python", "sql", "video", "ui",
            # 防衛系 (mental.json, legal.json などを引っ掛けるため)
            "法律", "下請法", "労働", "メンタル", "限界", "疲れた", "終わらない", "スケジュール", "理不尽", "ガントチャート"
        ]
        return [kw for kw in keywords if kw.lower() in message.lower()]

    def _load_relevant_knowledge(self, keywords: list) -> str:
        # (既存のロジックそのまま。指定キーワードを含むJSONを読み込む)
        if not os.path.exists(self.knowledge_dir):
            return "知識データベース（knowledgeフォルダ）が見つかりません。"
        
        relevant_data = {}
        search_pattern = os.path.join(self.knowledge_dir, "**", "*.json")
        all_json_files = glob.glob(search_pattern, recursive=True)

        for file_path in all_json_files:
            path_parts = file_path.lower().split(os.sep)
            for keyword in keywords:
                if any(keyword in part for part in path_parts):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            relevant_data[os.path.basename(file_path)] = json.load(f)
                    except Exception as e:
                        print(f" JSON読み込みエラー ({file_path}): {e}")
                    break 

        return json.dumps(relevant_data, ensure_ascii=False, indent=2) if relevant_data else ""

    async def handle(self, request) -> tuple[str, str]:
        # Inspectorを再度走らせてモードを確認（あるいはrequestからmodeを受け取る設計でも可）
        inspector = IntentInspector(request.message if hasattr(request, 'message') else "")
        analysis = inspector.inspect()
        
        # 🛡️ 自己防衛モードの場合の特別処理（LLMへのシステムプロンプト構築）
        if analysis.get("mode") == "self_defense":
            # 抽出したキーワードから legal.json や mental.json などを取得
            keywords = self._extract_keywords(request.message if hasattr(request, 'message') else "")
            knowledge_str = self._load_relevant_knowledge(keywords)
            
            # AIに対する「メンターとしての振る舞い」を強制するシステムプロンプトを構築
            defense_prompt = f"""
あなたはシステム開発者を守る専属のリーガル＆メンタルアドバイザーAIです。
開発者が限界を迎えている、あるいは理不尽な要求に晒されている兆候を検知しました。

【あなたのミッション】
1. 開発者の感情と努力を最大限に肯定し、絶対に責めないこと。
2. 以下のJSON形式の「労働法規・下請法」や「メンタルケア」のナレッジを元に、客観的かつ法的な視点で現在のアブノーマルな状況を指摘すること。
3. 必要であれば、クライアントへ提出する「ダミーのガントチャート（GantChartHandler）」の生成を提案すること。

【システムナレッジ（JSON）】
{knowledge_str}

上記を踏まえ、開発者に寄り添いつつ、システム的な自衛手段を提案する返答を生成してください。
"""
            # ※ここで実際にLLMのAPIを叩くか、プロンプトをテキストとして返すかはシステム全体の設計に依存します。
            # 今回はプロンプト（テキスト）として返却する想定とします。
            return "prompt", defense_prompt

        # ------------------------------------------------
        # 以下、通常の system_inquiry モードの処理（既存のまま）
        # ------------------------------------------------
        knowledge = getattr(request, "world_knowledge", {})
        
        if not knowledge:
            return "text", "現在、システム（To）の詳しいルールや知識データ（JSON）が読み込まれていません。"

        response_lines = [
            "システムの仕組み（JSONデータ）についてご説明しますね。\n",
            "現在、私が把握している「To」の内部ルールは以下の通りです：\n"
        ]

        for key, value in knowledge.items():
            response_lines.append(f"### 📌 {key}")
            if isinstance(value, list):
                if not value: response_lines.append("  データがありません。")
                else: [response_lines.append(f"  ・{item}") for item in value]
            elif isinstance(value, dict):
                if not value: response_lines.append("  設定がありません。")
                else: [response_lines.append(f"  ・{sub_key}: {sub_value}") for sub_key, sub_value in value.items()]
            else:
                response_lines.append(f"  {value}")
            response_lines.append("")

        return "text", "\n".join(response_lines)