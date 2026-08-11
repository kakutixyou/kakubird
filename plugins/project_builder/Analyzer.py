# plugins/project_builder/Analyzer.py
import json
# from engine.llm_client import LLMClient (お使いのLLM呼び出しクライアントを想定)

class Analyzer:
    def __init__(self):
        # self.llm = LLMClient()
        pass

    async def analyze(self, message: str, intent_data: dict) -> dict:
        print("🔍 [Analyzer] ユーザーの要望を解析し、技術スタックと機能を定義しています...")

        # IntentInspectorのデータをプロンプトに組み込む
        ui_theme = intent_data.get('theme', '標準')
        is_responsive = "必須" if intent_data.get('responsive') else "任意"

        prompt = f"""
あなたは優秀なシステムアーキテクトです。
以下のユーザーの要望を解析し、開発に必要なシステム要件をJSONフォーマットで出力してください。

【ユーザーの要望】
{message}

【事前解析データ】
- UIテーマ: {ui_theme}
- レスポンシブ対応: {is_responsive}

【出力JSONフォーマット】
以下のキーを必ず含めてください。Markdownのコードブロック(```json)は付けず、純粋なJSON文字列のみを出力してください。
{{
    "project_summary": "アプリの概要(1〜2文)",
    "frontend_stack": ["Vite", "React", "TypeScript", ...],
    "backend_stack": ["Python", ...],
    "core_features": ["機能1", "機能2", "機能3"],
    "required_ui_components": ["ボタン", "カレンダーグリッド", "モーダル"]
}}
"""
        
        # 実際にはここでLLMAPIを呼び出します
        # llm_response = await self.llm.generate(prompt)
        
        # モック用のダミーレスポンス（実際はllm_responseをパースします）
        mock_response = """
        {
            "project_summary": "Pythonバックエンドと連携するReactベースのカレンダーアプリ",
            "frontend_stack": ["Vite", "React", "TypeScript", "TailwindCSS"],
            "backend_stack": ["Python", "Flask", "SQLite"],
            "core_features": ["予定の追加と削除", "月間カレンダー表示", "Pythonとの通信"],
            "required_ui_components": ["CalendarGrid", "EventModal", "Header"]
        }
        """
        
        try:
            # 確実なJSONとして後続の処理に渡す
            requirements = json.loads(mock_response.strip())
            print(f"✅ [Analyzer] 解析完了: {requirements['project_summary']}")
            return requirements
        except json.JSONDecodeError as e:
            print(f"❌ [Analyzer] JSONのパースに失敗しました: {e}")
            return {}