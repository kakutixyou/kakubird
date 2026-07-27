# backend/services/ai_orchestrator.py

from services import memory_service
from services import nlp_service

from api.ai.schema_loader import get_schema_text


class AIOrchestrator:

    async def process(
        self,
        text: str,
        user_id: str = "default",
        db_path: str = ""
    ):

        # =========================
        # ① 会話履歴取得
        # =========================

        tasks = await memory_service.get_tasks(user_id)

        context_text = (
            " / ".join([t["task"] for t in tasks])
            if tasks else
            "特になし"
        )

        # =========================
        # ② DBスキーマ取得
        # =========================

        schema_text = ""

        if db_path:
            try:
                schema_text = get_schema_text(
                    db_type="sqlite",
                    db_path=db_path
                )
            except Exception as e:
                schema_text = f"スキーマ取得失敗: {str(e)}"

        # =========================
        # ③ 意図判定
        # =========================

        intent = self._detect_intent(text)

        # =========================
        # ④ モード選択
        # =========================

        if intent == "simple":

            result = self._template_mode(text)

        elif intent == "complex":

            result = await self._ai_mode(
                text=text,
                context=context_text,
                schema=schema_text
            )

        else:

            result = await self._hybrid_mode(
                text=text,
                context=context_text,
                schema=schema_text
            )

        # =========================
        # ⑤ 履歴保存
        # =========================

        await memory_service.save_tasks(
            user_id,
            [
                {
                    "task": text,
                    "priority": 1
                }
            ]
        )

        return result

    # =====================================
    # 意図判定
    # =====================================

    def _detect_intent(self, text: str) -> str:

        if len(text) < 15:
            return "simple"

        if "ランキング" in text:
            return "complex"

        if "集計" in text:
            return "complex"

        if "平均" in text:
            return "complex"

        if "件数" in text:
            return "complex"

        return "hybrid"

    # =====================================
    # テンプレモード
    # =====================================

    def _template_mode(self, text: str):

        template_type = nlp_service.detect_template_type(text)

        entities = nlp_service.extract_entities(text)

        return nlp_service.build_sql_template(
            template_type,
            text,
            entities
        )

    # =====================================
    # AIモード
    # =====================================

    async def _ai_mode(
        self,
        text: str,
        context: str,
        schema: str
    ):

        from api.ai.claude_ai import generate_sql

        prompt = f"""
あなたはSQL生成AIです。

{schema}

過去の文脈:
{context}

ユーザー要求:
{text}

ルール:

1. 必ず存在するテーブルのみ使用
2. 存在しないカラムを作らない
3. SQLのみ返す
4. 説明文は禁止
"""

        sql = await generate_sql(prompt)

        return {
            "type": "ai_generated",
            "title": "AIフル生成",
            "icon": "sparkles",
            "description": "スキーマを参照して生成されたSQL",
            "sql": sql,
            "parts": []
        }

    # =====================================
    # ハイブリッドモード
    # =====================================

    async def _hybrid_mode(
        self,
        text: str,
        context: str,
        schema: str
    ):

        base = self._template_mode(text)

        base_sql = base.get("sql", "")

        from api.ai.claude_ai import generate_sql

        prompt = f"""
あなたはSQL修正AIです。

現在のDB構造:

{schema}

元SQL:

{base_sql}

ユーザー要求:

{text}

過去文脈:

{context}

ルール:

- 存在するテーブルのみ使用
- WHERE句を中心に修正
- SQLのみ返す
"""

        fixed_sql = await generate_sql(prompt)

        base["sql"] = fixed_sql
        base["type"] = "hybrid"
        base["title"] = f"{base.get('title', 'SQL')} (AI補正)"
        base["icon"] = "wand-magic-sparkles"

        return base