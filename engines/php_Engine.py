"""
php_engine.py
────────────────────────────────────────────
PHP専用Knowledge Engine

役割
----------------------------------------
・Knowledge JSONを読む
・Promptを組み立てる
・LLMへ渡すデータを返す

※ファイル探索はしません。

ProjectKnowledgeEngineなどが
事前に作成したJSONを利用します。
"""

from pathlib import Path
import json


class PHPEngine:
    """
    PHP用Knowledge Engine

    このEngineは
    "PHPについて何を知っているか"
    をKnowledge JSONから取得します。

    実際のPHPコード生成はLLMが担当します。
    """

    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir)

    # =========================================================
    # Public API
    # =========================================================

    def generate(self, user_prompt: str) -> dict:
        """
        Engineの入口。

        Handlerはこのメソッドだけ呼びます。

        Flow

            Handler
                │
                ▼
            generate()
                │
                ▼
            JSON読込
                │
                ▼
            Prompt生成
                │
                ▼
            Prompt文字列を返す
        """

        knowledge = self._load_from_json()

        prompt = self._build_prompt(
            user_prompt=user_prompt,
            knowledge=knowledge,
        )

        return {
            "system_prompt": prompt,
            "knowledge": knowledge,
        }

    # =========================================================
    # Private
    # =========================================================

    def _load_from_json(self):
        """
        Knowledgeフォルダから
        PHP関連JSONを読み込みます。

        ここでは
        ファイル探索はしません。

        ProjectKnowledgeEngineが

            php_basics.json
            php_patterns.json
            php_security.json

        を既に生成している前提です。
        """

        result = []

        if not self.knowledge_dir.exists():
            return result

        for file in sorted(self.knowledge_dir.glob("*.json")):

            try:
                with open(file, encoding="utf-8") as f:
                    result.append(json.load(f))

            except Exception:

                # 壊れたJSONは無視
                continue

        return result

    def _build_prompt(
        self,
        user_prompt,
        knowledge,
    ):
        """
        KnowledgeをLLMへ渡すPromptへ変換します。

        EngineはPromptを作るだけです。

        実際にChatGPTやGeminiを呼ぶのは
        ChatServiceやHandlerです。
        """

        sections = []

        sections.append(
            "あなたはPHP専門AIです。"
        )

        sections.append(
            "以下のKnowledgeを優先してください。"
        )

        for item in knowledge:

            sections.append(
                json.dumps(
                    item,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        sections.append("### User Request")

        sections.append(user_prompt)

        return "\n\n".join(sections)