
# To/backend/api/services/recruit_service.py

import os
import re
import traceback
from typing import Dict, Any, Optional

import httpx
from sympy import evaluate

from core.memory_manager import save_chat_message

# plugin は service が吸収する
# from recruit.evaluator import evaluate


# ===
# Constants
# ===

JOB_KEYWORDS = [
    "募集要項",
    "給与",
    "勤務地",
    "応募資格",
    "福利厚生",
]

URL_REGEX = r"(https?://[^\s]+)"

DEFAULT_FETCH_TIMEOUT = 10.0

MAX_HTML_LENGTH = 3000


# ===
# Detection Logic
# ===

def is_recruit_message(
    message: str
) -> bool:
    """
    求人関連メッセージ判定

    True:
        - 求人票テキスト
        - 求人URL
        - 評価依頼

    False:
        通常会話
    """

    keyword_match_count = sum(
        1
        for keyword in JOB_KEYWORDS
        if keyword in message
    )

    url_match = re.search(
        URL_REGEX,
        message
    )

    is_job_url = (
        bool(url_match)
        and (
            "求人" in message
            or "評価" in message
            or "転職" in message
        )
    )

    return (
        keyword_match_count >= 2
        or is_job_url
    )


# ===
# URL Extraction
# ===

def extract_url(
    message: str
) -> Optional[str]:
    """
    メッセージからURL抽出
    """

    match = re.search(
        URL_REGEX,
        message
    )

    if not match:
        return None

    return match.group(1)


# ===
# HTML Fetch
# ===

async def fetch_job_page_content(
    url: str
) -> str:
    """
    求人ページHTML簡易取得

    NOTE:
    本格スクレイピングではない。
    LLM渡し用の軽量抽出。
    """

    try:

        async with httpx.AsyncClient(
            timeout=DEFAULT_FETCH_TIMEOUT
        ) as client:

            response = await client.get(
                url
            )

            response.raise_for_status()

            html = response.text

        return html[:MAX_HTML_LENGTH]

    except Exception as e:

        print(f"Recruit Fetch Error: {e}")

        return ""


# ===
# Prompt Builder
# ===

def build_recruit_analysis_text(
    user_message: str,
    page_content: str = ""
) -> str:
    """
    plugin evaluator に渡す解析テキスト生成
    """

    if not page_content:

        return user_message

    return (
        "=== 求人ページ内容 ===\n"
        f"{page_content}\n\n"
        "=== ユーザーメッセージ ===\n"
        f"{user_message}"
    )


# ===
# Plugin Execution
# ===

async def execute_recruit_evaluation(
    target_text: str
) -> Dict[str, Any]:
    """
    recruit plugin evaluator 実行
    """

    api_key = os.getenv(
        "ANTHROPIC_API_KEY",
        ""
    )

    try:

        result = evaluate(
            target_text,
            api_key
        )

        return result

    except Exception:

        traceback.print_exc()

        return {
            "company_name": "Unknown",
            "score": 0,
            "summary":
                "求人評価中にエラーが発生しました。",
            "red_flags": [
                "plugin execution failed"
            ]
        }


# ===
# UI Response Builder
# ===

def build_recruit_ui_response(
    evaluation_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Frontend UI Block構築
    """

    company_name = evaluation_result.get(
        "company_name",
        "該当企業"
    )

    return {
        "response_type": "ui_code",

        "content": {
            "message":
                f"🤖 {company_name} の求人情報を審査しました！",

            "blocks": [
                {
                    "type": "JsonViewerBlock",

                    "props": {
                        "title": "📊 求人審査レポート",

                        "data": evaluation_result
                    }
                },

                {
                    "type": "ChatActionBlock",

                    "props": {
                        "title": "次の一手:",

                        "actions": [
                            {
                                "label":
                                    "この求人に応募する",

                                "icon": "✉️",

                                "next_prompt":
                                    f"{company_name}"
                                    "への志望動機を作成して"
                            },

                            {
                                "label":
                                    "レッドフラッグを深掘りする",

                                "icon": "🚩",

                                "next_prompt":
                                    "この求人の懸念点について"
                                    "詳しく教えて"
                            },

                            {
                                "label":
                                    "面接対策をする",

                                "icon": "🎤",

                                "next_prompt":
                                    f"{company_name}"
                                    "の面接対策をしたい"
                            }
                        ]
                    }
                }
            ]
        }
    }


# ===
# Main Public API
# ===

async def handle_recruit_message(
    user_message: str
) -> Optional[Dict[str, Any]]:
    """
    orchestrator から呼ばれる公開API

    Returns:
        None:
            recruit対象外

        Dict:
            UI response
    """

    try:

        # -------------------------------------------------
        # recruit判定
        # -------------------------------------------------
        if not is_recruit_message(
            user_message
        ):
            return None

        # -------------------------------------------------
        # URL取得
        # -------------------------------------------------
        url = extract_url(
            user_message
        )

        page_content = ""

        if url:

            page_content = (
                await fetch_job_page_content(
                    url
                )
            )

        # -------------------------------------------------
        # evaluator用text生成
        # -------------------------------------------------
        target_text = (
            build_recruit_analysis_text(
                user_message=user_message,
                page_content=page_content,
            )
        )

        # -------------------------------------------------
        # plugin実行
        # -------------------------------------------------
        evaluation_result = (
            await execute_recruit_evaluation(
                target_text
            )
        )

        # -------------------------------------------------
        # memory保存
        # -------------------------------------------------
        save_chat_message(
            "assistant",
            "求人審査レポートを出力しました",
            metadata={
                "source": "recruit_plugin"
            }
        )

        # -------------------------------------------------
        # UI response
        # -------------------------------------------------
        return build_recruit_ui_response(
            evaluation_result
        )

    except Exception:

        traceback.print_exc()

        return {
            "response_type": "text",

            "content":
                "求人解析中に内部エラーが発生しました。"
        }


# ===
# Future Expansion Notes
# ===

"""
将来的な拡張ポイント

1. Plugin Registry
--------------------------------------------------------
plugin_manager.load_plugins()

2. Multi Recruit Plugin
--------------------------------------------------------
indeed plugin
linkedin plugin

3. HTML Cleaner
--------------------------------------------------------
BeautifulSoup
Readability

4. Scam Detection
--------------------------------------------------------
危険求人検知

5. Salary Analyzer
--------------------------------------------------------
市場相場比較

6. Company Reputation API
--------------------------------------------------------
OpenWork連携

7. Skill Gap Analysis
--------------------------------------------------------
不足スキル推定

8. Resume Optimization
--------------------------------------------------------
履歴書自動最適化

9. Interview Simulator
--------------------------------------------------------
AI模擬面接

10. Plugin Sandbox
--------------------------------------------------------
plugin isolation runtime
"""

