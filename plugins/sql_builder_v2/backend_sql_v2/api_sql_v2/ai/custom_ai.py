
import re
from typing import List, Dict

import anthropic
from .prompt import SYSTEM_PROMPT,build_prompt
from .judge import evaluate_response
from .schema_loader import get_schema_text
from core.config import ANTHROPIC_API_KEY, GEMINI_API_KEY
# from ai.prompt import SYSTEM_PROMPT, build_prompt
# from ai.judge import evaluate_response
# from ai.schema_loader import get_schema_text←事故の元
# from core.config import ANTHROPIC_API_KEY, GEMINI_API_KEY←事故の元
from .judge import evaluate_response
# ✅ scraping_handlerと同じDBを参照する
from plugins.ai_memory.vector_store import (
    ChromaVectorStore,
    CHROMA_PERSIST_PATH,
    CHROMA_COLLECTION_NAME,
)
from plugins.ai_memory.embedding_service import EmbeddingService

# ✅ シングルトンとして初期化（scraping_handlerと同じパス・同じコレクション）
_vector_store = ChromaVectorStore(
    persist_directory=CHROMA_PERSIST_PATH,
    collection_name=CHROMA_COLLECTION_NAME,
)
_embedding_service = EmbeddingService()
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# ===
# ✅ RAG検索（custom_aiから呼ぶ）
# ===

# ===
# ✅ RAG検索（custom_aiから呼ぶ）
# ===

def retrieve_relevant_chunks(query: str, top_k: int = 5) -> str:
    """
    ChromaDBから関連チャンクを取得してプロンプト用文字列を返す
    """
    try:
        # クエリをベクトル化
        query_vector = _embedding_service.embed(query)

        # ChromaVectorStore.search() はchromaの生dictを返す
        results = _vector_store.search(query_vector, top_k=top_k)

        # ✅ 対策1: 結果そのものが無い場合は終了
        if not results:
            return ""

        docs = results.get("documents")
        metas = results.get("metadatas")

        # ✅ 対策2: docsが None、または空リストの場合は終了
        if not docs or not docs[0]:
            return ""

        documents = docs[0]
        # metasがNoneの場合の安全対策
        metadatas = metas[0] if metas and metas[0] else [{}] * len(documents)

        chunks = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            # 万が一metaの中身がNoneだった場合の対策
            if meta is None:
                meta = {}
            source = meta.get("file_path", "unknown")
            chunks.append(f"[参考{i+1}: {source}]\n{doc}")

        return "\n\n".join(chunks)

    except Exception as e:
        print(f" RAG検索失敗: {e}")
        return ""


# ===
# LLM共通呼び出し口
# ===

async def call_llm_with_schema(prompt: str) -> str:
    if ANTHROPIC_API_KEY:
        try:
            from claude_ai import run_claude_ai_raw
            return await run_claude_ai_raw(prompt)
        except Exception as e:
            print(f"Claude失敗、Geminiへ: {e}")

    if GEMINI_API_KEY:
        try:
            from gemini_ai import run_gemini_ai_raw
            return await run_gemini_ai_raw(prompt)
        except Exception as e:
            print(f"Gemini失敗、ルールベースへ: {e}")

    return ""


# ===
# コンテキスト構築（会話履歴）
# ===

def build_context(history: List[Dict]) -> str:
    recent = history[-5:]
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "AI"
        content = msg.get("content") or msg.get("text", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


# ===
# ルールベースSQL生成（LLMなしのfallback）
# ===

def simple_sql_generator(user_input: str, context: str, schema_text: str = "") -> str:
    text = user_input.lower()
    table = _guess_table(text, schema_text)

    if any(k in text for k in ["合計", "sum", "total"]):
        return f"```sql\nSELECT SUM(amount) FROM {table};\n```"
    if any(k in text for k in ["件数", "count", "何件"]):
        return f"```sql\nSELECT COUNT(*) FROM {table};\n```"
    if any(k in text for k in ["平均", "avg", "average"]):
        return f"```sql\nSELECT AVG(amount) FROM {table};\n```"
    if "今日" in text:
        return f"```sql\nSELECT * FROM {table} WHERE DATE(created_at) = CURRENT_DATE;\n```"
    if "今月" in text:
        return f"```sql\nSELECT * FROM {table}\nWHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now');\n```"
    if any(k in text for k in ["最新", "新しい", "latest"]):
        return f"```sql\nSELECT * FROM {table}\nORDER BY created_at DESC LIMIT 10;\n```"
    if any(k in text for k in ["探す", "検索", "search", "find"]):
        col = _guess_column(text, schema_text) or "name"
        return f"```sql\nSELECT * FROM {table}\nWHERE {col} LIKE '%キーワード%';\n```"
    if any(k in text for k in ["join", "結合", "紐付"]):
        return _build_join_sql(schema_text)

    return f"```sql\nSELECT * FROM {table} LIMIT 100;\n```"


def _guess_table(text: str, schema_text: str) -> str:
    keyword_map = {
        "sales":    ["売上", "sales", "sale"],
        "users":    ["ユーザー", "user", "users", "会員"],
        "orders":   ["注文", "order", "orders"],
        "products": ["商品", "product", "products"],
        "payments": ["支払", "payment", "payments"],
    }
    for table, keywords in keyword_map.items():
        if table in schema_text and any(k in text for k in keywords):
            return table
    match = re.search(r"- (\w+):", schema_text)
    if match:
        return match.group(1)
    return "target_table"


def _guess_column(text: str, schema_text: str) -> str:
    keyword_map = {
        "name":       ["名前", "name"],
        "email":      ["メール", "email"],
        "status":     ["ステータス", "status", "状態"],
        "created_at": ["日付", "日時", "date"],
    }
    for col, keywords in keyword_map.items():
        if col in schema_text and any(k in text for k in keywords):
            return col
    return ""


def _build_join_sql(schema_text: str) -> str:
    tables = re.findall(r"- (\w+):", schema_text)
    if len(tables) >= 2:
        t1, t2 = tables[0], tables[1]
        return f"```sql\nSELECT *\nFROM {t1}\nINNER JOIN {t2} ON {t1}.id = {t2}.{t1}_id;\n```"
    return "```sql\nSELECT * FROM table_a INNER JOIN table_b ON table_a.id = table_b.table_a_id;\n```"


# ===
# メインエントリーポイント
# ===

async def run_custom_ai(req) -> Dict:

    # ① スキーマ取得
    db_type  = getattr(req, "db_type", "sqlite")
    db_path  = getattr(req, "db_path", "")
    conn_str = getattr(req, "conn_str", "")

    schema_text = get_schema_text(
        db_type=db_type,
        db_path=db_path,
        conn_str=conn_str,
    )

    # ② 会話履歴コンテキスト
    history = req.history or []
    conversation_context = build_context(
        [{"role": m.role, "content": m.content} for m in history]
    )

    # ✅ ③ RAG検索（ChromaDBから関連チャンクを取得）
    rag_context = retrieve_relevant_chunks(req.message)

    # ✅ ④ プロンプト構築（会話履歴 + RAGチャンクを両方渡す）
    prompt = build_prompt(
        user_input=req.message,
        schema_text=schema_text,
        context=conversation_context,
        rag_context=rag_context,   # ← build_promptに追加が必要（後述）
    )

    # ⑤ LLM呼び出し
    llm_reply = await call_llm_with_schema(prompt)

    if llm_reply:
        response = llm_reply
    else:
        sql = simple_sql_generator(req.message, conversation_context, schema_text)
        response = f"SQLを生成しました：\n\n{sql}"

    # ⑥ 品質チェック
    quality = evaluate_response(response)

    if quality == "danger":
        return {"reply": "安全でないSQLが検出されました。", "type": quality}

    if quality == "weak":
        retry_prompt = prompt + "\n\n※前回の回答が不完全でした。テーブル名・カラム名を必ずスキーマから選んでください。"
        retry_reply = await call_llm_with_schema(retry_prompt)
        if retry_reply and evaluate_response(retry_reply) == "good":
            return {"reply": retry_reply.strip(), "type": "good"}

    return {"reply": response.strip(), "type": quality}