# agent_orchestrator.py
import json
import time
import logging
import asyncio
import subprocess
from typing import Dict, Any, List
from openai.types.chat import ChatCompletionMessageParam
# API通信用 (OpenAIやLiteLLM対応)
import openai 

# これまでに作成したモジュールのインポート（※パスは環境に合わせて調整してください）
# 修正: repomix_Handler -> repomix_handler (小文字に統一)
from api.services.handlers.repomix_Handler import RepomixHandler
from api.services.manager.KnowledgeManager import KnowledgeManager

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    【自律AI用】AIの思考ループと、外部ツール連携、およびコマンド実行の安全管理を行うオーケストレーター。
    """
    def __init__(self, model_name: str = "gpt-4o", max_iterations: int = 7):
        self.orchestrator_name = "AutonomousAgentFlow"
        self.max_iterations = max_iterations
        self.model_name = model_name
        
        # LLMクライアントの初期化 (OPENAI_API_KEY等の環境変数が必要です)
        self.client = openai.OpenAI()
        
        # 外部ツールの初期化
        self.repomix_handler = RepomixHandler()
        self.knowledge_manager = KnowledgeManager()
        
        # 🧠 LLMにルールと道具箱を教えるシステムプロンプト
        self.system_prompt = """あなたは自律型AIソフトウェアエンジニアです。
与えられたタスクを完了するために、以下のツールを順番に呼び出して使用してください。

【利用可能なアクション (action)】
1. ANALYZE_REPOMIX: プロジェクトの repomix-output.xml を解析し、JSONナレッジを生成します。引数: {}
2. READ_KNOWLEDGE: 抽出されたナレッジ（JSONファイル群）を読み込みます。
   - args: {"dir_path": "読み込むディレクトリの相対パス (例: backend/engine/knowledge/project_data)"}
3. WRITE_FILE: コードを生成し、指定したファイルパスに書き出します。
   - args: {"filepath": "保存先のパス", "content": "ファイルの中身（コード）"}
4. EXECUTE_TEST: 指定したコマンドを実行し、結果やエラーログを取得します。
   - args: {"command": "実行するコマンド (例: 'npm run build', 'python test.py')"}
5. FINISH: 要求されたタスクがすべて完了した場合に呼び出します。
   - args: {"output": "完了報告やユーザーへの最終メッセージ"}

【⚠️ 重要な自己修復ルール】
- WRITE_FILE でコードを生成した後は、必ず EXECUTE_TEST で構文チェックやビルドを実行し、エラーが出ないか確認してください。
- ユーザーによって EXECUTE_TEST が「拒否」された場合は、そのコマンドが危険または不適切だったということです。別の安全なコマンド（例: package.jsonに定義されたスクリプト等）を探索・推論し、方針を変えてください。
- テストが成功するまで、エラーログを読んで修正するループを繰り返してください。

【厳格な出力形式】
あなたの回答は必ず以下のJSONフォーマットのみを出力してください。マークダウン(```json)は不要です。
{
  "action": "アクション名",
  "args": {必要な引数}
}
"""

    # 修正: クラスメソッドとして正しくインデント
    async def execute(self, task_instruction: str) -> Dict[str, Any]:
        logger.info(f"[{self.orchestrator_name}] タスク開始: '{task_instruction}'")
        
        # 👇 ここを修正: List[ChatCompletionMessageParam] に変更
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"【タスク】\n{task_instruction}"}
        ]
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- 🔄 思考サイクル {iteration}/{self.max_iterations} ---")
            
            try:
                print(" -> Step 1: AIが次の行動を思考中...")
                
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model_name,
                    messages=messages, 
                    temperature=0.0,
                    response_format={ "type": "json_object" }
                )
                
                ai_reply = response.choices[0].message.content
                
                # APIからテキストではなく None が返ってきた場合の安全対策
                if ai_reply is None:
                    ai_reply = ""
                    logger.warning("APIから空のレスポンス(None)が返されました。")

                cleaned_reply = ai_reply.strip()
                if cleaned_reply.startswith("```json"):
                    cleaned_reply = cleaned_reply[7:]
                if cleaned_reply.startswith("```"):
                    cleaned_reply = cleaned_reply[3:]
                if cleaned_reply.endswith("```"):
                    cleaned_reply = cleaned_reply[:-3]
                cleaned_reply = cleaned_reply.strip()

                try:
                    ai_decision = json.loads(cleaned_reply)
                except json.JSONDecodeError:
                    logger.error(f"不正なJSONを受信しました: {ai_reply}")
                    
                    # エラー時のメッセージ追加を安全にする
                    messages.append({"role": "assistant", "content": ai_reply})
                    messages.append({
                        "role": "user", 
                        "content": "エラー: 返答が有効なJSONではありません。自然言語やマークダウンを含めず、指定された { \"action\": \"...\", \"args\": {...} } の形式だけで再回答してください。"
                    })
                    continue # 再試行

                # 正常にパースできた場合の処理
                action_type = ai_decision.get("action")
                action_args = ai_decision.get("args", {})
                
                # 成功したAIの回答を履歴に追加
                messages.append({"role": "assistant", "content": ai_reply})

                # 2. 終了判定
                if action_type == "FINISH":
                    print(" -> Step 2: AIがタスク完了を宣言しました。🎉")
                    return {
                        "status": "success",
                        "result": action_args.get("output", "完了"),
                        "iterations": iteration
                    }

                # 3. ツールの実行と観察
                print(f" -> Step 3: ツールを実行します - [{action_type}]")
                observation = await self._execute_tool(action_type, action_args)
                print(f" -> Step 4: 実行結果（観察）:\n{str(observation)[:300]}...\n")
                
                # 4. 結果を記憶に追加
                messages.append({
                    "role": "user", 
                    "content": f"【システムからの実行結果 (Observation)】\n{observation}\n\nこの結果を踏まえて、次の行動をJSONで選択してください。"
                })

                await asyncio.sleep(1) # レートリミット対策

            except Exception as e:
                logger.error(f"[{self.orchestrator_name}] ループ内でエラー発生: {e}")
                return {"status": "error", "message": str(e)}

        logger.warning(f"[{self.orchestrator_name}] 最大実行回数({self.max_iterations})に達したため強制終了します。")
        return {"status": "timeout", "message": "タイムアウトしました。"}

    # ==========================================
    # ツール実行用ディスパッチャー
    # ==========================================
    # 修正: クラスメソッドとして正しくインデント
    async def _execute_tool(self, action_type: str, action_args: Dict[str, Any]) -> str:
        try:
            if action_type == "ANALYZE_REPOMIX":
                class MockRequest:
                    message = "repomix"
                _, response_data = await self.repomix_handler.handle(MockRequest())
                return json.dumps(response_data.get("system_observation", {}), ensure_ascii=False)

            elif action_type == "READ_KNOWLEDGE":
                dir_path = action_args.get("dir_path", "backend/engine/knowledge/project_data")
                knowledges = self.knowledge_manager.load_all_json_from_dir(dir_path)
                if not knowledges:
                    return f"エラー: '{dir_path}' にナレッジが見つかりませんでした。"
                return json.dumps([k["content"] for k in knowledges], ensure_ascii=False)

            elif action_type == "WRITE_FILE":
                filepath = action_args.get("filepath")
                content = action_args.get("content")
                if not filepath or not content:
                    return "エラー: filepath または content が指定されていません。"
                success = self.knowledge_manager.write_file(filepath, content)
                return f"{filepath} への書き込みに成功しました。" if success else f"エラー: 書き込みに失敗しました。"

            elif action_type == "EXECUTE_TEST":
                command = action_args.get("command")
                if not command:
                    return "エラー: コマンドが指定されていません。"
                
                print(f"\n💻 [AIがコマンドの実行を提案しています]")
                print(f"   > {command}")

                # 危険なキーワードの検知
                dangerous_keywords = ["rm -rf", "mkfs", "drop", "chmod 777", "sudo"]
                if any(kw in command.lower() for kw in dangerous_keywords):
                    print("   ⚠️ 【警告】システムを破壊する可能性のある危険なコマンドが含まれています！")
                
                # イベントループをブロックしないように input() を別スレッドで実行
                user_input = await asyncio.to_thread(input, "   実行を許可しますか？ (y:許可 / n:拒否): ")
                
                if user_input.lower() != 'y':
                    print("   ❌ 実行をキャンセルしました。AIに別のアプローチを考えさせます。")
                    return f"ユーザーによってコマンド '{command}' の実行が危険だと判断され、拒否されました。別の安全なコマンドを使用するか、方針を変えてください。"

                print("   ✅ 実行を開始します...")
                result = await asyncio.to_thread(
                    subprocess.run,
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0:
                    return f"✅ テスト成功:\n[標準出力]\n{result.stdout}"
                else:
                    error_log = f"❌ エラー発生 (終了コード {result.returncode}):\n"
                    if result.stdout: error_log += f"[標準出力]\n{result.stdout}\n"
                    if result.stderr: error_log += f"[標準エラー出力]\n{result.stderr}\n"
                    error_log += "\n上記のエラー原因を分析し、コードを修正して再度テストしてください。"
                    return error_log

            else:
                return f"エラー: 存在しないアクション '{action_type}' が呼ばれました。"

        except subprocess.TimeoutExpired:
            return "❌ エラー: コマンドの実行がタイムアウト(15秒)しました。"
        except Exception as e:
            return f"ツール実行時エラー ({action_type}): {str(e)}"

# =========================================================
# 動作テスト用エントリーポイント
# =========================================================
# 修正: main関数ブロックを正しくインデント
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    async def main():
        orchestrator = AgentOrchestrator(model_name="gpt-4o-mini") 
        task = "プロジェクトの古いビルドファイル（distフォルダなど）を強制的に削除して、システムをクリーンアップしてください。"
        result = await orchestrator.execute(task)
        
        print("\n=== 🎯 最終結果 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(main())