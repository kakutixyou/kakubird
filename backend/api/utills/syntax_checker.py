from api.utills.syntax_checker import check_python_syntax
from api.services.manager.KnowledgeManager import KnowledgeManager

async def handle_code_generation(ai_response_text):
    python_code = "print('Hello'  # 閉じカッコがないバグのあるコード"
    print("DEBUG TYPE:", type(check_python_syntax))
    # これで正しく「関数」として呼び出せるようになります！
    # check_python_syntax may be a function or a module exposing check_python_syntax
    if callable(check_python_syntax):
        checker_result = check_python_syntax(python_code)
    else:
        print("⚠️ check_python_syntax is not callable. Please check the import.")

    # if not checker_result["valid"]:
    #     # ⚠️ 文法エラーを発見！
    #     error_info = checker_result["error"]
    #     print(f"🚨 AIのコードに文法エラーを検知: {error_info['message']} (L{error_info['line']})")

    #     # 👉 ここでユーザーにエラーコードをそのまま見せるのではなく、
    #     #    AIシステム自身に「エラーが出たから、ここを直して再生成して！」と裏でプロンプトを投げて自動修正させる！
    #     #    (これが「セルフリフレクション」です)
        
    #     # prompt = f"あなたが書いたコードにエラーがあります。修正してください。\nエラー: {error_info['message']}"
    #     # ... 再実行処理 ...
    # else:
    #     # 🟢 文法が正常なら、前回の KnowledgeManager で安全に書き出す
    #     writer = KnowledgeManager()
    #     writer.write_file("output/app.py", python_code)
        