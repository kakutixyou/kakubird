
# To/backend/api/services/fallback_service.py

import re
from typing import Dict, Any, Optional, List


# ===
# UI Trigger Rules
# ===

"""
fallback_service の役割:

- 軽量UIトリガー
- 正規表現ベースの高速分岐
- LLMを使わない即時レスポンス
- 「迷子になったUI」を救済

重要:
ここには重い処理を書かない。
API通信もしない。

Orchestrator より前に通る
超軽量ルーティング層。
"""


# ===
# Keyword Groups
# ===

SQL_KEYWORDS = [
    "sql",
    "sqlite",
    "database",
    "データベース",
    "テーブル",
]

CHART_KEYWORDS = [
    "chart",
    "graph",
    "グラフ",
    "可視化",
]

MARKDOWN_KEYWORDS = [
    "markdown",
    "md",
    "マークダウン",
]

JSON_KEYWORDS = [
    "json",
    "api response",
]

REACT_KEYWORDS = [
    "react",
    "component",
    "frontend",
    "ui",
]

PYTHON_KEYWORDS = [
    "python",
    "fastapi",
    "backend",
]


# ===
# Utility
# ===

def contains_keywords(
    message: str,
    keywords: List[str]
) -> bool:
    """
    keyword 含有判定
    """

    msg_lower = message.lower()

    return any(
        keyword.lower() in msg_lower
        for keyword in keywords
    )


# ===
# SQL Example UI
# ===

def build_sql_ui_response(
    message: str
) -> Dict[str, Any]:

    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "SQLサンプルUIを表示します。",

            "blocks": [
                {
                    "type": "CodeBlock",

                    "props": {
                        "language": "sql",

                        "code":
                            "SELECT * FROM users LIMIT 10;"
                    }
                },
                {
                    "type": "ChatActionBlock",

                    "props": {
                        "title": "次の操作",

                        "actions": [
                            {
                                "label": "JOINの例を見る",
                                "icon": "🔗",
                                "next_prompt":
                                    "SQL JOIN のサンプルを見せて"
                            },
                            {
                                "label": "CREATE TABLEを見る",
                                "icon": "🗂️",
                                "next_prompt":
                                    "CREATE TABLE の例を見せて"
                            }
                        ]
                    }
                }
            ]
        }
    }


# ===
# Chart UI
# ===

def build_chart_ui_response(
    message: str
) -> Dict[str, Any]:

    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "グラフUIサンプルを生成しました。",

            "blocks": [
                {
                    "type": "ChartBlock",

                    "props": {
                        "title": "サンプル売上データ",

                        "chartType": "line",

                        "data": [
                            {
                                "name": "Mon",
                                "value": 120
                            },
                            {
                                "name": "Tue",
                                "value": 240
                            },
                            {
                                "name": "Wed",
                                "value": 180
                            },
                            {
                                "name": "Thu",
                                "value": 320
                            },
                            {
                                "name": "Fri",
                                "value": 290
                            }
                        ]
                    }
                }
            ]
        }
    }


# ===
# JSON Viewer UI
# ===

def build_json_ui_response(
    message: str
) -> Dict[str, Any]:

    sample_json = {
        "status": "success",
        "message": "sample response",
        "items": [
            {
                "id": 1,
                "name": "alpha"
            },
            {
                "id": 2,
                "name": "beta"
            }
        ]
    }

    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "JSON Viewer を表示します。",

            "blocks": [
                {
                    "type": "JsonViewerBlock",

                    "props": {
                        "title": "Sample JSON",
                        "data": sample_json
                    }
                }
            ]
        }
    }


# ===
# Markdown Preview UI
# ===

def build_markdown_ui_response(
    message: str
) -> Dict[str, Any]:

    markdown_text = """
# Markdown Preview

## Features

- Fast rendering
- Live preview
- Syntax highlight

python
print("hello")
`

"""


    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "Markdown Preview UI を表示します。",

            "blocks": [
                {
                    "type": "MarkdownBlock",

                    "props": {
                        "content": markdown_text
                    }
                }
            ]
        }
    }


# ===

# React Component UI

# ===

def build_react_ui_response(
message: str
) -> Dict[str, Any]:


    react_code = """


    export default function App() {
    return ( <div> <h1>Hello React</h1> </div>
    )
    }
    """


    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "React Component サンプルです。",

            "blocks": [
                {
                    "type": "CodeBlock",

                    "props": {
                        "language": "tsx",
                        "code": react_code
                    }
                }
            ]
        }
    }


# ===

# Python Sample UI

# ===

def build_python_ui_response(
message: str
) -> Dict[str, Any]:


    python_code = """


    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def root():
    return {"hello": "world"}
    """


    return {
        "response_type": "ui_code",

        "content": {
            "message":
                "Python / FastAPI サンプルです。",

            "blocks": [
                {
                    "type": "CodeBlock",

                    "props": {
                        "language": "python",
                        "code": python_code
                    }
                }
            ]
        }
    }


# ===

# Regex Pattern Rules

# ===

def check_regex_rules(
message: str
) -> Optional[Dict[str, Any]]:
    # """
    # 正規表現ベース判定
    # """


    # CREATE TABLE
    if re.search(
        r"create\s+table",
        message,
        re.IGNORECASE
    ):

        return build_sql_ui_response(
            message
        )

    # SELECT
    if re.search(
        r"select\s+\*",
        message,
        re.IGNORECASE
    ):

        return build_sql_ui_response(
            message
        )

    # graph/chart
    if re.search(
        r"(graph|chart|グラフ)",
        message,
        re.IGNORECASE
    ):

        return build_chart_ui_response(
            message
        )

    return None

# ===

# Main Public API

# ===

def check_fallback_ui_trigger(
message: str
) -> Optional[Dict[str, Any]]:

# fallback UI routing


# Returns:
#     None:
#         不一致

#     Dict:
#         UI response

# -----------------------------------------------------
# regex rules
# -----------------------------------------------------
    regex_result = check_regex_rules(
        message
    )

    if regex_result:
        return regex_result

# -----------------------------------------------------
# SQL
# -----------------------------------------------------
    if contains_keywords(
        message,
        SQL_KEYWORDS
    ):

        return build_sql_ui_response(
            message
        )

# -----------------------------------------------------
# Chart
# -----------------------------------------------------
    if contains_keywords(
        message,
        CHART_KEYWORDS
    ):

        return build_chart_ui_response(
            message
        )

# -----------------------------------------------------
# Markdown
# -----------------------------------------------------
    if contains_keywords(
        message,
        MARKDOWN_KEYWORDS
    ):

        return build_markdown_ui_response(
            message
        )

# -----------------------------------------------------
# JSON
# -----------------------------------------------------
    if contains_keywords(
        message,
        JSON_KEYWORDS
    ):

        return build_json_ui_response(
            message
        )

# -----------------------------------------------------
# React
# -----------------------------------------------------
    if contains_keywords(
        message,
        REACT_KEYWORDS
    ):

        return build_react_ui_response(
            message
        )

# -----------------------------------------------------
# Python
# -----------------------------------------------------
    if contains_keywords(
        message,
        PYTHON_KEYWORDS
    ):

        return build_python_ui_response(
            message
        )

    return None


# ===

# Future Expansion Notes

# ===

"""
将来的な拡張ポイント

1. Rule Registry

---

rules = [
SQLRule(),
ChartRule(),
]

2. Plugin Trigger

---

plugin manifest routing

3. AI-assisted fallback

---

軽量classifier導入

4. UI Recommendation Engine

---

適切なBlock自動選択

5. User Preference Cache

---

好み学習

6. Dynamic Prompt Suggestions

---

next_prompt生成

7. Template Marketplace

---

community UI blocks

8. Intent Classification

---

embedding routing

9. DSL Routing

---

mini routing language

10. Visual Workflow Builder

---

GUI rule editor
"""


