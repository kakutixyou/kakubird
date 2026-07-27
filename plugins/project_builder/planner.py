# plugins/project_builder/Planner.py
import json

class Planner:
    def __init__(self):
        pass

    async def create_plan(self, requirements: dict, current_codebase: str) -> list:
        print("📅 [Planner] 要件と現在のコードベースから、開発タスクリストを生成しています...")

        prompt = f"""
            あなたはプロジェクトマネージャーです。
            以下のシステム要件と、現在のプロジェクトのソースコード状況を比較し、
            アプリを完成させるための具体的なタスクリスト（ステップ）をJSON配列で出力してください。

            【システム要件】
            {json.dumps(requirements, ensure_ascii=False, indent=2)}

            【現在のソースコード (Repomix出力)】
            ```xml
            {current_codebase[:3000]} ... (長すぎる場合は先頭をトリミング)
            【出力ルール】

            各ステップは「1つのファイルを作成/修正する」程度の粒度にしてください。

            依存関係を考慮し、正しい順序（例: 型定義 -> UIコンポーネント -> API通信）にしてください。

            純粋なJSON配列のみを出力してください。

            【出力JSONフォーマット】
            [
            {{
            "step_number": 1,
            "task_name": "型定義ファイルの作成",
            "description": "カレンダーのイベント用インターフェースを types/index.ts に定義する",
            "target_files": ["src/types/index.ts"]
            }},
            ...
            ]
            """

            # 実際にはここでLLMAPIを呼び出します
            # llm_response = await self.llm.generate(prompt)

            # モック用のダミーレスポンス
        mock_response = """
            [
                {
                    "step_number": 1,
                    "task_name": "APIクライアントの修正",
                    "description": "Pythonバックエンドと通信する処理を fetch API で実装する",
                    "target_files": ["src/api/client.ts"]
                },
                {
                    "step_number": 2,
                    "task_name": "Calendar UIのバグ修正",
                    "description": "日付のズレを引き起こしているレンダリングロジックを修正する",
                    "target_files": ["src/components/Calendar.tsx"]
                }
            ]
            """

        try:
                plan = json.loads(mock_response.strip())
                print(f"✅ [Planner] {len(plan)}個のタスクを生成しました。")
                return plan
        except json.JSONDecodeError as e:
            print(f"❌ [Planner] JSONのパースに失敗しました: {e}")
            return []