# api/ai/judge.py←定期的にミスる To(と)/plugins/sql_builder_v2/backend_sql_v2/api_sql_v2/ai/judge.py←よし

import re

# 危険なキーワード（読み取り専用アプリなら）
DANGEROUS_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]

# プレースホルダーっぽい文字列
PLACEHOLDER_PATTERNS = ["table_name", "column_name", "your_table", "column LIKE"]

def evaluate_response(text: str) -> str:
    if not text or "```sql" not in text:
        return "fail"

    # SQLブロックを抽出
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if not match:
        return "fail"

    sql = match.group(1).strip()

    # 危険なSQL
    sql_upper = sql.upper()
    if any(kw in sql_upper for kw in DANGEROUS_KEYWORDS):
        return "danger"

    # プレースホルダーが残っている（生成失敗）
    if any(p in sql for p in PLACEHOLDER_PATTERNS):
        return "weak"

    # 短すぎる
    if len(sql) < 15:
        return "weak"

    return "good"