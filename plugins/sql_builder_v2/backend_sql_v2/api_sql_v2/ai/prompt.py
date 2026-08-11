# api/ai/prompt.py

# =========================================================
# システムプロンプト（AIの基本人格・ルール）
# =========================================================

SYSTEM_PROMPT = """
あなたは優秀なSQLエンジニアです。

ルール：
- 必ずSQLを ```sql ``` で囲んで生成する
- スキーマに存在するテーブル・カラムのみ使う
- 不明な場合も仮のSQLを出す
- 解説は1行以内で簡潔に
- JOINする場合は外部キーを必ず確認する
- 日付条件は CURRENT_DATE を基準にする
"""

# =========================================================
# プロンプト構築
# =========================================================

def build_prompt(
    user_input: str,
    schema_text: str,
    context: str,
    rag_context: str = "",
) -> str:
    """
    LLMに渡すプロンプトを組み立てる

    Args:
        user_input  : ユーザーの質問
        schema_text : DBスキーマ情報
        context     : 直近の会話履歴（build_contextの出力）
        rag_context : ChromaDBから取得した関連チャンク（省略可）
    """

    # RAGチャンクがある場合のみセクションを追加
    rag_section = ""
    if rag_context:
        rag_section = f"""
## 関連ドキュメント（参考情報）
{rag_context}
"""

    # 会話履歴がある場合のみセクションを追加
    context_section = ""
    if context:
        context_section = f"""
## 会話履歴（直近5件）
{context}
"""

    return f"""{SYSTEM_PROMPT}
## 利用可能なスキーマ
{schema_text}
{rag_section}{context_section}
## ユーザーの質問
{user_input}

SQLのみ返してください。説明は1行以内で。
"""