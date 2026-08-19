# ParserHandler.py
import re
import traceback
from typing import Any, Dict, Optional, Tuple

from .base_handler import BaseHandler

# 実際のディレクトリ位置に合わせて変更してください
from parsers.java_parser import JavaParser
from parsers.python_parser import PythonParser
from parsers.javascript_parser import JavaScriptParser


# ---------------------------------------------------------
# 1. コマンド・言語設定
# ---------------------------------------------------------

PARSER_COMMANDS = {
    "/parse",
    "/code",
    "/analyze",
}


LANGUAGE_ALIASES = {
    "java": "java",

    "python": "python",
    "py": "python",

    "javascript": "javascript",
    "js": "javascript",

    "jsx": "javascript",
    "react": "javascript",
}


# ---------------------------------------------------------
# 2. ParserHandler 本体
# ---------------------------------------------------------

class ParserHandler(BaseHandler):

    def __init__(self):
        # calculate_score / can_handle で検出した言語を一時保存
        self.detected_language: Optional[str] = None

        # Parserを一元管理
        self.parsers = {
            "java": JavaParser,
            "python": PythonParser(),
            "javascript": JavaScriptParser(),
        }


    # ----------------------------------------------------
    # サイズ予測
    # ----------------------------------------------------

    def estimate_size(self, message: str) -> int:
        """
        コード解析結果のおおよその最大サイズ。

        HTMLHandlerと同じく、
        Orchestrator側でトークン量やレスポンス量を
        判断するために使用する想定。
        """
        return 12000


    # ----------------------------------------------------
    # このHandlerが処理可能か
    # ----------------------------------------------------

    async def can_handle(self, message: str) -> bool:

        if not message:
            return False

        msg_lower = message.strip().lower()

        # 1. 明示コマンド
        if any(
            msg_lower.startswith(command)
            for command in PARSER_COMMANDS
        ):
            return True

        # 2. コードブロックが存在
        if "```" in message:
            return True

        # 3. コード解析を求めている
        analyze_keywords = [
            "コードを解析",
            "コード解析",
            "コードを説明",
            "変数を説明",
            "関数を説明",
            "クラスを説明",
            "コードの意味",
            "このコード",
            "ソースコード",
        ]

        if any(keyword in msg_lower for keyword in analyze_keywords):
            return True

        return False


    # ----------------------------------------------------
    # Handler選択用スコア
    # ----------------------------------------------------

    async def calculate_score(
        self,
        message: str,
        signals=None
    ) -> int:

        if not message:
            return 0

        msg_lower = message.strip().lower()

        # ------------------------------------------------
        # 1. 明示コマンド
        # ------------------------------------------------

        if any(
            msg_lower.startswith(command)
            for command in PARSER_COMMANDS
        ):
            self.detected_language = self._detect_language(message)
            return 100


        # ------------------------------------------------
        # 2. 言語を判定
        # ------------------------------------------------

        language = self._detect_language(message)

        if language:
            self.detected_language = language


        # ------------------------------------------------
        # 3. コードブロック + 言語判定成功
        # ------------------------------------------------

        if "```" in message and language:
            return 90


        # ------------------------------------------------
        # 4. コードブロックのみ
        # ------------------------------------------------

        if "```" in message:
            return 75


        # ------------------------------------------------
        # 5. 「解析して」などの明確な要求
        # ------------------------------------------------

        strong_keywords = [
            "コードを解析",
            "コード解析",
            "コードを説明",
            "変数を説明",
            "関数を説明",
            "クラスを説明",
        ]

        if any(keyword in msg_lower for keyword in strong_keywords):
            return 80


        # ------------------------------------------------
        # 6. 軽いコード関連要求
        # ------------------------------------------------

        weak_keywords = [
            "このコード",
            "ソースコード",
            "変数",
            "関数",
            "メソッド",
            "クラス",
        ]

        if language and any(
            keyword in msg_lower
            for keyword in weak_keywords
        ):
            return 65


        return 0


    # ----------------------------------------------------
    # メイン処理
    # ----------------------------------------------------

    async def handle(
        self,
        message: str
    ) -> Tuple[str, Any]:

        print(
            "⚡ Parser Handler 発動: コード解析を開始します",
            flush=True
        )

        try:

            # ------------------------------------------------
            # 1. コードを抽出
            # ------------------------------------------------

            code, block_language = self._extract_code(message)


            if not code:
                return (
                    "text",
                    "解析できるコードが見つかりませんでした。"
                )


            # ------------------------------------------------
            # 2. 言語判定
            # ------------------------------------------------

            language = (
                block_language
                or self.detected_language
                or self._detect_language(code)
            )


            if not language:
                return (
                    "text",
                    "プログラミング言語を判定できませんでした。"
                )


            # ------------------------------------------------
            # 3. Parser取得
            # ------------------------------------------------

            parser = self.parsers.get(language)


            if parser is None:
                return (
                    "text",
                    f"{language} は現在解析に対応していません。"
                )


            # ------------------------------------------------
            # 4. 各Parserに処理を委譲
            # ------------------------------------------------

            result = parser.parse(code)


            # async parserにも後で対応しやすくしたいなら、
            # 各Parserを async parse() に統一する方法もあります。


            # ------------------------------------------------
            # 5. フロントエンド用データに成形
            # ------------------------------------------------

            content = {
                "message": (
                    f"**{language}** のコードを解析しました。"
                ),

                "blocks": [
                    {
                        "type": "CodeAnalysisBlock",

                        "language": language,

                        "code": code,

                        "analysis": result,
                    }
                ]
            }


            return "code_analysis", content


        except Exception as e:

            print(
                f"[ParserHandler] エラー: {e}",
                flush=True
            )

            traceback.print_exc()

            return (
                "text",
                "コード解析中にエラーが発生しました。"
            )


    # ----------------------------------------------------
    # コード抽出
    # ----------------------------------------------------

    def _extract_code(
        self,
        message: str
    ) -> Tuple[str, Optional[str]]:
        """
        Markdownコードブロックからコードを取得。

        例:

        ```java
        public class Player {
        }
        ```

        ↓

        code:
            public class Player {
            }

        language:
            java
        """

        pattern = (
            r"```([a-zA-Z0-9_+\-#]*)\s*\n?"
            r"(.*?)"
            r"```"
        )

        match = re.search(
            pattern,
            message,
            flags=re.DOTALL
        )


        if match:

            language_hint = (
                match.group(1)
                .strip()
                .lower()
            )

            code = match.group(2).strip()


            normalized_language = (
                LANGUAGE_ALIASES.get(language_hint)
                if language_hint
                else None
            )


            return code, normalized_language


        # コードブロックが無い場合
        # /parse 等のコマンドを削除して残りをコードとして扱う

        cleaned = message.strip()


        for command in PARSER_COMMANDS:

            if cleaned.lower().startswith(command):

                cleaned = re.sub(
                    rf"^{re.escape(command)}\s*",
                    "",
                    cleaned,
                    flags=re.IGNORECASE
                )

                break


        return cleaned.strip(), None


    # ----------------------------------------------------
    # 言語判定
    # ----------------------------------------------------

    def _detect_language(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None


        text_lower = text.lower()


        # ------------------------------------------------
        # 1. Markdown言語指定
        # ------------------------------------------------

        markdown_match = re.search(
            r"```([a-zA-Z0-9_+\-#]+)",
            text
        )

        if markdown_match:

            hint = (
                markdown_match
                .group(1)
                .lower()
            )

            normalized = LANGUAGE_ALIASES.get(hint)

            if normalized:
                return normalized


        # ------------------------------------------------
        # 2. Java
        # ------------------------------------------------

        java_score = 0


        java_patterns = [
            r"\bpublic\s+class\b",
            r"\bprivate\s+\w+",
            r"\bprotected\s+\w+",
            r"\bpublic\s+static\s+void\s+main\b",
            r"\bSystem\.out\.println\b",
            r"\bimplements\b",
            r"\bextends\b",
            r"\bArrayList\s*<",
            r"\bList\s*<",
        ]


        for pattern in java_patterns:

            if re.search(pattern, text):
                java_score += 1


        # ------------------------------------------------
        # 3. Python
        # ------------------------------------------------

        python_score = 0


        python_patterns = [
            r"^\s*def\s+\w+\s*\(",
            r"^\s*class\s+\w+\s*[:\(]",
            r"^\s*import\s+\w+",
            r"^\s*from\s+\w+\s+import",
            r"\bself\.\w+",
            r"if\s+__name__\s*==",
            r"\bprint\s*\(",
        ]


        for pattern in python_patterns:

            if re.search(
                pattern,
                text,
                flags=re.MULTILINE
            ):
                python_score += 1


        # ------------------------------------------------
        # 4. JavaScript / JSX
        # ------------------------------------------------

        javascript_score = 0


        javascript_patterns = [
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\bvar\s+\w+\s*=",
            r"\bfunction\s+\w+\s*\(",
            r"=>",
            r"\bconsole\.log\s*\(",
            r"\bimport\s+React\b",
            r"\buseState\s*\(",
            r"</?[A-Z][A-Za-z0-9]*",
        ]


        for pattern in javascript_patterns:

            if re.search(pattern, text):
                javascript_score += 1


        # ------------------------------------------------
        # 5. 最大スコア
        # ------------------------------------------------

        scores = {
            "java": java_score,
            "python": python_score,
            "javascript": javascript_score,
        }


        best_language = max(
            scores,
            key=scores.get
        )


        # 何も特徴が見つからない
        if scores[best_language] == 0:
            return None


        return best_language


    # ----------------------------------------------------
    # execute
    # ----------------------------------------------------

    async def execute(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        HTMLHandlerのexecute()との互換性を意識した入口。
        """

        response_type, content = await self.handle(message)


        return {
            "id": "generate_parser_msg_id",

            "role": "ai",

            "type": response_type,

            "response_type": response_type,

            "content": (
                content
                if isinstance(content, dict)
                else {
                    "message": content,
                    "blocks": [],
                }
            )
        }